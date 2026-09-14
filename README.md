# Reproducibility Package — Asimov Cascade Monitoring in Humanoid Robotics (ICRA 2027 submission)

This repository archives every artifact behind the "archived with the
reproducibility package" statements in the manuscript. All numbers reported
in the paper were checked against the manifests, CSVs, and reports in this
tree by `01_manuscript_snapshot/check_tex_numbers_v26.py`.

The package is shared for double-anonymous review. The raw incoPat export is
not redistributable under its database license; see "Corpus access" below.

## Paper claim → package location

| Manuscript claim (section) | Location |
|---|---|
| Verbatim Boolean query (IV-A) | `02_corpus_scripts/query.txt` (also embedded in `merge_v5_dataset.py`) |
| Cleaning / family-normalization scripts (IV-A) | `02_corpus_scripts/clean_v5_dataset.py`, `05_family_censoring_2024/family_primary_reestimation.py` |
| Frozen screening prompt, settings, seeds (IV-C) | `03_screening/llm_safety_classify.py`, `03_screening/llm_safety_seeds.json` |
| Frozen screening labels + multi-run raw responses (IV-C, V-A) | `03_screening/llm_safety_labels.csv`, `03_screening/multirun_stability/{deepseek,kimi}/run_*/raw_responses.jsonl` |
| Screen scores and adjudication status (V-A) | `03_screening/llm_safety_labels.csv` + `12_dual_review_77/` |
| BERTopic frozen outputs and stability (IV-B) | `04_topic_model/` |
| D_j / R_j distributions (IV-E) | `05_family_censoring_2024/distribution_summary.csv` |
| Censored-2024 primary analysis, all outputs (IV-E, V-B) | `05_family_censoring_2024/` (frozen numbers in `manifest.json`) |
| STM train/test and cross-model gates (IV-F, V-C) | `06_stm_crossmodel/` |
| ASIMOV frozen reproduction + role diagnostic (IV-H, V-D) | `07_asimov/` (`evidence_report.md`, `role_separated/report.md`; scenario text in `mapping_v2.csv` is from the publicly released ASIMOV benchmark, arXiv:2503.08663) |
| Content-audit codebook and results (IV-G, V-E) | `08_content_audit_t22_t25/` (`CODEBOOK.md`, `audit_results.md`/`.xlsx`, `duplicate_text_sensitivity.xlsx`) |
| Simulation pilot preregistration, trial table, audit report (IV-I, V-F) | `09_simulation_pilot/` (`config/preregistered.yaml`, `outputs/raw_trials.csv`, `AUDIT_REPORT.md`, `final_manifest.json`) |
| Human review of 20 candidates (V-A, Table II) | `10_human_review/` (`P1_topic_safety_reviewed.csv`) |
| 57 negative blind-audit records (Table IV) | `10_human_review/negative_audit_blind/` (admin keys not included) |
| ISO 18-pair dual blind review (VI-C) | `11_iso_standards_review/` (scoring script included; admin key not included) |
| 77-topic dual adjudication (Limitations) | `12_dual_review_77/` |
| Frozen paper numbers (Tables I/IV provenance) | `paper_numbers.json`, `paper_numbers_v5.json`, `01_manuscript_snapshot/check_tex_numbers_v26.py` |
| Manuscript snapshot | `01_manuscript_snapshot/main.tex` (author block removed) + `figures/` |

## Corpus access

The corpus was exported from incoPat on 2026-07-18. incoPat is a licensed
database, so the raw export cannot be redistributed. To rebuild the corpus
with your own access:

1. Run the verbatim query in `02_corpus_scripts/query.txt` against incoPat
   (fields: title + abstract; no date restriction). The 2026-07-18 run
   returned 9,710 records.
2. Merge the batched exports with `02_corpus_scripts/merge_v5_dataset.py`.
3. Clean with `02_corpus_scripts/clean_v5_dataset.py` (9,710 → 8,928
   records; funnel counts in `paper_numbers_v5.json`).

Every downstream artifact in this package derives from that frozen corpus;
re-retrieval on a later date will yield slightly different counts as the
database grows.

Abstracts and claims of published patents are public disclosure documents
issued by patent offices. The text columns in
`06_stm_crossmodel/stm_input.csv` and
`05_family_censoring_2024/family_primary_reestimation/stm/stm_input_family.csv`
are therefore included so that every text-level result (STM, ASIMOV
exposure, content audit) can be recomputed. What is not redistributed is
the licensed incoPat batch export itself (incoPat value-added fields and
export format).

## Verifying the numbers

`01_manuscript_snapshot/check_tex_numbers_v26.py` diffs the key numbers in
the manuscript snapshot against the on-disk manifests and reports. The
script's path constants reference the original project layout; point them at
your checkout of this repository before running.

## Notes

- Blinding/admin keys are deliberately excluded: the ISO prespecified key,
  the negative-audit admin keys, and the content-audit topic key are not in
  this package.
- The frozen first-round screening judgments are archived as labels in
  `03_screening/llm_safety_labels.csv`; raw JSONL responses are included for
  the multi-run sensitivity re-screenings.
- The simulation trial table (`09_simulation_pilot/outputs/raw_trials.csv`)
  is kept in full so every statistic can be recomputed.
- Frozen review records (CSV/JSON) keep the reviewers' original free-text
  notes verbatim, including some Chinese; all labels, codebooks, protocols,
  and reports are in English.

## License

Code in this repository is released under the MIT License (see `LICENSE`).
Patent bibliographic data remain subject to the incoPat license; no raw
export is included.
