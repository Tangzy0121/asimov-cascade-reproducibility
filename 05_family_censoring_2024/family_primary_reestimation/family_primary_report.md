# Family-normalized primary re-estimation

## Corpus and reproducibility

- Publication corpus: 8,928 records.
- Simple-family primary corpus: 6,602 unique families (2,326 publication rows removed).
- Earliest-application selection differs from the earlier first-returned-record rule for 159 families, changes the representative BERTopic label for 16, and changes application year for 131.
- The independent reimplementation reproduces the frozen publication-level HMM, lifecycle, score, and risk labels exactly: {"hmm_direction_mismatches": 0, "hmm_decay_max_abs_diff": 1.1102230246251565e-16, "lifecycle_stage_mismatches": 0, "score_max_abs_diff": 2.220446049250313e-16, "risk_level_mismatches": 0}.

## Main score result

- Publication-level HIGH topics: [7, 22, 25, 29, 40].
- Family-normalized HIGH topics: [7, 22, 25].
- Retained: [7, 22, 25]; lost: [29, 40]; gained: [].
- Rank correlation across the 20 safety candidates: Spearman rho = 0.5539, p = 0.01128.
- Risk-level changes among safety candidates: 4.

| Topic | Full label | Family label | Full score | Family score |
|---|---:|---:|---:|---:|
| T29 | HIGH | LOW | 1.4700 | 0.0000 |
| T37 | MEDIUM | LOW | 0.0800 | 0.0040 |
| T40 | HIGH | MEDIUM | 1.6800 | 0.0210 |
| T62 | MEDIUM | LOW | 0.0600 | 0.0000 |

## Interpretation boundary

This is a primary re-estimation of temporal counts, five-state HMM decay, logistic S-curve lifecycle, and the published review-priority score in the frozen BERTopic topic space. It does not retrain BERTopic and does not convert patent-family trends into accident probabilities. The held-out family-normalized STM result is reported separately after the R fit completes.
