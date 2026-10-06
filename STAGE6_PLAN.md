# Stage 6 Plan: Conversation Memory

> **Status: ✅ built and evaluated (2026-10-04).** Results: `EVALUATION.md` → Stage 6. Deviations: added a `none` control strategy; the optional long-term memory tool was not built.

## Context
Every question currently starts from an empty message list. The agent can't handle follow-ups like *"Which department has the most employees?" → "And what's their average salary?"* An LLM has no memory of its own: **memory is whatever you choose to send back each turn.** The message list grows with every tool call and result, so any real agent eventually has to decide what to keep.

**Goal:** add multi-turn conversations, then build and measure memory strategies by hand: what each costs in tokens, and what it breaks.

## What gets built

```
memory.py             strategies for trimming/compacting the message history
agent_*.py            run_agent(question, history=None) -> RunRecord with the updated history
chat.py               interactive multi-turn chat for either agent, with a --memory flag
evals/cases.json      new multi-turn cases ("turns": [...])
evals/run_eval.py     supports multi-turn cases; reports tokens per turn
```

### 1. Multi-turn conversations
- `run_agent()` takes an optional `history` and returns the full updated message list alongside the RunRecord.
- `chat.py` keeps the history between questions: `py chat.py --agent native --memory window`.
- The trace shows history size every turn: `[MEMORY] 14 messages · ~3,200 tokens`.

### 2. Memory strategies (`memory.py`), each a function `history -> history`

| Strategy | What it does | Trade-off |
|---|---|---|
| `full` | Keep everything | Simple and exact; tokens grow without limit |
| `window` | Keep the last N **turns** | Cheap; forgets early facts |
| `trim_tool_results` | Replace old, bulky tool results with a short stub (`[result trimmed: 50 rows]`) | Keeps the conversation flow; loses raw data |
| `summary` | When history gets too big, ask the model to summarise older turns into one message | Remembers the gist; costs an extra LLM call and can lose detail |

**The key mechanical lesson:** you can't cut the history anywhere you like. A `tool_use` must stay paired with its `tool_result` (stage 2), and the list must still start with a user message. Cutting between a call and its result produces an API error, or for Ollama, silent confusion. Tests cover this explicitly.

### 3. Context limits, made visible
- Ollama has a context window per model (`num_ctx`). When a prompt is longer, **Ollama silently drops the beginning**. Set `num_ctx` explicitly in `llm.py` and show a warning when the history approaches it.
- Use this to investigate the open question from `EVALUATION.md`: why Llama's input-token count *drops* after a tool result.

### 4. Multi-turn eval cases
New case format, graded on the final turn:
```json
{"id": "followup_salary", "category": "memory",
 "turns": ["Which department has the most employees?",
           "What is the average salary in that department?"],
 "checks": [{"type": "number", "value": 105333.33, "tolerance": 1}]}
```
About 6 cases: pronoun follow-ups ("that department", "them"), a fact from turn 1 needed in turn 4 (catches `window` forgetting), and a correction ("Actually, I meant Sales").
`run_eval.py --memory full window summary` compares pass rate **and** tokens per strategy.

### 5. Optional: long-term memory
A `remember(fact)` / `recall(query)` tool pair backed by a small JSON file, so the agent can store facts across sessions ("my team is Support"). This shows the difference between conversation memory (context) and stored memory (a tool).

## Build order
1. `history` in/out for both agents + `chat.py` (with `full` memory).
2. `memory.py` strategies + tests (especially pairing integrity).
3. `num_ctx` setting + context warning; resolve the Llama token question.
4. Multi-turn cases + harness support; compare strategies (pass rate vs tokens).
5. Optional long-term memory tool.

## Verification
- Unit tests: every strategy keeps tool_use/tool_result pairs together and starts with a user turn; `window` keeps exactly N turns; `trim_tool_results` never touches the latest turn.
- Live: a 4-turn chat on Qwen answers the follow-ups correctly with `full` memory.
- Harness: `window` with a small N fails the "fact from turn 1" case, and `full`/`summary` pass. A strategy's weakness is demonstrated, not just described.
