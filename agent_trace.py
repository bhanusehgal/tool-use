"""Prints each step of the agent loop, labelled like the diagram:

  LLM -> needs a tool? -> which tool? -> validate -> execute -> result -> LLM -> finish
"""

import json
import sys

# Windows consoles may default to a legacy code page; make sure arrows/ticks print.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ENABLED = True
COLORS = {"llm": "\033[95m", "decide": "\033[94m", "select": "\033[96m", "ok": "\033[92m",
          "bad": "\033[91m", "result": "\033[93m", "finish": "\033[1;92m", "dim": "\033[2m"}
RESET = "\033[0m"


def _short(value, limit: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + " ..."


def step(tag: str, message: str, color: str = "dim") -> None:
    if ENABLED:
        print(f"{COLORS[color]}[{tag}]{RESET} {message}")


def llm_call(n: int, usage=None) -> None:
    extra = f"  (in={usage.input_tokens} out={usage.output_tokens} tokens)" if usage else ""
    step(f"LLM call #{n}", f"model replied{extra}", "llm")


def model_text(text: str) -> None:
    if text.strip():
        step("MODEL SAYS", _short(text.strip()), "dim")


def decide(needs_tool: bool) -> None:
    step("DECIDE", f"needs a tool: {'yes' if needs_tool else 'no'}", "decide")


def select(name: str, args) -> None:
    step("SELECT", f"{name}  args={_short(args)}", "select")


def validate(errors: list[str]) -> None:
    if errors:
        step("VALIDATE", "✗ " + "; ".join(errors), "bad")
    else:
        step("VALIDATE", "✓ arguments ok", "ok")


def execute(ok: bool, result, elapsed_ms: float) -> None:
    status = "✓" if ok else "✗"
    step("EXECUTE", f"{status} {elapsed_ms:.1f} ms  {_short(result)}", "ok" if ok else "bad")


def result_to_llm(note: str) -> None:
    step("RESULT → LLM", note, "result")


def memory(n_messages: int, est_tokens: int) -> None:
    step("MEMORY", f"sending {n_messages} earlier messages (~{est_tokens} tokens)", "dim")


def finish(reason: str) -> None:
    step("FINISH", reason, "finish")
