"""Tool specifications (Anthropic tool-use format).

The schemas live here; execution lives in PanelEnvironment.execute. Keeping them
separate is what lets a future DesktopEnvironment expose a different toolset without
touching the agent loop.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict

    def to_anthropic(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


def text_tool_specs() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="web_search",
            description="Search for recent state-of-the-art topics in your beat.",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
        ToolSpec(
            name="write_digest",
            description="Write/replace your running digest of your beat's state of the art.",
            input_schema={
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
            },
        ),
        ToolSpec(
            name="read_digest",
            description="Read digests. Omit 'beat' to read all agents' digests.",
            input_schema={
                "type": "object",
                "properties": {"beat": {"type": "string"}},
            },
        ),
        ToolSpec(
            name="post_message",
            description="Post to the shared chat. Omit 'to' to broadcast; set it to "
                        "another agent's beat name to address them directly.",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        ),
        ToolSpec(
            name="add_idea",
            description="Post a cross-domain idea to the shared ideas board.",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "beats": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "description", "beats"],
            },
        ),
        ToolSpec(
            name="endorse_idea",
            description="Endorse an existing idea you did not author, by its id.",
            input_schema={
                "type": "object",
                "properties": {"idea_id": {"type": "string"}},
                "required": ["idea_id"],
            },
        ),
        ToolSpec(
            name="read_ideas",
            description="Read all ideas currently on the board.",
            input_schema={"type": "object", "properties": {}},
        ),
        ToolSpec(
            name="skip_turn",
            description="Stay silent this turn. Call this if the conversation isn't "
                        "relevant to your beat or you have nothing worthwhile to add — "
                        "you are not required to speak.",
            input_schema={"type": "object", "properties": {}},
        ),
    ]
