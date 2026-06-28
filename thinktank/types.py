"""Core data types shared across the package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """One shared-chat entry. `to=None` means broadcast."""

    sender: str
    to: str | None
    text: str
    ts: int  # monotonic sequence number assigned by ChatLog

    def render(self) -> str:
        dest = self.to if self.to else "all"
        return f"[{self.sender}] -> [{dest}]: {self.text}"


@dataclass
class Idea:
    """One cross-domain idea on the board."""

    id: str
    title: str
    description: str
    beats: list[str]
    author: str
    endorsements: list[str] = field(default_factory=list)


@dataclass
class Digest:
    """An agent's running summary of its beat."""

    beat: str
    author: str
    content: str


@dataclass
class ToolResult:
    ok: bool
    content: list[dict]  # Anthropic content blocks (text and/or image)


@dataclass
class Observation:
    """What an agent perceives this step (text now, screenshots later)."""

    blocks: list[dict]


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict


@dataclass
class Response:
    """A single model turn: free text + any tool calls."""

    text: str
    tool_uses: list[ToolUse]
    raw_content: list[dict]  # assistant content blocks to append to the transcript


@dataclass
class StepResult:
    """Emitted each turn -> drives the per-agent widget + chat panel."""

    agent: str
    phase: str
    action: str
    thought: str
    messages_sent: list[Message]
    digest_excerpt: str
    ideas_added: list[Idea] = field(default_factory=list)


def to_jsonable(obj: Any) -> Any:
    """Best-effort conversion of our dataclasses to plain dict/list for JSON."""
    from dataclasses import asdict, is_dataclass

    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    return obj
