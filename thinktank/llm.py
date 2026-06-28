"""LLM wrapper: a real Anthropic-backed client and a deterministic MockLLM.

Isolating the model call here is what makes computer-use a future drop-in: adding
the `computer` tool + sending image blocks is the same `act()` call.

The MockLLM drives a realistic run with no API key by inspecting the transcript:
it counts how many tool results have come back this step and follows a fixed
per-phase script, building tool arguments from the prior tool results (so it
genuinely "uses" the search output, the digests, the ideas board).
"""

from __future__ import annotations

import json

from . import config, mock_data
from .tools import ToolSpec
from .types import Response, ToolUse


class LLM:
    """Real Anthropic-backed client."""

    def __init__(self, model: str, max_tokens: int = 1024) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._client = None

    def _client_lazy(self):
        if self._client is None:
            import anthropic  # imported lazily so --mock needs no dependency

            self._client = anthropic.Anthropic()
        return self._client

    def act(
        self,
        system: str,
        messages: list[dict],
        tools: list[ToolSpec],
        *,
        mock_ctx: dict | None = None,
    ) -> Response:
        client = self._client_lazy()
        resp = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            tools=[t.to_anthropic() for t in tools],
            messages=messages,
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        tool_uses = [
            ToolUse(id=b.id, name=b.name, input=dict(b.input))
            for b in resp.content
            if b.type == "tool_use"
        ]
        raw = [b.model_dump() for b in resp.content]
        return Response(text=text, tool_uses=tool_uses, raw_content=raw)

    def summarize(self, prior: str, new_events: str) -> str:
        client = self._client_lazy()
        resp = client.messages.create(
            model=self.model,
            max_tokens=256,
            system="Summarize the agent's activity concisely in 1-2 sentences.",
            messages=[{"role": "user", "content": f"Prior: {prior}\nNew: {new_events}"}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")


# Fixed per-phase action scripts for the mock.
_SCRIPTS = {
    "SCAN": ["web_search", "write_digest", "post_message"],
    "FUSE": ["read_digest", "add_idea", "post_message"],
    "DEEPEN": ["read_ideas", "endorse_idea", "post_message"],
    "REPLY": ["post_message"],
    "DISCUSS": ["post_message"],
}


def _tool_results(messages: list[dict]) -> list[dict]:
    """Extract parsed JSON payloads of tool_result blocks, in order."""
    out: list[dict] = []
    for m in messages:
        if m.get("role") != "user":
            continue
        content = m.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                inner = block.get("content", [])
                text = ""
                if isinstance(inner, list):
                    for ib in inner:
                        if isinstance(ib, dict) and ib.get("type") == "text":
                            text += ib.get("text", "")
                try:
                    out.append(json.loads(text))
                except (json.JSONDecodeError, ValueError):
                    out.append({})
    return out


class MockLLM(LLM):
    """Deterministic, no-API stand-in. Same interface as LLM."""

    def __init__(self, model: str = "mock", max_tokens: int = 1024) -> None:
        super().__init__(model, max_tokens)

    def act(
        self,
        system: str,
        messages: list[dict],
        tools: list[ToolSpec],
        *,
        mock_ctx: dict | None = None,
    ) -> Response:
        ctx = mock_ctx or {}
        beat = ctx.get("beat", "Unknown")
        phase = ctx.get("phase", "FUSE")
        results = _tool_results(messages)
        done = len(results)
        script = _SCRIPTS.get(phase, _SCRIPTS["FUSE"])

        if done >= len(script):
            return self._text(f"[{beat}] {phase} complete for this round.")

        action = script[done]
        if action == "post_message" and phase == "REPLY":
            text = (
                f"Good steer — I'll bias my {beat} thinking toward that angle and "
                "post fresh ideas on it next round."
            )
            return self._tool("Replying to the human's request.", "post_message",
                              {"to": "You", "text": text}, phase, done)
        if action == "post_message" and phase == "DISCUSS":
            others = [b["name"] for b in config.BEATS if b["name"] != beat]
            target = others[sum(ord(c) for c in beat) % len(others)] if others else beat
            text = (
                f"@{target}, genuine question — of everything moving in your field, "
                f"what would change how I think about {beat}?"
            )
            return self._tool("Opening a discussion thread.", "post_message",
                              {"to": target, "text": text}, phase, done)
        builder = getattr(self, f"_build_{action}")
        thought, name, tool_input = builder(beat, results)
        return self._tool(thought, name, tool_input, phase, done)

    # --- response helpers ---
    def _text(self, text: str) -> Response:
        return Response(text=text, tool_uses=[], raw_content=[{"type": "text", "text": text}])

    def _tool(self, thought, name, tool_input, phase, idx) -> Response:
        tid = f"tu_{phase}_{idx}"
        raw = [
            {"type": "text", "text": thought},
            {"type": "tool_use", "id": tid, "name": name, "input": tool_input},
        ]
        return Response(
            text=thought,
            tool_uses=[ToolUse(id=tid, name=name, input=tool_input)],
            raw_content=raw,
        )

    # --- per-action argument builders ---
    def _pick(self, options: list[str], beat: str, salt: int = 0) -> str:
        """Deterministic per-beat choice so phrasing varies but runs reproduce."""
        return options[(sum(ord(c) for c in beat) + salt) % len(options)]

    def _findings(self, results) -> list[dict]:
        for r in results:
            if r.get("_tool") == "web_search":
                return r.get("findings", [])
        return []

    def _build_web_search(self, beat, results):
        return (
            f"Let me catch up on what's moving in {beat} right now.",
            "web_search",
            {"query": f"latest {beat} state of the art 2026"},
        )

    def _build_write_digest(self, beat, results):
        content = mock_data.build_digest_from_findings(beat, self._findings(results))
        return (
            "Pulling the key threads together into my digest.",
            "write_digest",
            {"content": content},
        )

    def _build_read_digest(self, beat, results):
        return (
            "Curious what everyone else turned up — reading their digests.",
            "read_digest",
            {},
        )

    def _build_add_idea(self, beat, results):
        idea = mock_data.MOCK_IDEAS.get(beat, {})
        target = idea.get("target", beat)
        return (
            f"There's a real connection to {target} here, not a forced mashup.",
            "add_idea",
            {
                "title": idea.get("title", f"{beat} idea"),
                "description": idea.get("description", ""),
                "beats": [beat, target],
            },
        )

    def _build_read_ideas(self, beat, results):
        return ("Let me see which ideas on the board have legs.", "read_ideas", {})

    def _build_endorse_idea(self, beat, results):
        ideas = []
        for r in results:
            if r.get("_tool") == "read_ideas":
                ideas = r.get("ideas", [])
        target = next((i for i in ideas if i.get("author") != beat), None)
        if not target:
            return ("Nothing worth endorsing yet — I'll keep thinking.", "read_ideas", {})
        return (
            f"{target['author']}'s idea is the strongest one up there — backing it.",
            "endorse_idea",
            {"idea_id": target["id"]},
        )

    # --- the human-like chat messages ---
    def _build_post_message(self, beat, results):
        idea = mock_data.MOCK_IDEAS.get(beat, {})

        # SCAN: broadcast the most striking finding, conversationally.
        if any(r.get("_tool") == "write_digest" for r in results):
            findings = self._findings(results)
            top = findings[0] if findings else {"title": "some new work", "snippet": ""}
            openers = [
                f"Spent this round deep in {beat}. The thing that really jumped out:",
                f"Okay, {beat} update — the headline for me this round is:",
                f"Been digging through {beat}. What surprised me most:",
            ]
            text = (
                f"{self._pick(openers, beat)} {top['title']} — {top['snippet']} "
                "Does this spark anything on your end?"
            )
            return ("Sharing the finding I think the others will care about.", "post_message",
                    {"text": text})

        # FUSE: address the target beat personally about the shared idea.
        if any(r.get("_tool") == "add_idea" for r in results):
            target = idea.get("target")
            openers = [
                f"{target}, I keep circling back to where our fields overlap.",
                f"Hey {target} — this one's been nagging at me.",
                f"{target}, hear me out, I think there's something between our beats.",
            ]
            text = (
                f"{self._pick(openers, beat)} {idea.get('description','')} "
                f"I put it on the board as \"{idea.get('title','')}\" — worth building together?"
            )
            return (f"Reaching out to {target} about the overlap I see.", "post_message",
                    {"to": target, "text": text})

        # DEEPEN: reply to the author we endorsed, adding our own angle.
        endorsed = next((r for r in results if r.get("_tool") == "endorse_idea"), None)
        ideas_seen = next((r.get("ideas", []) for r in results if r.get("_tool") == "read_ideas"), [])
        if endorsed:
            author = endorsed.get("author")
            title = next((i["title"] for i in ideas_seen if i.get("author") == author), "your idea")
            replies = [
                f"{author}, \"{title}\" really clicks for me. From the {beat} side, "
                "I think we could push it further — want to co-develop it?",
                f"Strong work, {author} — \"{title}\" is the one I'd bet on. "
                f"{beat} could contribute the missing piece here. Shall we team up?",
            ]
            return (f"Building on {author}'s idea with a {beat} angle.", "post_message",
                    {"to": author, "text": self._pick(replies, beat)})

        return ("A quick note to the panel.", "post_message",
                {"text": f"Still chewing on how {beat} connects to the rest."})

    def summarize(self, prior: str, new_events: str) -> str:
        joined = (prior + " | " + new_events).strip(" |")
        return joined[:200]
