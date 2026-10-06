# Progress Log

Tracks the build of the hand-made tool-using agent. See [PLAN.md](PLAN.md) for the full plan.

## Status

| # | Step | Status |
|---|------|--------|
| 1 | Save plan + create progress log | ✅ Done |
| 2 | Sample data: docs + SQLite seed script | ✅ Done |
| 3 | Tools: calculate, search_documents, query_database | ✅ Done |
| 4 | Registry + hand-written argument validator | ✅ Done |
| 5 | Unit tests (no API key needed) | ✅ Done (18/18 passing) |
| 6 | Trace printer + `llm.py` API wrapper | ✅ Done |
| 7 | Stage 1 agent: hand-rolled JSON protocol | ✅ Done |
| 8 | Stage 2 agent: native tool_use | ✅ Done |
| 9 | README | ✅ Done |
| 10 | End-to-end runs (local Ollama: Qwen 2.5 7B + Llama 3.2 3B) | ✅ Done (Claude path not run: no key) |
| 11 | Evaluation + final report | ✅ Done (`EVALUATION.md`, `FINAL_REPORT.md`) |
| 12 | Stage 3: evaluation harness | 📝 Planned (`STAGE3_PLAN.md`), awaiting go-ahead |

## Log

### 2026-10-03
- Plan approved and saved to `PLAN.md`. Created the project folders.
- Wrote 6 sample policy docs in `data/docs/` and `data/seed_db.py` (5 departments, 19 employees, 60 orders, fixed random seed).
- Built the three tools: `calculate` (AST-based, no `eval`), `search_documents` (hand-written TF-IDF), `query_database` (SELECT-only check + read-only SQLite connection).
- Built `tools/registry.py`: the `TOOLS` registry, the hand-written `validate_args()`, and `execute()`, which never raises.
- `tests/test_tools.py`: 18 tests, all passing (`py -m unittest discover tests`). One test confirms the read-only connection blocks a `WITH ... DELETE` that gets past the SELECT check.
- Created `.venv` and installed `anthropic` 1.11.0 (`requirements.txt`).
- Wrote `agent_trace.py`, the labelled step printer. It was renamed from `trace.py` (as originally planned) because that name shadows Python's built-in `trace` module.
- Wrote `llm.py`: `claude-opus-5-5`, effort `low`, server-side refusal fallback enabled (beta endpoint), all in one function.
- Wrote `agent_text_protocol.py` (stage 1): the tool protocol lives in the system prompt as JSON, with parse-error and validation-error feedback and `MAX_STEPS=8`. Smoke test passed: the prompt builds, fenced JSON parses, and non-JSON replies produce a corrective error.
- Wrote `agent_native_tools.py` (stage 2): `tools=` from the registry, branches on `stop_reason`, all `tool_result` blocks returned in one user message, `is_error` on failures.
- Wrote `README.md` with the diagram, setup, a stage comparison table, sample questions and experiments.
- **Blocked:** no API credentials on this machine (`ANTHROPIC_API_KEY` unset, `ant` CLI not installed). End-to-end runs are pending.
- Ran Llama 3.2 3B (q5_K_M) on all 5 questions × 2 stages. Llama stopped being used after this; the user needed it for another setup.
- Verified the database after Llama claimed it had "deleted all orders from 2023": all 16 orders are still there.
- Wrote `EVALUATION.md`: Qwen 7/9, Llama 5/10. Built-in tool calling removed format errors but not reasoning errors; both models failed the multi-tool question; Llama falsely claimed a deletion in both stages. Corrected a draft error: Qwen stage 1 Q1 was counted but never run. Raw traces saved in `evals/raw/`.
- Wrote `FINAL_REPORT.md`: what we built, how, and what we learned.

## Next
- Stage 3 (evaluation harness) per `STAGE3_PLAN.md`, once approved. Add a `claims_action` check based on the Llama Q5 finding.

### Stage 3: evaluation harness
- Approved. The baseline uses Qwen only, because Llama is in use for another setup.
- Step 1 ✅: added `run_record.py` (`RunRecord`: answer, tool calls, LLM calls with tokens, parse/validation errors, stop reason, seconds). Both agents now return a RunRecord; the command line still prints just the answer.
- Step 2 ✅: `evals/graders.py` (number, contains_any/none, declines, tools_called, no_tools, claims_action, finished) and `evals/cases.json` (14 cases across calculator, documents, database, multi_tool and safety). `tests/test_graders.py`: 11 new tests, **29/29 passing**. They confirm the harness fails Qwen's made-up 5% salary answer (on both `number` and `tools_called`) and Llama's fake deletion (`claims_action`), passes Qwen's correct refusal, and recompute every expected answer from the real data.
- Step 3 ✅: `evals/run_eval.py` (`--models/--stages/--category/--cases/--repeats`). It asks Ollama whether a model supports tools (skipping stage 2 when it doesn't), writes results.jsonl as it goes plus summary.md, and records crashes as failures. Smoke test: 2 cases on Qwen stage 2, both passed.
- Step 4 ⏳: full baseline on Qwen (14 cases × 2 stages = 28 runs) running in the background. Runs take ~30s each because the user's Llama setup is sharing the GPU.
- Drafted plans for the next stages while the baseline runs: `STAGE5_PLAN.md` (RAG with nomic-embed-text: chunking, a hand-built vector index, keyword/semantic/hybrid search, a retrieval benchmark), `STAGE6_PLAN.md` (multi-turn memory: full/window/trim/summary strategies, tool_use/tool_result pairing, Ollama `num_ctx`), `STAGE7_PLAN.md` (LangGraph + ChatOllama rebuild, compared on the same harness). `STAGE4_PLAN.md` will be written from the baseline failures.
- Step 4 ✅: baseline on Qwen (28 runs, `evals/results/2026-10-03_225345/`). First score: 8/14 and 9/14.
- Grader audit: 2 failures were grader false negatives (correct refusals in unlisted wording). Widened the refusal phrases, added a test for each real example, and added `--regrade` (re-grade saved runs with no model calls). **Corrected baseline: stage 1 9/14, stage 2 10/14.**
- The 9 real failures: 1 tool bug (keyword search: "meal" ≠ "meals"), 2 made-up policy numbers, 2 multi-step calculation errors, and 4 stage 1 format/give-up failures. Multi-tool 0/6; calculator and database 12/12. Written up in `EVALUATION.md` (stage 3 section).
- Step 5 ✅: README "Evaluating" section. **Stage 3 complete.**
- Wrote `STAGE4_PLAN.md`: 5 switchable fixes, each targeting one failure group, measured by ablation. **Waiting for the user's approval before building.**

### Stage 4: prompts, error messages, guards
- Approved by the user, including a Llama 3.2 run for the claim guard (tell the user before and after).
- Step 1 ✅: `settings.py` (5 switches + variant presets; all off = baseline) and `guards.py` (claim check, now shared by the grader and the agents). `run_eval.py --variants ...` adds a Variant column; stage-1-only variants skip stage 2. `evals/compare.py` lists cases that flipped ✗→✓ / ✓→✗ between variants or runs.
- Steps 2–6 ✅: Fix 1 stemming (`tools/documents.py`), Fix 2 prompt rules (both agents), Fix 3 error messages that quote the mistake and show the fix, plus a one-time retry nudge (stage 1), Fix 4 `format: json` (`llm.py`, stage 1), Fix 5 claim guard (both agents).
- `tests/test_stage4.py`: 16 tests using a scripted fake LLM (no Ollama needed), covering each error-table row, nudge once-only/never on clean answers, JSON mode passthrough, and the guard replaying Llama's real false claim in both stages. **45/45 tests passing.** With all switches off, the 29 earlier tests are unchanged.
- Live smoke test (`all`, stage 1, docs_meals, a baseline failure): passed in 2 calls, 0 parse errors.
- Step 7 ⏳: Qwen ablation running: variants baseline, stemming, prompt, errors, json, all (~140 runs). Llama guard runs come after, and the user will be told before they start.
- Step 7 (Qwen ablation) ✅: 140 runs in `evals/results/2026-10-03_230935/`. Fresh baseline 9/14 and 10/14, with the same failing cases as stage 3 (reproducible at temperature 0). Prompt rules were the biggest lever (stage 2: 13/14, multi-tool 0/3 → 2/3); stemming fixed exactly docs_meals; JSON mode cut stage 1 parse errors from 16 to 3. `all` = stage 1 10/14, stage 2 13/14.
- **Regression found by the eval:** `all` stage 1 failed both safety cases. A trace showed the retry nudge overrode a correct refusal after a blocked DELETE and pushed the model to keep trying. Fix: the nudge now fires only after *format* (parse) errors, not after validation errors. Added a regression test plus `nudges` / `guard_triggers` counters in RunRecord. **46/46 tests passing.** Separate finding: JSON mode made Qwen call search_documents for the weather question (more tool use where none is needed).
- `compare.py` now re-grades saved runs with the current graders before comparing (an early "+1" was just the grader fix showing up).
- Next: Llama guard runs (waiting for the user's go-ahead), then re-run Qwen `errors` + `all` stage 1 to confirm the nudge fix.
- Llama guard runs started (user approved): llama3.2:3b-instruct-q5_K_M, safety category, baseline vs guard, both stages, repeats 2.
- Llama guard runs ✅ (`evals/results/2026-10-04_003712/`, 16 runs). Llama unloaded afterwards and the user was told. **Stage 2: the guard turned 2/2 false "deleted" claims into 2/2 truthful refusals** (guard fired once in each run). Stage 1: the guard never fired, because Llama's stage 1 failures weren't claims (it echoed a DELETE query, or returned an empty answer), and a guard can only catch what it checks for. scope_weather failed in every Llama run: it always calls a tool for the weather question.
- Re-running Qwen `errors` + `all` on stage 1 (28 runs) to confirm the nudge fix.
- Nudge fix round 2: the re-run (`2026-10-04_004726`) showed `all` stage 1 now passes safety_delete (stage 1 all: 11/14), but `errors` still failed it with a nudge (blocked DELETE → plain-text refusal = format error → nudge). Changed the rule to "nudge only if the model never made any tool call". Second regression test added; **47/47 tests passing**. Targeted re-run (8 runs): 0 nudges on safety_delete; weather and give-up cases behave as intended.
- Wrote the stage 4 section of `EVALUATION.md` (ablation table, nudge story, Llama guard results, lessons, limitations). **Stage 4 complete.** `--repeats 3` confirmation was not run (~2 h); noted as a limitation.
- Next: stage 5 (RAG). **Waiting for the user's approval** per the stage-approval rule.

### Overnight (user asleep; authorised 2026-10-04)
- The user asked for the 3-repeat check (baseline vs all, both stages, `--repeats 3`, 168 runs), then **authorised stage 5** to be built and evaluated without further approval. Results to be ready for the morning.
- 3-repeat check started.

### Stage 5: RAG (authorised overnight)
- Built `tools/chunking.py` (24 chunks: one per paragraph/bullet, prefixed with the doc title), `tools/embeddings.py` (Ollama /api/embed, nomic task prefixes), `tools/vector_index.py` (hand-written cosine similarity, a vector cache in `data/index.json` keyed by chunk hash), and semantic + hybrid (reciprocal rank fusion) modes in `search_documents` with the same interface. `settings.RETRIEVAL` plus variants `semantic`, `hybrid`, `all_hybrid`, `all_semantic`.
- Retrieval benchmark (`evals/run_retrieval_eval.py`, 22 queries, no chat model): answer line in top 3 — keyword 73%, keyword+stemming 77%, **semantic 95%**, hybrid 82%, hybrid+stemming 86%. On paraphrases, keyword finds the answer line 50% of the time and semantic 92%. **Hybrid did worse than semantic here**: keyword noise ("work" → Remote Work policy) pulled wrong chunks into the fusion. Nomic prefixes: better ranking (doc hit@1 86% → 95%) but one fewer answer line (PTO). Saved: `evals/results/retrieval_2026-10-04_013142.md`.
- Added 4 paraphrased documents cases to `evals/cases.json` (now 18). `tests/test_retrieval.py`: 8 tests (chunking, cosine, RRF, cache reuse with a fake embedder, same tool interface, variants, answers exist in docs). **55/55 passing.**
- Stage 5 harness run queued to start automatically after the 3-repeat check.
- 3-repeat check ✅ (`evals/results/2026-10-04_012024/`, 168 runs): baseline 27/42 and 30/42 (identical every repeat); all fixes 33/42 and 40/42; multi-tool stage 2 0/9 → 7/9. 54/56 case×variant cells gave the same result in every repeat. Nudge fix confirmed (safety 3/3); JSON-mode weather regression confirmed (0/3). Written up in `EVALUATION.md`.
- Stage 5 harness run started automatically.
- Stage 5 harness run ✅ (`evals/results/2026-10-04_022720/`, 100 runs, 0 crashes): stage 2 documents keyword 3/7 → semantic 7/7 (hybrid 7/7); stage 1 semantic alone 2/7 (failures were format give-ups with no search, not retrieval), stage 1 all fixes + semantic **9/10** (best stage 1 result). Remaining miss: a PTO chunk-boundary issue, predicted by the benchmark. Written up in `EVALUATION.md` (stage 5 section + recommended configuration). **Stage 5 complete.**
- Next: stages 6 (memory) and 7 (framework) are planned. **They need the user's approval** (authorisation covered only stage 5).

### Stage 6: conversation memory
- Approved by the user.
- **Llama token puzzle solved** (open since the first evaluation): Llama 3.2's Ollama chat template adds the tool definitions only when the *last* message is from the user (`if and $.Tools $last`). After a tool result the last message is a `tool` message, so from the 2nd call onward Llama can't see its tools. That explains the input-token drop (536 → 154) and probably part of Llama's weakness on multi-step questions. Found by reading `/api/show`, without running the model.
- Built `memory.py`: turn-based strategies none/full/window(2)/trim/summary, `check_history` (pairing + starts-with-question), `naive_last_messages` (breaks pairing on purpose), `run_conversation`. Agents accept `history=` and keep the final answer in the message list. `chat.py` provides interactive multi-turn chat (`/memory`, `/reset`). `llm.py` sets `num_ctx` explicitly (8192, the same as before) and warns near the limit; the trace shows a `[MEMORY]` line.
- 6 multi-turn cases (category `memory`): pronoun follow-ups, a correction, policy then maths, and a fact from turn 1 needed in turn 4 (built so `window` should forget it). `run_eval.py --memory ...`; conversation rows report whole-conversation tokens, including summary calls.
- `tests/test_memory.py`: 8 tests (strategies, pairing, summary trigger + cache, conversations with a fake LLM). **63/63 passing.** Live smoke test: "that department" resolved correctly ($105,333.33).
- Memory eval ✅ (`evals/results/2026-10-04_084809/`, 60 conversations, 0 crashes): none 2/12, full 10/12, window 8/12 (forgets the turn 1 fact), trim 10/12 (−9% tokens on the 4-turn case), summary 10/12 (but never triggered: identical to full). Low-trigger summary run (`2026-10-04_092346/`, 12): triggered on the 4-turn case, passed 2/2, history halved; the summary call cost ~1,180 tokens. Added a `SUMMARY_TRIGGER_TOKENS` env override.
- Finding: **memory carried a mistake forward.** mem_product_followup passed 2/2 with no memory and 0/8 with any memory (turn 1 took the price from the orders table; turn 2 trusted it and skipped the discount lookup).
- No context warnings (largest prompt 1,639 of 8,192). Long-term memory tool not built (optional; would change every eval's tool list).
- Wrote the stage 6 section of `EVALUATION.md`. **Stage 6 complete.** Stage 7 needs the user's approval.

### Stage 7: rebuild with a framework
- Approved by the user.
- Installed `requirements-framework.txt` (langchain 1.4.3, langgraph 1.2.12, langchain-ollama 1.1.0). Checked the APIs before writing code: `langgraph.prebuilt.create_react_agent` is **deprecated** in this version in favour of `langchain.agents.create_agent` (middleware-based), so the plan's LangGraph `create_react_agent` was swapped for `create_agent`.
- Built `agent_framework.py`: the same tools (thin `@tool` wrappers around our functions, schema inferred from type hints + pydantic bounds), the same system prompt/rules, ChatOllama, `ToolErrorMiddleware`, `ModelCallLimitMiddleware(run_limit=8)`, and the claim guard as `@after_model` middleware. A RunRecord adapter lets the harness grade it.
- Framework behaviours found while building: (1) **by default only argument-validation errors are caught; any other exception raised by a tool crashes the run** (`ToolErrorMiddleware` is opt-in); (2) `on_error` takes `(exception, request)`, which I first got wrong; (3) when the call limit is hit, the framework **adds a synthetic AI message "Model call limits exceeded…" that looks like a final answer**.
- `tests/test_framework.py`: 5 tests with a fake chat model (tool call + record, our ToolError, framework validation error, claim-guard middleware, call limit). Skipped if the framework isn't installed. **68/68 passing.**
- `run_eval.py`: `--agents text native framework` (stage 3 = framework; memory cases skipped for it). Head-to-head run started: native vs framework × baseline/all_semantic × 18 cases.
- Head-to-head ✅ (`evals/results/2026-10-04_103205/`, 72 runs, 0 crashes): hand-built 12/18 (baseline) and 16/18 (all_semantic); framework 12/18 and 16/18. Same failure modes; case-level differences are only in documents/multi-tool (known run-to-run variation). Code: ~319 lines hand-built vs ~127 framework (42 of them for the harness adapter); ~15 vs ~45 installed packages.
- Wrote `STAGE7_COMPARISON.md` (mapping table, sizes, what the framework gave/cost, verdict) and the stage 7 section in `EVALUATION.md`. **Stage 7 complete: all planned stages (1–7) done.**

### GitHub visuals (2026-10-04)
- Added `VISUAL_GUIDE.md`: a picture-first tour with 7 Mermaid diagrams (agent loop, architecture, stage journey, stage 2 message sequence, eval harness, stage 4 failure → fix map, RAG pipeline), 5 charts and a data table under each chart, plus the top 8 lessons.
- Added `docs/make_charts.py` (`requirements-docs.txt`: matplotlib): generates 5 charts as light **and** dark SVGs in `docs/images/`, chosen automatically on GitHub via `<picture>`. Colours come from the dataviz skill's validated colourblind-safe palette (first 3 slots only); Node wasn't available to re-run its validator. Each chart was previewed and fixed (rounded-bar geometry bug, a seam, a colour reused across panels).
- README: the ASCII loop was replaced with a "project at a glance" section (two Mermaid diagrams, the ablation chart, a results table) linking to the Visual Guide.
- Mermaid syntax was checked by script (quotes, brackets, no semicolons in the sequence diagram) but not rendered locally (no Node/mermaid-cli). Check it once in GitHub's preview after pushing.
