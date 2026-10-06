"""The one place an LLM is called. Two backends:

  ollama     local models via Ollama's HTTP API (free, default)
  anthropic  Claude via the Anthropic API (paid, needs ANTHROPIC_API_KEY)

Pick one with `--model NAME` on either agent. Names starting with "claude"
use the Anthropic backend; anything else is treated as an Ollama model.

The agents speak ONE internal format, the Anthropic one: a response has
`.stop_reason`, `.usage` and `.content` (a list of blocks with `.type` "text"
or "tool_use"), and tool results go back as `tool_result` blocks.
For Ollama, this file translates in both directions. Reading the
translation code shows that "tool calling" is just a message format,
and each provider uses a slightly different one.
"""

import json
import os
import urllib.error
import urllib.request
from types import SimpleNamespace

DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "qwen2.5:7b-instruct")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MAX_TOKENS = 16000
# Ollama context window (tokens). If a prompt is longer, Ollama SILENTLY drops the beginning.
# 8192 matches what Ollama was already using for these models, so earlier results are unaffected.
NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))
# Claude only. Opus 5.5 defaults to "medium"; "low" is fast and cheap.
EFFORT = "low"

model = DEFAULT_MODEL


def set_model(name: str) -> None:
    global model
    model = name


def provider() -> str:
    return "anthropic" if model.startswith("claude") else "ollama"


def call_llm(system: str, messages: list, tools: list | None = None, json_mode: bool = False):
    """Send one request to the selected model. Returns an Anthropic-shaped response.

    json_mode (Ollama only): constrained decoding, so the reply is always valid JSON.
    """
    if provider() == "anthropic":
        return _call_anthropic(system, messages, tools)
    return _call_ollama(system, messages, tools, json_mode)


# ── Anthropic ────────────────────────────────────────────────────────────────

_anthropic_client = None


def _call_anthropic(system, messages, tools):
    # Imported and created lazily, so Ollama-only users need no API key.
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic()

    params = dict(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=messages,
        output_config={"effort": EFFORT},
        # Server-side refusal fallback: if a safety classifier declines the
        # request, the API retries it on a fallback model. Remove these two
        # lines (and use .messages.create) for the plainest possible call.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if tools:
        params["tools"] = tools
    return _anthropic_client.beta.messages.create(**params)


# ── Ollama ───────────────────────────────────────────────────────────────────

def _call_ollama(system, messages, tools, json_mode=False):
    body = {
        "model": model,
        "stream": False,
        "messages": [{"role": "system", "content": system}] + _to_ollama_messages(messages),
        "options": {"temperature": 0, "num_ctx": NUM_CTX},  # temperature 0: deterministic-ish, easier to learn from
    }
    if json_mode:
        body["format"] = "json"  # Ollama only lets the model produce tokens that keep the JSON valid
    if tools:
        # Anthropic: {name, description, input_schema}
        # Ollama:    {type: "function", function: {name, description, parameters}}
        body["tools"] = [
            {"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": t["input_schema"]}}
            for t in tools
        ]

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        detail = json.loads(e.read() or b"{}").get("error", str(e))
        hint = " (this model can't run stage 2; try stage 1 or a model with tool support)" if "does not support tools" in detail else ""
        raise SystemExit(f"Ollama error: {detail}{hint}") from None
    except urllib.error.URLError as e:
        raise SystemExit(f"Can't reach Ollama at {OLLAMA_URL} ({e.reason}). Is `ollama serve` running?") from None

    if data.get("prompt_eval_count", 0) >= NUM_CTX * 0.9:
        print(f"[WARNING] prompt used {data['prompt_eval_count']} of {NUM_CTX} context tokens: "
              "Ollama may have silently dropped the start of the conversation")
    return _from_ollama_response(data)


def _to_ollama_messages(messages: list) -> list:
    """Translate our (Anthropic-format) history into Ollama's chat format."""
    out = []
    for msg in messages:
        content = msg["content"]
        if isinstance(content, str):
            out.append({"role": msg["role"], "content": content})
            continue

        blocks = [_as_dict(b) for b in content]
        if msg["role"] == "assistant":
            # Anthropic: one message holding text + tool_use blocks.
            # Ollama:    one message with `content` text + a `tool_calls` list.
            out.append({
                "role": "assistant",
                "content": "".join(b.get("text", "") for b in blocks if b["type"] == "text"),
                "tool_calls": [
                    {"id": b["id"], "function": {"name": b["name"], "arguments": b["input"]}}
                    for b in blocks if b["type"] == "tool_use"
                ],
            })
        else:
            # Anthropic: ONE user message holding all tool_result blocks.
            # Ollama:    a separate message with role "tool" per result.
            for b in blocks:
                if b["type"] == "tool_result":
                    out.append({"role": "tool", "tool_call_id": b["tool_use_id"],
                                "tool_name": _tool_name_for(b["tool_use_id"], out),
                                "content": b["content"]})
                elif b["type"] == "text":
                    out.append({"role": "user", "content": b["text"]})
    return out


def _tool_name_for(call_id: str, ollama_messages: list) -> str:
    for m in reversed(ollama_messages):
        for call in m.get("tool_calls", []):
            if call["id"] == call_id:
                return call["function"]["name"]
    return ""


def _as_dict(block) -> dict:
    return block if isinstance(block, dict) else vars(block)


def _from_ollama_response(data: dict):
    """Translate Ollama's reply into the Anthropic shape the agents expect."""
    message = data["message"]
    content = []
    if message.get("content"):
        content.append(SimpleNamespace(type="text", text=message["content"]))
    for i, call in enumerate(message.get("tool_calls") or []):
        args = call["function"].get("arguments", {})
        if isinstance(args, str):  # some models return arguments as a JSON string
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                pass  # leave it as a string; the validator will reject it
        content.append(SimpleNamespace(type="tool_use", id=call.get("id") or f"call_{i}",
                                       name=call["function"]["name"], input=args))

    # Ollama has no "tool_use" stop reason; the presence of tool_calls is the signal.
    if any(b.type == "tool_use" for b in content):
        stop_reason = "tool_use"
    elif data.get("done_reason") == "length":
        stop_reason = "max_tokens"
    else:
        stop_reason = "end_turn"

    usage = SimpleNamespace(input_tokens=data.get("prompt_eval_count", 0), output_tokens=data.get("eval_count", 0))
    return SimpleNamespace(content=content, stop_reason=stop_reason, usage=usage)
