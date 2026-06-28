"""Configuration: beats, rounds, model, and the agent prompts.

Everything tunable lives here. Adding/removing a beat is a one-line change to
BEATS; the rest of the system is beat-agnostic.
"""

from __future__ import annotations

# --- Model -------------------------------------------------------------------
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

# --- Panel -------------------------------------------------------------------
# The four domain "beats". `name` is also used as the agent id (kept short and
# human-readable so it renders nicely in the dashboard chat: "[AI & LLMs] -> ...").
BEATS = [
    {
        "name": "AI & LLMs",
        "focus": "agentic systems, reasoning, world models, on-device inference",
    },
    {
        "name": "Biotech & Longevity",
        "focus": "AI-driven drug discovery, gene editing, aging/longevity science",
    },
    {
        "name": "Energy & Climate Tech",
        "focus": "fusion progress, grid & storage, datacenter power demand",
    },
    {
        "name": "Engagement & Social",
        "focus": (
            "social platforms, online engagement & attention, virality, "
            "creator/community dynamics, recommendation algorithms"
        ),
    },
]

# --- Rounds ------------------------------------------------------------------
DEFAULT_ROUNDS = 3


def phase_sequence(rounds: int) -> list[str]:
    """Round 1 is SCAN; later rounds alternate FUSE / DEEPEN."""
    seq = ["SCAN"]
    cycle = ["FUSE", "DEEPEN"]
    i = 0
    while len(seq) < rounds:
        seq.append(cycle[i % len(cycle)])
        i += 1
    return seq[:rounds]


# --- Prompts -----------------------------------------------------------------
PREAMBLE = """\
You are one of several AI research agents on a standing panel. Each of you owns a
different domain ("beat"). You continuously track the state of the art in your beat,
and you collaborate in a shared channel to surface novel CROSS-DOMAIN ideas — ideas
that only appear when your beat's findings meet someone else's.

How the workspace works:
- CHAT: post_message shares findings and ideas (broadcast, or address an agent by
  name). READ what others posted before brainstorming — fusion is the goal.
- DIGEST: write_digest / read_digest maintains YOUR running summary of your beat's
  state of the art. read_digest also reads other agents' digests.
- IDEAS BOARD: add_idea posts a cross-domain idea (title, 1-2 sentence description,
  which beats it spans). endorse_idea backs someone else's strong idea. read_ideas
  shows the board.
- MEMORY: you keep private memory across rounds. Re-read it when you lose the thread.

Rules:
- Be concise and specific — concrete techniques/findings beat vague trends.
- The best cross-domain ideas are surprising but plausible. Avoid forced mashups.
- Build on others by name when you riff on their finding.
"""

BEAT_BLOCK = """\

YOUR BEAT: {name} — {focus}
You are the panel's expert on {name}. Track its state of the art (specific
techniques, results, hot debates), keep your digest current, and actively look for
surprising-but-plausible connections between {name} and the other panelists' beats.
"""

PHASE_INSTRUCTIONS = {
    "SCAN": (
        "THIS ROUND (SCAN): research the hottest / state-of-the-art topics in your "
        "beat with web_search, distill them into your digest with write_digest, then "
        "post a short summary of your findings to chat (broadcast)."
    ),
    "FUSE": (
        "THIS ROUND (FUSE): read the other agents' digests with read_digest, then "
        "brainstorm cross-domain ideas connecting your beat to theirs. Post each "
        "promising idea with add_idea (name the beats it spans), and share it with the "
        "whole panel via post_message (you can mention which beat it connects to in the "
        "text)."
    ),
    "DEEPEN": (
        "THIS ROUND (DEEPEN): read the ideas board with read_ideas, endorse the "
        "strongest idea you did not author with endorse_idea, and post a message to the "
        "whole panel building on or combining it (credit its author in the text)."
    ),
    "REPLY": (
        "A message was just posted to the panel (it may be from a human collaborator). "
        "Decide whether it's relevant to your beat or whether you have something "
        "worthwhile to add. If so, reply concretely (address people by name), and if "
        "they asked for ideas, add_idea for new ones that fit. If it's NOT relevant to "
        "you or you'd just be echoing others, call skip_turn and stay silent — you are "
        "not required to respond."
    ),
    "DISCUSS": (
        "OPEN DISCUSSION — no agenda. Read the recent chat, then, ONLY if you have "
        "something genuinely worth saying, post ONE conversational message: ask a "
        "pointed question of a specific agent by name, answer a question someone asked "
        "you, push back, or riff on an idea. Be specific — not a summary. If you have "
        "nothing fresh to add this round, call skip_turn and stay silent. Not every "
        "agent needs to speak every round."
    ),
}


def build_system(beat: dict, phase: str) -> str:
    return (
        PREAMBLE
        + BEAT_BLOCK.format(name=beat["name"], focus=beat["focus"])
        + "\n"
        + PHASE_INSTRUCTIONS.get(phase, PHASE_INSTRUCTIONS["FUSE"])
    )
