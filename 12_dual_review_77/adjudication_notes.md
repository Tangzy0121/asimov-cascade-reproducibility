# Adjudication Notes — dual-coder disagreements and P1 reconciliation

## Background

Independent dual coding of all 77 non-noise topics was completed (true double coding; per-field kappa in `kappa_report.md`). The final step was arbitrating the disagreement rows to produce the adjudicated label set used in the manuscript (full-corpus recall/precision and Table II reconciliation). `adjudication_sheet.csv` contains 33 rows:

- 23 rows: Rater A and Rater B disagreed on `safety_judgment` (mandatory arbitration).
- 10 rows: the two raters agreed with each other but differed from the first-pass P1 review, and the topic belongs to the frozen 20 candidates (needed for Table II reconciliation).

## Procedure

Only the final column `final_safety_judgment` was filled, with values DIRECT / PARTIAL / INCIDENTAL / NOT_SAFETY / UNCLEAR. The primary evidence was each row's `rep1_excerpt_220`, with the other two representative excerpts in `dual_review_workbook.xlsx` consulted when needed. Label definitions follow `label_definitions.md`. The third author arbitrated independently of A, B, and P1.

## Key rows flagged for the arbiter

- T25 (a HIGH topic described as the most robust in the paper): P1=DIRECT, A=DIRECT, B=INCIDENTAL
- T40 (becomes HIGH under the truncated primary analysis): P1=DIRECT, A=PARTIAL, B=PARTIAL
- T74 / T76 / T27 / T33 (evidence examples cited in Section V-A): P1=DIRECT, A/B mostly INCIDENTAL or NOT_SAFETY
- Large deviations from P1 would update Table II and the precision accounting.

## Outcome

The arbitration produced `final_labels_77.csv`: across all 77 topics DIRECT 3 / PARTIAL 10 / INCIDENTAL 21 / NOT_SAFETY 43; among the frozen 20 candidates DIRECT 3 / PARTIAL 4 / INCIDENTAL 8 / NOT_SAFETY 5 (Table II).
