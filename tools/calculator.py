"""calculate(): evaluate an arithmetic expression safely.

Why not just eval()? The expression comes from the model, and model output is
untrusted input. eval("__import__('os').remove('important.txt')") would run.
Instead we parse the expression into a syntax tree (AST) and only evaluate the
node types we explicitly allow. Anything else is rejected.
"""

import ast
import math
import operator

from tools import ToolError

BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY_OPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}
FUNCTIONS = {"sqrt": math.sqrt, "round": round, "abs": abs, "min": min, "max": max}


def calculate(expression: str) -> dict:
    try:
        tree = ast.parse(expression.replace(",", "") if _is_thousands(expression) else expression, mode="eval")
    except SyntaxError as e:
        raise ToolError(f"Could not parse expression: {e.msg}") from None

    try:
        value = _eval(tree.body)
    except ZeroDivisionError:
        raise ToolError("Division by zero") from None
    except OverflowError:
        raise ToolError("Result is too large") from None

    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return {"expression": expression, "result": value}


def _is_thousands(expression: str) -> bool:
    # "2,340 * 0.175" -> treat commas as thousands separators, unless they are
    # function-argument separators like "max(1, 2)".
    return "(" not in expression


def _eval(node: ast.AST):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ToolError("Exponent too large")
        return BINARY_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return UNARY_OPS[type(node.op)](_eval(node.operand))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in FUNCTIONS
        and not node.keywords
    ):
        return FUNCTIONS[node.func.id](*[_eval(arg) for arg in node.args])
    raise ToolError(
        f"Unsupported element '{ast.unparse(node)}'. Allowed: numbers, + - * / // % **, "
        f"parentheses, and the functions {', '.join(FUNCTIONS)}."
    )
