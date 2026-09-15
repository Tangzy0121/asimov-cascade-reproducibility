# Dual-Coder Agreement Report (kappa report)

- Workbook topic rows: 77
- Agreement metric: Cohen's kappa (Rater A vs Rater B, per field); interpretation bands follow Landis & Koch (1977).
- Headline metric: safety_judgment binarized — candidate = {DIRECT, PARTIAL}; all others (NOT_SAFETY / INCIDENTAL / UNCLEAR) are not-candidate.

## Per-Field Results

| Field | Dual-coded n | Agreement rate | Cohen's kappa | Band |
| ----- | ------------ | -------------- | ------------- | ---- |
| safety_judgment | 77 | 0.701 | 0.467 | moderate |
| harm_link | 77 | 0.688 | 0.371 | fair |
| cascade_role | 77 | 0.455 | 0.244 | fair |
| scope_limitation | 77 | 0.000 | 0.000 | slight |
| confidence | 77 | 0.623 | 0.297 | fair |
| **binary candidate (DIRECT/PARTIAL vs the rest)** | 77 | 0.896 | 0.606 | moderate |

> Note: `scope_limitation` is free text; kappa is computed on exact string match and is shown for completeness only — it is not reported in the paper.

## Status

- Raters A and B completed independent coding of all 77 non-noise topics; both rating sheets are archived here as `raterA_workbook.xlsx` and `raterB_workbook.xlsx`.
- `compute_dual_review_kappa.py` was re-run over the filled workbooks; every key field reports n = 77.
- `final_labels_77.csv` archives the adjudicated labels for all 77 topics; `adjudication_sheet.csv` archives the 33 rows sent to arbitration (see `adjudication_notes.md`).
- The manuscript reports these measured kappa values and the adjudicated-label counts (Table II).
