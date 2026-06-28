"""Shared state: the chat log, the ideas board, and per-agent digests.

Pure data structures — no LLM calls. All mutating ops are guarded by a lock so the
orchestrator can step agents concurrently (asyncio + threads) without races.
"""

from __future__ import annotations

import threading

from .types import Digest, Idea, Message


class ChatLog:
    def __init__(self) -> None:
        self._msgs: list[Message] = []
        self._seq = 0
        self._lock = threading.Lock()

    def post(self, sender: str, to: str | None, text: str) -> Message:
        with self._lock:
            self._seq += 1
            msg = Message(sender=sender, to=to, text=text, ts=self._seq)
            self._msgs.append(msg)
            return msg

    def since(self, after_seq: int, agent: str) -> list[Message]:
        """Broadcasts + messages addressed to `agent`, newer than `after_seq`.

        Excludes the agent's own messages (it already knows what it said).
        """
        with self._lock:
            return [
                m
                for m in self._msgs
                if m.ts > after_seq
                and m.sender != agent
                and (m.to is None or m.to == agent)
            ]

    @property
    def head(self) -> int:
        with self._lock:
            return self._seq

    def all(self) -> list[Message]:
        with self._lock:
            return list(self._msgs)


class IdeasBoard:
    def __init__(self) -> None:
        self._ideas: list[Idea] = []
        self._seq = 0
        self._lock = threading.Lock()

    def add(self, title: str, description: str, beats: list[str], author: str) -> Idea:
        with self._lock:
            self._seq += 1
            idea = Idea(
                id=f"idea-{self._seq}",
                title=title,
                description=description,
                beats=list(beats),
                author=author,
            )
            self._ideas.append(idea)
            return idea

    def endorse(self, idea_id: str, by: str) -> bool:
        with self._lock:
            for idea in self._ideas:
                if idea.id == idea_id:
                    if by not in idea.endorsements:
                        idea.endorsements.append(by)
                    return True
            return False

    def all(self) -> list[Idea]:
        with self._lock:
            return list(self._ideas)


class DigestStore:
    def __init__(self) -> None:
        self._by_beat: dict[str, Digest] = {}
        self._lock = threading.Lock()

    def write(self, beat: str, author: str, content: str) -> None:
        with self._lock:
            self._by_beat[beat] = Digest(beat=beat, author=author, content=content)

    def read(self, beat: str | None = None) -> list[Digest]:
        with self._lock:
            if beat is None:
                return list(self._by_beat.values())
            d = self._by_beat.get(beat)
            return [d] if d else []
