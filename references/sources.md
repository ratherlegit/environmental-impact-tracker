# Sources & How to Update

## Sources

| Source | What it informs |
|--------|----------------|
| Epoch AI — *Inference compute trends* (2025) — epochai.org | Model compute estimates, relative efficiency between model tiers |
| Li et al. — *Making AI Less Thirsty* (UC Riverside, 2023) — arxiv.org/abs/2304.03271 | Water consumption rates per Wh (1.3–2.0 mL/Wh range) |
| Anthropic pricing data | Relative token costs used to cross-check compute ratios between model tiers |
| Patterson et al. — *Carbon and the Cloud* (Google/UC Berkeley, 2021) | Data center PUE and carbon intensity context |

**Confidence level:** Rates are estimates derived from public compute benchmarks and pricing signals — not Anthropic-published energy figures. If Anthropic releases official per-token energy data, update the table and note the source change.

## How to Update

When a new Claude model is released or newer research is published:

1. Update the **Model Rates table** in `SKILL.md` with the new model's input/output/blended rates
2. Update the **Last updated** date at the top of `SKILL.md`
3. Add the new model to the **tier order** in the Model Efficiency Comparison section of `SKILL.md`
4. If Anthropic publishes official per-token energy figures, those supersede the estimated rates — note the source change in a comment next to the affected row
5. Add any new references to the Sources table above

To find updated rates: search Epoch AI's compute benchmarks, Anthropic's sustainability reports, or peer-reviewed papers on LLM inference energy.
