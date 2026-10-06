# Plan: Hand-built tool-using agent (no framework)

## Context
You want to learn how agents work at the mechanical level by building one from scratch, with no agent framework and no SDK tool runner. The agent has three tools: `calculate()`, `search_documents()` and `query_database()`. Every step of the loop should be visible and should match this diagram:

```
LLM → needs a tool? → which tool? → validate args → execute → return result → LLM → continue / finish
```

Decisions made:
- **LLM:** Claude API (`claude-opus-5-5`). The `anthropic` Python SDK is used only to send the HTTP request; you write the loop yourself.
- **How the model asks for a tool:** two stages. In stage 1 you design the protocol yourself: the prompt asks for JSON and you parse it. In stage 2 you switch to the API's native `tool_use` / `tool_result` blocks. Both stages share the same tools and validator, so you can compare them directly.
- **Data:** bundled sample data, meaning a few small markdown docs plus a SQLite database.

The project folder is empty at the start. Python 3.13 runs through the Windows `py` launcher.

## File layout
```
Tool Use/
  PLAN.md                   copy of this plan
  PROGRESS.md               progress log, updated after every completed step
  README.md                 the loop diagram, setup steps, how to run each stage
  requirements.txt          anthropic
  data/
    docs/*.md               5–6 short company docs (vacation, expenses, remote work, onboarding, product FAQ)
    seed_db.py              builds data/company.db: departments, employees, orders tables
  tools/
    calculator.py           calculate(expression)
    documents.py            search_documents(query, top_k=3)
    database.py             query_database(sql)
    registry.py             TOOLS registry + validate_args()
  agent_trace.py            prints each loop step, labelled like the diagram
  llm.py                    one function call_claude(...): the only place the API is called
  agent_text_protocol.py    STAGE 1: hand-rolled JSON protocol
  agent_native_tools.py     STAGE 2: native tool_use blocks
  tests/test_tools.py       unittest tests for the tools and the validator (no API key needed)
```

## The pieces

### 1. Tools (`tools/`): plain Python functions that know nothing about LLMs
- **calculate(expression: str)**: a safe evaluator that walks Python's AST. It allows only numbers and `+ - * / // % **`, unary minus, parentheses, and a small whitelist of functions (`sqrt, round, abs, min, max`). It never calls `eval()`. That is a lesson of its own: model output is untrusted input.
- **search_documents(query: str, top_k: int)**: lowercases and tokenizes the query and the docs, scores each doc by term frequency × inverse document frequency (TF-IDF, about 20 lines written by hand), and returns the top matches as `{doc, score, snippet}`. Using no vector database keeps the "retrieval" step easy to see.
- **query_database(sql: str)**: opens SQLite **read-only** (`file:company.db?mode=ro` URI), accepts only a single `SELECT` statement, caps results at 50 rows, and returns the column names and rows. Two layers of defence: the validator rejects non-SELECT statements, and the read-only connection blocks writes even if something slips past the validator.
- Each tool returns a JSON-serialisable result or raises `ToolError`. The loop turns a `ToolError` into an error result for the model; the program does not crash.

### 2. Registry + validation (`tools/registry.py`): the "which tool?" and "validate args" boxes
- `TOOLS = {name: {"fn": ..., "description": ..., "input_schema": {...}}}`. Each schema is plain JSON Schema. The same dict produces both the stage 1 prompt text and the stage 2 `tools=` parameter.
- `validate_args(name, args) -> list[str]` is a validator you write yourself. It checks that the tool exists, that required keys are present, that there are no unknown keys, the types (string/integer), and the bounds (`1 ≤ top_k ≤ 10`, non-empty strings). It returns readable error messages, which go back to the model so it can correct itself. It uses no `jsonschema` library, so you can see exactly what validation means.
- `execute(name, args)` looks up the function and calls it, catching `ToolError` and unexpected exceptions.

### 3. Trace (`agent_trace.py`)
Prints each step with a tag that matches the diagram, so a run reads like the flowchart:
`[LLM call #2]` → `[DECIDE] needs tool: yes` → `[SELECT] query_database` → `[VALIDATE] ok` / `[VALIDATE] ✗ unknown key 'query'` → `[EXECUTE] 3 rows in 2ms` → `[RESULT → LLM]` → `[FINISH] stop_reason=end_turn`.
A `--quiet` flag turns it off.

### 4. `llm.py`: one thin wrapper
`call_claude(system, messages, tools=None)` calls the API with `model="claude-opus-5-5"`, `max_tokens=16000` and `output_config={"effort": "low"}`. Effort is set explicitly because Opus 5.5 defaults to medium, and low is fast and cheap enough for a learning tool; you can change it later. It also enables the server-side refusal fallback (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`). That setting is the recommended default for this model, it is isolated in this one file, and you can remove it if you prefer. Credentials come from `ANTHROPIC_API_KEY` or an `ant auth login` profile.

### 5. STAGE 1: `agent_text_protocol.py` (you design the protocol)
- The system prompt is generated from `TOOLS`. It lists each tool's name, description and argument schema, then says: *reply with exactly one JSON object, either `{"action":"tool","tool":"<name>","args":{...}}` or `{"action":"final","answer":"..."}`*.
- The loop, written as one readable function of about 60 lines with comments keyed to the diagram:
  1. **LLM**: call with no `tools` parameter, then read the text reply.
  2. **Parse**: strip any code fences and run `json.loads`. If the reply doesn't parse, send a user message ("Your reply wasn't valid JSON: …") and loop again. This shows the main weakness of a protocol you write yourself.
  3. **Needs a tool?** `action == "final"` means finish.
  4. **Which tool / validate**: `validate_args`. If validation fails, send the errors back as a user message.
  5. **Execute** the tool, then send the result back as a user message: `TOOL_RESULT calculate: {...}`.
  6. Repeat, up to `MAX_STEPS = 8`; stop with a clear message when the limit is hit.
- Append the assistant's full reply to the history each time and never edit earlier turns. The history stays append-only, which is what the API expects.

### 6. STAGE 2: `agent_native_tools.py` (the API's tool calling)
- Pass `tools=[{name, description, input_schema}]` from the registry.
- The loop branches on `response.stop_reason`:
  - `tool_use`: append `response.content` as the assistant turn, unchanged. Then for **each** `tool_use` block: validate, execute, and build `{"type":"tool_result","tool_use_id":block.id,"content":json.dumps(result)}`. Failures get `"is_error": True`. **All** results go back in **one** user message, so parallel tool calls work.
  - `end_turn`: print the final text and finish.
  - `max_tokens` / `refusal`: report what happened and stop.
- Same `MAX_STEPS` limit and the same trace output. In the README, compare the two stages: what the API now does for you (structured calls, ids, parallel calls, no JSON parsing) and what is still your job (validation, execution, the loop, error feedback, stopping).

### 7. README
Covers the diagram, setup (`py -m venv .venv`, `.venv\Scripts\activate`, `pip install -r requirements.txt`, `py data/seed_db.py`), the sample questions below, and a "things to try" list: break a tool on purpose, remove validation and watch what happens, raise effort, add a fourth tool.

## Verification
1. `py -m unittest discover tests`: the calculator handles arithmetic and rejects `__import__`; search ranks the vacation doc first for "vacation days"; the database query returns rows and rejects `DELETE`/`DROP` and multiple statements; the validator catches missing, extra and wrongly typed arguments.
2. `py data/seed_db.py`, then run **both** agents on each of these and check the traces:
   - Single tool: "What is 17.5% of 2,340?" → calculate
   - Single tool: "How many vacation days do new employees get?" → search_documents
   - Single tool: "Which department has the most employees?" → query_database
   - Multiple tools: "What's the average Engineering salary, and what would it be after the 4% raise described in the compensation policy?" → query_database + search_documents + calculate
   - Error recovery: "Delete all orders from 2023" → validator/read-only rejection appears in the trace, and the model explains it can't do that
3. Confirm stage 2 sends all parallel `tool_result` blocks in one user message, and that both stages stop cleanly at `MAX_STEPS`.
