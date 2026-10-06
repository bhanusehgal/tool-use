# Stage 7 Plan: Rebuild with a Framework and Compare

> **Status: ✅ built and evaluated (2026-10-04).** Results: `STAGE7_COMPARISON.md`. Deviation: LangGraph's `create_react_agent` is deprecated in the installed version, so LangChain's `create_agent` (middleware-based, on LangGraph) was used; `--agents` was added alongside `--stages`, which was kept.

## Context
Stages 1–6 built every piece of an agent by hand: the loop, tool selection, validation, error feedback, stopping, memory and retrieval. Now we rebuild the same agent with a framework, to see **what it gives you, what it hides, and whether it's actually better** on our own eval.

**Goal:** a framework-based agent that uses the **same tools** and runs through the **same stage 3 harness**, plus a side-by-side write-up.

## Framework choice

| Option | Cost | Notes |
|---|---|---|
| **LangGraph** (`create_react_agent`) + `ChatOllama` *(recommended)* | Free, local | The most widely used agent framework; runs on your Ollama models; directly comparable to our results |
| Anthropic SDK tool runner (`client.beta.messages.tool_runner` + `@beta_tool`) | Paid (Claude API) | The closest match to stage 2 (same message format); worth doing if you get an API key |
| smolagents / pydantic-ai | Free | Alternatives; mention only |

The plan uses **LangGraph + ChatOllama**. Exact APIs are checked against the installed version when building, since framework APIs change often.

## What gets built

```
agent_framework.py     LangGraph agent wrapping our existing tools; returns a RunRecord
requirements-framework.txt   langgraph, langchain-ollama (kept separate from the core project)
evals/run_eval.py      third agent variant: --agents text native framework
STAGE7_COMPARISON.md   the write-up
```

### 1. Same tools, framework loop
- Wrap `calculate`, `search_documents` and `query_database` as framework tools, **calling our existing functions**. The tools and data don't change; only the loop does.
- Map our `MAX_STEPS = 8` to the framework's step limit (`recursion_limit`).
- Fill a `RunRecord` from the framework's message history, so the harness grades it exactly like the others.

### 2. Harness: agent variants instead of "stages"
- `run_eval.py --stages 1 2` becomes `--agents text native framework` (with `--stages` kept as an alias). It avoids confusing "stage 2 agent" with "project stage 7".

### 3. The comparison (`STAGE7_COMPARISON.md`)

**What maps to what:**

| Our hand-built piece | Framework equivalent | Visible? |
|---|---|---|
| `while` loop + `stop_reason` check | graph with a model node and a tool node, with conditional edges | partly |
| `TOOLS` registry + JSON Schema | tool decorator, schema inferred from type hints and docstring | yes |
| `validate_args()` | schema validation (pydantic) | error format differs |
| `execute()` never raising | tool error handling setting | config |
| tool_result with `is_error` | ToolMessage | yes |
| `MAX_STEPS` | `recursion_limit` (counts graph steps, not LLM calls) | subtle |
| trace printer | callbacks / streaming events / LangSmith | needs setup |
| memory strategies (stage 6) | checkpointer + message trimming helpers | yes |

**Measured, from the same harness:** pass rate per category, LLM calls, tokens, time, and lines of code. Ours: loop + validation + translation. Theirs: wrapper + config.

**Judgement:** what was easier, what became harder to debug, and what the framework does by default that we chose differently (e.g. how errors are phrased back to the model, which stage 1/2 showed matters a lot).

## Build order
1. Separate venv extras: `pip install -r requirements-framework.txt`; confirm the APIs against the installed version.
2. `agent_framework.py` on Qwen; one manual run with a trace.
3. RunRecord adapter + harness `--agents` support.
4. Full harness run: text vs native vs framework on the same model.
5. `STAGE7_COMPARISON.md` + `FINAL_REPORT.md` update.

## Verification
- The framework agent passes the single-tool cases on Qwen, like native stage 2.
- The harness runs all three agents in one command; the summary table shows them side by side.
- The comparison's numbers come from the eval run, not impressions.

## Risks
- Framework APIs drift between versions. Pin versions in `requirements-framework.txt`.
- Framework system prompts and error messages differ from ours, so differences in pass rate may come from the prompt rather than the framework. The comparison notes this and, where possible, gives both the same system prompt.
