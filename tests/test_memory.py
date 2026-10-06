"""Tests for stage 6 memory. A scripted fake LLM replaces the model, so no Ollama needed.

Run from the project folder:  py -m unittest discover tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import agent_native_tools  # noqa: E402
import agent_text_protocol  # noqa: E402
import llm  # noqa: E402
import memory  # noqa: E402
import settings  # noqa: E402
from data.seed_db import build  # noqa: E402
from tests.test_stage4 import FakeLLM, text_reply, tool_reply  # noqa: E402


def native_turn(i: int, big: bool = False) -> list[dict]:
    """One stage 2 turn: question, tool_use, tool_result, answer."""
    return [
        {"role": "user", "content": f"question {i}"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": f"c{i}", "name": "calculate", "input": {"expression": "1+1"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"c{i}", "content": "x" * (2000 if big else 10)}]},
        {"role": "assistant", "content": [{"type": "text", "text": f"answer {i}"}]},
    ]


class StrategyTests(unittest.TestCase):
    def setUp(self):
        self.turns = [native_turn(i) for i in range(4)]

    def test_full_keeps_everything(self):
        self.assertEqual(len(memory.full(self.turns)), 16)

    def test_window_keeps_whole_turns(self):
        sent = memory.window(self.turns, 2)
        self.assertEqual(len(sent), 8)
        self.assertEqual(sent[0]["content"], "question 2")
        self.assertEqual(memory.check_history(sent), [])

    def test_trim_stubs_old_results_only(self):
        turns = [native_turn(i, big=True) for i in range(3)]
        sent = memory.trim_tool_results(turns)
        self.assertIn("[trimmed, 2000 chars]", sent[2]["content"][0]["content"])
        self.assertEqual(sent[-2]["content"][0]["content"], "x" * 2000)   # latest turn untouched
        self.assertEqual(turns[0][2]["content"][0]["content"], "x" * 2000)  # originals not modified
        self.assertEqual(memory.check_history(sent), [])

    def test_trim_stage1_text_results(self):
        turns = [[{"role": "user", "content": "q"}, {"role": "assistant", "content": "{}"},
                  {"role": "user", "content": "TOOL_RESULT query_database: " + "y" * 500},
                  {"role": "assistant", "content": "{}"}], [{"role": "user", "content": "q2"}]]
        sent = memory.trim_tool_results(turns)
        self.assertTrue(sent[2]["content"].startswith("TOOL_RESULT query_database: [trimmed"))

    def test_naive_cut_breaks_pairing(self):
        """Why strategies work on whole turns: cutting by message count orphans a tool_result."""
        sent = memory.naive_last_messages(self.turns, k=2)
        problems = memory.check_history(sent)
        self.assertTrue(any("no matching tool_use" in p for p in problems), problems)
        self.assertTrue(any("doesn't start with a user question" in p for p in problems), problems)

    def test_summary_only_when_over_budget(self):
        calls = []
        summary = memory.SummaryMemory(summarise=lambda msgs: calls.append(len(msgs)) or "- user asked things")
        self.assertEqual(len(summary(self.turns[:2])), 8)       # small: sent unchanged
        self.assertEqual(calls, [])
        big = [native_turn(i, big=True) for i in range(4)]
        sent = summary(big)
        self.assertTrue(sent[0]["content"].startswith("[Summary of our earlier conversation]"))
        self.assertEqual(sent[1]["role"], "assistant")
        self.assertEqual(len(sent), 2 + 4)                      # summary pair + last turn
        self.assertEqual(memory.check_history(sent), [])
        summary(big)                                             # same turns again: cached
        self.assertEqual(len(calls), 1)


class ConversationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()

    def setUp(self):
        settings.apply_variant("baseline")
        self._real = llm.call_llm

    def tearDown(self):
        llm.call_llm = self._real

    def test_stage2_second_turn_sees_first(self):
        fake = FakeLLM([
            tool_reply("query_database", {"sql": "SELECT 'Engineering'"}),
            text_reply("Engineering."),
            text_reply("Its average salary is ..."),
        ])
        llm.call_llm = fake
        records = memory.run_conversation(agent_native_tools, ["Which department is biggest?", "Its average salary?"])
        self.assertEqual(len(records), 2)
        sent = fake.calls[2]["messages"]
        self.assertEqual(sent[0]["content"], "Which department is biggest?")
        self.assertEqual(sent[-1]["content"], "Its average salary?")
        self.assertEqual(memory.check_history(sent[:-1]), [])
        self.assertGreater(records[1].history_tokens, 0)

    def test_stage1_conversation_and_window_forgets(self):
        llm.call_llm = FakeLLM([text_reply('{"action": "final", "answer": f"a{i}"}'.replace("f\"a{i}\"", f'"a{i}"'))
                                for i in range(3)])
        records = memory.run_conversation(agent_text_protocol, ["q0", "q1", "q2"], strategy="window")
        self.assertEqual([r.answer for r in records], ["a0", "a1", "a2"])
        # window keeps 2 turns, so turn 3 (index 2) was sent turns 0 and 1; a 4th would lose q0
        turns = [r.messages for r in records]
        self.assertEqual(turns[2][0]["content"], "q0")


if __name__ == "__main__":
    unittest.main()
