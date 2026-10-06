"""Compare variants (or two result folders) case by case: which cases flipped ✗→✓ or ✓→✗.

Examples:
  py evals/compare.py evals/results/<run>                       variants inside one run vs "baseline"
  py evals/compare.py evals/results/<run> --base baseline --other all
  py evals/compare.py evals/results/<old> evals/results/<new>   two runs (e.g. stage 3 baseline vs stage 4)

With --repeats, a case counts as passed in proportion (e.g. 2/3).
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from evals.graders import grade  # noqa: E402

CASES = {c["id"]: c for c in json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))}


def load(run_dir: Path) -> list[dict]:
    """Load saved runs and RE-GRADE them with the current graders, so runs graded
    by an older grader version are compared fairly (apples to apples)."""
    rows = [json.loads(line) for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    for r in rows:
        record = SimpleNamespace(answer=r["answer"], tool_calls=r["tool_calls"], stop=r["stop"])
        r["passed"], r["checks"] = grade(record, CASES[r["case"]]["checks"])
    return rows


def pass_rates(rows: list[dict]) -> dict:
    """(model, stage, case) -> fraction of runs passed."""
    buckets = defaultdict(list)
    for r in rows:
        buckets[(r["model"], r["stage"], r["case"])].append(r["passed"])
    return {k: sum(v) / len(v) for k, v in buckets.items()}


def compare(base_rows: list[dict], other_rows: list[dict], base_name: str, other_name: str) -> list[str]:
    base, other = pass_rates(base_rows), pass_rates(other_rows)
    lines = []
    for model, stage in sorted({(m, s) for m, s, _ in other}):
        keys = sorted(k for k in other if k[:2] == (model, stage) and k in base)
        if not keys:
            continue
        b_total, o_total = sum(base[k] for k in keys), sum(other[k] for k in keys)
        lines.append(f"\n{model} · stage {stage}: {base_name} {b_total:g}/{len(keys)} → {other_name} {o_total:g}/{len(keys)}"
                     f"  ({o_total - b_total:+g})")
        for k in keys:
            if other[k] != base[k]:
                arrow = "✓ fixed " if other[k] > base[k] else "✗ broke "
                lines.append(f"   {arrow} {k[2]:<28} {base[k]:.2g} → {other[k]:.2g}")
    return lines


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", type=Path, help="one run folder (compare variants) or two (compare runs)")
    parser.add_argument("--base", default="baseline")
    parser.add_argument("--other", nargs="+", help="variants to compare against --base (default: all others)")
    args = parser.parse_args()

    if len(args.runs) == 2:
        for line in compare(load(args.runs[0]), load(args.runs[1]), args.runs[0].name, args.runs[1].name):
            print(line)
        return

    rows = load(args.runs[0])
    by_variant = defaultdict(list)
    for r in rows:
        by_variant[r.get("variant", "baseline")].append(r)
    if args.base not in by_variant:
        sys.exit(f"No '{args.base}' runs in {args.runs[0]}")
    for variant in args.other or [v for v in by_variant if v != args.base]:
        print(f"\n=== {variant} vs {args.base} ===")
        for line in compare(by_variant[args.base], by_variant[variant], args.base, variant):
            print(line)


if __name__ == "__main__":
    main()
