# Stage 7: Hand-built Agent vs Framework

**Date:** 2026-10-04 · **Framework:** LangChain 1.4.3 `create_agent` (on LangGraph 1.2.12) + `langchain-ollama` 1.1.0 · **Model:** Qwen 2.5 7B (Ollama) · **Cost:** $0
**Results:** `evals/results/2026-10-04_103205/` (72 runs: 18 single-turn cases × 2 agents × 2 variants)

## What was compared
- **Hand-built:** `agent_native_tools.py` (stage 2: our own loop, validator, error handling, Ollama client).
- **Framework:** `agent_framework.py`, using **the same tool functions**, the same system prompt and stage 4 rules, the same retrieval (stage 5), the same model and temperature. Only the loop, validation and error plumbing are the framework's.

## Results

| | Hand-built | Framework |
|---|---|---|
| **No fixes** (`baseline`) | **12/18** | **12/18** |
| **All fixes + semantic retrieval** (`all_semantic`) | **16/18** | **16/18** |
| Calculator / Database / Safety (both variants) | 6/6 · 6/6 · 4/4 | 6/6 · 6/6 · 4/4 |
| Documents (baseline → all_semantic) | 3/7 → 6/7 | 4/7 → 7/7 |
| Multi-tool (baseline → all_semantic) | 1/3 → 2/3 | 0/3 → 1/3 |
| Avg model calls | 2.4 | 2.4–2.5 |
| Avg input tokens per question | 1,513 → 1,958 | 1,692 → 1,909 |

**Same score, same failure modes.** Both got the Atlas question wrong the same way (`50 × 12 × 0.85 = $510`, forgetting the $12 seat price) and both invented policy numbers on the multi-tool questions. The case-level differences are all in documents and multi-tool cases, which the stage 4 repeat check showed vary between runs; they cancel out in the totals. Time per run isn't compared: the two agents ran interleaved while other Ollama models shared the GPU.

**Conclusion: the loop isn't what limits quality.** Once tools, prompt, retrieval and model are the same, a 90-line hand-written loop and a production framework behave the same. Everything that moved the score in this project (prompt rules, stemming, semantic retrieval, memory) lives *outside* the loop.

## What maps to what

| Our hand-built piece | Framework equivalent | Notes |
|---|---|---|
| `while` loop + `stop_reason` check | `create_agent()`: a LangGraph graph with a model node and a tools node | Same idea: the model node decides, the tools node runs, edges loop back |
| `TOOLS` dict + hand-written JSON Schema | `@tool` + type hints; the schema is inferred | Bounds via `Annotated[int, Field(ge=1, le=10)]` |
| `validate_args()` (~40 lines) | pydantic validation, automatic | Error text: *"top_k: Input should be less than or equal to 10. Please fix the error and try again."* Clearer than ours, and it tells the model to retry |
| `execute()` never raises | `ToolErrorMiddleware(on_error=...)` | **Opt-in.** By default only *argument-validation* errors are returned to the model; any other exception from a tool **crashes the run** |
| `MAX_STEPS = 8` | `ModelCallLimitMiddleware(run_limit=8)` | When hit, it **adds a synthetic AI message** "Model call limits exceeded: run limit (8/8)" that looks like a final answer |
| claim guard inside the loop (~10 lines) | `@after_model` middleware that returns `jump_to: "model"` (~15 lines) | Clean hook point; same logic |
| `agent_trace.py` (live, every step) | Reconstructed from the final message list, or streaming/callbacks/LangSmith | Needed a 42-line adapter to get a RunRecord for grading |
| `llm.py` Ollama translation (~60 lines) | `ChatOllama` | Handled for us |
| memory strategies (stage 6) | checkpointer + `SummarizationMiddleware` / `ContextEditingMiddleware` | Not wired up here |

## Size (lines of code, excluding comments, docstrings, blank lines)

| Hand-built | Lines | Framework | Lines |
|---|---|---|---|
| Loop (`agent_native_tools.py`) | 94 | `agent_framework.py` total | 127 |
| Validation + execution (`registry.py`) | 46 | · tool wrappers | 9 |
| Tool definitions (`TOOLS` dict) | 54 | · middleware + `build_agent` | 32 |
| Model client + format translation (`llm.py`, includes Claude) | 125 | · RunRecord adapter + trace (only for our harness) | 42 |
| **Total** | **~319** | **Total** | **~127** (reuses our tool descriptions and system prompt) |

**Dependencies:** the core project needs only `anthropic` (~15 installed packages); the framework adds `langchain`, `langgraph` and `langchain-ollama` (~45 packages in total).

## What the framework gave us
- **Less code to write and maintain:** about 60% less, mostly by dropping our validator and our Ollama message translation.
- **Better default validation messages**, which tell the model what to fix; that mattered a lot in stage 1.
- **A middleware ecosystem** we didn't use but could switch on: retries, human-in-the-loop, PII redaction, summarisation, model fallback, tool-call limits.
- **Model portability:** swap `ChatOllama` for another provider's chat model with one line.

## What it cost us / what to watch for
1. **Hidden defaults that differ from ours.** A tool exception crashes the run unless you opt in to `ToolErrorMiddleware`, and the call limit returns a fake "answer". Both are easy to miss if you haven't built the loop yourself.
2. **API churn.** The plan named LangGraph's `create_react_agent`; in the installed version it's **deprecated** in favour of `langchain.agents.create_agent`. The middleware callback signature (`on_error(exception, request)`) was also not what I assumed. I had to read the installed code to get it right.
3. **Less visibility by default.** Our trace prints each step as it happens; with the framework I rebuilt it afterwards from the message list (or you set up streaming/LangSmith).
4. **More dependencies:** about 30 extra packages for one agent loop.

## Verdict
- **For learning and for small, fixed agents:** the hand-built loop is short, transparent, and every behaviour is a choice you made.
- **For production agents:** a framework is worth it for the middleware, integrations and maintained plumbing. Because we built the loop by hand first, **every framework default was recognisable**, and the two that would have bitten us (tool exceptions crashing, the synthetic limit message) were spotted during building, not in production.
- **Either way, quality comes from outside the loop.** Same tools, prompt, retrieval and model gave the same score.

## Limitations
- Single runs (72). Totals match exactly; individual multi-tool cases vary between runs anyway.
- Memory (stage 6) wasn't wired into the framework agent; the multi-turn cases were skipped for it.
- Only the Ollama path was tested; the Claude path in `llm.py` remains untested (no API key).
