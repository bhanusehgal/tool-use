"""STAGE 1: an agent with a tool protocol you design yourself.

The model is NOT given the API's `tools` parameter. Instead, the system prompt
describes the tools in plain text and asks the model to reply with a JSON
object. Our code parses that JSON, decides what to do, and sends the tool's
result back as an ordinary user message.

This is roughly how tool use worked before APIs supported it natively, and it
shows every step the API later automates for you.

Usage:
  py agent_text_protocol.py "How many vacation days do new employees get?"
  py agent_text_protocol.py            (interactive: asks for questions)
  py agent_text_protocol.py --quiet "..."   (final answer only, no trace)
  py agent_text_protocol.py --model llama3.2:3b-instruct-q5_K_M "..."   (any Ollama model, or claude-opus-5-5)
"""

import json
import re
import sys

import agent_trace as trace
import llm
import settings
from guards import claim_correction, false_claim
from memory import estimate_tokens as llm_estimate
from run_record import RunRecord
from tools.registry import TOOLS, execute, validate_args

MAX_STEPS = 8


def build_system_prompt() -> str:
    tool_lines = []
    for name, t in TOOLS.items():
        tool_lines.append(f"- {name}: {t['description']}\n  arguments (JSON Schema): {json.dumps(t['input_schema'])}")
    return (
        "You are a helpful assistant for a company. You can use tools to answer questions.\n\n"
        "TOOLS:\n" + "\n".join(tool_lines) + "\n\n"
        "PROTOCOL - every reply must be exactly one JSON object and nothing else:\n"
        '  To use a tool:   {"action": "tool", "tool": "<tool name>", "args": {<arguments>}}\n'
        '  To finish:       {"action": "final", "answer": "<your answer to the user>"}\n'
        "Call one tool at a time. After each tool call you will receive a message starting with "
        "TOOL_RESULT or TOOL_ERROR. Use tools for facts and math rather than guessing. "
        "If a request cannot be done with these tools, say so in a final answer."
    ) + (settings.PROMPT_RULES_TEXT if settings.PROMPT_RULES else "")


def parse_reply(text: str) -> tuple[dict | None, str | None]:
    """Turn the model's text into a dict. Returns (parsed, error_message)."""
    cleaned = text.strip()
    # Models sometimes wrap JSON in ```json fences even when told not to.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        if settings.BETTER_ERRORS:
            return None, explain_bad_json(cleaned, e)
        return None, f"Your reply was not valid JSON ({e.msg}). Reply with exactly one JSON object."
    if settings.BETTER_ERRORS:
        problem = explain_bad_shape(parsed)
        return (None, problem) if problem else (parsed, None)
    if not isinstance(parsed, dict) or parsed.get("action") not in ("tool", "final"):
        return None, 'Your reply must be a JSON object with "action" set to "tool" or "final".'
    return parsed, None


# -- Stage 4, Fix 3: error messages that quote the mistake and show the fix --

TOOL_EXAMPLE = '{"action": "tool", "tool": "<tool name>", "args": {...}}'
FINAL_EXAMPLE = '{"action": "final", "answer": "<your answer>"}'


def explain_bad_json(text: str, error: json.JSONDecodeError) -> str:
    if "{" not in text:
        return (f"Your reply was plain text, not JSON. If this is your answer, send exactly: {FINAL_EXAMPLE}. "
                f"To use a tool, send: {TOOL_EXAMPLE}")
    before = text[: text.index("{")].strip()
    if before:
        return (f"Your reply had extra text before the JSON ('{before[:40]}'). "
                "Send ONLY one JSON object, starting with { and ending with }.")
    return (f"Your JSON is invalid ({error.msg} at position {error.pos}). Send ONE complete JSON object, "
            f"e.g. {TOOL_EXAMPLE}")


def explain_bad_shape(parsed) -> str | None:
    if not isinstance(parsed, dict):
        return f"Send one JSON object, not a {type(parsed).__name__}. Example: {TOOL_EXAMPLE}"
    action = parsed.get("action")
    if action in TOOLS:
        args = parsed.get("args", {k: v for k, v in parsed.items() if k not in ("action", "tool")})
        fixed = json.dumps({"action": "tool", "tool": action, "args": args})
        return f'You wrote "action": "{action}". "action" must be "tool" or "final". Send: {fixed}'
    if action not in ("tool", "final"):
        return (f'"action" must be "tool" or "final", you wrote {json.dumps(action)}. '
                f"Examples: {TOOL_EXAMPLE} or {FINAL_EXAMPLE}")
    if action == "tool" and not isinstance(parsed.get("args"), dict):
        stray = {k: v for k, v in parsed.items() if k not in ("action", "tool", "args")}
        fixed = json.dumps({"action": "tool", "tool": parsed.get("tool"), "args": stray})
        return f'Put the tool arguments inside "args". Send: {fixed}'
    if action == "final" and "answer" not in parsed:
        return f'A final reply needs an "answer" field: {FINAL_EXAMPLE}'
    return None


def run_agent(question: str, history: list | None = None) -> RunRecord:
    """history: earlier conversation turns (stage 6). None = a fresh conversation."""
    record = RunRecord(question=question, model=llm.model, stage=1)
    trace.step("MODEL", f"{llm.model} via {llm.provider()}", "dim")
    system = build_system_prompt()
    messages = list(history or []) + [{"role": "user", "content": question}]
    record.messages = messages
    if history:
        trace.memory(len(history), llm_estimate(history))
    successful_tools: set[str] = set()
    last_was_format_error = nudged = guarded = False

    for step_number in range(1, MAX_STEPS + 1):
        # ── LLM ──────────────────────────────────────────────────────────────
        response = llm.call_llm(system, messages, json_mode=settings.JSON_MODE)  # note: no `tools` parameter
        trace.llm_call(step_number, response.usage)
        record.add_llm_call(response.usage)
        if response.stop_reason in ("max_tokens", "refusal"):
            trace.finish(f"stopped early: stop_reason={response.stop_reason}")
            return record.finish(response.stop_reason, f"[Stopped: {response.stop_reason}]")

        # The reply can include thinking blocks; our protocol lives in the text.
        text = "".join(b.text for b in response.content if b.type == "text")
        trace.model_text(text)
        # Append the full reply unchanged. The history is append-only.
        messages.append({"role": "assistant", "content": response.content})

        # ── Parse our protocol ───────────────────────────────────────────────
        reply, parse_error = parse_reply(text)
        if parse_error:
            trace.step("PARSE", "✗ " + parse_error, "bad")
            record.parse_errors += 1
            messages.append({"role": "user", "content": f"TOOL_ERROR: {parse_error}"})
            trace.result_to_llm("sent the parse error back")
            last_was_format_error = True
            continue

        # ── Needs a tool? ────────────────────────────────────────────────────
        needs_tool = reply["action"] == "tool"
        trace.decide(needs_tool)
        if not needs_tool:
            answer = str(reply.get("answer", ""))
            # Fix 3: don't accept "I couldn't find it" straight after a format error if the model never
            # managed to make a single tool call. If it DID make a call that was blocked (e.g. a DELETE),
            # refusing is the right answer: nudging there pushed the model to keep trying the forbidden action.
            # (Found by the stage 4 eval, in two rounds: see EVALUATION.md.)
            if settings.BETTER_ERRORS and last_was_format_error and not record.tool_calls and not nudged:
                nudged = True
                record.nudges += 1
                trace.step("NUDGE", "final answer right after an error, with no successful tool call yet", "bad")
                messages.append({"role": "user", "content": "TOOL_ERROR: You haven't successfully used a tool yet. "
                                 "Fix the call and try again before answering."})
                continue
            # Fix 5: don't let the answer claim an action no tool performed.
            claim = false_claim(answer, successful_tools) if settings.CLAIM_GUARD else None
            if claim and not guarded:
                guarded = True
                record.guard_triggers += 1
                trace.step("GUARD", f"✗ answer claims '{claim}' but no tool did that", "bad")
                messages.append({"role": "user", "content": "TOOL_ERROR: " + claim_correction(claim)})
                continue
            trace.finish("model gave a final answer")
            return record.finish("final", answer)

        # ── Which tool? + validate arguments ─────────────────────────────────
        name, args = reply.get("tool"), reply.get("args", {})
        trace.select(name, args)
        errors = validate_args(name, args)
        trace.validate(errors)
        if errors:
            record.add_tool_call(name, args, errors)
            messages.append({"role": "user", "content": "TOOL_ERROR: invalid call: " + "; ".join(errors)})
            trace.result_to_llm("sent validation errors back")
            last_was_format_error = False
            continue

        # ── Execute ──────────────────────────────────────────────────────────
        ok, result, elapsed_ms = execute(name, args)
        trace.execute(ok, result, elapsed_ms)
        record.add_tool_call(name, args, [], ok, result)
        last_was_format_error = False
        if ok:
            successful_tools.add(name)

        # ── Return result to the LLM ─────────────────────────────────────────
        if ok:
            messages.append({"role": "user", "content": f"TOOL_RESULT {name}: {json.dumps(result, default=str)}"})
        else:
            messages.append({"role": "user", "content": f"TOOL_ERROR {name}: {result}"})
        trace.result_to_llm(f"sent {name} {'result' if ok else 'error'} back")

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
    print(f"Stage 1 agent (hand-rolled JSON protocol) using {llm.model}. Empty line to quit.")
    while question := input("\nYou: ").strip():
        print("\nANSWER:", run_agent_answer(question))


if __name__ == "__main__":
    main()
