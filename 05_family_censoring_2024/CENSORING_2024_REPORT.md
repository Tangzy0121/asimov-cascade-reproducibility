# Censoring re-analysis: both 2025 and 2026 right-censored (primary series ends 2024)

Retrieval was 2026-07-18; under the 18-month
publication-lag rule, 2025 is as incomplete as 2026 outside the CN fast
channel, so the primary series censors both 2025 and 2026 rather than 2026 alone. The 5-state HMM on 21 annual
points reads the censored right edge as decline; four HIGH labels flipped
under recent-year perturbation. This run truncates the family-normalized
annual series at 2024 and re-estimates D_j (5-state Gaussian HMM), L_j
(logistic S-curve), R_j = 10 x S_j x D_j x L_j, and the HIGH/MEDIUM/LOW tiers
with the frozen thresholds (0.08 / 0.02, conditional on s_j >= 2). All
estimators are imported unmodified from `scripts/family_primary_reestimation.py`;
`full_2026_raw` reproduces the frozen family outputs exactly
({"score_max_abs_diff": 8.881784197001252e-16, "risk_level_mismatches": 0, "decay_max_abs_diff": 1.1102230246251565e-16}).

## Corpus under censoring

- Full family corpus: 6,602 simple families, 21 annual points (2006-2026).
- Censored primary: 4,729 families with application year <= 2024, 19 annual points (2006-2024); 1,873 families removed (28.4%: 2025 = 1,371, 2026 = 502).

## HIGH sets

- Publication-level frozen HIGH: [7, 22, 25, 29, 40].
- Family full-series (to 2026) HIGH: [7, 22, 25].
- Family censored-2024 HIGH: [7, 25, 40].
- Retained [7, 25]; lost [22]; gained [40].
- Review-priority tier changes among the 20 safety candidates: 6.
- Rank correlation full vs censored-2024 (20 candidates): Spearman rho = 0.4866, p = 0.02959.
- HMM trend-direction changes (all 77 topics): 51; lifecycle-stage changes: 26.

## Focus topics (former publication/family HIGH)

| Topic | s_j | D_j full | D_j c2024 | R_j full | R_j c2024 | Tier full | Tier c2024 |
|---|---:|---:|---:|---:|---:|---|---|
| T7 | 2 | 0.9091 | 0.2500 | 1.2727 | 0.3500 | HIGH | HIGH |
| T22 | 5 | 0.8000 | 0.0100 | 4.8000 | 0.0600 | HIGH | MEDIUM |
| T25 | 4 | 0.0100 | 0.7000 | 0.0800 | 5.6000 | HIGH | HIGH |
| T29 | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | LOW | LOW |
| T40 | 3 | 0.0100 | 0.3333 | 0.0210 | 0.7000 | MEDIUM | HIGH |

## Tier changes among the 20 safety candidates

| Topic | Tier full | Tier c2024 | R_j full | R_j c2024 |
|---|---|---|---:|---:|
| T12 | LOW | MEDIUM | 0.0040 | 0.0240 |
| T22 | HIGH | MEDIUM | 4.8000 | 0.0600 |
| T27 | LOW | MEDIUM | 0.0060 | 0.0210 |
| T40 | MEDIUM | HIGH | 0.0210 | 0.7000 |
| T62 | LOW | MEDIUM | 0.0000 | 0.0600 |
| T74 | MEDIUM | LOW | 0.0400 | 0.0000 |

## Recent-year perturbation retention (tier per year-window variant)

Variants follow the frozen design of `scripts/temporal_sensitivity.py`
(delete censored years vs annualize 2026 x 12/6.5). `cut_2024` is the new
primary; the other columns are perturbations around it.

| Topic | full_2026_raw | cut_2025 | cut_2024 (main) | annualized_2026 |
|---|---|---|---|---|
| T7 | HIGH | LOW | HIGH | LOW |
| T22 | HIGH | HIGH | MEDIUM | MEDIUM |
| T25 | HIGH | HIGH | HIGH | HIGH |
| T29 | LOW | MEDIUM | LOW | MEDIUM |
| T40 | MEDIUM | MEDIUM | HIGH | MEDIUM |

## D_j / R_j distribution under the censored-2024 primary

| Scope | Metric | min | q25 | median | q75 | max |
|---|---|---:|---:|---:|---:|---:|
| all_77_topics | D_j | 0.0000 | 0.0100 | 0.0100 | 0.0100 | 0.9333 |
| all_77_topics | R_j | 0.0000 | 0.0000 | 0.0000 | 0.0040 | 5.6000 |
| 20_safety_candidates | D_j | 0.0000 | 0.0100 | 0.0100 | 0.0100 | 0.7000 |
| 20_safety_candidates | R_j | 0.0000 | 0.0040 | 0.0110 | 0.0510 | 5.6000 |

Threshold support (20 safety candidates, censored-2024): the HIGH tier holds
3 topic(s) with R_j in [0.3500, 5.6000];
the lowest HIGH score is 4.4x the 0.08 cutoff,
and 5.8x the highest non-HIGH candidate score
(0.0600). The cutoff sits in a distribution gap, not inside
the HIGH cluster.

## Number backfill map (paper old -> new -> main.tex location)

main.tex: `<manuscript>/main.tex` (READ-ONLY; not modified by this run).

| # | Quantity | Paper value | New value | main.tex location |
|---|---|---|---|---|
| 1 | Right-censoring statement | "the 2026 count is right-censored" (2026 only) | 2025 and 2026 both right-censored; primary series ends 2024 | line 179 (Methods, corpus paragraph); line 184 (Table I caption); line 230 (score/sensitivity paragraph) |
| 2 | Annual points for HMM | 21 (2006-2026) | 19 (2006-2024) | line 179 / Section III methods (HMM description) |
| 3 | Family corpus size | 6,602 families | 4,729 families (censored primary) | line 179, line 202 (Table I row), line 410 (Table IV row), abstract line 84 |
| 4 | Family HIGH set | Topics 7, 22, 25 (from 7/22/25/29/40) | Topics 7, 25, 40 | abstract line 84; line 305; line 410 |
| 5 | Recent-year flips | "Four HIGH labels changed under at least one recent-year perturbation" | see retention table above (cut_2024 column is now the primary, not a perturbation) | line 305 |
| 6 | Rank correlation | Spearman rho = 0.554, p = 0.0113 (full vs family) | rho = 0.4866, p = 0.02959 (family full vs censored-2024) | line 305 |
| 7 | Tier changes | 4/20 tier assignments changed (publication vs family) | 6/20 changed (family full vs censored-2024) | line 305, line 410 |
| 8 | HIGH threshold 0.08 support | "heuristic review-queue thresholds" (no distribution support) | HIGH R_j range [0.3500, 5.6000]; min HIGH = 4.4x cutoff; gap to max non-HIGH = 5.8x; D_j/R_j quantiles in table above | line 230 |
| 9 | Bootstrap P(HIGH) 0.94 vs 0.24-0.48 | publication-level, full series | NOT recomputed here (out of scope; publication-level artifact) | line 305, line 406 — flag for follow-up |

## Interpretation boundary

Same boundary as the frozen primary: re-estimation of temporal counts, HMM
decay, S-curve lifecycle, and the review-priority score in the frozen
BERTopic topic space. No BERTopic retraining; patent-family trends are not
accident probabilities. The held-out family STM gate is unaffected by year
truncation only if re-run on the censored corpus; that re-fit is NOT part of
this script.
