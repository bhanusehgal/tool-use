"""Multi-turn chat with memory (stage 6).

Usage:
  py chat.py                                   stage 2 agent, full memory
  py chat.py --agent text --memory window      stage 1 agent, keep the last 2 turns
  py chat.py --memory summary --quiet          summarise old turns; no step-by-step trace
  py chat.py --model llama3.2:3b-instruct-q5_K_M

Commands while chatting:  /memory  show what would be sent next turn
                          /reset   forget everything
                          (empty line) quit
"""

import argparse
import sys

import agent_native_tools
import agent_text_protocol
import agent_trace as trace
import llm
import memory
import settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", choices=["native", "text"], default="native")
    parser.add_argument("--memory", choices=memory.STRATEGIES, default="full")
    parser.add_argument("--model", default=llm.DEFAULT_MODEL)
    parser.add_argument("--variant", default="baseline", choices=list(settings.VARIANTS))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    llm.set_model(args.model)
    settings.apply_variant(args.variant)
    trace.ENABLED = not args.quiet
    agent = agent_native_tools if args.agent == "native" else agent_text_protocol
    remember = memory.get_strategy(args.memory)
    turns: list[list[dict]] = []

    print(f"Chat: {args.agent} agent · {args.model} · memory={args.memory} · variant={args.variant}. Empty line to quit.")
    while question := input("\nYou: ").strip():
        if question == "/reset":
            turns, remember = [], memory.get_strategy(args.memory)
            print("(memory cleared)")
            continue
        history = remember(turns)
        if question == "/memory":
            print(f"({len(turns)} turns stored; next question would send {len(history)} messages, "
                  f"~{memory.estimate_tokens(history)} tokens)")
            continue
        record = agent.run_agent(question, history=history)
        turns.append(record.messages[len(history):])
        print(f"\nAgent: {record.answer}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
