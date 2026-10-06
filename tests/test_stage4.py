"""Tests for the stage 4 fixes. A scripted fake LLM replaces the model, so no Ollama needed.

Run from the project folder:  py -m unittest discover tests
"""

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

import agent_native_tools  # noqa: E402
import agent_text_protocol  # noqa: E402
import agent_trace  # noqa: E402
import llm  # noqa: E402
import settings  # noqa: E402
from data.seed_db import build  # noqa: E402
from tools.documents import search_documents  # noqa: E402

agent_trace.ENABLED = False
USAGE = SimpleNamespace(input_tokens=10, output_tokens=5)


def text_reply(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn", usage=USAGE)


def tool_reply(name, args, call_id="call_1"):
    return SimpleNamespace(content=[SimpleNamespace(type="tool_use", id=call_id, name=name, input=args)],
                           stop_reason="tool_use", usage=USAGE)


class FakeLLM:
    """Replays scripted replies and remembers what the agent sent."""

    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, system, messages, tools=None, json_mode=False):
        self.calls.append({"system": system, "messages": [dict(m) for m in messages], "json_mode": json_mode})
        return self.replies.pop(0)


class Stage4Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()

    def setUp(self):
        settings.apply_variant("baseline")
        self._real_call = llm.call_llm

    def tearDown(self):
        llm.call_llm = self._real_call
        settings.apply_variant("baseline")

    def fake(self, replies):
        llm.call_llm = FakeLLM(replies)
        return llm.call_llm


class VariantTests(Stage4Base):
    def test_apply_variant_resets_switches(self):
        settings.apply_variant("all")
        self.assertEqual(settings.active(), settings.SWITCHES)
        settings.apply_variant("stemming")
        self.assertEqual(settings.active(), ["STEMMING"])
        with self.assertRaises(ValueError):
            settings.apply_variant("nope")


class StemmingTests(Stage4Base):
    def test_meal_line_found_only_with_stemming(self):
        snippet = search_documents("daily meal allowance travel", top_k=1)["results"][0]["snippet"]
        self.assertNotIn("Meals while traveling", snippet)
        settings.STEMMING = True
        snippet = search_documents("daily meal allowance travel", top_k=1)["results"][0]["snippet"]
        self.assertIn("Meals while traveling: up to $60 per day", snippet)


class PromptRulesTests(Stage4Base):
    def test_rules_added_only_when_on(self):
        self.assertNotIn("RULES:", agent_text_protocol.build_system_prompt())
        settings.PROMPT_RULES = True
        self.assertIn("must come from search_documents", agent_text_protocol.build_system_prompt())
        fake = self.fake([text_reply("ok")])
        agent_native_tools.run_agent("hi")
        self.assertIn("RULES:", fake.calls[0]["system"])


class BetterErrorTests(Stage4Base):
    """Each row of the STAGE4_PLAN.md error table."""

    def parse(self, text):
        return agent_text_protocol.parse_reply(text)[1]

    def test_baseline_messages_unchanged(self):
        self.assertIn("not valid JSON", self.parse("Hello there"))
        self.assertIn('"action" set to "tool" or "final"', self.parse('{"action": "search_documents"}'))
        # Baseline lets args-at-top-level through to the validator (which then says "Missing 'sql'").
        self.assertIsNone(self.parse('{"action": "tool", "tool": "query_database", "sql": "SELECT 1"}'))

    def test_action_is_tool_name(self):
        settings.BETTER_ERRORS = True
        msg = self.parse('{"action": "search_documents", "args": {"query": "x"}}')
        self.assertIn('You wrote "action": "search_documents"', msg)
        self.assertIn('{"action": "tool", "tool": "search_documents", "args": {"query": "x"}}', msg)

    def test_args_at_top_level(self):
        settings.BETTER_ERRORS = True
        msg = self.parse('{"action": "tool", "tool": "query_database", "sql": "SELECT 1"}')
        self.assertIn('inside "args"', msg)
        self.assertIn('"args": {"sql": "SELECT 1"}', msg)

    def test_plain_text(self):
        settings.BETTER_ERRORS = True
        msg = self.parse("New employees get 15 days.")
        self.assertIn("plain text", msg)
        self.assertIn('"action": "final"', msg)

    def test_text_before_json(self):
        settings.BETTER_ERRORS = True
        self.assertIn("extra text before the JSON ('TOOL_RESULT')",
                      self.parse('TOOL_RESULT\n{"action": "tool", "tool": "calculate", "args": {}}'))

    def test_valid_reply_passes(self):
        settings.BETTER_ERRORS = True
        self.assertIsNone(self.parse('{"action": "final", "answer": "hi"}'))


class NudgeTests(Stage4Base):
    def test_nudge_after_error_then_success(self):
        settings.BETTER_ERRORS = True
        self.fake([
            text_reply("Let me look that up"),                                           # parse error
            text_reply('{"action": "final", "answer": "I could not find it."}'),         # nudged
            text_reply('{"action": "tool", "tool": "calculate", "args": {"expression": "2+2"}}'),
            text_reply('{"action": "final", "answer": "4"}'),
        ])
        record = agent_text_protocol.run_agent("2+2?")
        self.assertEqual(record.answer, "4")
        self.assertEqual(record.nudges, 1)
        self.assertEqual(len(record.llm_calls), 4)

    def test_nudge_fires_only_once(self):
        settings.BETTER_ERRORS = True
        self.fake([
            text_reply("oops"),
            text_reply('{"action": "final", "answer": "Cannot find."}'),
            text_reply('{"action": "final", "answer": "Still cannot find."}'),
        ])
        self.assertEqual(agent_text_protocol.run_agent("q").answer, "Still cannot find.")

    def test_no_nudge_after_blocked_delete(self):
        """Regression found by the stage 4 eval: the nudge overrode a correct refusal."""
        settings.BETTER_ERRORS = True
        refusal = "I cannot execute that command. Only SELECT queries are allowed."
        fake = self.fake([
            text_reply('{"action": "tool", "tool": "query_database", "args": {"sql": "DELETE FROM orders"}}'),
            text_reply(json.dumps({"action": "final", "answer": refusal})),
        ])
        record = agent_text_protocol.run_agent("Delete all orders from 2023.")
        self.assertEqual(record.answer, refusal)
        self.assertEqual(record.nudges, 0)
        self.assertEqual(len(fake.calls), 2)

    def test_no_nudge_after_blocked_delete_then_format_error(self):
        """Second-round regression: blocked DELETE, then the refusal arrives as plain text (a format error)."""
        settings.BETTER_ERRORS = True
        fake = self.fake([
            text_reply('{"action": "tool", "tool": "query_database", "args": {"sql": "DELETE FROM orders"}}'),
            text_reply("I cannot delete orders, only SELECT is allowed."),                      # format error
            text_reply('{"action": "final", "answer": "I cannot delete orders; only SELECT is allowed."}'),
        ])
        record = agent_text_protocol.run_agent("Delete all orders from 2023.")
        self.assertEqual(record.nudges, 0)
        self.assertIn("cannot delete", record.answer)
        self.assertEqual(len(fake.calls), 3)

    def test_no_nudge_for_clean_out_of_scope_answer(self):
        settings.BETTER_ERRORS = True
        fake = self.fake([text_reply('{"action": "final", "answer": "I cannot check the weather."}')])
        self.assertEqual(agent_text_protocol.run_agent("weather?").answer, "I cannot check the weather.")
        self.assertEqual(len(fake.calls), 1)


class JsonModeTests(Stage4Base):
    def test_json_mode_passed_to_llm(self):
        fake = self.fake([text_reply('{"action": "final", "answer": "x"}')] * 2)
        agent_text_protocol.run_agent("q")
        settings.JSON_MODE = True
        agent_text_protocol.run_agent("q")
        self.assertEqual([c["json_mode"] for c in fake.calls], [False, True])


class ClaimGuardTests(Stage4Base):
    LLAMA_CLAIM = "All orders from 2023 have been deleted from the database."  # Llama's real answer

    def test_stage1_guard_replays_llama_claim(self):
        settings.CLAIM_GUARD = True
        fake = self.fake([
            text_reply(json.dumps({"action": "final", "answer": self.LLAMA_CLAIM})),
            text_reply('{"action": "final", "answer": "I cannot delete orders; the database is read-only."}'),
        ])
        record = agent_text_protocol.run_agent("Delete all orders from 2023.")
        self.assertIn("cannot delete", record.answer)
        self.assertEqual(record.guard_triggers, 1)
        self.assertIn("no tool performed that action", fake.calls[1]["messages"][-1]["content"])

    def test_stage2_guard_replays_llama_claim(self):
        settings.CLAIM_GUARD = True
        self.fake([
            tool_reply("query_database", {"sql": "SELECT * FROM orders WHERE order_date LIKE '2023%'"}),
            text_reply(self.LLAMA_CLAIM),
            text_reply("I can't delete orders: my database access is read-only."),
        ])
        record = agent_native_tools.run_agent("Delete all orders from 2023.")
        self.assertIn("can't delete", record.answer)

    def test_guard_off_lets_claim_through(self):
        self.fake([text_reply(self.LLAMA_CLAIM)])
        self.assertEqual(agent_native_tools.run_agent("Delete all orders from 2023.").answer, self.LLAMA_CLAIM)


if __name__ == "__main__":
    unittest.main()
