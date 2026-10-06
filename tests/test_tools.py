"""Tests for the tools and the validator. No API key needed.

Run from the project folder:  py -m unittest discover tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.seed_db import build  # noqa: E402
from tools import ToolError  # noqa: E402
from tools.calculator import calculate  # noqa: E402
from tools.database import query_database  # noqa: E402
from tools.documents import search_documents  # noqa: E402
from tools.registry import execute, validate_args  # noqa: E402


class CalculatorTests(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(calculate("2340 * 0.175")["result"], 409.5)
        self.assertEqual(calculate("(1 + 2) ** 3 - 7 // 2")["result"], 24)
        self.assertEqual(calculate("sqrt(16) + max(1, 5)")["result"], 9)

    def test_thousands_separator(self):
        self.assertEqual(calculate("2,340 * 2")["result"], 4680)

    def test_rejects_code(self):
        with self.assertRaises(ToolError):
            calculate("__import__('os').getcwd()")
        with self.assertRaises(ToolError):
            calculate("open('x.txt')")

    def test_errors(self):
        with self.assertRaises(ToolError):
            calculate("1 / 0")
        with self.assertRaises(ToolError):
            calculate("2 +")


class DocumentSearchTests(unittest.TestCase):
    def test_vacation_ranks_first(self):
        results = search_documents("vacation days new employees")["results"]
        self.assertEqual(results[0]["doc"], "vacation_policy.md")
        self.assertIn("1.25", results[0]["snippet"])

    def test_top_k(self):
        self.assertLessEqual(len(search_documents("policy employees", top_k=2)["results"]), 2)

    def test_empty_query(self):
        with self.assertRaises(ToolError):
            search_documents("the and of")


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()

    def test_select(self):
        result = query_database("SELECT COUNT(*) AS n FROM employees")
        self.assertEqual(result["columns"], ["n"])
        self.assertEqual(result["rows"], [[19]])

    def test_rejects_writes(self):
        for sql in ["DELETE FROM orders", "DROP TABLE employees", "SELECT 1; DELETE FROM orders"]:
            with self.assertRaises(ToolError, msg=sql):
                query_database(sql)

    def test_read_only_connection(self):
        # A CTE starts with WITH, so it passes the SELECT check; the read-only
        # connection is the second layer that must still block it.
        with self.assertRaises(ToolError):
            query_database("WITH x AS (SELECT 1) DELETE FROM orders")

    def test_sql_error(self):
        with self.assertRaises(ToolError):
            query_database("SELECT * FROM no_such_table")


class ValidatorTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_args("calculate", {"expression": "1+1"}), [])
        self.assertEqual(validate_args("search_documents", {"query": "x", "top_k": 5}), [])

    def test_unknown_tool(self):
        self.assertIn("Unknown tool", validate_args("send_email", {})[0])

    def test_missing_extra_and_type(self):
        self.assertIn("Missing required argument 'expression'", validate_args("calculate", {}))
        self.assertTrue(any("Unknown argument 'query'" in e for e in validate_args("query_database", {"query": "x"})))
        self.assertTrue(any("must be of type integer" in e for e in validate_args("search_documents", {"query": "x", "top_k": "3"})))
        self.assertTrue(any("must be of type integer" in e for e in validate_args("search_documents", {"query": "x", "top_k": True})))

    def test_bounds_and_empty(self):
        self.assertTrue(any("<= 10" in e for e in validate_args("search_documents", {"query": "x", "top_k": 50})))
        self.assertTrue(any("must not be empty" in e for e in validate_args("calculate", {"expression": "  "})))

    def test_sql_rule(self):
        self.assertEqual(validate_args("query_database", {"sql": "DELETE FROM orders"}), ["Only SELECT queries are allowed"])

    def test_not_a_dict(self):
        self.assertIn("must be a JSON object", validate_args("calculate", "1+1")[0])

    def test_execute_never_raises(self):
        ok, result, _ = execute("calculate", {"expression": "1/0"})
        self.assertFalse(ok)
        self.assertEqual(result, "Division by zero")


if __name__ == "__main__":
    unittest.main()
