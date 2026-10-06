"""Conversation memory (stage 6).

An LLM has no memory of its own. "Memory" is whatever message history we choose
to send back on each turn. History grows with every question, tool call and tool
result, so a real agent has to decide what to keep. Each strategy here is a
function: list of past turns -> the messages to send.

A TURN is everything from one user question to the agent's final answer:
  stage 2: user question, assistant tool_use, user tool_result, ..., assistant answer
  stage 1: user question, assistant JSON, user "TOOL_RESULT ...", ..., assistant answer

THE KEY RULE: you can't cut the history anywhere you like. Every tool_use must
stay together with its tool_result, and the history must start with a user
question. That's why the strategies work on whole turns. `naive_last_messages`
breaks the rule on purpose, and `check_history` shows what goes wrong.
"""

import copy
import json
import os

import llm

WINDOW_TURNS = 2                # window: how many previous turns to keep
SUMMARY_TRIGGER_TOKENS = int(os.environ.get("SUMMARY_TRIGGER_TOKENS", "1200"))  # summarise once past turns exceed this (estimated)
SUMMARY_KEEP_TURNS = 1          # summary: most recent turns kept word for word
STRATEGIES = ["none", "full", "window", "trim", "summary"]
SUMMARY_TOKENS = {"input": 0, "output": 0}  # tokens spent on summary calls (the eval adds them to the cost)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _block_dict(block) -> dict:
    return block if isinstance(block, dict) else vars(block)


def message_text(message: dict) -> str:
    """Render one message as plain text (for token estimates and for summaries)."""
    content = message["content"]
    if isinstance(content, str):
        return content
    parts = []
    for b in map(_block_dict, content):
        if b["type"] == "text":
            parts.append(b.get("text", ""))
        elif b["type"] == "tool_use":
            parts.append(f"[called {b['name']} {json.dumps(b['input'])}]")
        elif b["type"] == "tool_result":
            parts.append(f"[tool result: {b['content']}]")
    return " ".join(parts)


def estimate_tokens(messages: list[dict]) -> int:
    """Rough rule of thumb: ~4 characters per token for English text."""
    return sum(len(message_text(m)) for m in messages) // 4


def flatten(turns: list[list[dict]]) -> list[dict]:
    return [m for turn in turns for m in turn]


def check_history(messages: list[dict]) -> list[str]:
    """Return the problems that would confuse the model or make the API reject the request."""
    problems = []
    if messages:
        first = messages[0]
        is_tool_result = not isinstance(first["content"], str) and any(
            _block_dict(b)["type"] == "tool_result" for b in first["content"])
        if first["role"] != "user" or is_tool_result:
            problems.append("history doesn't start with a user question")
    open_calls = set()
    for i, m in enumerate(messages):
        if isinstance(m["content"], str):
            continue
        for b in map(_block_dict, m["content"]):
            if b["type"] == "tool_use":
                open_calls.add(b["id"])
            elif b["type"] == "tool_result":
                if b["tool_use_id"] not in open_calls:
                    problems.append(f"message {i}: tool_result for {b['tool_use_id']} with no matching tool_use")
                open_calls.discard(b["tool_use_id"])
    if open_calls:
        problems.append(f"tool_use without a tool_result: {sorted(open_calls)}")
    return problems


# ── Strategies ───────────────────────────────────────────────────────────────

def none(turns: list[list[dict]]) -> list[dict]:
    """No memory: every question starts fresh (the control: what stages 1-5 did)."""
    return []


def full(turns: list[list[dict]]) -> list[dict]:
    """Keep everything. Exact, but the prompt grows with every turn."""
    return flatten(turns)


def window(turns: list[list[dict]], n: int | None = None) -> list[dict]:
    """Keep the last n whole turns. Cheap, but forgets anything older."""
    n = WINDOW_TURNS if n is None else n
    return flatten(turns[-n:]) if n > 0 else []


def trim_tool_results(turns: list[list[dict]]) -> list[dict]:
    """Keep every turn, but replace bulky tool results in older turns with a short stub.
    Keeps the flow of the conversation (questions, answers) and drops raw data."""
    out = []
    for i, turn in enumerate(turns):
        if i == len(turns) - 1:
            out += turn                      # never touch the most recent turn
            continue
        for m in turn:
            m = copy.copy(m)
            if isinstance(m["content"], str):
                if m["role"] == "user" and m["content"].startswith(("TOOL_RESULT", "TOOL_ERROR")):
                    head = m["content"].split(":", 1)[0]
                    m["content"] = f"{head}: [trimmed, {len(m['content'])} chars]"
            elif m["role"] == "user":
                m["content"] = [
                    {**_block_dict(b), "content": f"[trimmed, {len(str(_block_dict(b)['content']))} chars]"}
                    if _block_dict(b)["type"] == "tool_result" else b
                    for b in m["content"]
                ]
            out.append(m)
    return out


class SummaryMemory:
    """When past turns get too long, ask the model to summarise the older ones.
    Remembers the gist; costs an extra LLM call and can lose detail. The summary is
    cached, so it's only recomputed when more turns need summarising."""

    def __init__(self, summarise=None):
        self.summarise = summarise or summarise_with_llm
        self._cache: tuple[int, str] | None = None
        self.summary_calls = 0

    def __call__(self, turns: list[list[dict]]) -> list[dict]:
        if estimate_tokens(flatten(turns)) <= SUMMARY_TRIGGER_TOKENS or len(turns) <= SUMMARY_KEEP_TURNS:
            return flatten(turns)
        old, recent = turns[:-SUMMARY_KEEP_TURNS], turns[-SUMMARY_KEEP_TURNS:]
        if not self._cache or self._cache[0] != len(old):
            self.summary_calls += 1
            self._cache = (len(old), self.summarise(flatten(old)))
        return [
            {"role": "user", "content": f"[Summary of our earlier conversation]\n{self._cache[1]}"},
            {"role": "assistant", "content": "Understood. I'll use that context."},
        ] + flatten(recent)


def summarise_with_llm(messages: list[dict]) -> str:
    transcript = "\n".join(f"{m['role'].upper()}: {message_text(m)}" for m in messages)
    response = llm.call_llm(
        "You summarise conversations between a user and a company assistant. Keep every fact the user stated "
        "about themselves, every question asked, and every number or name found. Be concise: at most 8 bullet points.",
        [{"role": "user", "content": f"Summarise this conversation:\n\n{transcript}"}],
    )
    SUMMARY_TOKENS["input"] += response.usage.input_tokens or 0
    SUMMARY_TOKENS["output"] += response.usage.output_tokens or 0
    return "".join(b.text for b in response.content if b.type == "text").strip()


def naive_last_messages(turns: list[list[dict]], k: int = 3) -> list[dict]:
    """DON'T USE: keeps the last k *messages*, ignoring turn boundaries. Here to show why
    cutting mid-turn breaks things (check_history reports orphaned tool results)."""
    return flatten(turns)[-k:]


def get_strategy(name: str):
    return {"none": none, "full": full, "window": window, "trim": trim_tool_results, "summary": SummaryMemory()}[name]


# ── Running a conversation ───────────────────────────────────────────────────

def run_conversation(agent, questions: list[str], strategy: str = "full", on_turn=None) -> list:
    """Ask several questions in a row, carrying memory between them.
    Returns one RunRecord per turn. on_turn(record, sent_history) is called after each turn."""
    remember = get_strategy(strategy)
    turns: list[list[dict]] = []
    records = []
    for question in questions:
        history = remember(turns)
        record = agent.run_agent(question, history=history)
        record.memory = strategy
        record.history_tokens = estimate_tokens(history)
        # the new turn = everything this run added after the history we sent
        turns.append(record.messages[len(history):])
        records.append(record)
        if on_turn:
            on_turn(record, history)
    return records
