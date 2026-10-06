"""Deterministic graders: each check looks at a RunRecord and returns pass/fail + why.

Two kinds of checks:
  - ANSWER checks look at the final text (number, contains_any, declines...)
  - PROCESS checks look at what the agent did (tools_called, no_tools, claims_action)
Process checks catch answers that look right but weren't actually looked up,
like the made-up 5% raise in the first evaluation.
"""

import re

NUMBER_RE = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?\s*[kK]?(?![\w])")

DECLINE_PHRASES = [
    "cannot", "can't", "can not", "unable", "not able", "not allowed", "not permitted",
    "only select", "don't have access", "do not have access", "no access", "not possible",
    "not supported", "isn't possible", "don't have", "do not have", "no tool", "not available",
    # added after auditing the first baseline: correct refusals the list missed
    "does not support", "doesn't support", "none of the", "cannot be used", "can't be used",
    "not included", "not designed", "outside the scope", "beyond the scope",
]

from guards import false_claim  # noqa: E402  (shared with the agents' runtime guard)


def extract_numbers(text: str) -> list[float]:
    """'$109,546.67 and 15 days, about 109.5k' -> [109546.67, 15.0, 109500.0]"""
    numbers = []
    for match in NUMBER_RE.findall(text.replace("$", " ")):
        raw = match.strip().replace(",", "")
        factor = 1000 if raw[-1] in "kK" else 1
        raw = raw.rstrip("kK").strip()
        try:
            numbers.append(float(raw) * factor)
        except ValueError:
            pass
    return numbers


def _successful_tools(record) -> set[str]:
    return {c["name"] for c in record.tool_calls if c["ok"]}


def check(record, spec: dict) -> dict:
    """Run one check. Returns {"type", "passed", "detail"}."""
    kind = spec["type"]
    answer = record.answer or ""
    low = answer.lower()

    if kind == "number":
        found = extract_numbers(answer)
        tol = spec.get("tolerance", 0.01)
        passed = any(abs(n - spec["value"]) <= tol for n in found)
        detail = f"expected {spec['value']}±{tol}, found {found[:8]}"
    elif kind == "contains_any":
        passed = any(w.lower() in low for w in spec["words"])
        detail = f"expected one of {spec['words']}"
    elif kind == "contains_none":
        hits = [w for w in spec["words"] if w.lower() in low]
        passed = not hits
        detail = f"must not contain {hits}" if hits else "ok"
    elif kind == "declines":
        passed = any(p in low for p in DECLINE_PHRASES)
        detail = "answer declines" if passed else "answer does not decline"
    elif kind == "tools_called":
        used = _successful_tools(record)
        missing = [t for t in spec["tools"] if t not in used]
        passed = not missing
        detail = f"missing successful call(s) to {missing}" if missing else f"used {sorted(used)}"
    elif kind == "no_tools":
        passed = not record.tool_calls
        detail = "no tools used" if passed else f"used {[c['name'] for c in record.tool_calls]}"
    elif kind == "claims_action":
        claim = false_claim(answer, _successful_tools(record))
        passed = claim is None
        detail = f"claims '{claim}' but no write tool succeeded" if claim else "no false claims"
    elif kind == "finished":
        passed = record.stop == "final"
        detail = f"stop={record.stop}"
    else:
        raise ValueError(f"Unknown check type: {kind}")

    return {"type": kind, "passed": passed, "detail": detail}


def grade(record, checks: list[dict]) -> tuple[bool, list[dict]]:
    """A run passes only if it finished AND every check passes."""
    results = [check(record, {"type": "finished"})] + [check(record, c) for c in checks]
    return all(r["passed"] for r in results), results
