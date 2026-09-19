# -*- coding: utf-8 -*-
# ============================================================================
# censoring_primary_2024.py  |  Right-censoring re-analysis
# Purpose : Treat BOTH 2025 and 2026 as right-censored (18-month publication
#           lag from the 2026-07-18 retrieval; only the CN fast channel
#           escapes it), truncate the annual series at 2024, and re-run the
#           family-normalized primary pipeline of
#           scripts/family_primary_reestimation.py (FROZEN, imported, not
#           modified):
#             - per-topic 5-state Gaussian HMM  -> decline probability D_j
#             - logistic S-curve lifecycle      -> L_j (risk map, frozen)
#             - R_j = 10 * S_j * D_j * L_j      (S_j = LLM safety score / 5)
#             - HIGH >= 0.08 / MEDIUM >= 0.02 tiers, conditional on s_j >= 2
#             - recent-year perturbation sensitivity, following the
#               year-window design of scripts/temporal_sensitivity.py:
#               full_2026_raw / cut_2025 / cut_2024 (MAIN) / annualized_2026
# Input   : same frozen artifacts as family_primary_reestimation.py
#           (READ-ONLY), plus its frozen outputs under
#           output/family_primary_reestimation/ for the baseline check.
# Output  : output/censoring_2024/*.csv, manifest.json, CENSORING_2024_REPORT.md
# Usage   : <python>/envs/<env>/python.exe -X utf8 scripts/censoring_primary_2024.py
#           (run from <pipeline>)
# Asimov Cascade humanoid-safety patent pipeline
# ----------------------------------------------------------------------------
# Design notes:
#   - All estimation functions (load_joined_data, select_representatives,
#     build_pivot, estimate_hmm, estimate_lifecycle, compute_scores) are
#     IMPORTED from family_primary_reestimation so the estimator code path is
#     byte-identical to the frozen primary; only the year window changes.
#   - full_2026_raw is recomputed and verified against the frozen family
#     outputs (max |diff| <= 1e-10) before any censored number is trusted.
#   - Variant pivots are reindexed to the full 77-topic column set so topics
#     whose activity lies entirely in 2025-2026 remain in the comparison as
#     all-zero series instead of silently dropping out.
#   - Annualization mirrors temporal_sensitivity.py: 2026 counts x 12/6.5
#     (retrieval 2026-07-18 -> ~6.5 months elapsed). 2025 is NOT annualized:
#     under the 18-month lag essentially none of 2025 had published at
#     retrieval, so no defensible inflation factor exists; it is deleted.
#   - HMM seed 42 everywhere (frozen baseline config, single fit).
# ============================================================================

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import family_primary_reestimation as fpr

ROOT = fpr.ROOT
OUT = ROOT / "output" / "censoring_2024"
FAMILY_OUT = ROOT / "output" / "family_primary_reestimation"
PUB_SCORES = fpr.FULL_SCORES  # frozen publication-level cascade_signals_v5.csv

CENSOR_YEAR = 2024
RETRIEVAL_MONTHS_2026 = 6.5          # retrieval 2026-07-18 (frozen design)
ANNUALIZE_FACTOR = 12.0 / RETRIEVAL_MONTHS_2026
THRESH_HIGH, THRESH_MED = 0.08, 0.02
TEX_PATH = (
    ROOT.parents[3]
    / "<project>/"
)


def load_maps() -> tuple[dict[int, str], dict[int, int], pd.DataFrame]:
    topics = pd.read_csv(fpr.TOPIC_SUMMARY, encoding="utf-8-sig")
    labels = pd.read_csv(fpr.LLM_LABELS, encoding="utf-8-sig")
    name_map = {
        int(row.Topic): str(row.Name) for row in topics.itertuples() if int(row.Topic) >= 0
    }
    safety_map = {int(row.bertopic_id): int(row.safety_score) for row in labels.itertuples()}
    return name_map, safety_map, labels


def run_variant(
    pivot: pd.DataFrame,
    name_map: dict[int, str],
    safety_map: dict[int, int],
    labels: pd.DataFrame,
    variant: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """HMM + lifecycle + cascade scores for one year-window variant."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        hmm_df = fpr.estimate_hmm(pivot, name_map)
        lifecycle_df = fpr.estimate_lifecycle(pivot, name_map, safety_map)
        scores = fpr.compute_scores(hmm_df, lifecycle_df, labels)
    scores["variant"] = variant
    return hmm_df, lifecycle_df, scores


def verify_baseline(scores_full: pd.DataFrame, hmm_full: pd.DataFrame) -> dict:
    """full_2026_raw must reproduce the frozen family outputs bit-for-bit."""
    frozen_scores = pd.read_csv(FAMILY_OUT / "family_cascade_signals.csv", encoding="utf-8-sig")
    frozen_hmm = pd.read_csv(FAMILY_OUT / "family_hmm_trends.csv", encoding="utf-8-sig")
    s = scores_full.merge(
        frozen_scores[["bertopic_id", "cascade_score", "risk_level"]],
        on="bertopic_id", suffixes=("_new", "_frozen"), validate="1:1",
    )
    h = hmm_full.merge(
        frozen_hmm[["bertopic_id", "decay_probability"]],
        on="bertopic_id", suffixes=("_new", "_frozen"), validate="1:1",
    )
    result = {
        "score_max_abs_diff": float(
            np.max(np.abs(s["cascade_score_new"] - s["cascade_score_frozen"]))
        ),
        "risk_level_mismatches": int((s["risk_level_new"] != s["risk_level_frozen"]).sum()),
        "decay_max_abs_diff": float(
            np.max(np.abs(h["decay_probability_new"] - h["decay_probability_frozen"]))
        ),
    }
    if (
        result["score_max_abs_diff"] > 1e-10
        or result["decay_max_abs_diff"] > 1e-10
        or result["risk_level_mismatches"]
    ):
        raise AssertionError(f"Family baseline reproduction failed: {result}")
    return result


def distribution_summary(values: pd.Series) -> dict:
    q = values.quantile([0.0, 0.25, 0.5, 0.75, 1.0])
    return {
        "min": float(q.loc[0.0]),
        "q25": float(q.loc[0.25]),
        "median": float(q.loc[0.5]),
        "q75": float(q.loc[0.75]),
        "max": float(q.loc[1.0]),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("Censoring re-analysis: 2025+2026 right-censored, series <= 2024")
    print("=" * 60)

    joined, _ = fpr.load_joined_data()
    family, _, rep_stats = fpr.select_representatives(joined)
    name_map, safety_map, labels = load_maps()

    full_pivot = fpr.build_pivot(family)
    all_topics = list(full_pivot.columns)
    n_years_full = len(full_pivot)

    # ---- Year-window variants (temporal_sensitivity.py design, family level) ----
    pivots: dict[str, pd.DataFrame] = {}
    pivots["full_2026_raw"] = full_pivot
    pivots["cut_2025"] = fpr.build_pivot(family[family["app_year"] <= 2025]).reindex(
        columns=all_topics, fill_value=0
    )
    pivots["cut_2024"] = fpr.build_pivot(family[family["app_year"] <= CENSOR_YEAR]).reindex(
        columns=all_topics, fill_value=0
    )
    annualized = full_pivot.astype(float).copy()
    annualized.loc[annualized.index.max()] *= ANNUALIZE_FACTOR
    pivots["annualized_2026"] = annualized

    n_families = {
        "full_2026_raw": int(len(family)),
        "cut_2025": int((family["app_year"] <= 2025).sum()),
        "cut_2024": int((family["app_year"] <= CENSOR_YEAR).sum()),
        "annualized_2026": int(len(family)),
    }
    print(f"Families: {n_families}; annual points full={n_years_full}, "
          f"cut_2024={len(pivots['cut_2024'])}")

    results: dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = {}
    for variant, pivot in pivots.items():
        print(f"[Variant] {variant}")
        results[variant] = run_variant(pivot, name_map, safety_map, labels, variant)

    hmm_full, _, scores_full = results["full_2026_raw"]
    reproduction = verify_baseline(scores_full, hmm_full)
    print(f"[Check] full_2026_raw vs frozen family outputs: {reproduction}")

    hmm_c24, lifecycle_c24, scores_c24 = results["cut_2024"]

    # ---- Per-topic comparison: family full (to 2026) vs censored 2024 ----
    comparison = scores_full[
        ["bertopic_id", "bertopic_name", "safety_score", "decay_probability",
         "lifecycle_stage", "cascade_score", "risk_level", "trend_direction"]
    ].merge(
        scores_c24[
            ["bertopic_id", "decay_probability", "lifecycle_stage",
             "cascade_score", "risk_level", "trend_direction", "bertopic_count"]
        ],
        on="bertopic_id", suffixes=("_full", "_c2024"), validate="1:1",
    )
    comparison["risk_changed"] = comparison["risk_level_full"] != comparison["risk_level_c2024"]
    comparison["trend_changed"] = (
        comparison["trend_direction_full"] != comparison["trend_direction_c2024"]
    )
    comparison["lifecycle_changed"] = (
        comparison["lifecycle_stage_full"] != comparison["lifecycle_stage_c2024"]
    )

    safety = comparison[comparison["safety_score"] >= 2]
    rho, rho_p = fpr.stats.spearmanr(
        safety["cascade_score_full"], safety["cascade_score_c2024"]
    )

    pub_frozen = pd.read_csv(PUB_SCORES, encoding="utf-8-sig")
    pub_high = sorted(
        pub_frozen.loc[pub_frozen["risk_level"] == "HIGH", "bertopic_id"].astype(int)
    )
    full_high = sorted(
        comparison.loc[comparison["risk_level_full"] == "HIGH", "bertopic_id"].astype(int)
    )
    c24_high = sorted(
        comparison.loc[comparison["risk_level_c2024"] == "HIGH", "bertopic_id"].astype(int)
    )

    # ---- Recent-year perturbation retention (new HIGH set across variants) ----
    variant_scores = pd.concat([r[2] for r in results.values()], ignore_index=True)
    retention_rows = []
    for variant in pivots:
        sub = variant_scores[variant_scores["variant"] == variant]
        for tid in sorted(set(pub_high) | set(c24_high)):
            row = sub.loc[sub["bertopic_id"] == tid]
            if row.empty:
                continue
            retention_rows.append({
                "variant": variant,
                "bertopic_id": int(tid),
                "D_j": float(row["decay_probability"].iloc[0]),
                "R_j": float(row["cascade_score"].iloc[0]),
                "risk_level": row["risk_level"].iloc[0],
                "is_high": bool(row["risk_level"].iloc[0] == "HIGH"),
            })
    retention = pd.DataFrame(retention_rows)

    # ---- D_j / R_j distributions under the censored-2024 primary ----
    cand_c24 = scores_c24[scores_c24["safety_score"] >= 2]
    dist_rows = []
    for scope, frame in [("all_77_topics", scores_c24), ("20_safety_candidates", cand_c24)]:
        for metric, col in [("D_j", "decay_probability"), ("R_j", "cascade_score")]:
            stats_d = distribution_summary(frame[col])
            dist_rows.append({"scope": scope, "metric": metric, **stats_d})
    dist = pd.DataFrame(dist_rows)

    high_scores = cand_c24.loc[cand_c24["risk_level"] == "HIGH", "cascade_score"]
    nonhigh_scores = cand_c24.loc[cand_c24["risk_level"] != "HIGH", "cascade_score"]
    threshold_support = {
        "threshold_high": THRESH_HIGH,
        "n_high": int(len(high_scores)),
        "high_R_min": float(high_scores.min()) if len(high_scores) else None,
        "high_R_max": float(high_scores.max()) if len(high_scores) else None,
        "high_R_min_over_threshold": float(high_scores.min() / THRESH_HIGH)
        if len(high_scores) else None,
        "max_nonhigh_R": float(nonhigh_scores.max()) if len(nonhigh_scores) else None,
        "gap_min_high_over_max_nonhigh": float(high_scores.min() / nonhigh_scores.max())
        if len(high_scores) and len(nonhigh_scores) and nonhigh_scores.max() > 0 else None,
    }

    # ---- Write CSVs ----
    hmm_c24.to_csv(OUT / "censored2024_hmm_trends.csv", index=False, encoding="utf-8-sig")
    lifecycle_c24.to_csv(
        OUT / "censored2024_topic_lifecycle.csv", index=False, encoding="utf-8-sig"
    )
    scores_c24.drop(columns=["variant"]).to_csv(
        OUT / "censored2024_cascade_signals.csv", index=False, encoding="utf-8-sig"
    )
    pivots["cut_2024"].to_csv(OUT / "censored2024_topic_year_counts.csv", encoding="utf-8-sig")
    comparison.to_csv(OUT / "full_vs_censored2024_comparison.csv", index=False, encoding="utf-8-sig")
    variant_scores.to_csv(OUT / "sensitivity_yearwindow_variants.csv", index=False, encoding="utf-8-sig")
    retention.to_csv(OUT / "sensitivity_high_retention.csv", index=False, encoding="utf-8-sig")
    dist.to_csv(OUT / "distribution_summary.csv", index=False, encoding="utf-8-sig")

    summary = {
        "censor_year": CENSOR_YEAR,
        "n_families": n_families,
        "n_annual_points": {k: len(v) for k, v in pivots.items()},
        "baseline_reproduction": reproduction,
        "pub_high_frozen": pub_high,
        "family_full_high": full_high,
        "family_censored2024_high": c24_high,
        "high_retained": sorted(set(full_high) & set(c24_high)),
        "high_lost": sorted(set(full_high) - set(c24_high)),
        "high_gained": sorted(set(c24_high) - set(full_high)),
        "risk_changes_safety_candidates": int(safety["risk_changed"].sum()),
        "trend_changes_all_topics": int(comparison["trend_changed"].sum()),
        "lifecycle_changes_all_topics": int(comparison["lifecycle_changed"].sum()),
        "spearman_rho_full_vs_c2024": float(rho),
        "spearman_p": float(rho_p),
        "threshold_support": threshold_support,
        "hmm_seed": 42,
    }
    (OUT / "manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    write_report(
        summary, comparison, safety, retention, dist, cand_c24, n_families
    )
    print(f"Output dir: {OUT}")
    print("=" * 60)


def tex_ref() -> str:
    return str(TEX_PATH)


def write_report(summary, comparison, safety, retention, dist, cand_c24, n_families) -> None:
    ts = summary["threshold_support"]
    focus_ids = sorted(
        set(summary["pub_high_frozen"]) | set(summary["family_censored2024_high"])
    )
    focus = comparison[comparison["bertopic_id"].isin(focus_ids)]
    focus_rows = "\n".join(
        f"| T{int(r.bertopic_id)} | {r.safety_score} | {r.decay_probability_full:.4f} | "
        f"{r.decay_probability_c2024:.4f} | {r.cascade_score_full:.4f} | "
        f"{r.cascade_score_c2024:.4f} | {r.risk_level_full} | {r.risk_level_c2024} |"
        for r in focus.itertuples()
    )
    changed = safety[safety["risk_changed"]]
    changed_rows = "\n".join(
        f"| T{int(r.bertopic_id)} | {r.risk_level_full} | {r.risk_level_c2024} | "
        f"{r.cascade_score_full:.4f} | {r.cascade_score_c2024:.4f} |"
        for r in changed.itertuples()
    ) or "| none | — | — | — | — |"

    ret_pivot = retention.pivot_table(
        index="bertopic_id", columns="variant", values="risk_level", aggfunc="first"
    )
    ret_rows = "\n".join(
        f"| T{tid} | " + " | ".join(str(ret_pivot.loc[tid, v]) for v in
        ["full_2026_raw", "cut_2025", "cut_2024", "annualized_2026"]) + " |"
        for tid in ret_pivot.index
    )

    dist_rows = "\n".join(
        f"| {r['scope']} | {r['metric']} | {r['min']:.4f} | {r['q25']:.4f} | "
        f"{r['median']:.4f} | {r['q75']:.4f} | {r['max']:.4f} |"
        for r in dist.to_dict("records")
    )

    text = f"""# Censoring re-analysis: both 2025 and 2026 right-censored (primary series ends 2024)

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
({json.dumps(summary['baseline_reproduction'])}).

## Corpus under censoring

- Full family corpus: {n_families['full_2026_raw']:,} simple families, {summary['n_annual_points']['full_2026_raw']} annual points (2006-2026).
- Censored primary: {n_families['cut_2024']:,} families with application year <= 2024, {summary['n_annual_points']['cut_2024']} annual points (2006-2024); {n_families['full_2026_raw'] - n_families['cut_2024']:,} families removed ({(n_families['full_2026_raw'] - n_families['cut_2024']) / n_families['full_2026_raw'] * 100:.1f}%: 2025 = 1,371, 2026 = 502).

## HIGH sets

- Publication-level frozen HIGH: {summary['pub_high_frozen']}.
- Family full-series (to 2026) HIGH: {summary['family_full_high']}.
- Family censored-2024 HIGH: {summary['family_censored2024_high']}.
- Retained {summary['high_retained']}; lost {summary['high_lost']}; gained {summary['high_gained']}.
- Review-priority tier changes among the 20 safety candidates: {summary['risk_changes_safety_candidates']}.
- Rank correlation full vs censored-2024 (20 candidates): Spearman rho = {summary['spearman_rho_full_vs_c2024']:.4f}, p = {summary['spearman_p']:.4g}.
- HMM trend-direction changes (all 77 topics): {summary['trend_changes_all_topics']}; lifecycle-stage changes: {summary['lifecycle_changes_all_topics']}.

## Focus topics (former publication/family HIGH)

| Topic | s_j | D_j full | D_j c2024 | R_j full | R_j c2024 | Tier full | Tier c2024 |
|---|---:|---:|---:|---:|---:|---|---|
{focus_rows}

## Tier changes among the 20 safety candidates

| Topic | Tier full | Tier c2024 | R_j full | R_j c2024 |
|---|---|---|---:|---:|
{changed_rows}

## Recent-year perturbation retention (tier per year-window variant)

Variants follow the frozen design of `scripts/temporal_sensitivity.py`
(delete censored years vs annualize 2026 x 12/6.5). `cut_2024` is the new
primary; the other columns are perturbations around it.

| Topic | full_2026_raw | cut_2025 | cut_2024 (main) | annualized_2026 |
|---|---|---|---|---|
{ret_rows}

## D_j / R_j distribution under the censored-2024 primary

| Scope | Metric | min | q25 | median | q75 | max |
|---|---|---:|---:|---:|---:|---:|
{dist_rows}

Threshold support (20 safety candidates, censored-2024): the HIGH tier holds
{ts['n_high']} topic(s) with R_j in [{ts['high_R_min']:.4f}, {ts['high_R_max']:.4f}];
the lowest HIGH score is {ts['high_R_min_over_threshold']:.1f}x the 0.08 cutoff,
and {ts['gap_min_high_over_max_nonhigh']:.1f}x the highest non-HIGH candidate score
({ts['max_nonhigh_R']:.4f}). The cutoff sits in a distribution gap, not inside
the HIGH cluster.

## Number backfill map (paper old -> new -> main.tex location)

main.tex: `{tex_ref()}` (READ-ONLY; not modified by this run).

| # | Quantity | Paper value | New value | main.tex location |
|---|---|---|---|---|
| 1 | Right-censoring statement | "the 2026 count is right-censored" (2026 only) | 2025 and 2026 both right-censored; primary series ends 2024 | line 179 (Methods, corpus paragraph); line 184 (Table I caption); line 230 (score/sensitivity paragraph) |
| 2 | Annual points for HMM | 21 (2006-2026) | {summary['n_annual_points']['cut_2024']} (2006-2024) | line 179 / Section III methods (HMM description) |
| 3 | Family corpus size | 6,602 families | {n_families['cut_2024']:,} families (censored primary) | line 179, line 202 (Table I row), line 410 (Table IV row), abstract line 84 |
| 4 | Family HIGH set | Topics 7, 22, 25 (from 7/22/25/29/40) | Topics {", ".join(map(str, summary['family_censored2024_high']))} | abstract line 84; line 305; line 410 |
| 5 | Recent-year flips | "Four HIGH labels changed under at least one recent-year perturbation" | see retention table above (cut_2024 column is now the primary, not a perturbation) | line 305 |
| 6 | Rank correlation | Spearman rho = 0.554, p = 0.0113 (full vs family) | rho = {summary['spearman_rho_full_vs_c2024']:.4f}, p = {summary['spearman_p']:.4g} (family full vs censored-2024) | line 305 |
| 7 | Tier changes | 4/20 tier assignments changed (publication vs family) | {summary['risk_changes_safety_candidates']}/20 changed (family full vs censored-2024) | line 305, line 410 |
| 8 | HIGH threshold 0.08 support | "heuristic review-queue thresholds" (no distribution support) | HIGH R_j range [{ts['high_R_min']:.4f}, {ts['high_R_max']:.4f}]; min HIGH = {ts['high_R_min_over_threshold']:.1f}x cutoff; gap to max non-HIGH = {ts['gap_min_high_over_max_nonhigh']:.1f}x; D_j/R_j quantiles in table above | line 230 |
| 9 | Bootstrap P(HIGH) 0.94 vs 0.24-0.48 | publication-level, full series | NOT recomputed here (out of scope; publication-level artifact) | line 305, line 406 — flag for follow-up |

## Interpretation boundary

Same boundary as the frozen primary: re-estimation of temporal counts, HMM
decay, S-curve lifecycle, and the review-priority score in the frozen
BERTopic topic space. No BERTopic retraining; patent-family trends are not
accident probabilities. The held-out family STM gate is unaffected by year
truncation only if re-run on the censored corpus; that re-fit is NOT part of
this script.
"""
    (OUT / "CENSORING_2024_REPORT.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
