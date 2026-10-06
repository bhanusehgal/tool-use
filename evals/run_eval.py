"""Run the test cases against models and stages, grade every run, write results.

Examples (from the project folder):
  py evals/run_eval.py
  py evals/run_eval.py --models qwen2.5:7b-instruct llama3.2:3b-instruct-q5_K_M
  py evals/run_eval.py --stages 1 --models mistral:7b-instruct-q4_K_M
  py evals/run_eval.py --category multi_tool --repeats 3
  py evals/run_eval.py --cases calc_percent safety_delete
  py evals/run_eval.py --regrade evals/results/<timestamp>   (re-grade saved runs, no model calls)
  py evals/run_eval.py --variants baseline stemming prompt all   (stage 4 ablation, see settings.py)
  py evals/run_eval.py --category memory --memory full window trim summary   (stage 6 multi-turn)

Output: evals/results/<timestamp>/results.jsonl (every run, written as it goes)
        evals/results/<timestamp>/summary.md   (the table)
"""

import argparse
import json
import sys
import traceback
from types import SimpleNamespace
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import agent_native_tools  # noqa: E402
import agent_framework  # noqa: E402  (stage 7; needs requirements-framework.txt)
import agent_text_protocol  # noqa: E402
import agent_trace  # noqa: E402
import llm  # noqa: E402
import memory  # noqa: E402
import settings  # noqa: E402
from evals.graders import grade  # noqa: E402
from run_record import RunRecord  # noqa: E402

CASES_PATH = ROOT / "evals" / "cases.json"
RESULTS_DIR = ROOT / "evals" / "results"
AGENTS = {1: agent_text_protocol, 2: agent_native_tools, 3: agent_framework}
AGENT_NAMES = {"text": 1, "native": 2, "framework": 3}  # --agents names for the stage numbers
STAGE_LABELS = {1: "1 (text)", 2: "2 (native)", 3: "3 (framework)"}
CATEGORIES = ["calculator", "documents", "database", "multi_tool", "safety", "memory"]


def supports_tools(model: str) -> bool:
    """Ask Ollama whether a model has the 'tools' capability (stage 2 needs it)."""
    if model.startswith("claude"):
        return True
    req = urllib.request.Request(f"{llm.OLLAMA_URL}/api/show", data=json.dumps({"model": model}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return "tools" in json.load(resp).get("capabilities", [])
    except Exception:
        return True  # unknown: try it, and a failure is recorded as a crash


def run_one(model: str, stage: int, case: dict, variant: str = "baseline", memory_strategy: str = "") -> dict:
    llm.set_model(model)
    settings.apply_variant(variant)
    turns_info = None
    try:
        if "turns" in case:  # stage 6: a multi-turn conversation, graded on the final turn
            memory.SUMMARY_TOKENS["input"] = memory.SUMMARY_TOKENS["output"] = 0
            records = memory.run_conversation(AGENTS[stage], case["turns"], memory_strategy or "full")
            record = records[-1]
            turns_info = [{"question": r.question, "answer": r.answer, "history_tokens": r.history_tokens,
                           "input_tokens": r.input_tokens, "output_tokens": r.output_tokens} for r in records]
        else:
            record = AGENTS[stage].run_agent(case["question"])
    except BaseException as e:  # includes SystemExit raised by llm.py on Ollama errors
        if isinstance(e, KeyboardInterrupt):
            raise
        record = RunRecord(question=case.get("question") or case["turns"][-1], model=model, stage=stage)
        record.finish("crash", f"[Crash: {type(e).__name__}: {e}]")
        record_error = traceback.format_exc(limit=3)
    else:
        record_error = None

    passed, checks = grade(record, case["checks"])
    row = {"case": case["id"], "category": case["category"], "variant": variant, "switches": settings.active(),
           "passed": passed, "checks": checks, **record.to_dict()}
    if turns_info:
        # For conversations, the token columns show the WHOLE conversation's cost (every turn + any
        # summary calls), since that is what a memory strategy changes.
        row["turns"] = turns_info
        row["final_turn_input_tokens"] = row["input_tokens"]
        row["input_tokens"] = sum(t["input_tokens"] for t in turns_info) + memory.SUMMARY_TOKENS["input"]
        row["output_tokens"] = sum(t["output_tokens"] for t in turns_info) + memory.SUMMARY_TOKENS["output"]
        row["summary_tokens"] = dict(memory.SUMMARY_TOKENS)
    row["memory"] = memory_strategy
    if record_error:
        row["error"] = record_error
    return row


def summarise(rows: list[dict], skipped: list[str]) -> str:
    groups = defaultdict(list)
    for r in rows:
        groups[(r["model"], r.get("variant", "baseline"), r.get("memory") or "–", r["stage"])].append(r)

    lines = [f"# Eval summary ({datetime.now():%Y-%m-%d %H:%M})", ""]
    header = ["Model", "Variant", "Memory", "Stage", "Pass"] + [c.replace("_", " ").title() for c in CATEGORIES] + \
             ["Avg LLM calls", "Parse err", "Val err", "Max steps", "Avg time", "Avg tokens in/out"]
    lines += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    order = {v: i for i, v in enumerate(settings.VARIANTS)}
    mem_order = {m: i for i, m in enumerate(["–"] + memory.STRATEGIES)}
    for (model, variant, mem, stage), rs in sorted(
            groups.items(), key=lambda kv: (kv[0][0], order.get(kv[0][1], 99), mem_order.get(kv[0][2], 99), kv[0][3])):
        n = len(rs)
        cells = [model, variant, mem, STAGE_LABELS.get(stage, str(stage)), f"**{sum(r['passed'] for r in rs)}/{n}**"]
        for cat in CATEGORIES:
            cat_rs = [r for r in rs if r["category"] == cat]
            cells.append(f"{sum(r['passed'] for r in cat_rs)}/{len(cat_rs)}" if cat_rs else "–")
        cells += [
            f"{sum(len(r['llm_calls']) for r in rs) / n:.1f}",
            str(sum(r["parse_errors"] for r in rs)),
            str(sum(r["validation_errors"] for r in rs)),
            str(sum(r["stop"] == "max_steps" for r in rs)),
            f"{sum(r['seconds'] for r in rs) / n:.1f}s",
            f"{sum(r['input_tokens'] for r in rs) // n} / {sum(r['output_tokens'] for r in rs) // n}",
        ]
        lines.append("| " + " | ".join(cells) + " |")

    if skipped:
        lines += ["", "**Skipped (n/a):** " + "; ".join(skipped)]

    failures = [r for r in rows if not r["passed"]]
    lines += ["", f"## Failures ({len(failures)})", ""]
    for r in failures:
        why = "; ".join(f"{c['type']}: {c['detail']}" for c in r["checks"] if not c["passed"])
        answer = r["answer"].replace("\n", " ")
        mem = f" · memory={r['memory']}" if r.get("memory") else ""
        lines.append(f"- **{r['model']} · {r.get('variant', 'baseline')}{mem} · stage {r['stage']} · {r['case']}**: {why}  \n"
                     f"  answer: _{answer[:220]}{'…' if len(answer) > 220 else ''}_")
    return "\n".join(lines) + "\n"


def regrade(run_dir: Path) -> None:
    """Re-grade saved runs with the current graders and cases. Running and grading are separate,
    so a grader fix doesn't need the (slow) model runs to be repeated."""
    cases = {c["id"]: c for c in json.loads(CASES_PATH.read_text(encoding="utf-8"))}
    rows = []
    for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        record = SimpleNamespace(answer=row["answer"], tool_calls=row["tool_calls"], stop=row["stop"])
        row["passed"], row["checks"] = grade(record, cases[row["case"]]["checks"])
        rows.append(row)
    summary = summarise(rows, []).replace("# Eval summary", "# Eval summary (re-graded)", 1)
    (run_dir / "summary_regraded.md").write_text(summary, encoding="utf-8")
    print(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=[llm.DEFAULT_MODEL])
    parser.add_argument("--stages", nargs="+", type=int, default=[1, 2], choices=[1, 2, 3])
    parser.add_argument("--agents", nargs="+", choices=list(AGENT_NAMES),
                        help="same as --stages, by name: text=1, native=2, framework=3")
    parser.add_argument("--category", nargs="+", choices=CATEGORIES)
    parser.add_argument("--cases", nargs="+", help="run only these case ids")
    parser.add_argument("--repeats", type=int, default=1, help="run each case N times (consistency)")
    parser.add_argument("--regrade", type=Path, help="re-grade a saved results folder instead of running")
    parser.add_argument("--variants", nargs="+", default=["baseline"], choices=list(settings.VARIANTS),
                        help="stage 4 fix presets to compare (see settings.py)")
    parser.add_argument("--memory", nargs="+", default=["full"], choices=memory.STRATEGIES,
                        help="stage 6 memory strategies for multi-turn cases (single-turn cases ignore it)")
    args = parser.parse_args()
    if args.regrade:
        return regrade(args.regrade)
    if args.agents:
        args.stages = [AGENT_NAMES[a] for a in args.agents]

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if args.category:
        cases = [c for c in cases if c["category"] in args.category]
    if args.cases:
        cases = [c for c in cases if c["id"] in args.cases]

    agent_trace.ENABLED = False  # no step-by-step printing during evals
    out_dir = RESULTS_DIR / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_dir.mkdir(parents=True)
    results_file = out_dir / "results.jsonl"

    plan, skipped = [], []
    for model in args.models:
        for variant in args.variants:
            for stage in args.stages:
                if stage != 1 and variant in settings.STAGE1_ONLY:
                    continue  # this fix only changes stage 1; stage 2 would just repeat the baseline
                if stage != 1 and not supports_tools(model):
                    skipped.append(f"{model} stage {stage} (no tool support in Ollama)")
                    continue
                for case in cases:
                    if stage == 3 and "turns" in case:
                        continue  # memory isn't wired up for the framework agent
                    strategies = args.memory if "turns" in case else [""]
                    plan += [(model, stage, case, variant, m) for m in strategies for _ in range(args.repeats)]

    skipped = sorted(set(skipped))
    print(f"Running {len(plan)} runs → {out_dir.relative_to(ROOT)}")
    for s in skipped:
        print(f"  skipped: {s}")

    rows = []
    with results_file.open("w", encoding="utf-8") as f:
        for i, (model, stage, case, variant, mem) in enumerate(plan, 1):
            row = run_one(model, stage, case, variant, mem)
            rows.append(row)
            f.write(json.dumps(row, default=str) + "\n")
            f.flush()
            mark = "✓" if row["passed"] else "✗"
            print(f"[{i}/{len(plan)}] {model} {variant:<9} {mem or '-':<7} stage{stage} {case['id']:<28} {mark} "
                  f"{row['seconds']:.1f}s", flush=True)

    summary = summarise(rows, skipped)
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    print("\n" + summary)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
