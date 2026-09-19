# Protocol for Dual Human Screening and Annotation of the 77 Topics

## 0. Purpose

After the frozen screening, the corpus contains
only 77 non-noise BERTopic topics, all of which are independently reviewed by two
authors, with Cohen's kappa reported. The annotation label scheme
follows the P1 pilot (`output/subsystem_validation/human_review/P1_topic_safety_reviewed.csv`)
and the framework of Section IV-C of the paper; the value definitions are given in
`label_definitions.md` in the same directory.

## 1. Materials

| File | Description |
| ---- | ----------- |
| `dual_review_workbook.xlsx` | The annotation workbook: 77 rows (one per topic), containing the topic id, label, top keywords, and excerpts of 3 representative patents (first ~400 characters of each abstract), followed by two empty column blocks for Rater A and Rater B. |
| `label_definitions.md` | Value definitions for the five annotation fields; **required reading before annotation**. |
| `PROTOCOL.md` | This file. |

Each rater fills in 6 columns: `*_safety_judgment`, `*_harm_link`, `*_cascade_role`,
`*_scope_limitation`, `*_confidence`, and `*_note`. The first four enumerated fields
have dropdowns configured (the enumerated values are consistent with the P1 schema);
`scope_limitation` and `note` are free text.

## 2. Blinding Requirements (Mandatory)

- The workbook does **not** contain the DeepSeek frozen labels (`llm_safety_labels.csv`);
  raters must not consult that file at any point, nor the author labels of the 20
  topics already reviewed in P1.
- Rater A and Rater B **each keep their own copy of the workbook and annotate
  independently**; they must not communicate or view each other's columns before
  annotation is complete. Before reconciliation, each rater is advised to rename
  their copy to `dual_review_workbook_raterA.xlsx` / `dual_review_workbook_raterB.xlsx`
  for archiving.
- Judgments are based solely on the topic label, top keywords, and the 3 representative
  patent excerpts; if more context is needed, the full text can be retrieved via the
  publication number in `rep*_patent`, but both raters must follow the same lookup
  rule (recommended: read the excerpt first; consult the full text only if
  insufficient, and note "consulted full text" in the note field).

## 3. Annotation Procedure

1. **Independent annotation** (Raters A and B in parallel, not visible to each other):
   - Read `label_definitions.md` thoroughly;
   - Review each of the 77 topics row by row, filling in all six fields with **no
     blanks** (if there is no scope limitation, enter "None" in `scope_limitation`;
     when uncertain, use `UNCLEAR` and state the reason in the note);
   - Provide a `confidence` rating (HIGH/MEDIUM/LOW) for every row.
2. **Reconciliation and comparison**: the two raters merge their columns back into a
   single workbook (the A column block / the B column block), then run
   `scripts/compute_dual_review_kappa.py` to obtain the per-field kappa and the
   binarized (candidate = DIRECT/PARTIAL) overall kappa.
3. **Disagreement adjudication**:
   - First, the two raters discuss each disagreeing topic one by one, referring to the
     full text of the representative patents; cases where agreement is reached are
     recorded directly as the final label (consensus takes priority);
   - Cases still in disagreement after discussion are adjudicated by a third author,
     whose ruling becomes the final label;
   - For any disagreement where either side originally marked `UNCLEAR`, the
     adjudication **must** produce a non-UNCLEAR final label (unless all three raters
     agree that the evidence is genuinely insufficient, in which case UNCLEAR is
     retained with an explanation in the note);
   - Adjudication results are written to the final dataset (saved as separate
     adjudicated columns or a separate CSV) and must not overwrite the original
     independent annotations of A/B in the workbook.

## 4. Estimated Effort

77 topics × roughly 3–4 minutes per topic ≈ 4–5 hours per person; reconciliation and
adjudication take about 1 hour. The task can be completed by the two raters in one
afternoon (working independently) plus one short meeting.

## 5. Backfill and Paper Update Steps

1. Both raters complete annotation → backfill into the A/B column blocks of
   `dual_review_workbook.xlsx`.
2. Run:
   ```
   <python>/envs/<env>/python.exe -X utf8 scripts/compute_dual_review_kappa.py
   ```
   This generates `output/dual_review/kappa_report.md`; confirm that all fields have
   n = 77.
3. Paste the bilingual result-sentence templates from the report (with placeholders
   replaced by the measured values) into the experiments/validation section of the
   paper, and remove the original manuscript's limitation statement about
   "57 unadjudicated topics", replacing it with
   "all 77 non-noise topics were independently adjudicated by two authors
   (Cohen's κ = …)".
4. Archive the final adjudicated labels to `output/dual_review/` (e.g.,
   `adjudicated_labels.csv`) for citation in the main-text figures and the appendix.
