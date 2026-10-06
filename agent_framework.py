"""STAGE 7: the same agent, built with a framework (LangChain v1 `create_agent` on LangGraph).

Same tools (our functions in tools/), same system prompt and stage 4 rules, same model
(through ChatOllama). Only the LOOP is the framework's. Compare with agent_native_tools.py:

  our hand-built piece            framework equivalent here
  ─────────────────────────────   ──────────────────────────────────────────────
  while loop + stop_reason        create_agent(): a graph with a model node and a tools node
  TOOLS registry + JSON Schema    @tool + type hints (schema inferred, bounds via pydantic Field)
  validate_args()                 pydantic validation of tool arguments (automatic)
  execute() never raises          ToolErrorMiddleware(on_error=...)  (opt-in! default: crash)
  MAX_STEPS                       ModelCallLimitMiddleware(run_limit=...)
  claim guard in the loop         @after_model middleware that jumps back to the model
  trace printer                   reconstructed from the final message list (or use streaming)

Usage:
  pip install -r requirements-framework.txt
  py agent_framework.py "Which department has the most employees?"
"""

import sys
from types import SimpleNamespace
from typing import Annotated

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolErrorMiddleware, after_model
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from pydantic import Field

import agent_trace as trace
import llm
import settings
from agent_native_tools import MAX_STEPS, SYSTEM
from guards import claim_correction, false_claim
from run_record import RunRecord
from tools import ToolError
from tools import calculator, database, documents
from tools.registry import TOOLS

ERROR_PREFIX = "Tool error: "
# When ModelCallLimitMiddleware stops the loop (exit_behavior="end") it ADDS a synthetic AIMessage with this
# text and no tool calls, which looks exactly like a final answer. We detect it so it's not mistaken for one.
LIMIT_MESSAGE_PREFIX = "Model call limits exceeded"


# ── Tools: thin wrappers around OUR functions; the framework infers the schema ──

@tool("calculate", description=TOOLS["calculate"]["description"])
def calculate_tool(expression: Annotated[str, Field(min_length=1, description="The arithmetic expression to evaluate.")]) -> dict:
    return calculator.calculate(expression)


@tool("search_documents", description=TOOLS["search_documents"]["description"])
def search_documents_tool(
    query: Annotated[str, Field(min_length=1, description="Keywords to search for.")],
    top_k: Annotated[int, Field(ge=1, le=10, description="How many documents to return (1-10).")] = 3,
) -> dict:
    return documents.search_documents(query, top_k)


@tool("query_database", description=TOOLS["query_database"]["description"])
def query_database_tool(sql: Annotated[str, Field(min_length=1, description="A single SQLite SELECT statement.")]) -> dict:
    return database.query_database(sql)


FRAMEWORK_TOOLS = [calculate_tool, search_documents_tool, query_database_tool]


# ── Middleware ───────────────────────────────────────────────────────────────

def on_tool_error(error: Exception, request=None):
    """Our ToolErrors go back to the model; anything else (a real bug) propagates.
    (Our hand-built execute() returns EVERY exception to the model instead.)"""
    if isinstance(error, ToolError):
        return ERROR_PREFIX + str(error)
    return None


def _successful_tools(messages) -> set[str]:
    return {m.name for m in messages if isinstance(m, ToolMessage) and m.status != "error"}


@after_model(can_jump_to=["model"])
def claim_guard(state, runtime):
    """Stage 4, Fix 5 as middleware: send back answers that claim actions no tool performed."""
    if not settings.CLAIM_GUARD:
        return None
    messages = state["messages"]
    last = messages[-1]
    already_guarded = any(isinstance(m, HumanMessage) and "no tool performed that action" in str(m.content)
                          for m in messages)
    if not isinstance(last, AIMessage) or last.tool_calls or already_guarded:
        return None
    claim = false_claim(str(last.content), _successful_tools(messages))
    if claim:
        return {"messages": [HumanMessage(claim_correction(claim))], "jump_to": "model"}
    return None


def build_agent(model=None):
    """model: a LangChain chat model; tests pass a fake one. Default: ChatOllama with the selected model."""
    model = model or ChatOllama(model=llm.model, temperature=0, num_ctx=llm.NUM_CTX, base_url=llm.OLLAMA_URL)
    system = SYSTEM + (settings.PROMPT_RULES_TEXT if settings.PROMPT_RULES else "")
    return create_agent(
        model,
        FRAMEWORK_TOOLS,
        system_prompt=system,
        middleware=[
            ToolErrorMiddleware(on_error=on_tool_error),
            ModelCallLimitMiddleware(run_limit=MAX_STEPS, exit_behavior="end"),
            claim_guard,
        ],
    )


# ── Run + fill a RunRecord so the stage 3 harness grades it like the others ───

def run_agent(question: str, history: list | None = None, model=None) -> RunRecord:
    if history:
        raise NotImplementedError("Memory (stage 6) isn't wired up for the framework agent.")
    if model is None and llm.provider() != "ollama":
        raise NotImplementedError("The framework agent is set up for Ollama models only.")
    record = RunRecord(question=question, model=llm.model, stage=3)
    trace.step("MODEL", f"{llm.model} via LangChain create_agent + ChatOllama", "dim")

    result = build_agent(model).invoke({"messages": [HumanMessage(question)]}, config={"recursion_limit": 100})
    messages = result["messages"]
    record.messages = messages

    calls_by_id = {}
    hit_limit = False
    for m in messages:
        if isinstance(m, AIMessage) and str(m.content).startswith(LIMIT_MESSAGE_PREFIX) and not m.usage_metadata:
            hit_limit = True  # framework-generated, not a model call
            continue
        if isinstance(m, AIMessage):
            usage = m.usage_metadata or {}
            record.add_llm_call(SimpleNamespace(input_tokens=usage.get("input_tokens", 0),
                                                output_tokens=usage.get("output_tokens", 0)))
            trace.llm_call(len(record.llm_calls), SimpleNamespace(input_tokens=usage.get("input_tokens", 0),
                                                                  output_tokens=usage.get("output_tokens", 0)))
            trace.model_text(str(m.content))
            for call in m.tool_calls:
                calls_by_id[call["id"]] = call
                trace.select(call["name"], call["args"])
        elif isinstance(m, ToolMessage):
            call = calls_by_id.get(m.tool_call_id, {"name": m.name, "args": {}})
            content = str(m.content)
            ok = m.status != "error"
            # An error that isn't one of our ToolErrors came from the framework's argument validation.
            invalid = not ok and not content.startswith(ERROR_PREFIX)
            record.add_tool_call(call["name"], call["args"], [content] if invalid else [], ok, content)
            trace.execute(ok, content, 0.0)
        elif isinstance(m, HumanMessage) and "no tool performed that action" in str(m.content):
            record.guard_triggers += 1
            trace.step("GUARD", "✗ answer claimed an action no tool performed", "bad")

    last = messages[-1]
    if not hit_limit and isinstance(last, AIMessage) and not last.tool_calls:
        trace.finish("framework finished: model gave a final answer")
        return record.finish("final", str(last.content))
    trace.finish(f"stopped by ModelCallLimitMiddleware (run_limit={MAX_STEPS})")
    return record.finish("max_steps", f"[Stopped: no final answer after {MAX_STEPS} model calls]")


def run_agent_answer(question: str) -> str:
    return run_agent(question).answer


def main() -> None:
    args = sys.argv[1:]
    if "--model" in args:
        i = args.index("--model")
        llm.set_model(args[i + 1])
        del args[i:i + 2]
    if "--quiet" in args:
        trace.ENABLED = False
        args.remove("--quiet")
    if args:
        print("\nANSWER:", run_agent_answer(" ".join(args)))
        return
    print(f"Stage 7 agent (LangChain create_agent) using {llm.model}. Empty line to quit.")
    while question := input("\nYou: ").strip():
        print("\nANSWER:", run_agent_answer(question))


if __name__ == "__main__":
    main()
