"""The Environment seam.

`Agent` only ever calls `env.observe()` / `env.execute()`, so swapping the text
workspace for a computer-use desktop later is a matter of adding a new Environment
implementation — the agent loop, memory, orchestrator, and dashboard are untouched.
"""

from __future__ import annotations

import json
import threading
from typing import Callable, Protocol

from .channel import ChatLog, DigestStore, IdeasBoard
from .tools import ToolSpec, text_tool_specs
from .types import Observation, ToolResult


class Environment(Protocol):
    name: str

    def tools(self) -> list[ToolSpec]: ...
    def observe(self, agent_id: str) -> Observation: ...
    def execute(self, agent_id: str, tool: str, input: dict) -> ToolResult: ...


def _json_block(payload: dict) -> list[dict]:
    return [{"type": "text", "text": json.dumps(payload)}]


class PanelEnvironment:
    """Text workspace: chat + ideas board + digests, exposed as tools."""

    name = "panel-text"

    def __init__(
        self,
        chat: ChatLog,
        ideas: IdeasBoard,
        digests: DigestStore,
        beats_by_agent: dict[str, str],
        search_fn: Callable[[str, str], list[dict]],
    ) -> None:
        self.chat = chat
        self.ideas = ideas
        self.digests = digests
        self.beats_by_agent = beats_by_agent
        self.search_fn = search_fn
        self._last_seen: dict[str, int] = {a: 0 for a in beats_by_agent}
        self._lock = threading.Lock()

    def tools(self) -> list[ToolSpec]:
        return text_tool_specs()

    def observe(self, agent_id: str) -> Observation:
        head = self.chat.head
        new_msgs = self.chat.since(self._last_seen.get(agent_id, 0), agent_id)
        self._last_seen[agent_id] = head

        chat_text = "\n".join(m.render() for m in new_msgs) or "(no new messages)"
        ideas = self.ideas.all()
        ideas_text = (
            "\n".join(
                f"- {i.id} \"{i.title}\" [{', '.join(i.beats)}] by {i.author} "
                f"(+{len(i.endorsements)})"
                for i in ideas
            )
            or "(empty)"
        )
        my_beat = self.beats_by_agent[agent_id]
        my_digest = self.digests.read(my_beat)
        digest_text = my_digest[0].content if my_digest else "(not written yet)"

        blocks = [
            {"type": "text", "text": f"=== NEW CHAT ===\n{chat_text}"},
            {"type": "text", "text": f"=== IDEAS BOARD ===\n{ideas_text}"},
            {"type": "text", "text": f"=== YOUR DIGEST ===\n{digest_text}"},
        ]
        return Observation(blocks=blocks)

    def execute(self, agent_id: str, tool: str, input: dict) -> ToolResult:
        beat = self.beats_by_agent.get(agent_id, agent_id)
        try:
            if tool == "web_search":
                findings = self.search_fn(beat, input.get("query", ""))
                return ToolResult(True, _json_block({"_tool": tool, "findings": findings}))

            if tool == "write_digest":
                self.digests.write(beat, agent_id, input.get("content", ""))
                return ToolResult(True, _json_block({"_tool": tool, "ok": True}))

            if tool == "read_digest":
                rows = self.digests.read(input.get("beat"))
                data = [{"beat": d.beat, "author": d.author, "content": d.content} for d in rows]
                return ToolResult(True, _json_block({"_tool": tool, "digests": data}))

            if tool == "post_message":
                self.chat.post(agent_id, input.get("to"), input.get("text", ""))
                return ToolResult(True, _json_block({"_tool": tool, "ok": True}))

            if tool == "add_idea":
                idea = self.ideas.add(
                    input.get("title", ""),
                    input.get("description", ""),
                    input.get("beats", [beat]),
                    agent_id,
                )
                return ToolResult(True, _json_block({"_tool": tool, "id": idea.id}))

            if tool == "endorse_idea":
                idea_id = input.get("idea_id", "")
                author = next((i.author for i in self.ideas.all() if i.id == idea_id), None)
                ok = self.ideas.endorse(idea_id, agent_id)
                return ToolResult(ok, _json_block({"_tool": tool, "ok": ok, "author": author}))

            if tool == "read_ideas":
                data = [
                    {
                        "id": i.id,
                        "title": i.title,
                        "author": i.author,
                        "beats": i.beats,
                        "endorsements": i.endorsements,
                    }
                    for i in self.ideas.all()
                ]
                return ToolResult(True, _json_block({"_tool": tool, "ideas": data}))

            if tool == "skip_turn":
                return ToolResult(True, _json_block({"_tool": tool, "ok": True}))

            return ToolResult(False, _json_block({"_tool": tool, "error": "unknown tool"}))
        except Exception as e:  # keep one bad tool call from killing the run
            return ToolResult(False, _json_block({"_tool": tool, "error": str(e)}))


class DesktopEnvironment:
    """Computer-use backend — intentionally a stub for now.

    Implementing this is the entire 'add computer-use later' story: observe()
    returns a screenshot block, tools() returns Anthropic's computer/bash/text_editor,
    and execute() forwards click/type/etc. to a VM driver. Nothing else changes.
    """

    name = "desktop"

    def tools(self) -> list[ToolSpec]:
        raise NotImplementedError("DesktopEnvironment is a planned future backend.")

    def observe(self, agent_id: str) -> Observation:
        raise NotImplementedError("DesktopEnvironment is a planned future backend.")

    def execute(self, agent_id: str, tool: str, input: dict) -> ToolResult:
        raise NotImplementedError("DesktopEnvironment is a planned future backend.")
