"""STAGE 2: the same agent, using the API's native tool calling.

Compared with stage 1:
  - The API gets the tool definitions through `tools=`; no protocol in the prompt.
  - The model's tool calls arrive as structured `tool_use` blocks with an id,
    a name and already-parsed arguments. No JSON parsing on our side.
  - "Needs a tool?" is answered by `stop_reason == "tool_use"`.
  - The model can ask for several tools at once (parallel tool calls).

Still your job: validating arguments, executing tools, sending results back,
running the loop, and deciding when to stop.

Usage:
  py agent_native_tools.py "Which department has the most employees?"
  py agent_native_tools.py            (interactive)
  py agent_native_tools.py --quiet "..."
  py agent_native_tools.py --model llama3.2:3b-instruct-q5_K_M "..."   (any Ollama model, or claude-opus-5-5)
"""

import json
import sys

import agent_trace as trace
import llm
import settings
from guards import claim_correction, false_claim
from memory import estimate_tokens as llm_estimate
from run_record import RunRecord
from tools.registry import api_tool_definitions, execute, validate_args

MAX_STEPS = 8
SYSTEM = (
    "You are a helpful assistant for a company. Use the tools for facts and math rather than "
    "guessing. If a request cannot be done with the available tools, say so."
)


def run_agent(question: str, history: list | None = None) -> RunRecord:
    """history: earlier conversation turns (stage 6). None = a fresh conversation."""
    record = RunRecord(question=question, model=llm.model, stage=2)
    trace.step("MODEL", f"{llm.model} via {llm.provider()}", "dim")
    tools = api_tool_definitions()
    system = SYSTEM + (settings.PROMPT_RULES_TEXT if settings.PROMPT_RULES else "")
    messages = list(history or []) + [{"role": "user", "content": question}]
    record.messages = messages
    if history:
        trace.memory(len(history), llm_estimate(history))
    successful_tools: set[str] = set()
    guarded = False

    for step_number in range(1, MAX_STEPS + 1):
        # ── LLM ──────────────────────────────────────────────────────────────
        response = llm.call_llm(system, messages, tools=tools)
        trace.llm_call(step_number, response.usage)
        record.add_llm_call(response.usage)
        text = "".join(b.text for b in response.content if b.type == "text")
        trace.model_text(text)

        # ── Needs a tool? The API tells us through stop_reason. ──────────────
        if response.stop_reason == "end_turn":
            trace.decide(False)
            # Fix 5: don't let the answer claim an action no tool performed.
            claim = false_claim(text, successful_tools) if settings.CLAIM_GUARD else None
            if claim and not guarded:
                guarded = True
                record.guard_triggers += 1
                trace.step("GUARD", f"✗ answer claims '{claim}' but no tool did that", "bad")
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": claim_correction(claim)})
                continue
            trace.finish("stop_reason=end_turn")
            messages.append({"role": "assistant", "content": response.content})  # keep the answer in the history
            return record.finish("final", text)
        if response.stop_reason != "tool_use":
            # max_tokens, refusal, ...: we can't continue safely.
            trace.finish(f"stopped early: stop_reason={response.stop_reason}")
            return record.finish(response.stop_reason, text or f"[Stopped: {response.stop_reason}]")
        trace.decide(True)

        # Append the assistant turn exactly as received (tool_use blocks included).
        messages.append({"role": "assistant", "content": response.content})

        # ── Which tool? → validate → execute, for EVERY tool_use block ──────
        tool_results = []
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        for call in tool_calls:
            trace.select(call.name, call.input)
            errors = validate_args(call.name, call.input)
            trace.validate(errors)
            if errors:
                ok, result = False, "Invalid call: " + "; ".join(errors)
                record.add_tool_call(call.name, call.input, errors)
            else:
                ok, result, elapsed_ms = execute(call.name, call.input)
                trace.execute(ok, result, elapsed_ms)
                record.add_tool_call(call.name, call.input, [], ok, result)
                if ok:
                    successful_tools.add(call.name)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,  # ties this result to the model's request
                "content": json.dumps(result, default=str) if ok else str(result),
                "is_error": not ok,
            })

        # ── Return results: ALL of them in ONE user message ──────────────────
        messages.append({"role": "user", "content": tool_results})
        trace.result_to_llm(f"sent {len(tool_results)} tool_result block(s) in one message")

    trace.finish(f"hit MAX_STEPS={MAX_STEPS} without a final answer")
    messages.append({"role": "assistant", "content": "(no final answer)"})  # keep turns ending on the assistant
    return record.finish("max_steps", f"[Stopped: no final answer after {MAX_STEPS} steps]")


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
    print(f"Stage 2 agent (native tool_use) using {llm.model}. Empty line to quit.")
    while question := input("\nYou: ").strip():
        print("\nANSWER:", run_agent_answer(question))


if __name__ == "__main__":
    main()
