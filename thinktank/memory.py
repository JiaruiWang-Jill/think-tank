"""Per-agent tiered memory.

Tiers:
  working  — recent steps / current focus (kept in full, injected each turn)
  episodic — append-only log of everything (persisted)
  summary  — rolling natural-language summary of older working items

`maybe_summarize` folds the oldest working items into the summary once working
grows past a threshold — the "re-read trigger" in miniature. The default fold is
deterministic (no LLM) so --mock stays reproducible; pass a real llm to get a
model-written summary instead.
"""

from __future__ import annotations

import json
import os

WORKING_LIMIT = 8
KEEP_RECENT = 4


class AgentMemory:
    def __init__(self, agent_id: str, path: str | None = None) -> None:
        self.agent_id = agent_id
        self.path = path
        self.working: list[str] = []
        self.episodic: list[str] = []
        self.summary: str = ""

    def context_block(self) -> dict:
        recent = "\n".join(f"- {w}" for w in self.working[-KEEP_RECENT:]) or "- (none yet)"
        text = (
            "YOUR MEMORY\n"
            f"Summary so far: {self.summary or '(nothing yet)'}\n"
            f"Recent activity:\n{recent}"
        )
        return {"type": "text", "text": text}

    def record(self, event: str) -> None:
        self.working.append(event)
        self.episodic.append(event)

    def maybe_summarize(self, llm=None) -> None:
        if len(self.working) <= WORKING_LIMIT:
            return
        old = self.working[:-KEEP_RECENT]
        self.working = self.working[-KEEP_RECENT:]
        folded = "; ".join(old)
        if llm is not None and hasattr(llm, "summarize"):
            self.summary = llm.summarize(self.summary, folded)
        else:
            self.summary = (self.summary + " | " + folded).strip(" |")

    def save(self) -> None:
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(
                {"agent": self.agent_id, "summary": self.summary, "episodic": self.episodic},
                f,
                indent=2,
            )
