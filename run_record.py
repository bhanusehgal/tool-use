"""RunRecord: a structured account of one agent run.

The trace prints what happens for a human to read. The RunRecord stores the
same events as data, so a script (evals/run_eval.py) can grade not only the
final answer but also HOW the agent got there.
"""

import time
from dataclasses import asdict, dataclass, field


@dataclass
class RunRecord:
    question: str
    model: str
    stage: int
    answer: str = ""
    # one entry per tool call the model asked for:
    # {"name", "args", "valid", "ok", "result" (or error message)}
    tool_calls: list = field(default_factory=list)
    # one entry per LLM call: {"input_tokens", "output_tokens"}
    llm_calls: list = field(default_factory=list)
    parse_errors: int = 0
    nudges: int = 0          # stage 4: retry reminders sent
    guard_triggers: int = 0  # stage 4: false claims sent back
    validation_errors: int = 0
    # how the run ended: "final" | "max_steps" | "max_tokens" | "refusal" | "crash"
    stop: str = ""
    seconds: float = 0.0
    # stage 6: conversation memory
    memory: str = ""
    history_tokens: int = 0          # estimated size of the history sent with this question
    messages: list = field(default_factory=list, repr=False)  # full message list after the run
    _start: float = field(default_factory=time.perf_counter, repr=False)

    def add_llm_call(self, usage) -> None:
        self.llm_calls.append({"input_tokens": getattr(usage, "input_tokens", 0) or 0,
                               "output_tokens": getattr(usage, "output_tokens", 0) or 0})

    def add_tool_call(self, name, args, errors: list[str], ok: bool | None = None, result=None) -> None:
        if errors:
            self.validation_errors += 1
        self.tool_calls.append({"name": name, "args": args, "valid": not errors,
                                "ok": bool(ok) and not errors,
                                "result": "; ".join(errors) if errors else result})

    def finish(self, stop: str, answer: str) -> "RunRecord":
        self.stop, self.answer = stop, answer
        self.seconds = round(time.perf_counter() - self._start, 2)
        return self

    @property
    def input_tokens(self) -> int:
        return sum(c["input_tokens"] for c in self.llm_calls)

    @property
    def output_tokens(self) -> int:
        return sum(c["output_tokens"] for c in self.llm_calls)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("_start")
        d.pop("messages")  # SDK objects; not saved to results
        d["input_tokens"], d["output_tokens"] = self.input_tokens, self.output_tokens
        return d
