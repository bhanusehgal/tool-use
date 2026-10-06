"""query_database(): run a read-only SQL SELECT against data/company.db.

Two layers of defence, because the SQL is written by the model:
  1. We only accept a single SELECT statement (checked below and in the validator).
  2. The connection is opened in SQLite read-only mode, so even if a write
     slipped past check 1, the database itself refuses it.
"""

import sqlite3
from pathlib import Path

from tools import ToolError

DB_PATH = Path(__file__).parent.parent / "data" / "company.db"
MAX_ROWS = 50

SCHEMA_DESCRIPTION = (
    "departments(id, name, location); "
    "employees(id, name, department_id -> departments.id, title, salary [yearly USD], hire_date [YYYY-MM-DD]); "
    "orders(id, customer, product [Atlas|Beacon|Compass], seats, amount [USD per month], "
    "order_date [YYYY-MM-DD], sales_rep_id -> employees.id)"
)


def check_select_only(sql: str) -> str | None:
    """Return an error message if sql is not exactly one SELECT statement."""
    stripped = sql.strip().rstrip(";").strip()
    if not stripped.lower().startswith(("select", "with")):
        return "Only SELECT queries are allowed"
    if ";" in stripped:
        return "Only a single statement is allowed"
    return None


def query_database(sql: str) -> dict:
    error = check_select_only(sql)
    if error:
        raise ToolError(error)
    if not DB_PATH.exists():
        raise ToolError("Database not found. Run: py data/seed_db.py")

    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchmany(MAX_ROWS + 1)
        columns = [c[0] for c in cursor.description or []]
    except sqlite3.Error as e:
        raise ToolError(f"SQL error: {e}") from None
    finally:
        conn.close()

    truncated = len(rows) > MAX_ROWS
    return {
        "columns": columns,
        "rows": [list(r) for r in rows[:MAX_ROWS]],
        "row_count": min(len(rows), MAX_ROWS),
        "truncated": truncated,
    }
