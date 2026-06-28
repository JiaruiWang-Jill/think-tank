"""Fixed corpus + canned outputs for --mock mode.

Lets the whole system run offline, free, and deterministically (demo + smoke test
without an API key). Real mode ignores all of this.
"""

from __future__ import annotations

# Per-beat "search results" the mock web_search returns.
MOCK_FINDINGS: dict[str, list[dict]] = {
    "AI & LLMs": [
        {"title": "Long-horizon agentic loops", "source": "arxiv:2026.0142",
         "snippet": "Tool-using agents now sustain multi-day tasks via external memory."},
        {"title": "Reasoning via verifiers", "source": "blog:lab-x",
         "snippet": "Self-verification + search at inference time lifts hard-task accuracy."},
        {"title": "On-device small models", "source": "press:edge-ai",
         "snippet": "3B-class models hit useful quality on laptops/phones."},
    ],
    "Biotech & Longevity": [
        {"title": "Generative protein design", "source": "nature:2026",
         "snippet": "Diffusion models design novel binders validated in the wet lab."},
        {"title": "In-vivo base editing", "source": "cell:2026",
         "snippet": "One-shot gene edits show durable effect in primate trials."},
        {"title": "Aging clocks", "source": "biorxiv:2026.5",
         "snippet": "Multi-omic clocks predict biological age; interventions reverse markers."},
    ],
    "Energy & Climate Tech": [
        {"title": "Net-energy-gain fusion repeats", "source": "doe:2026",
         "snippet": "Repeatable ignition shots; engineering breakeven is the next bar."},
        {"title": "Grid-scale storage", "source": "iea:2026",
         "snippet": "Iron-air and sodium-ion batteries cut long-duration storage cost."},
        {"title": "Datacenter power demand", "source": "report:grid",
         "snippet": "AI compute is now a top driver of new electricity demand."},
    ],
    "Engagement & Social": [
        {"title": "Recommendation beyond engagement", "source": "blog:platform",
         "snippet": "Platforms test 'time well spent' objectives over raw watch time."},
        {"title": "AI-generated content floods feeds", "source": "press:social",
         "snippet": "Provenance/watermarking emerges as feeds fill with synthetic media."},
        {"title": "Creator-community economics", "source": "report:creator",
         "snippet": "Small paid communities outperform broad ad-funded reach."},
    ],
}

# Each beat's canned cross-domain idea (FUSE phase). `target` is the other beat it
# connects to -> drives an addressed chat message so routing is visible.
MOCK_IDEAS: dict[str, dict] = {
    "AI & LLMs": {
        "title": "Agentic lab assistants for protein design",
        "description": "Use long-horizon tool-using agents to run the design-build-test "
                       "loop in biology, with external memory tracking experiments across days.",
        "target": "Biotech & Longevity",
    },
    "Biotech & Longevity": {
        "title": "Biological aging clocks for online wellbeing",
        "description": "Borrow multi-omic 'clock' methodology to build healthier-engagement "
                       "metrics that detect when a platform is good vs. harmful for users.",
        "target": "Engagement & Social",
    },
    "Energy & Climate Tech": {
        "title": "Inference scheduling on the clean-energy grid",
        "description": "Shift AI compute to when/where the grid is greenest, using storage "
                       "forecasts — turning datacenters into flexible grid assets.",
        "target": "AI & LLMs",
    },
    "Engagement & Social": {
        "title": "Provenance-native climate communication",
        "description": "Combine content-provenance tooling with community dynamics to make "
                       "trustworthy climate messaging that resists synthetic misinformation.",
        "target": "Energy & Climate Tech",
    },
}


def build_digest_from_findings(beat: str, findings: list[dict]) -> str:
    """Compose a markdown digest from search findings (deterministic)."""
    lines = [f"## {beat} — state of the art", ""]
    for f in findings:
        lines.append(f"- **{f['title']}** ({f['source']}): {f['snippet']}")
    return "\n".join(lines)
