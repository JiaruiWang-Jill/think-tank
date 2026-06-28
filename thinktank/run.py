"""Entrypoint: wire the panel and run it.

    python -m thinktank.run --mock                 # offline, free, deterministic
    python -m thinktank.run --mock --dashboard     # + live web view at :8000
    python -m thinktank.run --real                 # uses ANTHROPIC_API_KEY

In v1 web_search returns a fixed per-beat corpus (deterministic); swapping in a
real search backend is a one-function change (see make_search).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import json
import os
import re

from . import config, mock_data
from .agents import Agent
from .channel import ChatLog, DigestStore, IdeasBoard
from .environment import PanelEnvironment
from .llm import LLM, MockLLM
from .memory import AgentMemory
from .orchestrator import Orchestrator
from .types import StepResult, to_jsonable

RUNS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runs")


def make_search():
    def search(beat: str, query: str) -> list[dict]:
        return mock_data.MOCK_FINDINGS.get(beat, [])

    return search


def _safe(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def build(run_dir: str, mock: bool, model: str, max_tokens: int):
    chat, ideas, digests = ChatLog(), IdeasBoard(), DigestStore()
    beats_by_agent = {b["name"]: b["name"] for b in config.BEATS}
    env = PanelEnvironment(chat, ideas, digests, beats_by_agent, make_search())
    llm = MockLLM() if mock else LLM(model, max_tokens)

    agents = []
    for b in config.BEATS:
        mem_path = os.path.join(run_dir, "memory", f"{_safe(b['name'])}.json")
        agents.append(Agent(b["name"], b, env, AgentMemory(b["name"], mem_path), llm))
    return chat, ideas, digests, agents


def console_emitter(event: dict) -> None:
    t = event.get("type")
    if t == "phase_start":
        print(f"\n{'='*70}\n  ROUND {event['round']} — {event['phase']}\n{'='*70}")
    elif t == "step":
        r: StepResult = event["result"]
        print(f"\n• {r.agent}  [{r.action}]")
        if r.thought:
            print(f"    thinks: {r.thought}")
        for m in r.messages_sent:
            dest = m.to if m.to else "all"
            print(f"    chat:   [{r.agent}] -> [{dest}]: {m.text}")
    elif t == "done":
        print(f"\n{'='*70}\n  RUN COMPLETE\n{'='*70}")


def persist(run_dir: str, chat: ChatLog, ideas: IdeasBoard, digests: DigestStore) -> None:
    os.makedirs(run_dir, exist_ok=True)
    out = {
        "ideas": to_jsonable(ideas.all()),
        "digests": to_jsonable(digests.read()),
        "chat": to_jsonable(chat.all()),
    }
    with open(os.path.join(run_dir, "result.json"), "w") as f:
        json.dump(out, f, indent=2)


def print_summary(ideas: IdeasBoard, digests: DigestStore) -> None:
    print("\n--- CROSS-POLLINATION IDEAS BOARD ---")
    for i in ideas.all():
        print(f"  {i.id} \"{i.title}\"  [{', '.join(i.beats)}]")
        print(f"      by {i.author}, endorsed by {i.endorsements or '—'}")
        print(f"      {i.description}")
    print(f"\n--- DIGESTS ({len(digests.read())} beats) ---")
    for d in digests.read():
        first = d.content.splitlines()[0] if d.content else "(empty)"
        print(f"  {d.beat}: {first}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Think Tank — cross-domain research panel")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--mock", action="store_true", help="run offline with the mock LLM (default)")
    g.add_argument("--real", action="store_true", help="use the Anthropic API (needs key)")
    ap.add_argument("--rounds", type=int, default=config.DEFAULT_ROUNDS)
    ap.add_argument("--discuss", type=int, default=0,
                    help="free-discussion rounds after the structured rounds (each agent "
                         "posts once per round; e.g. --discuss 5)")
    ap.add_argument("--model", default=config.MODEL,
                    help="model id for --real (e.g. claude-haiku-4-5-20251001 for a cheaper run)")
    ap.add_argument("--max-tokens", type=int, default=config.MAX_TOKENS,
                    help="max output tokens per call (lower = cheaper)")
    ap.add_argument("--dashboard", action="store_true", help="serve a live web view")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    mock = not args.real  # mock is the default
    run_id = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(RUNS_DIR, run_id)

    chat, ideas, digests, agents = build(run_dir, mock, args.model, args.max_tokens)

    emit = console_emitter
    dash = None
    if args.dashboard:
        from . import dashboard as dashboard_mod

        dash = dashboard_mod.start(args.port, agents, chat, ideas, digests)

        def emit(event):  # noqa: F811 — fan out to console + dashboard
            console_emitter(event)
            dash.push(event)

    orch = Orchestrator(agents, args.rounds, emit=emit, discuss=args.discuss)
    asyncio.run(orch.run())

    persist(run_dir, chat, ideas, digests)
    print_summary(ideas, digests)
    print(f"\nSaved to {run_dir}")

    if dash is not None:
        print(f"\nDashboard live at http://localhost:{args.port}  (Ctrl+C to quit)")
        try:
            dash.wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
