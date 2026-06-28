"""The Agent: a beat persona + tiered memory + the perceive->think->act loop.

The loop is identical regardless of which Environment backs it — that is the whole
point of the seam in environment.py.
"""

from __future__ import annotations

from . import config
from .environment import Environment
from .memory import AgentMemory
from .types import Message, StepResult

MAX_INNER_STEPS = 6  # safety cap on the per-turn tool loop

# Conversational phases get a restricted toolset so the agent actually talks
# (otherwise the model may wander off into web_search/write_digest and never post).
PHASE_TOOLS = {
    "REPLY": {"post_message", "add_idea", "read_ideas", "read_digest", "skip_turn"},
    "DISCUSS": {"post_message", "add_idea", "read_ideas", "read_digest", "skip_turn"},
}


class Agent:
    def __init__(self, agent_id: str, beat: dict, env: Environment, memory: AgentMemory, llm):
        self.id = agent_id
        self.beat = beat
        self.env = env
        self.memory = memory
        self.llm = llm

    def step(self, phase: str) -> StepResult:
        obs = self.env.observe(self.id)
        ctx = self.memory.context_block()
        system = config.build_system(self.beat, phase)

        messages = [{"role": "user", "content": obs.blocks + [ctx]}]
        mock_ctx = {"beat": self.id, "phase": phase}

        tools = self.env.tools()
        allowed = PHASE_TOOLS.get(phase)
        if allowed:
            tools = [t for t in tools if t.name in allowed]

        last_thought = ""
        last_action = "thinking"
        messages_sent: list[Message] = []
        ideas_added = []
        skipped = False

        for _ in range(MAX_INNER_STEPS):
            resp = self.llm.act(system, messages, tools, mock_ctx=mock_ctx)

            if not resp.tool_uses:
                if not last_thought:
                    last_thought = resp.text
                break

            # Keep the reasoning tied to an actual action, not the final wrap-up turn.
            if resp.text:
                last_thought = resp.text

            messages.append({"role": "assistant", "content": resp.raw_content})
            tool_result_blocks = []
            for tu in resp.tool_uses:
                last_action = tu.name
                if tu.name == "skip_turn":
                    skipped = True
                if tu.name == "post_message":
                    tu.input["to"] = None  # all chat is broadcast to the whole panel
                    messages_sent.append(
                        Message(self.id, None, tu.input.get("text", ""), 0)
                    )
                result = self.env.execute(self.id, tu.name, tu.input)
                if tu.name == "add_idea":
                    ideas_added.append(tu.input.get("title", ""))
                self.memory.record(f"{phase}: {tu.name}")
                tool_result_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": result.content,
                    }
                )
            messages.append({"role": "user", "content": tool_result_blocks})

            # Conversational turns are one-shot: stop once the agent has posted or skipped
            # (reading tools like read_ideas don't count, so it can look first then speak).
            if phase in PHASE_TOOLS and (messages_sent or skipped):
                break

        # Agents may opt out of a conversational turn via skip_turn (stay silent).
        # Safety net only when they neither posted nor explicitly skipped but left
        # substantive prose — post it so a genuine reply isn't lost.
        if phase in PHASE_TOOLS and not messages_sent and not skipped and last_thought:
            self.env.execute(self.id, "post_message", {"to": None, "text": last_thought})
            messages_sent.append(Message(self.id, None, last_thought, 0))
            last_action = "post_message"

        self.memory.maybe_summarize(self.llm)
        self.memory.save()

        my_digest = self.env.digests.read(self.beat["name"]) if hasattr(self.env, "digests") else []
        excerpt = my_digest[0].content[:240] if my_digest else ""

        return StepResult(
            agent=self.id,
            phase=phase,
            action=last_action,
            thought=last_thought,
            messages_sent=messages_sent,
            digest_excerpt=excerpt,
        )
