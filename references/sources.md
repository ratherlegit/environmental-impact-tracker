# Sources & How to Update

## Sources

| Source | What it informs |
|--------|----------------|
| Epoch AI, *Inference compute trends* (2025), epochai.org | Model compute estimates, relative efficiency between model tiers |
| Li et al., *Making AI Less Thirsty* (UC Riverside, 2023), arxiv.org/abs/2304.03271 | Water consumption rates per Wh (1.3–2.0 mL/Wh range) |
| Anthropic pricing data | Relative token costs used to cross-check compute ratios between model tiers |
| Patterson et al., *Carbon and the Cloud* (Google/UC Berkeley, 2021) | Data center PUE and carbon intensity context |
| *Energy use of AI inference, efficiency pathways, and test-time scaling*, Joule (2026), cell.com/joule/fulltext/S2542-4351(26)00114-5 | Peer-reviewed measured per-query energy for optimized frontier-scale inference (median 0.31 Wh, IQR 0.16–0.60 Wh), a stronger source tier than the derived-ratio approach below. Not yet integrated into the per-token rate table (see Update Log) |
| *How Hungry is AI? Benchmarking Energy, Water, and Carbon Footprint of LLM Inference*, arXiv 2505.09598 | Direct joint benchmarking of energy, water, and carbon footprint per inference; defines the "short-form" (100 in / 300 out), "medium" (1,000 in / 1,000 out), and "long-form" (10,000 in / 1,500 out) prompt configs used as the query-length anchor below |
| Third-party estimate (public gist, not peer-reviewed), Opus 4.7, 800K-token context, ~14.1 Wh/query vs. ~0.7 Wh for a short chat | Single-data-point anchor for the long-context marginal rate; flagged low-confidence, see Methodology below |

**Confidence level:** Rates are estimates derived from public compute benchmarks, pricing signals, and (as of 2026-09-03) one peer-reviewed measurement, not Anthropic-published energy figures. If Anthropic releases official per-token energy data, update the table and note the source change.

## Methodology: Fixed Overhead + Marginal Rate (added 2026-09-03)

Prior versions of this skill used a single flat Wh/MTok rate per model, scaled from Anthropic's pricing ratios. That has two known weaknesses: (1) price is a proxy for compute cost, not a measurement of it, and (2) a flat per-token rate can't represent that real inference has a fixed per-query cost (routing, model load) that a pure per-token multiplier dilutes away at longer lengths.

**Deriving the fixed overhead.** The Joule 2026 paper reports that test-time-scaling queries ~15x longer than typical cost ~13x more energy (median 0.31 Wh → 3.91 Wh), not 15x, which a pure per-token model would require. Solving `B + mL = 0.31` and `B + m(15L) = 3.91` for the fixed term `B` eliminates `L` entirely: `B ≈ 0.053 Wh` per query, for the Sonnet tier, independent of any query-length assumption.

**Deriving the marginal rate.** Isolating `m` still requires an absolute query-length anchor: `mL = 0.257 Wh`, so `m = 0.257 / L`. We anchor `L` to the "medium" config (2,000 total tokens) from the *How Hungry is AI* paper, since it sits inside the well-documented typical range for chat/coding interactions (200–2,000 tokens per the general token-usage literature) and is the same paper's own definition of a representative real-world prompt, not an assumption invented for this skill. This gives `m ≈ 129 Wh/MTok` blended for Sonnet.

**Tier scaling.** Both `B` and `m` are scaled to Opus/Haiku/Fable using the existing 5:3:1 pricing ratio (Fable at 2x Opus), same as prior revisions. This assumes overhead and marginal cost scale with model size in the same proportion pricing does, which is unverified but consistent with the rest of the table's methodology.

**Why a second, large-context tier exists.** Extrapolating the above formula to a real-world 800K-token long-context call (Opus-tier, ~14.1 Wh actual per the gist estimate) overpredicts by roughly 10x (~172 Wh predicted). This is a real signal, not noise: long-context inference is almost certainly meaningfully more efficient per token (KV-cache reuse, batching, attention optimizations) than short/medium queries. Rather than force one formula to cover both regimes, turns above 50,000 total tokens use a separate marginal rate anchored directly to the 800K data point (with fixed overhead treated as negligible at that scale). **This anchor is a single non-peer-reviewed estimate: the lowest-confidence number in this skill.** There is no data between ~30,000 tokens (the top of Joule's own test-time-scaling measurement) and 800,000 tokens; 50,000 is a pragmatic switchover point in that gap, not itself measured. Revisit if a source with intermediate long-context measurements turns up.

## How to Update

When a new Claude model is released or newer research is published:

1. Update the **Model Rates table** in `SKILL.md` with the new model's input/output/blended rates
2. Update the **Last updated** date at the top of `SKILL.md`
3. Add the new model to the **tier order** in the Model Efficiency Comparison section of `SKILL.md`
4. If Anthropic publishes official per-token energy figures, those supersede the estimated rates. Note the source change in a comment next to the affected row
5. Add any new references to the Sources table above

To find updated rates: search Epoch AI's compute benchmarks, Anthropic's sustainability reports, or peer-reviewed papers on LLM inference energy.

## Update Log

- **2026-09-03**: Relabeled the tier table to current-generation models (Fable 5, Opus 5, Sonnet 5, Haiku 4.5). No rate changes to the Opus/Sonnet/Haiku tiers: current API pricing (Opus $5 : Sonnet $3 : Haiku $1 per MTok input) preserves the same 5:3:1 ratio the existing Wh estimates were built on, so the cross-check still holds. Added Claude Fable 5 as a new top tier, priced at 2x Opus 5 ($10 vs $5 input), scaled its Wh rate linearly from Opus 5 on the same basis.
- **2026-09-03**: Added two 2026 sources: a peer-reviewed Joule paper with measured per-query inference energy (median 0.31 Wh), and an arXiv benchmarking paper covering energy, water, and carbon jointly. Confirmed Anthropic still has not published official per-token/per-query energy figures, so the "estimate, not official" disclaimer stands. Not yet incorporated into the rate table: the Joule paper measures per-query energy (which bundles prompt length, output length, and model choice into one number), while this skill's table is per-token; converting between the two requires an assumed average query size, which is a methodology decision rather than a mechanical update. Flagged for the next rate-table revision.
- **2026-09-03**: Replaced the flat per-token rate model with a fixed-overhead + marginal-rate model (see Methodology above), and added a separate long-context marginal rate for turns above 50,000 total tokens. This is the rate-table revision flagged in the entry above. `SKILL.md` and `README.md` updated to match.
- **2026-09-03**: Empirically tested the four "ask directly" trigger phrases from the README's Usage section against four independent, fresh Claude instances (no prior context, no instruction to use this skill). Result: 0 of 4 autonomously invoked the skill. "Session total" / "week's impact" / "project's total" were judged too ambiguous against other plausible meanings (billing, task counts, product metrics). "What was the environmental impact of that?" (a near-verbatim match for this skill's own trigger description) was still declined: the test instance recognized the skill existed but reasoned that reporting a specific Wh/mL number without real per-request telemetry would look like fabricating precision, and chose not to invoke the skill on that basis. Rewrote the README Usage section and added a note in `SKILL.md`'s "When to Display" section to stop overclaiming soft-phrase reliability and point users to the `CLAUDE.md` enforcement rule as the actually-reliable trigger.
- **2026-09-03**: Removed the fixed "reviewed every 2 months" cadence claim from the README; this repo is updated on triggering events (new model, new research), not a calendar promise. Also removed em dashes from prose throughout `README.md`, `SKILL.md`, and this file for a plainer writing style.
- **2026-09-03**: Added an on/off toggle (`~/.claude/environmental-impact-tracker.state`) so automatic firing can be disabled without uninstalling the skill or hand-editing `CLAUDE.md`. The rule text in `SKILL.md`'s Setup section and the README's Usage/Setup sections were updated to check this file before displaying. Also added a README Setup section: the `CLAUDE.md` rule and log file steps were previously documented only inside `SKILL.md`, invisible to anyone reading the repo on GitHub rather than installing the skill directly.
