# Code Plan — Think Tank: Cross-Domain Research Panel

> High-level code design. Interfaces & signatures only — no implementations yet.
> Build the text-tool version now, but architect the **perception/action seam** so
> a `computer-use` backend drops in later with no rewrite.

---

## 0. The key idea for future-proofing (read this first)

The agent loop must be **modality-agnostic**. An agent doesn't know whether it's
"using text tools" or "driving a desktop" — it asks an `Environment` what it sees
and hands back actions. Computer-use becomes *a different Environment*, not a
different Agent.

```
            ┌─────────────┐
            │    Agent     │  (model + memory + loop)  — never changes
            └──────┬──────┘
                   │ observe() / execute()
            ┌──────▼──────────────────┐
            │   Environment (Protocol) │  ← the seam
            └──────┬──────────────┬────┘
                   │              │
        ┌──────────▼───┐   ┌──────▼────────────┐
        │ PanelEnv     │   │ DesktopEnv (later) │
        │ (text tools) │   │ (computer-use)     │
        └──────────────┘   └────────────────────┘
```

- **Now:** `PanelEnvironment` — observation is *text* (new chat, the ideas board,
  my digest, my memory); tools are `web_search`, `post_message`, digest, ideas.
- **Later:** `DesktopEnvironment` — observation is a *screenshot* block; tools are
  Anthropic's `computer`/`bash`/`text_editor`. A `CompositeEnvironment` merges
  desktop + chat so a computer-use agent still participates in the panel.

Both implement the same protocol, so `Agent` / `Orchestrator` / `Memory` /
`Dashboard` are written once.

---

## 1. Module map

```
thinktank/
  __init__.py
  types.py        # Message, Idea, Digest, ToolResult, Observation
  environment.py  # Environment protocol + PanelEnvironment + (stub) DesktopEnvironment
  channel.py      # ChatLog + IdeasBoard + DigestStore (shared state; pure, no LLM)
  tools.py        # ToolSpec registry; text-tool implementations
  memory.py       # AgentMemory: tiered store + summarizer
  agents.py       # Agent: beat persona + loop
  orchestrator.py # round-based scheduler; concurrent agents per round
  llm.py          # Anthropic client wrapper (+ MockLLM)
  dashboard.py    # FastAPI + SSE live view
  run.py          # entrypoint: define beats, wire env, run N rounds
  config.py       # BEATS, round count, models, paths
```

---

## 2. Core data types (`types.py`)

```python
@dataclass
class Message:        # one shared-chat entry
    sender: str
    to: str | None    # None = broadcast; else addressed
    text: str
    ts: int

@dataclass
class Idea:           # one cross-domain idea on the board
    id: str
    title: str
    description: str
    beats: list[str]      # which domains it spans
    author: str
    endorsements: list[str]   # agent names backing it

@dataclass
class Digest:         # an agent's running summary of its beat
    beat: str
    author: str
    content: str          # markdown; appended/revised over rounds

@dataclass
class ToolResult:
    ok: bool
    content: list[dict]   # Anthropic content blocks (text and/or image)

@dataclass
class Observation:        # what an agent perceives this step
    blocks: list[dict]    # content blocks: text now, screenshots later
```

---

## 3. The seam (`environment.py`)

```python
class Environment(Protocol):
    name: str
    def tools(self) -> list[ToolSpec]: ...
    def observe(self, agent_id: str) -> Observation: ...
    def execute(self, agent_id: str, tool: str, input: dict) -> ToolResult: ...

class PanelEnvironment:          # built now
    # observe(): new chat (broadcast + addressed to me) + ideas board snapshot
    #            + my current digest + my memory summary, as text blocks
    # tools():   web_search, post_message, write_digest, read_digest,
    #            add_idea, endorse_idea, read_ideas
    # execute(): dispatch to channel / tools

class DesktopEnvironment:          # stub now (NotImplementedError), built later
    # observe(): screenshot block (+ optional a11y text)
    # tools():   anthropic "computer", "bash", "text_editor"
    # execute(): forward click/type/etc. to the VM driver

class CompositeEnvironment:        # later: desktop agent that also uses chat
    # merges tools + observations from several environments
```

> **This build:** fully implement `PanelEnvironment`; leave `DesktopEnvironment`
> a documented stub so the contract is visible and the later swap is obvious.

---

## 4. Shared state (`channel.py`)

```python
class ChatLog:
    def post(self, msg: Message) -> None
    def since(self, ts: int, for_agent: str) -> list[Message]   # broadcasts + addressed

class IdeasBoard:                  # append-only, with provenance
    def add(self, title, description, beats, author) -> Idea
    def endorse(self, idea_id: str, by: str) -> bool
    def all(self) -> list[Idea]

class DigestStore:                 # one digest per agent/beat
    def write(self, beat: str, author: str, content: str) -> None
    def read(self, beat: str | None = None) -> list[Digest]   # None = all beats
```
No claiming/locking needed — beats are fixed, so agents never contend. The board
is purely additive (post + endorse).

---

## 5. Tools (`tools.py`)

```python
@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict       # JSON schema (Anthropic tool format)
    handler: Callable[[str, dict], ToolResult]   # (agent_id, input) -> result
```
Toolset: `web_search` (mocked per-beat corpus first), `post_message`,
`write_digest`, `read_digest`, `add_idea`, `endorse_idea`, `read_ideas`.

---

## 6. Memory (`memory.py`)

```python
class AgentMemory:
    # tiers: working (recent steps/focus) · episodic (append log) · summary (rolling)
    def context_block(self) -> dict          # injected each step
    def record(self, event: str) -> None
    def maybe_summarize(self, llm) -> None    # re-summarize past a token threshold
    def save(self) / load(self)               # JSON per agent
```
Persisted as `runs/<run_id>/memory/<agent>.json` — legible, dashboard-inspectable.

---

## 7. Agent (`agents.py`)

```python
class Agent:
    def __init__(self, id, beat: dict, env: Environment, memory: AgentMemory, llm): ...
    def step(self, phase: str) -> StepResult:
        # 1 perceive: obs = env.observe(self.id); ctx = memory.context_block()
        # 2 think:    resp = llm.act(system=persona(beat, phase), obs+ctx, env.tools())
        # 3 act:      for each tool_use -> env.execute(...) -> tool_result
        # 4 observe:  feed results back; memory.record(...); maybe_summarize()
        # `phase` ∈ {SCAN, FUSE, DEEPEN} selects the per-round instructions
```
```python
@dataclass
class StepResult:        # emitted each turn → drives the per-agent widget
    agent: str
    phase: str
    action: str             # e.g. "web_search", "post_message", "add_idea"
    thought: str            # the model's reasoning text this turn (what it "thinks")
    messages_sent: list[Message]   # so the chat panel can render routing live
    digest_excerpt: str
```
The loop is identical regardless of environment — that's the whole point.

---

## 8. Orchestrator (`orchestrator.py`)

```python
class Orchestrator:
    def __init__(self, agents, chat, ideas, digests, rounds): ...
    async def run(self):
        # for each round r with phase in [SCAN, FUSE, DEEPEN, ...]:
        #     await asyncio.gather(*(a.step(phase) for a in agents))  # concurrent
        #     broadcast state to dashboard
        # output = digests + ideas board (persisted)
```
Concurrency is single-threaded asyncio: agents overlap on I/O-bound LLM + search
calls (real parallelism to watch), while shared-state writes stay race-free.
Fixed rounds → bounded cost and a clean stopping point.

---

## 9. LLM wrapper (`llm.py`)

```python
class LLM:
    def act(self, system: str, content: list[dict], tools: list[ToolSpec]) -> Response:
        # single Anthropic messages call with tool-use; returns text + tool_use blocks

class MockLLM(LLM):   # --mock: scripted, deterministic responses, no API key
    ...
```
`--mock` swaps in `MockLLM` + the fixed per-beat corpus so the whole system runs
offline, free, and deterministically (demo + smoke test without a key).

---

## 10. Dashboard (`dashboard.py`)

FastAPI app, SSE stream. Layout: a **chat panel** + a row of **per-agent widgets**
+ an **ideas board panel**.

**Chat panel — must show who-talks-to-whom and what they think.**
Each message renders with explicit routing and is color-coded per sender:
```
[AI & LLMs] → [Energy & Climate]:  "your fusion-control point connects to RL…"
[Biotech]   → all (broadcast):     "SOTA in protein design this round: …"
```
- `to = None` renders as `→ all`; an addressed message renders `→ [recipient]`.
- This comes straight from `Message{sender, to, text}` — the routing is already in
  the data model, the dashboard just renders it.
- "What they think": each chat entry shows the message text; the agent's *reasoning*
  (its think-step text, distinct from the posted message) shows in its own widget.

**Per-agent widget (one per agent) — individual progress.**
Each shows: beat name · current phase (SCAN/FUSE/DEEPEN) · current action (e.g.
"searching…", "writing digest", "posting idea") · latest **thought** (the model's
reasoning this turn) · a peek at its current digest. Driven by `StepResult` emitted
each turn (it carries `{agent, phase, action, thought, digest_excerpt}`).

**Ideas board panel:** ideas with their spanning beats, author, and endorsements.

Computer-use later: the per-agent widget just additionally renders the screenshot —
no other change, since widgets are already per-agent.

---

## 11. Build order
1. `types.py`, `channel.py`, `tools.py` — pure, unit-testable, no LLM.
2. `memory.py` — tiers + summarizer.
3. `llm.py` (+ MockLLM) + `environment.py` (PanelEnvironment).
4. `agents.py` — the loop.
5. `orchestrator.py` + `run.py` — end-to-end `--mock` run.
6. `dashboard.py` — live view.
7. `README.md` — design writeup (incl. the computer-use extension story).
