# Negative Audit Blinded Dual Review — Reviewer Instructions (P0-5 / Safety Screening Recall Estimation)

## 1. What this package is

The automated safety screening split 77 non-noise topics into 20 positives (already reviewed) and 57 negatives (never manually checked).
To estimate the screening recall / specificity / F1, we drew a stratified sample of 18 from the 57 negatives
(sampling plan: `../negative_audit_sampling_plan.md`, seed=20260728).

**This package mixes these 18 negative samples with the 20 already-reviewed positives** (38 topics in total), shuffles them, and hands them to
two reviewers for independent re-adjudication — **no column in the files you receive can distinguish negatives from positives**,
and neither the machine scores nor the LLM rationales are visible. The mapping exists only in `admin_keys.csv`
(held by the administrator only; do not open it before the review is finished).

## 2. File inventory

- `blind_review_reviewerA.csv` / `blind_review_reviewerB.csv` — two review sheets, 38 rows each.
  Identical content, only the row order differs (A seed 20260808, B seed 20260809).
  **Reviewer A fills in only the A file, Reviewer B fills in only the B file; during the review, do not communicate with each other or look at each other's files.**
- `admin_keys.csv` — administrator key (topic_id, is_negative_sample, safety_score, stratum,
  ht_weight, original_judgment). Reviewers must not open it.
- This file.

## 3. How to fill in each row

The judgment criteria are exactly the same as for the P1 topic safety review
(`../human_review/P1_human_review_protocol.md` §3.1–3.1d): rely only on the
topic label plus the representative patent number / title / abstract excerpt given in the sheet; do not guess from the topic name alone.

| Column | Values | Description |
|----|------|------|
| `human_safety_judgment` | DIRECT / PARTIAL / INCIDENTAL / NOT_SAFETY / UNCLEAR | Whether the topic genuinely concerns robot safety (required) |
| `human_harm_link` | DIRECT / INDIRECT / NONE / UNCLEAR | Traceable link from the mechanism to bodily harm (required) |
| `cascade_role` | HAZARD_ENDPOINT / PROPAGATION_NODE / SAFETY_BARRIER / CONTEXT_ONLY / OUT_OF_SCOPE / UNCLEAR | Position in the Cascade propagation chain (required) |
| `plausible_cascade_path` | Free text | A testable propagation hypothesis; not a causal claim — see protocol §3.1c for the format |
| `scope_limitation` | Free text | Boundaries of the evidence (non-humanoid, indirect inference, mixed topics, etc.) |
| `reviewer_confidence` | HIGH / MEDIUM / LOW | Required |
| `reviewer_note` | Free text | Leave a note for difficult rows |

**Red lines**: do not modify the existing columns `item_no / topic_id / topic_label / rep_*`; do not add or delete rows;
do not check answers with anyone else; when unsure, mark UNCLEAR — that is better than forcing a guess.

## 4. Computation after collection (administrator)

Both reviewers place their completed files back in this directory (file names unchanged). The computation covers:

1. **A/B agreement**: Cohen's κ (first collapse DIRECT/PARTIAL into S+ and INCIDENTAL/NOT_SAFETY
   into S−; UNCLEAR is resolved after adjudication); disagreements are discussed and adjudicated, then labels are locked.
2. **Test–retest agreement**: of the 38 items, 20 are compared against the first-pass approval results
   (`../human_review/P1_topic_safety_reviewed.csv`); report the agreement rate.
3. **False-negative rate and metrics**: per the sampling plan §6, HT-weighted p̂_FN → recall / specificity / F1,
   with intervals from a stratified bootstrap.

(The computation script is to be written in a later work package; see the validation-sprint task list.)

## 5. Reproducing this package (if needed)

```bash
cd <project>/Cascade/BERT_Python
<python>/python.exe -X utf8 scripts/build_negative_blind_review.py
```

It reads only `negative_audit_package.csv` and `P1_topic_safety_reviewed.csv`, and never modifies its inputs.
