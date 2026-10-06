"""Tests for the stage 7 framework agent. A fake chat model replaces Ollama.
Skipped automatically if the framework packages (requirements-framework.txt) aren't installed.

Run from the project folder:  py -m unittest discover tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage

    import agent_framework
    HAVE_FRAMEWORK = True
except ImportError:
    HAVE_FRAMEWORK = False

import agent_trace  # noqa: E402
import settings  # noqa: E402
from data.seed_db import build  # noqa: E402

agent_trace.ENABLED = False


if HAVE_FRAMEWORK:
    class FakeToolModel(GenericFakeChatModel):
        """GenericFakeChatModel replays scripted messages; create_agent also needs bind_tools()."""

        def bind_tools(self, tools, **kwargs):
            return self

    def fake(*messages):
        return FakeToolModel(messages=iter(messages))

    def call(name, args, call_id="c1"):
        return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
                         usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110})

    def answer(text):
        return AIMessage(content=text, usage_metadata={"input_tokens": 120, "output_tokens": 20, "total_tokens": 140})


@unittest.skipUnless(HAVE_FRAMEWORK, "framework packages not installed")
class FrameworkAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()

    def setUp(self):
        settings.apply_variant("baseline")

    def test_tool_call_and_record(self):
        record = agent_framework.run_agent("Biggest department?", model=fake(
            call("query_database", {"sql": "SELECT 'Engineering' AS name"}),
            answer("Engineering."),
        ))
        self.assertEqual(record.answer, "Engineering.")
        self.assertEqual(record.stop, "final")
        self.assertEqual(len(record.llm_calls), 2)
        self.assertEqual(record.input_tokens, 220)
        self.assertEqual([(c["name"], c["ok"]) for c in record.tool_calls], [("query_database", True)])

    def test_our_tool_error_goes_back_to_model(self):
        record = agent_framework.run_agent("Delete orders", model=fake(
            call("query_database", {"sql": "DELETE FROM orders"}),
            answer("I can't delete; only SELECT is allowed."),
        ))
        tool_call = record.tool_calls[0]
        self.assertFalse(tool_call["ok"])
        self.assertTrue(tool_call["valid"])               # well-formed call, refused by our tool
        self.assertIn("Only SELECT queries are allowed", tool_call["result"])
        self.assertEqual(record.stop, "final")

    def test_framework_validation_error(self):
        record = agent_framework.run_agent("Search", model=fake(
            call("search_documents", {"query": "vacation", "top_k": 50}),
            answer("Sorry."),
        ))
        self.assertFalse(record.tool_calls[0]["valid"])   # rejected by the framework's pydantic check
        self.assertEqual(record.validation_errors, 1)

    def test_claim_guard_middleware(self):
        settings.CLAIM_GUARD = True
        record = agent_framework.run_agent("Delete all orders from 2023.", model=fake(
            answer("All orders from 2023 have been deleted from the database."),
            answer("I can't delete orders; the tools are read-only."),
        ))
        self.assertEqual(record.guard_triggers, 1)
        self.assertIn("can't delete", record.answer)

    def test_call_limit_stops_the_loop(self):
        loops = [call("calculate", {"expression": "1+1"}, call_id=f"c{i}") for i in range(12)]
        record = agent_framework.run_agent("loop forever", model=fake(*loops))
        self.assertEqual(record.stop, "max_steps")
        self.assertLessEqual(len(record.llm_calls), agent_framework.MAX_STEPS)


if __name__ == "__main__":
    unittest.main()
