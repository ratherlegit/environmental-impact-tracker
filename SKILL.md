---
name: environmental-impact-tracker
version: 1.2.0
description: Calculates and displays the environmental footprint of Claude's token usage, translating computational costs into energy consumption (Wh), water usage (mL), and relatable real-world comparisons. Use when: (1) a single request/response exceeds 5,000 tokens, (2) completing a complex task like coding, document generation, or research, (3) the user asks about environmental impact, energy use, or sustainability, (4) tracking cumulative session, weekly, or project totals when requested.
---

# Environmental Impact Tracker

**Version:** 1.2.0 · **Last updated:** 2026-09-03. If today is 6+ months past this date, flag to the user that rates may be stale and read `references/sources.md`.

---

## Setup (First Use)

1. **Add enforcement rule to `CLAUDE.md`** (or `AGENTS.md` / `GEMINI.md`) if not already present. Global (`~/.claude/CLAUDE.md`, applies to every project) is recommended over per-project, since the auto-trigger is only as reliable as the rule's reach:
```markdown
## Environmental Impact
Before responding to any turn that involves subagents OR is estimated to exceed 5,000 tokens, check `~/.claude/environmental-impact-tracker.state`. If the file is missing or contains "on" (the default), display the environmental impact using the `environmental-impact-tracker` skill; treat this as a hard rule and do not skip it. If the file contains "off", skip the automatic display, but the skill is still available on explicit request.
```

2. **Create the toggle state file** at `~/.claude/environmental-impact-tracker.state` if it doesn't exist, containing exactly: `on`

3. **Create log file** at `.environmental-impact-log.json` in the project root if it doesn't exist: `{ "entries": [] }`

---

## Enable / Disable

The skill's automatic firing is controlled by `~/.claude/environmental-impact-tracker.state`, a single-word file: `on` or `off`.

- **"Turn off environmental impact tracking"** (or similar): write `off` to the state file, confirm it's done, and stop auto-displaying until it's turned back on.
- **"Turn on environmental impact tracking"** (or similar): write `on` to the state file, confirm it's done.
- **When off**, the hard rule in `CLAUDE.md` does not fire automatically, but the skill is still fully usable on explicit request ("show me my session total" plus the skill named directly, or a clear ask about environmental impact). Off means "stop interrupting me automatically," not "disable entirely."
- **When checking state**, missing file or unreadable content defaults to `on` (fail open, matching the original always-on behavior) rather than silently going quiet.

---

## When to Display

- Single turn exceeds **5,000 tokens**, or involves subagents, or completes a complex task
- User asks about environmental impact, energy use, or sustainability
- After displaying, offer: "Want to see your session, weekly, or project total?"

**Note on autonomous triggering:** testing found that a bare, vague phrase like "show me my session total" or "show me this week's impact" (with no mention of environmental/energy/carbon/footprint) does not reliably trigger this skill on its own, even when this skill is installed and available; it reads as too ambiguous against other plausible meanings. Don't rely on soft phrase-matching alone. If a user's request could plausibly mean this skill (session/weekly/project totals, especially as a follow-up after this skill has already displayed impact once this session), treat it as a match rather than asking for clarification. The ambiguity problem is specifically about a *cold* trigger with no prior signal, not about a follow-up in a conversation where this skill's domain is already established.

---

## Calculation

Every query pays a **fixed per-query overhead** (model routing/load, independent of length) plus a **marginal per-token rate**. Turns whose total tokens (input + output + skill + this agent's own tokens) exceed **50,000** switch to the Large-Context Marginal Rate. See `references/sources.md` for why 50,000 is a pragmatic interpolation point, not a measured boundary.

```
tier = "large-context" if total_tokens > 50,000 else "typical"
marginal_input, marginal_output, marginal_blended = rate columns for [model, tier] below

Energy_input   (Wh) = input_tokens  × marginal_input    / 1,000,000
Energy_output  (Wh) = output_tokens × marginal_output   / 1,000,000
Energy_skill   (Wh) = 2,500         × marginal_input    / 1,000,000  (this skill's load cost)
Energy_query   (Wh) = fixed_overhead(model) + Energy_input + Energy_output + Energy_skill

Energy_agents  (Wh) = sum over agents of [ fixed_overhead(agent_model) + agent_total_tokens × marginal_blended(agent_model, tier by that agent's own total tokens) / 1,000,000 ]

Total_energy   (Wh) = Energy_query + Energy_agents
Total_water    (mL) = Total_energy × 1.7
```

### Model Rates

| Model | Fixed overhead (Wh/query) | Marginal Input (Wh/MTok) | Marginal Output (Wh/MTok) | Marginal Blended (Wh/MTok) | Large-Context Marginal Blended (Wh/MTok, >50K tok) |
|-------|------|-------|--------|---------|---------|
| Claude Fable 5 | 0.177 | 90 | 447 | 430 | 35 |
| Claude Opus 5 | 0.088 | 45 | 223 | 215 | 18 |
| Claude Sonnet 5 | 0.053 | 27 | 134 | 129 | 11 |
| Claude Haiku 4.5 | 0.018 | 9 | 45 | 43 | 4 |
| Unknown (use Sonnet) | 0.053 | 27 | 134 | 129 | 11 |

Older generations (Opus/Sonnet/Haiku 4.x and earlier) share the same rate as their current-generation successor in the table above. Anthropic hasn't published per-generation compute deltas, so we hold the rate constant within a tier rather than guess.

- Cached reads: 10% of the applicable tier's marginal input rate
- A subagent is its own model invocation: give it its own fixed overhead, not just its token count folded into the parent's marginal cost
- Subagent tokens: read from `<usage>total_tokens: N</usage>` blocks in agent results; classify that agent's own tier independently by its own total tokens

For comparison tables (LED bulb, phone charge, water bottle etc.) read `references/comparisons.md`.
For sources and update instructions read `references/sources.md`.

---

## Display Template

```
🌍 Environmental Impact of This Response

Energy: [X.XX] Wh ([comparison])
Water:  [X.XX] mL ([comparison])

Model: [model name]
Tokens: [input] in + [output] out + ~2,500 skill = [total][ · long-context tier, if total > 50,000]
[If agents]: + [N] agent tokens across [X] agents = [grand total]

💡 If a lighter model had been used:
  [Model]: [X.XX] Wh / [X.XX] mL  ([Y]x less)

Note: Estimates. See references/sources.md for methodology.
```

Omit agent line if no Agent calls. Omit lighter model section if Haiku was used. Read `references/comparisons.md` to select the right relatable comparison for the energy/water values.

**Model efficiency:** Opus → show Sonnet + Haiku alternatives. Sonnet → show Haiku only. Present as neutral data, not a recommendation.

---

## Cumulative Tracking

After every impact display, append to `.environmental-impact-log.json`:
```json
{ "timestamp": "2026-09-03T14:32:00Z", "model": "claude-sonnet-5", "tier": "large-context", "energy_wh": 22.1, "water_ml": 37.6, "total_tokens": 167000, "context": "brief description" }
```

**Summaries (read log and aggregate):**
- **Session**: entries since today's first entry
- **This week**: entries within the current Mon–Sun week
- **This project**: all entries in the file

To reset a session: append `{ "timestamp": "...", "context": "session_start" }` and use that as the new session boundary.

---

## Tone

Informative, not preachy. Specific: never say "negligible." Honest: these are estimates. Don't display for every tiny interaction.
