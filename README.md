# Think Tank — a panel of AI researchers that brainstorm together

Think Tank is a small "research panel" of AI agents. Each agent is an expert in one
field, keeps up with what's new there, and then **talks with the others to spark
new ideas at the intersections of their fields**.

The whole point is **emergent research ideas through open agent discussion** — you
don't get them from any single agent, only from the conversation between them.

The four experts:

| Agent | Watches |
|---|---|
| 🤖 **AI & LLMs** | agentic systems, reasoning, on-device models |
| 🧬 **Biotech & Longevity** | drug discovery, gene editing, aging science |
| ⚡ **Energy & Climate Tech** | fusion, grids & storage, datacenter power |
| 📣 **Engagement & Social** | social platforms, attention, recommendation |

You can change, add, or remove fields easily.

## Demo


https://github.com/user-attachments/assets/36475cd6-8bff-4795-ae92-c328e1f421ba


▶️ **[Watch the demo](https://github.com/JiaruiWang-Jill/think-tank/blob/main/assets/demo.mp4)** — click the image above to play it on GitHub.

---

## What you get

- **A live conversation** you can watch unfold — the agents post to a shared chat,
  react to each other, and build on each other's points.
- **A board of cross-domain ideas** — every interesting connection an agent makes
  becomes an idea on the board (e.g. *"use AI datacenter waste heat to power
  longevity bioreactors"*), tagged with which fields it bridges and who backed it.
- **Open-ended discussion** — after the structured rounds, the agents just talk
  freely about whatever they find interesting, and can **choose to stay quiet** if a
  topic isn't their area. Not every agent speaks every time — it feels like a real
  panel.
- **You can join in** — type into the chat and the agents will respond.

---

## Getting started

```bash
# Try it free, offline (no setup, no account):
python3 -m thinktank.run --mock --dashboard
```

Then open **http://localhost:8000** in your browser.

To run it with real AI (richer ideas and discussion), you need an Anthropic API
key set up, then:

```bash
python3 -m thinktank.run --real --dashboard
```

> Tip for a cheaper real run: add `--model claude-haiku-4-5-20251001`.

---

## How a session flows

1. **Each expert scans its field** and shares a quick summary.
2. **They cross-pollinate** — reading each other's summaries and posting
   cross-domain ideas to the board.
3. **They react** — endorsing and building on the strongest ideas.
4. **Open discussion** — the agents talk freely with each other (ask questions,
   debate, riff), or sit a round out if they've nothing to add.

Want more free discussion? Add `--discuss N` to give the agents N extra open rounds
of conversation after the structured part:

```bash
python3 -m thinktank.run --real --discuss 5 --dashboard
```

`N` is the most each agent will speak — so `--discuss 5` means up to five turns per
agent of free back-and-forth. Then sit back and see where the conversation goes.

---

## The dashboard

- **Agent panels** — what each expert is doing and thinking right now, plus its
  running summary of its field.
- **Chat** — the full conversation. Every message goes to the whole panel.
- **Ideas board** — the cross-domain ideas as they accumulate, with the fields they
  connect and who endorsed them.
- **Message box** — write to the panel yourself; the agents will read it and reply
  (or skip it if it's not relevant to them).

---

## Handy options

| Option | What it does |
|---|---|
| `--mock` | Run offline with no API key (great for trying it out) |
| `--real` | Use real AI (needs an Anthropic API key + credits) |
| `--dashboard` | Open the live web view at http://localhost:8000 |
| `--discuss N` | Add N rounds of free agent discussion at the end |
| `--rounds N` | How many structured rounds before discussion (default 3) |
| `--model …` | Pick the AI model (e.g. a cheaper one for lighter runs) |

To stop a run, press **Ctrl+C** in the terminal.

Every session is saved to a `runs/` folder so you can revisit the ideas later.
