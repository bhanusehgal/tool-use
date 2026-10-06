# Final Report: A Tool-Using Agent Built by Hand

**Period:** 2026-10-03 to 2026-10-04 · **Scope:** stages 1–7 (complete) · **Total API spend:** $0 (about 690 local model runs/conversations)

## 1. What we set out to do
Learn how an AI agent works **at the mechanical level** by building one from scratch, with no agent framework and no SDK helper that runs the loop. The agent has three tools, `calculate()`, `search_documents()` and `query_database()`, and every run should visibly follow this loop:

```
LLM → needs a tool? → which tool? → validate arguments → execute → return result → LLM → continue / finish
```

## 2. What we built

| Part | File(s) | What it does |
|---|---|---|
| Sample data | `data/docs/*.md`, `data/seed_db.py` | 6 company policy docs; SQLite DB with 5 departments, 19 employees, 60 orders (fixed seed) |
| Tools | `tools/calculator.py`, `documents.py`, `database.py` | Safe math (AST walking, no `eval`), TF-IDF keyword search, SELECT-only SQL on a read-only connection |
| Registry + validator | `tools/registry.py` | Tool definitions (JSON Schema), a hand-written argument validator, an `execute()` that never crashes |
| Trace | `agent_trace.py` | Prints every loop step with diagram labels: `[LLM] → [DECIDE] → [SELECT] → [VALIDATE] → [EXECUTE] → [RESULT → LLM] → [FINISH]` |
| Model access | `llm.py` | One function for every model: **Ollama** (local, free, default) or **Claude** (paid API), with format translation |
| Stage 1 agent | `agent_text_protocol.py` | Tool format designed by us: the model replies in JSON we defined, and we parse it |
| Stage 2 agent | `agent_native_tools.py` | Built-in tool calling: structured `tool_use` / `tool_result` messages |
| Tests | `tests/test_tools.py`, `test_graders.py`, `test_stage4.py`, `test_retrieval.py`, `test_memory.py`, `test_framework.py` | 68 offline tests (tools, validator, graders, fixes; a scripted fake LLM stands in for the model) |
| Eval harness (stage 3) | `run_record.py`, `evals/` | 14 cases with known answers; graders for answer *and* process; runner, re-grader, variant comparison |
| Fixes (stage 4) | `settings.py`, `guards.py` | 5 switchable fixes: stemming, prompt rules, better errors + nudge, JSON mode, claim guard |
| Retrieval (stage 5) | `tools/chunking.py`, `embeddings.py`, `vector_index.py` | Chunks + nomic-embed-text + hand-written cosine index; keyword / semantic / hybrid modes; a retrieval benchmark |
| Memory (stage 6) | `memory.py`, `chat.py` | Multi-turn conversations; none / full / window / trim / summary strategies; history integrity checks |
| Framework (stage 7) | `agent_framework.py`, `requirements-framework.txt` | The same agent on LangChain `create_agent` + ChatOllama with middleware; compared on the same harness |
| Docs | `README.md`, `PLAN.md`, `PROGRESS.md`, `EVALUATION.md`, `STAGE3_PLAN.md` | How to run it, the design, the build log, results, next stage |

## 3. How we did it

### Step by step
1. **Planned first** (`PLAN.md`): chose the Claude API for the model, two stages for the tool format, bundled sample data, and Python with no framework.
2. **Built the tools as plain Python functions** that know nothing about LLMs, and tested them offline.
3. **Wrote the "which tool?" and "validate" steps by hand.** The registry is a dict; validation is about 40 lines checking required, unknown, types and bounds, plus a SELECT-only rule for SQL. No `jsonschema` library, so nothing is hidden.
4. **Wrote stage 1:** the system prompt describes the tools and a JSON reply format (`{"action":"tool",...}` / `{"action":"final",...}`). Our code parses the reply, validates it, executes the tool, and sends the result back as a text message. Bad JSON or bad arguments become error messages the model can correct.
5. **Wrote stage 2:** the same loop, but tools go in the API's `tools=` parameter and the model returns structured calls. "Needs a tool?" becomes `stop_reason == "tool_use"`; results go back as `tool_result` blocks matched by id, all of them in one message.
6. **Avoided API costs:** after seeing the Claude API is pay-per-use, we switched the default to **local models via Ollama** (`qwen2.5:7b-instruct`). `llm.py` translates between Ollama's message format and the one the agents use, so neither agent loop changed.
7. **Evaluated** 2 local models × 2 stages × 5 questions and graded every trace against correct answers computed from the data (`EVALUATION.md`).
8. **Stage 3, evaluation harness:** agents return a structured `RunRecord`; 14 test cases are graded automatically on the answer *and* the process (which tools succeeded, false claims). Expected answers are recomputed from the data by tests. Baseline on Qwen: 9/14 (stage 1), 10/14 (stage 2).
9. **Stage 4, fixes measured one at a time:** five switchable fixes, each targeting a baseline failure group, run as separate variants (an ablation) plus a Llama run for the claim guard. Confirmed with 3 repeats: stage 2 with all fixes **40/42 (13.3/14)**, from 30/42.
10. **Stage 5, retrieval with embeddings:** split the docs into chunks, embedded them locally, searched by cosine similarity, and compared keyword, semantic and hybrid search, first on a 22-query retrieval benchmark, then end to end. Stage 2 document questions: **3/7 → 7/7**.
11. **Stage 6, conversation memory:** agents take a history; five strategies decide what to send back each turn; six multi-turn conversations measure accuracy vs tokens. No memory 2/12 → full or trimmed memory **10/12**.
12. **Stage 7, framework rebuild:** the same tools, prompt and retrieval on LangChain's `create_agent`, run through the same harness. **Same score as the hand-built loop (12/18 → 16/18)** with ~60% less code (`STAGE7_COMPARISON.md`).

### Design choices worth remembering

| Choice | Why |
|---|---|
| No framework, no tool runner | Every step of the loop is our own code and shows up in the output |
| Tools know nothing about LLMs | Easy to test offline; the same tools serve both agents and any model |
| One registry, two formats | The same `TOOLS` dict produces stage 1's prompt text and stage 2's `tools=` list |
| `execute()` never raises | A failing tool becomes an error the model can read, not a crash |
| Two layers on the database | Validator (SELECT only) + read-only connection. A test shows layer 2 catches what gets past layer 1 |
| `MAX_STEPS = 8` | A stuck model can't loop forever (and it did happen) |
| Append-only history | The model sees exactly what happened; nothing is rewritten |
| `--model` switch, translation in `llm.py` | The same agents run on free local models or Claude |

## 4. Results

### Stages 1–2 (manual grading, 5 questions)

| | Qwen 2.5 7B | Llama 3.2 3B |
|---|---|---|
| Stage 1 (our JSON format) | 3/4 | 2/5 |
| Stage 2 (built-in tool calling) | 4/5 | 3/5 |
| Multi-tool question | ❌ both stages | ❌ both stages |
| "Delete all orders" | declined ✅ | **falsely claimed it deleted them** (database verified unchanged) |

### Stages 3–4 (automatic harness, 14 cases, Qwen 2.5 7B)

| | Stage 1 (our JSON format) | Stage 2 (built-in tool calling) |
|---|---|---|
| Baseline | 9/14 | 10/14 |
| + stemming | 10/14 | 11/14 |
| + prompt rules | 11/14 | 13/14 |
| + all fixes (3 repeats) | 11/14 | **13.3/14** |
| Multi-tool questions | 0/3 → 1/3 | 0/3 → 2.3/3 |

Claim guard on Llama 3.2 3B, stage 2: false "orders deleted" claims went from 2/2 to 0/2.

### Stage 5 (retrieval)

| | Keyword | Semantic | Hybrid |
|---|---|---|---|
| Benchmark: answer line in top 3 (22 queries) | 73% | **95%** | 82% |
| Benchmark: paraphrased queries, right doc first | 67% | **92%** | 83% |
| Agent, stage 2, document questions | 3/7 | **7/7** | 7/7 |

Best stage 1 result of the project: all stage 4 fixes + semantic retrieval = 9/10 on the document and multi-tool cases.

### Stage 6 (memory, 6 conversations × 2)

| none | full | window (2 turns) | trim | summary |
|---|---|---|---|---|
| 2/12 | 10/12 | 8/12 | **10/12** (−9% tokens) | 10/12 |

### Stage 7 (framework, 18 single-turn cases)

| | Hand-built | Framework |
|---|---|---|
| No fixes | 12/18 | 12/18 |
| All fixes + semantic | 16/18 | 16/18 |

Full breakdown, traces and per-case analysis: `EVALUATION.md`.

## 5. What we learned

### About how agents work
1. **An agent is a loop around a stateless model.** The model doesn't "use" tools: it *writes a request*, and our code decides whether and how to run it. Every bit of memory is the message list we send back each turn.
2. **Tool calling is just a message format.** Stage 1 proved you can build it from a prompt and a JSON parser. Stage 2's built-in tool calling is the same idea with the structure guaranteed. Ollama and Claude spell the format differently, and `llm.py` translates in about 60 lines.
3. **The API does less than it seems.** Built-in tool calling gives you structured calls, ids and parallel calls. Validation, execution, error handling, the loop and when to stop are **still your code**.
4. **Model output is untrusted input.** The calculator walks the syntax tree instead of calling `eval`; SQL is checked *and* run read-only. The tests include a code-injection attempt and a `WITH … DELETE` that gets past the first check.

### About making agents reliable
5. **Built-in tool calling fixes format, not reasoning.** Stage 2 had zero format errors and 33–67% fewer LLM calls, but both models still got the multi-tool question wrong.
6. **Error messages are prompts.** "Missing required argument 'sql'" sent Llama into a six-turn loop because the real problem was *where* it put `sql`. An error has to say how to fix it.
7. **Valid ≠ correct.** Qwen's wrong salary answer passed every validation: it filtered by job title instead of department and invented a 5% raise without reading the policy. You have to check the *process* (which tools were used), not just the arguments.
8. **Guard claims as well as actions.** The safety layers stopped the deletion, but Llama still told the user "all orders have been deleted". An agent can be safe in what it does and dishonest in what it says.
9. **Small models do fine on simple calls and struggle with multi-step work.** On single-tool questions, 3B matched 7B. Following a format, recovering from errors, multi-step reasoning and honesty are where size showed.
10. **Reading traces by eye doesn't scale.** The trace made every failure *visible*, but spotting them took careful reading and checking numbers. That's why stage 3 is an automated evaluation harness.

### About evaluating and improving agents (stages 3–4)
11. **Check the checker.** The first automatic score was too low: 2 "failures" were correct refusals the grader didn't recognise. Keeping running and grading separate (`--regrade`) made the fix free.
12. **Measure fixes one at a time.** The ablation showed *which* fix helped: prompt rules were the biggest lever (+3), stemming fixed exactly one case, JSON mode removed format errors but caused unneeded tool calls.
13. **Telling the model where facts come from works.** "Policy numbers must come from search_documents" turned made-up raises into looked-up ones. Multi-tool went from 0/3 to 2/3.
14. **Fixes can break things, including safety.** The retry nudge overrode correct refusals of a DELETE. Only the safety cases in the eval caught it, and it took two rounds to find the right signal (did the model *attempt* a call?).
15. **A guard only catches what it checks for.** The claim guard fixed every false "deleted" claim in stage 2, and did nothing for Llama's other stage 1 failures, which weren't claims.
16. **Temperature 0 makes small evals usable.** The 3-repeat check gave the same result for 54 of 56 case/variant combinations; only the hardest multi-tool questions varied (2/3). Small evals are trustworthy for stable cases, not for borderline ones.

### About retrieval (stage 5)
17. **Embeddings fix paraphrases, and paraphrases are where users live.** On the docs' own words every method was perfect; on paraphrases, keyword found the answer half the time and semantic 11 times out of 12.
18. **"Best practice" isn't automatically best.** Hybrid search is the usual recommendation, but here it was worse than semantic alone, because keyword noise polluted the fusion. Measure on your own data.
19. **Fixes stack in layers.** In stage 1, better retrieval did nothing on its own: the agent was giving up before searching. Only after the stage 4 fixes made it call the tool reliably did retrieval pay off (9/10).
20. **Chunk boundaries decide what the model sees.** The one remaining miss had the right document but the wrong chunk (the PTO mention without the number). The model then fell back on assuming, despite the prompt rule.

### About memory (stage 6)
21. **An LLM has no memory; history is the memory.** Follow-ups like "that department" went from 0/10 to 10/10 by sending earlier turns back.
22. **Cut history on turn boundaries.** A `tool_use` must stay with its `tool_result`; cutting by message count breaks the conversation.
23. **Memory carries mistakes forward.** A wrong price from turn 1 was trusted in turn 2, which skipped the lookup that would have fixed it (2/2 without memory, 0/8 with).
24. **Short conversations don't need clever memory.** System prompt and tool definitions dominated the cost; trim saved 9%, and summary only paid off once there were several turns to compress.
25. **Read the model's template.** Llama 3.2's template hides the tool list after the first tool result. That explained a token puzzle from the very first evaluation, without running anything.

### About frameworks (stage 7)
26. **The loop isn't what limits quality.** A 90-line hand-written loop and LangChain's `create_agent` scored identically with the same tools, prompt, retrieval and model.
27. **Frameworks have defaults you need to know.** Tool exceptions crash the run unless you opt in to error handling; hitting the call limit inserts a fake final answer. Building the loop by hand first made both easy to spot.
28. **Check the installed version, not memory.** The planned API (`create_react_agent`) was already deprecated; reading the installed code avoided building on it.

### About the process
- **Plan, then build in small tested steps.** Tools were tested before any LLM was involved, so every failure in the runs was the model's behaviour, not a tool bug.
- **Local models make experimenting free.** Every run in this project cost $0, so failing was cheap.
- **Keep a progress log.** `PROGRESS.md` recorded each step, including a mistake in the evaluation's first draft (a run counted that hadn't happened), which was caught and corrected.

## 6. Known limitations
- Stages 1–2 were graded by hand. Stages 3–4 are graded automatically but mostly with single runs per variant, and the planned `--repeats 3` confirmation wasn't run. Treat single-case flips with caution.
- Retrieval is tuned on six short documents; chunking (one bullet = one chunk) needs re-testing on longer ones. Stage 5 agent results are single runs.
- No memory across questions; each run starts fresh.
- The Claude path is written but **has not been run** (no API key on this machine).

## 7. What's next

| Stage | Focus | Status |
|---|---|---|
| 3 | Evaluation harness | ✅ Done |
| 4 | Prompts, error messages, guards (ablation) | ✅ Done |
| 5 | Real retrieval (RAG) with your local `nomic-embed-text` embeddings | ✅ Done |
| 6 | Conversation memory | ✅ Done |
| 7 | Rebuild with a framework and compare | ✅ Done |

## 8. How to run everything
```powershell
.venv\Scripts\activate
py data/seed_db.py
py -m unittest discover tests                              # offline, 55 tests
py evals/run_retrieval_eval.py                             # retrieval benchmark (stage 5)
py evals/run_eval.py --variants baseline all              # eval harness (stage 3) + fixes (stage 4)
py agent_text_protocol.py "Which department has the most employees?"
py agent_native_tools.py  "Which department has the most employees?"
py agent_native_tools.py --model llama3.2:3b-instruct-q5_K_M "..."
```
