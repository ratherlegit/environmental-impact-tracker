# Environmental Impact Tracker

A Claude Code skill that calculates and displays the environmental footprint of your AI interactions — translating abstract token usage into energy consumption (Wh), water usage (mL), and relatable real-world comparisons.

## What it does

After heavy turns (5,000+ tokens, subagent use, or complex tasks), Claude automatically displays:

```
🌍 Environmental Impact of This Response

Energy: 22.1 Wh (about 1 phone charge)
Water:  37.6 mL (about 2.5 tablespoons)

Model: Claude Sonnet 4.6
Tokens: 25,000 in + 6,000 out + ~2,500 skill = 33,500
+ 136,000 agent tokens across 4 agents = 169,500 total

💡 If a lighter model had been used:
  Haiku: 7.6 Wh / 12.9 mL  (2.9x less)

Note: Estimates — see references/sources.md for methodology.
```

Features:
- **Per-turn impact** — energy and water for each heavy exchange
- **Subagent tracking** — includes all spawned agent activity in the total
- **Skill cost included** — accounts for the tokens used to load this skill itself
- **Model efficiency comparison** — shows what the same work would have cost on a lighter model
- **Cumulative tracking** — session, weekly, and project totals via a local log file
- **Auto-wires enforcement** — adds a rule to your `CLAUDE.md` on first use so it never gets skipped

## Installation

### Claude Code

```
/plugin install example-skills@anthropic-agent-skills
```

Or copy `SKILL.md` (and the `references/` folder) into your Claude Code skills directory:

```
~/.claude/plugins/cache/anthropic-agent-skills/example-skills/unknown/skills/environmental-impact-tracker/
```

### Manual (any Claude environment)

Paste the contents of `SKILL.md` into your system prompt or project instructions.

## Usage

Once installed, the skill triggers automatically. You can also ask directly:

- *"What was the environmental impact of that?"*
- *"Show me my session total"*
- *"Show me this week's impact"*
- *"Show me this project's total"*

## How it works

Energy and water estimates are calculated using published research on LLM inference compute costs:

| Model | Input (Wh/MTok) | Output (Wh/MTok) |
|-------|----------------|-----------------|
| Claude Opus 4.x | 50 | 250 |
| Claude Sonnet 4.x | 30 | 150 |
| Claude Haiku 4.x | 10 | 50 |

Water usage: 1.7 mL per Wh (average data center cooling + power generation).

Sources: Epoch AI (2025), UC Riverside / Li et al. (2023). See `references/sources.md` for full citations.

> **Note:** These are estimates derived from public benchmarks and pricing signals, not official Anthropic energy figures. Actual consumption varies by data center location, cooling method, and grid energy mix.

## Keeping it up to date

Model rates are reviewed every 2 months. When new Claude models are released or new research is published, update the rates table in `SKILL.md` following the instructions in `references/sources.md`.

## License

MIT
