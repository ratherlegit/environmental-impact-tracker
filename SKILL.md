---
name: environmental-impact-tracker
version: 1.4.0
description: Calculates and displays the environmental footprint of Claude's token usage, translating computational costs into energy consumption (Wh), water usage (mL), and relatable real-world comparisons. Use when: (1) a single request/response exceeds 5,000 tokens, (2) completing a complex task like coding, document generation, or research, (3) the user asks about environmental impact, energy use, or sustainability, (4) tracking cumulative session, weekly, or project totals when requested, (5) the user asks for a weekly, monthly, quarterly, or annual environmental impact report (e.g. "monthly impact report", "Q3 environmental report", "last month's footprint").
---

# Environmental Impact Tracker

**Version:** 1.4.0 · **Last updated:** 2026-10-19. If today is 6+ months past this date, flag to the user that rates may be stale and read `references/sources.md`.

---

## Setup (First Use)

1. **Ask the user which mode they want** if `~/.claude/environmental-impact-tracker.state` does not exist, then write their choice to it (see Modes). Recommend `reports`.

2. **Install the tracking hook.** Tracking is done by a Stop hook, not by Claude, so it records every response. Add this to `hooks.Stop` in `~/.claude/settings.json` (ask the user first, since it edits their global settings):
```json
{ "hooks": [ { "type": "command", "command": "python3 -I ~/.claude/skills/environmental-impact-tracker/scripts/impact_hook.py", "timeout": 30 } ] }
```
3. **Backfill existing history** once: `python3 -I ~/.claude/skills/environmental-impact-tracker/scripts/impact_hook.py --backfill`. It reads every transcript under `~/.claude/projects` (only as far back as Claude Code kept them) and skips responses already logged.

4. **Add this rule to `~/.claude/CLAUDE.md`** so Claude does not display impact on its own:
```markdown
## Environmental Impact
Impact tracking is automatic (a Stop hook logs every response). Do not display impact on your own. When the user asks for an impact report, a total, or to change the tracking mode, use the `environmental-impact-tracker` skill.
```
5. **Shared log** lives at `~/.claude/environmental-impact-log.json` and is created by the hook. Older per-project logs can be imported with `impact_report.py migrate <project-dir>`.

---

## Modes

The mode is a single word in `~/.claude/environmental-impact-tracker.state`. Tracking always runs unless the mode is `off`.

| Mode | Tracking | Per-response line after large responses | Reports on request |
|------|----------|------------------------------------------|--------------------|
| `reports` (recommended) | yes | no | yes |
| `per-response` | yes | yes | yes |
| `both` | yes | yes | yes |
| `off` | no | no | yes, from what is already logged |

- `both` behaves the same as `per-response`; the name is kept so the choice reads naturally. The legacy value `on` also means `per-response`.
- A "large response" is a turn with more than 5,000 fresh tokens (cache re-reads excluded) or any subagent response. The hook prints the line itself, so Claude does not need to.
- When the user asks to change mode ("only reports", "show me after big responses", "turn it off"), write the new word to the state file and confirm. Turning it `off` also stops logging; say so.
- Missing or unreadable state file: tracking still runs, nothing is displayed, and the skill asks the user to pick a mode.

---

## When to Display

- Claude does not display impact on its own. The hook handles per-response lines according to the mode.
- Use this skill when the user asks for a report, a session or period total, or the impact of the current conversation, or wants to change the mode.
- After showing a report, offer the other periods (weekly, monthly, quarterly, annual).

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

The hook appends one entry per assistant response (subagent responses included) to `~/.claude/environmental-impact-log.json`. Claude never writes to the log by hand. An entry looks like:
```json
{ "timestamp": "2026-10-19T14:32:00.000Z", "project": "StepGoals", "model": "claude-sonnet-5-5", "tier": "large-context", "energy_wh": 0.21, "water_ml": 0.36, "total_tokens": 89000, "fresh_tokens": 1900, "id": "msg_...", "session": "...", "subagent": false }
```
- Energy is computed per response with the Calculation rates: tier is decided by that response's own total tokens, cache reads count at 10% of the input rate, and each response pays the model's fixed overhead.
- `project` is the response's working directory, rolled up to its git repo when it has one.
- Entries written before 1.4.0 are hand estimates with `context` text and no `id`.

**Summaries:** use the period reports below. For "this session", sum entries with the current session id.

---

## Period Reports

For weekly, monthly, quarterly, or annual reports, **run the script instead of aggregating by hand**. Treat any request pairing "report" (or "impact", "footprint", "usage") with one of those periods as a match, even without the words environmental or energy.

```
python3 -I ~/.claude/skills/environmental-impact-tracker/scripts/impact_report.py report <weekly|monthly|quarterly|annual> [--back N]
```

- Periods: weekly is Mon–Sun, the rest are calendar months, quarters, and years (UTC). `--back N` reports N periods ago ("last month" is `monthly --back 1`).
- Output covers total energy and water with change vs the previous period, tokens, a per-project breakdown (largest first), and water over time by day (weekly), week (monthly), or month (quarterly/annual). The current period is marked "in progress", so its comparison to a full previous period can look low.
- The script prints a blue-block visual (this vs last period, share by project, water over time). Paste its output unchanged inside a code block so the blocks stay aligned. It already includes bottle and phone-charge comparisons, so only add other comparisons from `references/comparisons.md` if asked.
- Entries logged before 1.3.0 may lack `project` and show as "unknown"; entries without `energy_wh` (such as `session_start` markers) are ignored.

---

## Tone

Informative, not preachy. Specific: never say "negligible." Honest: these are estimates. Don't display for every tiny interaction.
