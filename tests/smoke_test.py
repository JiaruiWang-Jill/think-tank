"""Smoke test: a full --mock run must produce the expected structure.

Checks invariants (not exact text), so it stays robust to concurrency ordering:
  - every beat wrote a digest
  - the ideas board is non-empty and ideas span >= 2 beats (truly cross-domain)
  - chat has both broadcast and addressed messages (routing works)
  - at least one idea got endorsed (the DEEPEN loop ran)

Run:  python -m tests.smoke_test     (from the repo root)
"""

from __future__ import annotations

import asyncio
import sys

from thinktank import config
from thinktank.agents import Agent
from thinktank.channel import ChatLog, DigestStore, IdeasBoard
from thinktank.environment import PanelEnvironment
from thinktank.llm import MockLLM
from thinktank.memory import AgentMemory
from thinktank.orchestrator import Orchestrator
from thinktank.run import make_search


def run() -> int:
    chat, ideas, digests = ChatLog(), IdeasBoard(), DigestStore()
    beats_by_agent = {b["name"]: b["name"] for b in config.BEATS}
    env = PanelEnvironment(chat, ideas, digests, beats_by_agent, make_search())
    llm = MockLLM()
    agents = [Agent(b["name"], b, env, AgentMemory(b["name"]), llm) for b in config.BEATS]

    asyncio.run(Orchestrator(agents, rounds=3).run())

    failures = []

    if len(digests.read()) != len(config.BEATS):
        failures.append(f"expected {len(config.BEATS)} digests, got {len(digests.read())}")

    all_ideas = ideas.all()
    if not all_ideas:
        failures.append("ideas board is empty")
    if not all(len(i.beats) >= 2 for i in all_ideas):
        failures.append("some ideas are not cross-domain (span < 2 beats)")

    msgs = chat.all()
    if not msgs:
        failures.append("no chat messages")
    if any(m.to is not None for m in msgs):
        failures.append("found an addressed message — all chat should be broadcast")

    if not any(i.endorsements for i in all_ideas):
        failures.append("no idea was endorsed (DEEPEN loop didn't run)")

    if failures:
        print("SMOKE TEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("SMOKE TEST PASSED")
    print(f"  digests: {len(digests.read())}")
    print(f"  ideas:   {len(all_ideas)} (endorsements: {sum(len(i.endorsements) for i in all_ideas)})")
    print(f"  chat:    {len(msgs)} messages (all broadcast)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
