# Sources & How to Update

## Sources

| Source | What it informs |
|--------|----------------|
| Epoch AI — *Inference compute trends* (2025) — epochai.org | Model compute estimates, relative efficiency between model tiers |
| Li et al. — *Making AI Less Thirsty* (UC Riverside, 2023) — arxiv.org/abs/2304.03271 | Water consumption rates per Wh (1.3–2.0 mL/Wh range) |
| Anthropic pricing data | Relative token costs used to cross-check compute ratios between model tiers |
| Patterson et al. — *Carbon and the Cloud* (Google/UC Berkeley, 2021) | Data center PUE and carbon intensity context |
| *Energy use of AI inference, efficiency pathways, and test-time scaling* — Joule (2026) — cell.com/joule/fulltext/S2542-4351(26)00114-5 | Peer-reviewed measured per-query energy for optimized frontier-scale inference (median 0.31 Wh, IQR 0.16–0.60 Wh) — a stronger source tier than the derived-ratio approach below; not yet integrated into the per-token rate table (see Update Log) |
| *How Hungry is AI? Benchmarking Energy, Water, and Carbon Footprint of LLM Inference* — arXiv 2505.09598 | Direct joint benchmarking of energy, water, and carbon footprint per inference — candidate to replace the separate 2023 water / 2021 carbon sources with one unified benchmark |

**Confidence level:** Rates are estimates derived from public compute benchmarks and pricing signals — not Anthropic-published energy figures. If Anthropic releases official per-token energy data, update the table and note the source change.

## How to Update

When a new Claude model is released or newer research is published:

1. Update the **Model Rates table** in `SKILL.md` with the new model's input/output/blended rates
2. Update the **Last updated** date at the top of `SKILL.md`
3. Add the new model to the **tier order** in the Model Efficiency Comparison section of `SKILL.md`
4. If Anthropic publishes official per-token energy figures, those supersede the estimated rates — note the source change in a comment next to the affected row
5. Add any new references to the Sources table above

To find updated rates: search Epoch AI's compute benchmarks, Anthropic's sustainability reports, or peer-reviewed papers on LLM inference energy.

## Update Log

- **2026-09-03** — Relabeled the tier table to current-generation models (Fable 5, Opus 5, Sonnet 5, Haiku 4.5). No rate changes to the Opus/Sonnet/Haiku tiers: current API pricing (Opus $5 : Sonnet $3 : Haiku $1 per MTok input) preserves the same 5:3:1 ratio the existing Wh estimates were built on, so the cross-check still holds. Added Claude Fable 5 as a new top tier, priced at 2x Opus 5 ($10 vs $5 input) — scaled its Wh rate linearly from Opus 5 on the same basis.
- **2026-09-03** — Added two 2026 sources: a peer-reviewed Joule paper with measured per-query inference energy (median 0.31 Wh), and an arXiv benchmarking paper covering energy, water, and carbon jointly. Confirmed Anthropic still has not published official per-token/per-query energy figures, so the "estimate, not official" disclaimer stands. Not yet incorporated into the rate table — the Joule paper measures per-query energy (which bundles prompt length, output length, and model choice into one number), while this skill's table is per-token; converting between the two requires an assumed average query size, which is a methodology decision rather than a mechanical update. Flagged for the next rate-table revision.
