# Environmental Impact Tracker

**v1.1.0**

A Claude Code skill that calculates and displays the environmental footprint of your AI interactions — translating abstract token usage into energy consumption (Wh), water usage (mL), and relatable real-world comparisons.

## What it does

After heavy turns (5,000+ tokens, subagent use, or complex tasks), Claude automatically displays:

```
🌍 Environmental Impact of This Response

Energy: 19.36 Wh (about 1 phone charge)
Water:  32.90 mL (about 2 tablespoons)

Model: Claude Sonnet 5
Tokens: 25,000 in + 6,000 out + ~2,500 skill = 33,500
+ 136,000 agent tokens across 4 agents = 169,500 total

💡 If a lighter model had been used:
  Haiku: 6.46 Wh / 10.97 mL  (3.0x less)

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

**Reliable trigger**: the `CLAUDE.md` rule added during Setup — it fires automatically on any heavy turn (5,000+ tokens or subagent use), no need to ask.

**Asking directly is less reliable than it sounds.** Testing this against fresh Claude instances (no prior context, no explicit instruction to use the skill) found that vague phrases don't autonomously trigger it — even a phrase that closely echoes the skill's own description can get declined, because Claude may reason that reporting a specific Wh/mL figure without real per-request telemetry looks like fabricating precision, and choose not to invoke the skill on that basis alone. Two things help:

- **Be explicit** about wanting an environmental/energy estimate, not just "impact" or "total": *"What's the estimated environmental impact of that response?"* works far more reliably than *"Show me this week's impact."*
- **Name the skill directly** if a vague phrase doesn't land: *"Use the environmental-impact-tracker skill to show my session total."*

If you want the "ask casually and it just works" experience, extend the `CLAUDE.md` enforcement rule from Setup to also cover explicit cumulative-total requests, rather than relying on the skill description to be picked up unprompted.

## How it works

Each query pays a **fixed per-query overhead** (routing/model load, independent of length) plus a **marginal per-token rate**. Long-context turns (>50,000 total tokens) switch to a separate, lower marginal rate — real-world long-context inference is meaningfully more efficient per token than short chat turns, and a single flat rate can't represent both.

| Model | Fixed overhead (Wh/query) | Marginal Input (Wh/MTok) | Marginal Output (Wh/MTok) | Long-context Marginal Blended (Wh/MTok) |
|-------|------|-------|--------|---------|
| Claude Fable 5 | 0.177 | 90 | 447 | 35 |
| Claude Opus 5 | 0.088 | 45 | 223 | 18 |
| Claude Sonnet 5 | 0.053 | 27 | 134 | 11 |
| Claude Haiku 4.5 | 0.018 | 9 | 45 | 4 |

Water usage: 1.7 mL per Wh (average data center cooling + power generation).

The fixed-overhead/marginal-rate split is derived from a peer-reviewed 2026 Joule paper's own test-time-scaling data (a 15x longer query costs only 13x more energy — implying a fixed cost that dilutes with length), anchored to a "medium" query-length definition (1,000 in / 1,000 out) from a companion 2026 benchmarking paper. The long-context rate is anchored separately to a real-world long-context estimate, since extrapolating the short/medium-query rate out to very large contexts overpredicts by roughly 10x. Full derivation and confidence notes: `references/sources.md`.

### Worked example

Using the sample output above — Claude Sonnet 5, 25,000 input + 6,000 output + 2,500 skill-load tokens on the main turn, plus 4 subagents averaging 34,000 tokens each (all under the 50,000-token long-context threshold, so every component uses the typical-tier rates: fixed overhead 0.053 Wh, marginal input 27 Wh/MTok, marginal output 134 Wh/MTok, marginal blended 129 Wh/MTok):

**Main query:**
```
Energy_input  = 25,000 × 27  / 1,000,000 = 0.6750 Wh
Energy_output =  6,000 × 134 / 1,000,000 = 0.8040 Wh
Energy_skill  =  2,500 × 27  / 1,000,000 = 0.0675 Wh
Energy_query  = 0.053 (fixed overhead) + 0.6750 + 0.8040 + 0.0675 = 1.60 Wh
```

**Each subagent** (own fixed overhead, own tier check — 34,000 tokens is under 50,000, so typical-tier blended rate applies):
```
Energy_agent = 0.053 + (34,000 × 129 / 1,000,000) = 0.053 + 4.386 = 4.44 Wh
```
Four subagents: `4 × 4.44 = 17.76 Wh`

**Total:**
```
Total_energy = 1.60 (query) + 17.76 (agents) = 19.36 Wh
Total_water  = 19.36 × 1.7 = 32.9 mL
```

Notice most of the cost here comes from the four subagents, not the main turn — each one pays its own 0.053 Wh fixed overhead on top of its marginal token cost, which is exactly the behavior the old flat-rate model couldn't represent: spinning up four separate model invocations has a real, distinct cost from one invocation handling four times the tokens.

> **Note:** These are estimates derived from public benchmarks and pricing signals, not official Anthropic energy figures. Actual consumption varies by data center location, cooling method, and grid energy mix.

## Keeping it up to date

Model rates are reviewed every 2 months. When new Claude models are released or new research is published, update the rates table in `SKILL.md` following the instructions in `references/sources.md`.

## Changelog

**1.1.0** — 2026-09-03
- Replaced the flat per-token rate model with a fixed-overhead + marginal-rate model, derived from a peer-reviewed 2026 Joule paper's test-time-scaling data
- Added a separate long-context marginal rate for turns over 50,000 tokens (the flat/typical-tier formula overpredicts long-context energy by ~10x)
- Subagents now carry their own fixed overhead instead of being folded into the parent turn's marginal cost
- Relabeled the model table to current-generation models (Fable 5, Opus 5, Sonnet 5, Haiku 4.5)
- Added MIT `LICENSE` file
- Rewrote the Usage section after testing the documented "ask directly" phrases against fresh Claude instances — none of the four autonomously triggered the skill. Usage now documents the reliable path (the `CLAUDE.md` rule) and explains why vague phrasing fails instead of overclaiming it works

**1.0.0** — 2026-03-16
- Initial release

## License

MIT
