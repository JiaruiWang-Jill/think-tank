# Think Tank — Cross-Domain Research Panel

> **Purpose:** Portfolio / coding-demo artifact.
> **Scope:** Self-contained, no real-world side effects, no computer-use (yet).
> **Status:** Planning — not yet built. Discuss before implementing.

---

## 1. What it is

A **standing panel of domain-specialist research agents**. Each agent owns a
permanent "beat," continuously researches the state-of-the-art / hottest topics in
it, summarizes, and brainstorms new ideas. They share a **common chat channel** —
and the payoff is **cross-domain fusion**: novel ideas that only surface when one
beat's findings collide with another's.

This keeps the *interesting* part of AI Digest's "AI Village" — **autonomous
agents with their own standing goals, coordinating via chat** — while dropping the
hardest/least-insightful infra:
- ❌ Computer-use (virtual desktops, screenshots) — added later via a clean seam.
- ❌ Real-world side effects (emails, payments, posting) — risk, no upside.

We **keep** what demonstrates engineering skill:
- ✅ Concurrent multi-agent orchestration
- ✅ The Anthropic tool-use (function-calling) loop
- ✅ Self-managed, tiered, persistent memory
- ✅ A **chat channel that is load-bearing** (fusion happens here)
- ✅ A shared, accumulating **ideas board** (the deliverable)
- ✅ A live web dashboard

---

## 2. What it's for (the pitch)

A finished artifact that reads as *"this person can build real agent systems."*
It showcases long-horizon autonomy, memory, multi-agent coordination, and tool
use. The README documents the design and handled failure modes — for a portfolio,
the writeup is half the value.

---

## 3. The agents (the panel)

Four homogeneous **Domain Researcher** agents — identical loop, specialized only by
**beat** (config-driven; scales to N).

| Agent beat | Focus |
|---|---|
| **AI & LLMs** | agentic systems, reasoning, world models, on-device |
| **Biotech & Longevity** | AI drug discovery, gene editing, aging |
| **Energy & Climate Tech** | fusion, grid/storage, datacenter power |
| **Engagement & Social** | social platforms, online attention, virality, creator/community dynamics, recommendation algorithms |

Chosen for **heat × fusion density**: every pair of beats yields non-obvious
cross-domain ideas, which is exactly what the chat channel is built to surface.

---

## 4. How a run works — fixed rounds

Default **3 rounds**; agents act **concurrently** within each round (asyncio).

1. **SCAN** — each agent researches its beat (`web_search`), writes a **digest**
   (its own running doc) and posts a summary to chat.
2. **FUSE** — each agent reads the others' digests/summaries and brainstorms
   **cross-domain ideas**, posting them to chat + the shared **ideas board**.
3. **DEEPEN** — agents react to each other's ideas: combine, refine, endorse the
   strongest. The ideas board is finalized.

Round count is configurable. Bounded cost, clean to reason about and demo.

### Output (deliverable)
- **Per-agent digests** — each beat's running summary of the state of the art.
- **Cross-pollination ideas board** — accumulated cross-domain ideas, each tagged
  with the beats involved and which agents contributed/endorsed it.

---

## 5. Architecture

```
thinktank/
  __init__.py
  types.py        # Message, Idea, Digest, Action, ToolResult, Observation
  environment.py  # Environment protocol + PanelEnvironment + (stub) DesktopEnvironment
  channel.py      # ChatLog + IdeasBoard + DigestStore (shared state; pure, no LLM)
  tools.py        # web_search, post_message, write/read_digest, add/endorse/read_ideas
  memory.py       # per-agent tiered memory + summarizer
  agents.py       # Agent: beat persona + loop (perceive→think→act→observe)
  orchestrator.py # round-based scheduler; concurrent agents per round
  llm.py          # Anthropic client wrapper (+ MockLLM)
  dashboard.py    # FastAPI + SSE: chat + per-agent digest + ideas board
  run.py          # define beats, wire env, run N rounds
  config.py       # beats list, round count, models, paths
```

### Things designed to "shine"
- **Chat as the fusion mechanism** — agents genuinely read and build on each other.
- **Memory as a real subsystem** — tiered, with a re-read trigger.
- **Ideas board** — a tangible, growing artifact with provenance (who/which beats).
- **Live dashboard** — a **chat panel** that shows who-talks-to-whom (`[AI] → [Energy]: …`,
  or `→ all` for broadcasts) and what each says; a **per-agent widget** for each
  agent showing its phase, current action, latest reasoning ("thought"), and digest;
  and an **ideas board** of accumulating cross-domain ideas. Watch the fusion happen live.
- **README** — design decisions + failure modes.

---

## 5a. Runnability (hard requirement)
- Entrypoint: `python -m thinktank.run`. `requirements.txt` + README run section.
- **`--mock` mode**: per-beat fixed corpus + scripted LLM → runs offline, free,
  deterministic. Demoable without API credits; smoke-testable without a key.
- A tiny smoke test so "it runs" is verified, not assumed.

## 5b. Stack
- Python, `anthropic` SDK (Sonnet 4.6 as the agent model to start)
- FastAPI + server-sent events (SSE) for the dashboard
- ~700–900 lines total

---

## 6. Resolved decisions
- Design: **panel of domain-specialist researchers** (not worker/synthesizer).
- Beats: **AI/LLMs · Biotech/Longevity · Energy/Climate · Engagement/Social** (config).
- Output: **per-agent digests + shared cross-pollination ideas board**.
- Cadence: **fixed rounds** (default 3), agents concurrent within a round.
- Chat: **load-bearing** — sharing digests + cross-domain brainstorming.
- Persistence: **flat JSON files** (legible, dashboard-inspectable).
- web_search: **mocked per-beat corpus** in v1 (deterministic); real search is a swap.
- Models: all on **Sonnet 4.6** to start.

## 7. Computer-use future
The `Environment` protocol is the seam (see CODE_PLAN §0/§3). `PanelEnvironment`
(text tools) now; `DesktopEnvironment` (screenshots + `computer`/`bash` tools)
later, with **no rewrite** of the agent loop, memory, orchestrator, or dashboard.

## 8. Build order
1. `types.py`, `channel.py`, `tools.py` — pure, unit-testable, no LLM.
2. `memory.py` — tiers + summarizer.
3. `llm.py` (+ MockLLM) + `environment.py` (PanelEnvironment).
4. `agents.py` — the loop.
5. `orchestrator.py` + `run.py` — end-to-end `--mock` run.
6. `dashboard.py` — live view.
7. `README.md` — design writeup.
