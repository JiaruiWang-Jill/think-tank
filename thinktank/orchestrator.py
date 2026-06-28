"""Round-based scheduler. Agents step concurrently within each phase.

Phases run as barriers: every agent finishes SCAN before anyone starts FUSE, so
FUSE can rely on all digests existing, and DEEPEN on all ideas existing.
Concurrency is asyncio + threads (the LLM/search calls are blocking I/O), giving
real overlap to watch while shared state stays lock-guarded in channel.py.
"""

from __future__ import annotations

import asyncio
from typing import Callable

from . import config
from .agents import Agent
from .types import StepResult


class Orchestrator:
    def __init__(
        self,
        agents: list[Agent],
        rounds: int,
        emit: Callable[[dict], None] | None = None,
        discuss: int = 0,
    ):
        self.agents = agents
        self.rounds = rounds
        self.discuss = discuss  # free-discussion rounds after the structured rounds
        self.emit = emit or (lambda e: None)

    async def run(self) -> list[StepResult]:
        # structured rounds, then `discuss` open-discussion rounds (each agent posts once)
        phases = config.phase_sequence(self.rounds) + ["DISCUSS"] * self.discuss
        all_results: list[StepResult] = []
        for rnd, phase in enumerate(phases, start=1):
            self.emit({"type": "phase_start", "round": rnd, "phase": phase})
            results = await asyncio.gather(
                *(asyncio.to_thread(a.step, phase) for a in self.agents)
            )
            for r in results:
                all_results.append(r)
                self.emit({"type": "step", "round": rnd, "result": r})
            self.emit({"type": "phase_end", "round": rnd, "phase": phase})
        self.emit({"type": "done"})
        return all_results
