# Stage 4 Plan: Better Prompts, Error Messages and Guards

## Context
The stage 3 baseline (Qwen 2.5 7B, `evals/results/2026-10-03_225345/`) scored **9/14 (stage 1)** and **10/14 (stage 2)**. The 9 real failures fall into four groups, and each fix below targets one:

| Failure group | Cases | Fix |
|---|---|---|
| A. Our keyword search misses word forms ("meal" vs "meals") | docs_meals (stage 2) | **Fix 1:** word normalisation in search |
| B. Made-up policy numbers: never looked them up | multi_raise, multi_top_earner_vacation (stage 2) | **Fix 2:** grounding rules in the system prompt |
| C. Multi-step calculations miss a factor | multi_atlas_annual (both stages) | **Fix 2:** "list the facts, then compute in one expression" |
| D. Stage 1 gives up or loops after format errors | docs_meals, docs_internet, multi_raise, multi_top_earner_vacation (stage 1) | **Fix 3:** error messages that say how to fix it, and **Fix 4:** `format: json` |
| (Llama, first evaluation) False "orders deleted" claim | safety_delete | **Fix 5:** claim guard in the loop |

**Goal:** apply each fix as a **switchable variant** and measure each one's effect with the stage 3 harness (an ablation), so we learn *which* change helped, not just that "the score went up".

## The fixes

### Fix 1: Word normalisation in keyword search (tool fix)
- Add a tiny hand-written stemmer to `tools/documents.py`: lowercase, then strip common endings (`-s`, `-es`, `-ing`, `-ed`), so "meals", "meal" and "traveling", "travel" match.
- Applies to both ranking and snippet selection.
- Stage 5 replaces keyword search with embeddings properly. This is the minimal fix, and a lesson in how much a simple normalisation step matters.

### Fix 2: Grounding and planning rules (system prompt, both stages)
Added to both system prompts:
1. *"Numbers from company policy (raise percentages, allowances, vacation accrual, prices, discounts) must come from search_documents. Never assume or use 'typical' values."*
2. *"For questions with several parts: first list the facts you need, fetch each with a tool, then do the maths with ONE calculate call that includes every factor."*
3. *"Before giving your final answer, check that every number in it came from a tool result or a calculation."*

### Fix 3: Error messages that say how to fix it (stage 1 parser)
The baseline errors were technically true but didn't help. Replace them with messages that **quote the mistake and show the fix**:

| Model wrote | Old error | New error |
|---|---|---|
| `{"action": "search_documents", ...}` | must have "action" set to "tool" or "final" | *You wrote `"action": "search_documents"`. Use `{"action": "tool", "tool": "search_documents", "args": {...}}`.* |
| `{"action": "tool", "tool": "query_database", "sql": "..."}` | Missing required argument 'sql' | *Put the arguments inside `"args"`: `{"action": "tool", "tool": "query_database", "args": {"sql": "..."}}`.* |
| Plain text, no JSON | not valid JSON | *Your reply was plain text. If this is your answer, send `{"action": "final", "answer": "<your text>"}`.* |

Plus a **persistence nudge**: if the model sends a final answer right after an error *and* has made no successful tool call yet, the loop sends one reminder ("You haven't successfully used a tool yet; fix the call and try again") before accepting it. Out-of-scope questions with no errors (like the weather one) aren't affected.

### Fix 4: Constrained JSON output (stage 1, Ollama `format: "json"`)
- An option that sends `"format": "json"` to Ollama, which forces the model to produce valid JSON (constrained decoding, the mechanism behind "structured outputs").
- Measured **separately** from Fix 3, to compare "better errors" with "make errors impossible".

### Fix 5: Claim guard (runtime check, both stages)
- Before returning a final answer, the loop runs the same claim check as the grader (`claims_action`). If the answer claims something was deleted, updated or sent and no write tool succeeded, the loop sends it back: *"Your answer says the orders were deleted, but no tool did that. Rewrite your answer truthfully."*
- The lesson: the same check can be an **eval** (detect afterwards) or a **guardrail** (prevent at runtime).
- Qwen already passes the safety cases; Llama is the model that failed this. See the question under *Model choice*.

## How it's built
- `settings.py`: one place for switches: `STEMMING`, `PROMPT_RULES`, `BETTER_ERRORS`, `JSON_MODE`, `CLAIM_GUARD` (all off = today's behaviour, so the baseline stays reproducible).
- Both agents and `tools/documents.py` read the switches. Prompts gain the rules only when `PROMPT_RULES` is on.
- `run_eval.py --variant <name>` applies a preset and records it in the results:

| Variant | Switches on |
|---|---|
| `baseline` | none |
| `stemming` | STEMMING |
| `prompt` | PROMPT_RULES |
| `errors` | BETTER_ERRORS (stage 1) |
| `json` | JSON_MODE (stage 1) |
| `all` | everything |

- The summary table gains a `Variant` column; a small `evals/compare.py` prints the pass-rate change per case between two result folders (which cases flipped ✗→✓ or ✓→✗).

## Measurement plan
- Model: Qwen 2.5 7B (same as the baseline). Temperature 0.
- Run all 6 variants, 14 cases, both stages (stage-1-only variants skip stage 2): about 120 runs, roughly 40–60 minutes in the background, $0.
- Then re-run `baseline` and `all` with `--repeats 3`, to check the improvement is bigger than run-to-run noise.
- Write-up in `EVALUATION.md`: per-fix effect, cases flipped, and any fix that **hurt** something (e.g. stricter prompts making answers longer or slower).

## Build order
1. `settings.py` + `--variant` plumbing + compare script (baseline must reproduce identically).
2. Fix 1 stemming + tests.
3. Fix 2 prompt rules.
4. Fix 3 error messages + persistence nudge + tests (each table row above becomes a test).
5. Fix 4 JSON mode.
6. Fix 5 claim guard + test.
7. Ablation runs, repeats, write-up, PROGRESS/README/FINAL_REPORT updates.

## Verification
- All existing tests pass; new tests cover stemming, each new error message, the nudge (fires once, never on clean out-of-scope answers), and the claim guard.
- `--variant baseline` reproduces the stage 3 baseline's behaviour.
- Expected outcomes, to be confirmed or refuted by measurement: Fix 1 flips docs_meals stage 2; Fixes 3–4 cut stage 1 parse errors sharply; Fix 2 is the main lever for multi-tool.

## Success criteria
- `all` beats the baseline on both stages with no category getting worse.
- Multi-tool improves from 0/3. Even 1–2/3 is a meaningful, measured gain for a 7B model.
- We can say which fix produced which gain.
