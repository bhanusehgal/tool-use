"""The tool registry and argument validator.

This file covers two boxes of the agent diagram:
  "Which tool?"        -> look the name up in TOOLS
  "Validate arguments" -> validate_args() checks the arguments against the schema

The same TOOLS dict is used by both agents: stage 1 turns it into prompt text,
stage 2 passes it to the API's `tools=` parameter.
"""

import time

from tools import ToolError
from tools.calculator import calculate
from tools.database import SCHEMA_DESCRIPTION, check_select_only, query_database
from tools.documents import search_documents

TOOLS = {
    "calculate": {
        "fn": calculate,
        "description": (
            "Evaluate an arithmetic expression and return the exact result. Use this for any math "
            "instead of calculating in your head. Supports + - * / // % ** and parentheses, "
            "and the functions sqrt, round, abs, min, max. Example: '2340 * 0.175'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "The arithmetic expression to evaluate."},
            },
            "required": ["expression"],
        },
    },
    "search_documents": {
        "fn": search_documents,
        "description": (
            "Search the company's internal policy documents (vacation, compensation, expenses, "
            "remote work, onboarding, product FAQ) by keyword. Returns the best-matching documents "
            "with the relevant lines. Use this for questions about policies, rules or products."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords to search for, e.g. 'vacation days new employees'."},
                "top_k": {"type": "integer", "description": "How many documents to return (1-10). Default 3.",
                          "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
    "query_database": {
        "fn": query_database,
        "description": (
            "Run a read-only SQL SELECT query against the company's SQLite database and return the rows. "
            f"Tables: {SCHEMA_DESCRIPTION}. Only single SELECT statements are allowed; at most 50 rows are returned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "A single SQLite SELECT statement."},
            },
            "required": ["sql"],
        },
    },
}

JSON_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "object": dict}


def validate_args(name: str, args) -> list[str]:
    """Check args against the tool's input_schema. Returns a list of errors (empty = valid).

    The messages are written for the model to read: they go back to it as an
    error result so it can fix the call and try again.
    """
    if name not in TOOLS:
        return [f"Unknown tool '{name}'. Available tools: {', '.join(TOOLS)}"]
    if not isinstance(args, dict):
        return [f"Arguments must be a JSON object, got {type(args).__name__}"]

    schema = TOOLS[name]["input_schema"]
    properties = schema["properties"]
    errors = []

    for key in schema.get("required", []):
        if key not in args:
            errors.append(f"Missing required argument '{key}'")

    for key, value in args.items():
        if key not in properties:
            errors.append(f"Unknown argument '{key}'. Expected: {', '.join(properties)}")
            continue
        spec = properties[key]
        expected = JSON_TYPES[spec["type"]]
        # bool is a subclass of int in Python, so reject it explicitly for integers.
        if not isinstance(value, expected) or (spec["type"] == "integer" and isinstance(value, bool)):
            errors.append(f"Argument '{key}' must be of type {spec['type']}, got {type(value).__name__}")
            continue
        if spec["type"] == "string" and not value.strip():
            errors.append(f"Argument '{key}' must not be empty")
        if "minimum" in spec and value < spec["minimum"]:
            errors.append(f"Argument '{key}' must be >= {spec['minimum']}, got {value}")
        if "maximum" in spec and value > spec["maximum"]:
            errors.append(f"Argument '{key}' must be <= {spec['maximum']}, got {value}")

    # Tool-specific rule: the SQL must be a single SELECT. Checking it here means
    # a bad query is rejected before we ever touch the database.
    if name == "query_database" and not errors:
        sql_error = check_select_only(args["sql"])
        if sql_error:
            errors.append(sql_error)

    return errors


def execute(name: str, args: dict) -> tuple[bool, object, float]:
    """Run a tool. Returns (ok, result_or_error_message, elapsed_ms). Never raises."""
    start = time.perf_counter()
    try:
        result = TOOLS[name]["fn"](**args)
        ok = True
    except ToolError as e:
        result, ok = str(e), False
    except Exception as e:  # a bug in the tool itself; still don't crash the agent
        result, ok = f"Tool crashed: {type(e).__name__}: {e}", False
    return ok, result, (time.perf_counter() - start) * 1000


def api_tool_definitions() -> list[dict]:
    """The TOOLS registry in the shape the Claude API's `tools=` parameter expects."""
    return [
        {"name": name, "description": t["description"], "input_schema": t["input_schema"]}
        for name, t in TOOLS.items()
    ]
