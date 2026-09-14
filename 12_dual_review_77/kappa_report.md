# Dual-Coder Agreement Report (kappa report)

- Workbook topic rows: 77
- Agreement metric: Cohen's kappa (Rater A vs Rater B, per field); interpretation bands follow Landis & Koch (1977).
- Headline metric: safety_judgment binarized — candidate = {DIRECT, PARTIAL}; all others (NOT_SAFETY / INCIDENTAL / UNCLEAR) are not-candidate.

## Per-Field Results

| Field | Dual-coded n | Agreement rate | Cohen's kappa | Band |
| ----- | ------------ | -------------- | ------------- | ---- |
| safety_judgment | 0 | [—] | [—] | waiting for human fill-in |
| harm_link | 0 | [—] | [—] | waiting for human fill-in |
| cascade_role | 0 | [—] | [—] | waiting for human fill-in |
| scope_limitation | 0 | [—] | [—] | waiting for human fill-in |
| confidence | 0 | [—] | [—] | waiting for human fill-in |
| **binary candidate (DIRECT/PARTIAL vs the rest)** | 0 | [—] | [—] | waiting for human fill-in |

> Note: `scope_limitation` is free text; kappa is computed on exact string match and is shown for completeness only — it is not reported in the paper.

## English results sentence, ready to paste into the paper (placeholders auto-replaced after fill-in)

```text
Two authors independently adjudicated all 77 non-noise topics using the label schema of Section IV-C. Inter-rater agreement was [substantial/almost perfect]: Cohen's kappa was [κ_safety] for the five-way safety judgment, [κ_harm] for the harm link, [κ_role] for the cascade role, and [κ_conf] for reviewer confidence. On the headline binary decision (candidate = DIRECT or PARTIAL, n = [N]), the two raters agreed on [agreement] of topics (kappa = [κ_binary]). Disagreements were resolved by discussion, with a third author arbitrating the remaining cases.
```

## To-do

- [ ] Rater A / B complete their independent coding and fill the workbook back in
- [ ] Re-run this script and confirm n = 77 for every field
- [ ] Replace the placeholders in the English results sentence with the measured values, paste it into the paper, and delete the "57 unadjudicated topics" limitation statement
