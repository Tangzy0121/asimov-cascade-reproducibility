# Focused independent standards validation — blinded review protocol

## Fixed scope

This round was frozen before human scoring. It evaluates two mechanisms that remain HIGH after family-normalized primary re-estimation (T22 and T25), against ISO 10218-1:2025, ISO 10218-2:2025, and ISO 13482:2014. For each mechanism-standard combination, the package contains two prespecified applicable clauses and one within-standard negative-control clause (18 pairs total; 12 applicable and 6 decoys).

## Blinding and independence

Reviewer A completes only `focused_iso_review_reviewer_A.csv`; Reviewer B completes only the B file. Work independently and do not compare answers before both files are frozen. Do not open `_admin_prespecified_key_DO_NOT_SHARE.csv`. Rows are independently shuffled, and the reviewer files do not reveal applicable/decoy status or any model-generated mapping.

## Mandatory source check

Clause titles are navigation aids, not normative text. For every row, consult a licensed or otherwise authorized copy of the cited standard and clause. Enter `Y` in `normative_text_checked` only after reading the applicable normative text. If access is unavailable, enter `N` and use `INSUFFICIENT` rather than inferring a requirement from the title.

## Coding

- `requirement_type`: `HAZARD`, `SAFEGUARD`, `INTERFACE`, or `NONE`.
- `mapping_judgment`: `DIRECT`, `PARTIAL`, `NONE`, or `INSUFFICIENT`.
- `confidence`: `HIGH`, `MEDIUM`, or `LOW`.
- `reviewer_comment`: required for `PARTIAL` and `INSUFFICIENT`; briefly identify the missing or mismatched element.

`DIRECT` means the mechanism instantiates the clause's normative hazard, safeguard, or interface requirement without adding a material unstated element. `PARTIAL` means there is a real but incomplete correspondence. `NONE` means no defensible normative correspondence. `INSUFFICIENT` means the reviewer cannot judge from authorized source material.

## Scoring after both files are returned

Run `<python>/python.exe -X utf8 scripts/score_focused_iso_review.py`. It reports raw agreement and Cohen's kappa (four-class and binary), applicable-pair coverage, mechanism-by-standard coverage, and decoy false-mapping rates. No standards-validation result should be inserted into the manuscript before this scoring step succeeds.
