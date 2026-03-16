---
name: environmental-impact-tracker
description: Calculates and displays the environmental footprint of Claude's token usage, translating computational costs into energy consumption (Wh), water usage (mL), and relatable real-world comparisons. Use when: (1) a single request/response exceeds 5,000 tokens, (2) completing a complex task like coding, document generation, or research, (3) the user asks about environmental impact, energy use, or sustainability, (4) tracking cumulative session, weekly, or project totals when requested.
---

# Environmental Impact Tracker

**Last updated:** 2026-03-16 — if today is 6+ months past this date, flag to the user that rates may be stale and read `references/sources.md`.

---

## Setup (First Use)

1. **Add enforcement rule to `CLAUDE.md`** (or `AGENTS.md` / `GEMINI.md`) if not already present:
```markdown
## Environmental Impact
After any turn that involves subagents OR is estimated to exceed 5,000 tokens, display the environmental impact using the `environmental-impact-tracker` skill. This is a hard rule — do not skip it.
```

2. **Create log file** at `.environmental-impact-log.json` in the project root if it doesn't exist: `{ "entries": [] }`

---

## When to Display

- Single turn exceeds **5,000 tokens**, or involves subagents, or completes a complex task
- User asks about environmental impact, energy use, or sustainability
- After displaying, offer: "Want to see your session, weekly, or project total?"

---

## Calculation

```
Energy_input   (Wh) = input_tokens  × model_input_rate  / 1,000,000
Energy_output  (Wh) = output_tokens × model_output_rate / 1,000,000
Energy_skill   (Wh) = 2,500         × model_input_rate  / 1,000,000  (this skill's load cost)
Energy_agents  (Wh) = sum(agent total_tokens) × model_blended_rate / 1,000,000
Total_energy   (Wh) = sum of all above
Total_water    (mL) = Total_energy × 1.7
```

### Model Rates (Wh per million tokens)

| Model | Input | Output | Blended |
|-------|-------|--------|---------|
| Claude Opus 4.x | 50 | 250 | ~240 |
| Claude Sonnet 4.x | 30 | 150 | ~145 |
| Claude Haiku 4.x | 10 | 50 | ~50 |
| Unknown | 30 | 150 | (use Sonnet) |

- Cached reads: 10% of input rate
- Blended rate assumes ~80/20 input/output mix — use split formula when counts are known
- Subagent tokens: read from `<usage>total_tokens: N</usage>` blocks in agent results; use blended rate

For comparison tables (LED bulb, phone charge, water bottle etc.) read `references/comparisons.md`.
For sources and update instructions read `references/sources.md`.

---

## Display Template

```
🌍 Environmental Impact of This Response

Energy: [X.XX] Wh ([comparison])
Water:  [X.XX] mL ([comparison])

Model: [model name]
Tokens: [input] in + [output] out + ~2,500 skill = [total]
[If agents]: + [N] agent tokens across [X] agents = [grand total]

💡 If a lighter model had been used:
  [Model]: [X.XX] Wh / [X.XX] mL  ([Y]x less)

Note: Estimates — see references/sources.md for methodology.
```

Omit agent line if no Agent calls. Omit lighter model section if Haiku was used. Read `references/comparisons.md` to select the right relatable comparison for the energy/water values.

**Model efficiency:** Opus → show Sonnet + Haiku alternatives. Sonnet → show Haiku only. Present as neutral data, not a recommendation.

---

## Cumulative Tracking

After every impact display, append to `.environmental-impact-log.json`:
```json
{ "timestamp": "2026-03-16T14:32:00Z", "model": "claude-sonnet-4-6", "energy_wh": 22.1, "water_ml": 37.6, "total_tokens": 167000, "context": "brief description" }
```

**Summaries (read log and aggregate):**
- **Session** — entries since today's first entry
- **This week** — entries within the current Mon–Sun week
- **This project** — all entries in the file

To reset a session: append `{ "timestamp": "...", "context": "session_start" }` and use that as the new session boundary.

---

## Tone

Informative, not preachy. Specific — never say "negligible." Honest — these are estimates. Don't display for every tiny interaction.
