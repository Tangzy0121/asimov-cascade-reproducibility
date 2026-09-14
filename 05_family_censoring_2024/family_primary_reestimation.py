# -*- coding: utf-8 -*-
"""Primary re-estimation on one representative per simple patent family.

This script freezes the published BERTopic topic space and safety labels, then
re-estimates the temporal components of the manuscript on 6,703 simple-family
representatives.  The family representative is the earliest application-date
record, with application year and original row order as deterministic tie
breakers.  It also prepares the family-normalized STM input and, after the R
model is run, summarizes held-out STM and cross-model gates.

Usage (from Cascade/BERT_Python):
  <python>/python.exe -X utf8 scripts/family_primary_reestimation.py
  E:/R-4.6.0/bin/Rscript.exe ../STM_R/run_stm_family_primary.R
  <python>/python.exe -X utf8 scripts/family_primary_reestimation.py --post-stm-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from hmmlearn import hmm
from scipy import stats
from scipy.optimize import curve_fit
from statsmodels.stats.multitest import multipletests


ROOT = Path(__file__).resolve().parent.parent
DATA_XLSX = ROOT.parent / "data" / "humanoid_safety_patents_v5_clean.xlsx"
DOC_TOPIC = ROOT / "output/time_analysis/04_bertopic_time/document_topic_assignment.csv"
TOPIC_SUMMARY = ROOT / "output/time_analysis/04_bertopic_time/topic_summary.csv"
LLM_LABELS = ROOT / "output/time_analysis/10_cascade/llm_safety_labels.csv"
FULL_HMM = ROOT / "output/time_analysis/11_temporal_enrichment/01_direct_trends/hmm_trends.csv"
FULL_LIFECYCLE = ROOT / "output/time_analysis/11_temporal_enrichment/02_lifecycle/topic_lifecycle.csv"
FULL_SCORES = ROOT / "output/time_analysis/11_temporal_enrichment/06_cascade_v3/cascade_signals_v5.csv"
STM_INPUT = ROOT / "output/time_analysis/04_stm/stm_input.csv"
HUMAN_REVIEW = ROOT / "output/subsystem_validation/human_review/P1_topic_safety_reviewed.csv"
OUT = ROOT / "output/family_primary_reestimation"
STM_OUT = OUT / "stm"

N_STATES = 5
STATE_NAMES = ["nascent", "emerging", "growing", "mature", "declining"]
MIN_YEARS_FOR_HMM = 5
EXPECTED_FULL_N = 8928
EXPECTED_FAMILY_N = 6602  # after family-ID type normalization (was 6,703 on raw mixed-type IDs)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_identifier(values: pd.Series) -> pd.Series:
    return values.fillna("").astype(str).str.strip()


def load_joined_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    patent = pd.read_excel(
        DATA_XLSX,
        usecols=["Publication No", "Application Date", "简单同族ID"],
    )
    # Normalize mixed str/int simple-family IDs BEFORE any dedup/groupby:
    # the raw column mixes str and int rows; raw drop_duplicates overcounts
    # families (6,703 raw vs 6,602 normalized).
    patent["简单同族ID"] = normalize_identifier(patent["简单同族ID"])
    assignment = pd.read_csv(DOC_TOPIC, encoding="utf-8-sig")
    if len(patent) != EXPECTED_FULL_N or len(assignment) != EXPECTED_FULL_N:
        raise AssertionError(
            f"Unexpected corpus size: patent={len(patent)}, assignment={len(assignment)}"
        )
    if not normalize_identifier(patent["Publication No"]).equals(
        normalize_identifier(assignment["patent_number"])
    ):
        raise AssertionError("Publication-number join is not 1:1 in row order")
    if (patent["简单同族ID"] == "").any():
        raise AssertionError("Missing simple-family IDs")

    joined = pd.concat(
        [patent.reset_index(drop=True), assignment.reset_index(drop=True)], axis=1
    )
    joined["source_row"] = np.arange(len(joined), dtype=int)
    joined["application_date"] = pd.to_datetime(
        joined["Application Date"], errors="coerce"
    )
    joined["app_year"] = joined["app_year"].astype(int)
    return joined, assignment


def select_representatives(joined: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    first = joined.sort_values("source_row").drop_duplicates("简单同族ID", keep="first")
    earliest = (
        joined.sort_values(
            ["简单同族ID", "application_date", "app_year", "source_row"],
            na_position="last",
        )
        .drop_duplicates("简单同族ID", keep="first")
        .sort_values("source_row")
        .reset_index(drop=True)
    )
    if len(earliest) != EXPECTED_FAMILY_N:
        raise AssertionError(f"Expected {EXPECTED_FAMILY_N} families, found {len(earliest)}")
    if earliest["简单同族ID"].nunique() != EXPECTED_FAMILY_N:
        raise AssertionError("Family representatives are not unique")

    audit = first[["简单同族ID", "source_row", "topic", "app_year"]].merge(
        earliest[["简单同族ID", "source_row", "topic", "app_year"]],
        on="简单同族ID",
        suffixes=("_first", "_earliest"),
        validate="1:1",
    )
    stats_out = {
        "n_publications": int(len(joined)),
        "n_family_ids_raw_excel": 6703,  # documented pre-normalization count (mixed str/int IDs)
        "n_simple_families": int(len(earliest)),
        "rows_removed": int(len(joined) - len(earliest)),
        "representative_row_changed": int(
            (audit["source_row_first"] != audit["source_row_earliest"]).sum()
        ),
        "representative_topic_changed": int(
            (audit["topic_first"] != audit["topic_earliest"]).sum()
        ),
        "representative_year_changed": int(
            (audit["app_year_first"] != audit["app_year_earliest"]).sum()
        ),
    }
    return earliest, audit, stats_out


def build_pivot(records: pd.DataFrame) -> pd.DataFrame:
    clean = records[records["topic"] >= 0].copy()
    pivot = clean.pivot_table(
        index="app_year", columns="topic", aggfunc="size", fill_value=0
    ).astype(int)
    years = range(int(pivot.index.min()), int(pivot.index.max()) + 1)
    return pivot.reindex(years, fill_value=0)


def discretize_observations(series: np.ndarray) -> np.ndarray:
    if series.max() == 0:
        return np.zeros(len(series), dtype=int)
    positive = series[series > 0]
    tertiles = np.percentile(positive, [33.33, 66.67]) if len(positive) else [0, 1]
    observations = np.zeros(len(series), dtype=int)
    observations[series > tertiles[1]] = 2
    observations[(series > tertiles[0]) & (series <= tertiles[1])] = 1
    return observations


def slope_fallback(yearly_counts: np.ndarray) -> dict:
    years = np.arange(len(yearly_counts))
    slope, _, _, p_value, _ = stats.linregress(years, yearly_counts)
    if p_value < 0.1 and slope < -0.05:
        direction = "declining"
    elif p_value < 0.1 and slope > 0.05:
        direction = "growing"
    elif slope < -0.05:
        direction = "weak_decline"
    elif slope > 0.05:
        direction = "weak_growth"
    else:
        direction = "stable"
    decay = max(0.0, min(1.0, -slope / max(abs(slope), 0.01)))
    return {
        "hmm_fitted": False,
        "current_state": -1,
        "current_state_name": "fallback_linear",
        "decay_probability": decay if "declin" in direction else 0.01,
        "trend_direction": direction,
        "viterbi_path": "",
        "hmm_score": 0.0,
    }


def fit_hmm(yearly_counts: np.ndarray) -> dict:
    first_nonzero = int(np.argmax(yearly_counts > 0))
    counts = yearly_counts[first_nonzero:]
    if len(yearly_counts) < MIN_YEARS_FOR_HMM or len(counts) < MIN_YEARS_FOR_HMM:
        return slope_fallback(yearly_counts)
    observations = discretize_observations(counts)
    x = observations.reshape(-1, 1)
    try:
        model = hmm.GaussianHMM(
            n_components=N_STATES,
            covariance_type="diag",
            n_iter=500,
            random_state=42,
            tol=1e-4,
        )
        model.fit(x)
        log_probability, raw_states = model.decode(x)
    except Exception:
        return slope_fallback(yearly_counts)

    means = {}
    for state in range(N_STATES):
        mask = raw_states == state
        means[state] = observations[mask].mean() if mask.any() else -1
    ordered = sorted(means, key=means.get)
    state_map: dict[int, int] = {}
    for index, raw_state in enumerate(ordered):
        if index == 0:
            state_map[raw_state] = 0
        elif index == 1:
            state_map[raw_state] = 1
        elif index == len(ordered) - 1:
            state_map[raw_state] = 3
        else:
            state_map[raw_state] = 2
    recent = observations[-min(3, len(observations)) :]
    if len(recent) >= 2 and recent[-1] < recent[0]:
        state_map[int(raw_states[-1])] = 4
    lifecycle_states = np.array([state_map.get(int(state), 2) for state in raw_states])
    declining_raw = [raw for raw, mapped in state_map.items() if mapped == 4]
    if declining_raw:
        decay = float(model.transmat_[int(raw_states[-1]), declining_raw[0]])
    else:
        decay = 0.01

    if lifecycle_states[-1] == 4:
        direction = "declining"
    elif lifecycle_states[-1] == 0:
        direction = "nascent"
    elif len(lifecycle_states) >= 3 and lifecycle_states[-1] > lifecycle_states[-3]:
        direction = "growing"
    elif len(lifecycle_states) >= 3 and lifecycle_states[-1] < lifecycle_states[-3]:
        direction = "declining"
    elif lifecycle_states[-1] == 3:
        direction = "mature"
    elif lifecycle_states[-1] == 2:
        direction = "growing"
    elif lifecycle_states[-1] == 1:
        direction = "emerging"
    else:
        direction = "stable"
    return {
        "hmm_fitted": True,
        "current_state": int(lifecycle_states[-1]),
        "current_state_name": STATE_NAMES[int(lifecycle_states[-1])],
        "decay_probability": min(decay, 1.0),
        "trend_direction": direction,
        "viterbi_path": ",".join(str(int(value)) for value in lifecycle_states),
        "hmm_score": float(log_probability / len(x)),
    }


def estimate_hmm(pivot: pd.DataFrame, name_map: dict[int, str]) -> pd.DataFrame:
    rows = []
    for topic_id in sorted(int(value) for value in pivot.columns):
        result = fit_hmm(pivot[topic_id].to_numpy(dtype=float))
        rows.append(
            {
                "bertopic_id": topic_id,
                "bertopic_name": name_map.get(topic_id, f"Topic_{topic_id}"),
                "n_years_active": int((pivot[topic_id].to_numpy() > 0).sum()),
                **result,
            }
        )
    return pd.DataFrame(rows).sort_values("bertopic_id").reset_index(drop=True)


def logistic(t: np.ndarray, capacity: float, rate: float, midpoint: float) -> np.ndarray:
    return capacity / (1.0 + np.exp(-rate * (t - midpoint)))


def fit_s_curve(years: np.ndarray, cumulative: np.ndarray) -> tuple:
    if len(years) < 4:
        return None, None, None, 0.0, False
    capacity_max = max(cumulative[-1] * 3, cumulative[-1] + 5)
    capacity_min = cumulative[-1] * 0.8
    try:
        params, _ = curve_fit(
            logistic,
            years.astype(float),
            cumulative.astype(float),
            p0=[cumulative[-1] * 1.2, 0.3, np.median(years)],
            bounds=(
                [capacity_min, 0.01, years.min() - 5],
                [capacity_max, 2.0, years.max() + 5],
            ),
            maxfev=5000,
        )
        capacity, rate, midpoint = params
        predicted = logistic(years, capacity, rate, midpoint)
        residual = np.sum((cumulative - predicted) ** 2)
        total = np.sum((cumulative - cumulative.mean()) ** 2)
        r_squared = 1.0 - residual / max(total, 1e-10)
        return capacity, rate, midpoint, r_squared, True
    except Exception:
        return None, None, None, 0.0, False


def classify_lifecycle(
    slope: float,
    tau: float,
    capacity: float | None,
    rate: float | None,
    r_squared: float,
    fit_ok: bool,
    counts: np.ndarray,
) -> tuple[str, float]:
    total = counts.sum()
    active_years = int((counts > 0).sum())
    if total < 5 or active_years < 3:
        return "nascent", 0.0
    if not fit_ok or r_squared < 0.3:
        if slope > 0.1 and total >= 3:
            return "growing", min(total / max(total, 50), 1.0)
        if slope < -0.05:
            return "declining", max(1.0 - total / max(counts.max(), 1), 0.0)
        return "nascent", total / max(total, 50)
    cumulative_fraction = total / max(float(capacity), 1.0)
    if cumulative_fraction < 0.10:
        stage = "emerging"
    elif cumulative_fraction < 0.50 and float(rate) > 0.1:
        stage = "growing"
    elif cumulative_fraction < 0.90 and float(rate) > 0:
        stage = "mature"
    elif slope < -0.02 or (tau < -0.1 and not np.isnan(tau)):
        stage = "declining"
    elif cumulative_fraction >= 0.90:
        stage = "saturated"
    else:
        stage = "mature"
    growth_component = min(max(float(rate) / 0.5, 0), 1) if rate else 0.5
    tmi = cumulative_fraction * (1.0 - growth_component)
    return stage, min(max(tmi, 0), 1)


def estimate_lifecycle(
    pivot: pd.DataFrame,
    name_map: dict[int, str],
    safety_map: dict[int, int],
) -> pd.DataFrame:
    years = pivot.index.to_numpy(dtype=float)
    rows = []
    for topic_id in sorted(int(value) for value in pivot.columns):
        counts = pivot[topic_id].to_numpy(dtype=float)
        active = int((counts > 0).sum())
        total = int(counts.sum())
        if active < 3 or total < 5:
            rows.append(
                {
                    "bertopic_id": topic_id,
                    "bertopic_name": name_map.get(topic_id, f"T{topic_id}"),
                    "bertopic_count": total,
                    "n_years_active": active,
                    "K": np.nan,
                    "r": np.nan,
                    "tm": np.nan,
                    "r_squared": np.nan,
                    "lifecycle_stage": "nascent",
                    "tmi": 0.0,
                    "current_fraction_of_K": np.nan,
                    "fit_reliable": False,
                    "safety_score": safety_map.get(topic_id, 0),
                }
            )
            continue
        cumulative = np.cumsum(counts)
        capacity, rate, midpoint, r_squared, fit_ok = fit_s_curve(years, cumulative)
        mask = counts > 0
        slope, _, _, _, _ = stats.linregress(years[mask], counts[mask])
        tau, _ = stats.kendalltau(years[mask], counts[mask])
        stage, tmi = classify_lifecycle(
            slope, tau, capacity, rate, r_squared, fit_ok, counts
        )
        current_fraction = (
            cumulative[-1] / max(float(capacity), 1.0)
            if fit_ok and capacity
            else np.nan
        )
        rows.append(
            {
                "bertopic_id": topic_id,
                "bertopic_name": name_map.get(topic_id, f"T{topic_id}"),
                "bertopic_count": total,
                "n_years_active": active,
                "K": round(capacity, 2) if capacity else np.nan,
                "r": round(rate, 4) if rate else np.nan,
                "tm": round(midpoint, 1) if midpoint else np.nan,
                "r_squared": round(r_squared, 4),
                "lifecycle_stage": stage,
                "tmi": round(tmi, 4),
                "current_fraction_of_K": round(current_fraction, 4)
                if not np.isnan(current_fraction)
                else np.nan,
                "fit_reliable": bool(fit_ok and r_squared >= 0.3),
                "safety_score": safety_map.get(topic_id, 0),
            }
        )
    return pd.DataFrame(rows).sort_values("bertopic_id").reset_index(drop=True)


def compute_scores(
    hmm_df: pd.DataFrame,
    lifecycle_df: pd.DataFrame,
    labels: pd.DataFrame,
) -> pd.DataFrame:
    frame = labels[
        ["bertopic_id", "bertopic_name", "safety_score", "safety_category"]
    ].copy()
    frame = frame.merge(
        hmm_df[
            [
                "bertopic_id",
                "decay_probability",
                "trend_direction",
                "current_state_name",
            ]
        ],
        on="bertopic_id",
        how="left",
    )
    frame = frame.merge(
        lifecycle_df[
            ["bertopic_id", "lifecycle_stage", "tmi", "fit_reliable", "bertopic_count"]
        ],
        on="bertopic_id",
        how="left",
    )
    frame["dim_safety"] = frame["safety_score"].fillna(0) / 5.0
    frame["dim_temporal_decay"] = frame["decay_probability"].fillna(0).clip(0, 1)
    lifecycle_risk = {
        "declining": 1.0,
        "saturated": 0.6,
        "mature": 0.35,
        "growing": 0.1,
        "emerging": 0.0,
        "nascent": 0.15,
    }
    frame["dim_lifecycle_risk"] = (
        frame["lifecycle_stage"].map(lifecycle_risk).fillna(0.2)
    )
    frame["cascade_score"] = (
        10
        * frame["dim_safety"]
        * frame["dim_temporal_decay"]
        * frame["dim_lifecycle_risk"]
    )
    frame["risk_level"] = np.select(
        [frame["cascade_score"] >= 0.08, frame["cascade_score"] >= 0.02],
        ["HIGH", "MEDIUM"],
        default="LOW",
    )
    frame.loc[frame["safety_score"] < 2, "risk_level"] = "NON_SAFETY"
    return frame.sort_values("bertopic_id").reset_index(drop=True)


def prepare_family_stm_input(
    representatives: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    stm = pd.read_csv(STM_INPUT, encoding="utf-8-sig")
    if len(stm) != EXPECTED_FULL_N or not np.array_equal(
        stm["doc_id"].to_numpy(dtype=int), np.arange(EXPECTED_FULL_N)
    ):
        raise AssertionError("Frozen STM input is not aligned to source rows")
    rows = representatives["source_row"].to_numpy(dtype=int)
    family_stm = stm.iloc[rows].copy().reset_index(drop=True)
    family_stm.insert(1, "source_doc_id", family_stm["doc_id"].astype(int))
    family_stm["doc_id"] = np.arange(len(family_stm), dtype=int)
    family_stm["simple_family_id"] = representatives["简单同族ID"].astype(str).to_numpy()
    family_stm["bertopic_topic"] = representatives["topic"].astype(int).to_numpy()
    family_stm["publication_number"] = representatives["Publication No"].astype(str).to_numpy()
    document_map = pd.DataFrame(
        {
            "doc_id": family_stm["doc_id"],
            "source_doc_id": family_stm["source_doc_id"],
            "simple_family_id": family_stm["simple_family_id"],
            "publication_number": family_stm["publication_number"],
            "bertopic_topic": family_stm["bertopic_topic"],
            "year": family_stm["year"],
        }
    )
    return family_stm, document_map


def compare_outputs(
    full_scores: pd.DataFrame,
    family_scores: pd.DataFrame,
    full_hmm: pd.DataFrame,
    family_hmm: pd.DataFrame,
    full_lifecycle: pd.DataFrame,
    family_lifecycle: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    comparison = full_scores[
        ["bertopic_id", "safety_score", "cascade_score", "risk_level"]
    ].merge(
        family_scores[
            ["bertopic_id", "bertopic_count", "cascade_score", "risk_level"]
        ],
        on="bertopic_id",
        suffixes=("_full", "_family"),
        validate="1:1",
    )
    comparison = comparison.merge(
        full_hmm[["bertopic_id", "trend_direction", "decay_probability"]],
        on="bertopic_id",
        how="left",
    ).merge(
        family_hmm[["bertopic_id", "trend_direction", "decay_probability"]],
        on="bertopic_id",
        how="left",
        suffixes=("_full", "_family"),
    )
    comparison = comparison.merge(
        full_lifecycle[["bertopic_id", "lifecycle_stage"]],
        on="bertopic_id",
        how="left",
    ).merge(
        family_lifecycle[["bertopic_id", "lifecycle_stage"]],
        on="bertopic_id",
        how="left",
        suffixes=("_full", "_family"),
    )
    comparison["risk_changed"] = (
        comparison["risk_level_full"] != comparison["risk_level_family"]
    )
    comparison["trend_changed"] = (
        comparison["trend_direction_full"] != comparison["trend_direction_family"]
    )
    comparison["lifecycle_changed"] = (
        comparison["lifecycle_stage_full"] != comparison["lifecycle_stage_family"]
    )
    safety = comparison[comparison["safety_score"] >= 2]
    full_high = sorted(
        comparison.loc[comparison["risk_level_full"] == "HIGH", "bertopic_id"].astype(int)
    )
    family_high = sorted(
        comparison.loc[comparison["risk_level_family"] == "HIGH", "bertopic_id"].astype(int)
    )
    rank_rho, rank_p = stats.spearmanr(
        safety["cascade_score_full"], safety["cascade_score_family"]
    )
    summary = {
        "full_high_topics": full_high,
        "family_high_topics": family_high,
        "high_retained": sorted(set(full_high) & set(family_high)),
        "high_lost": sorted(set(full_high) - set(family_high)),
        "high_gained": sorted(set(family_high) - set(full_high)),
        "safety_score_rank_spearman_rho": float(rank_rho),
        "safety_score_rank_spearman_p": float(rank_p),
        "risk_level_changes_all_topics": int(comparison["risk_changed"].sum()),
        "risk_level_changes_safety_topics": int(safety["risk_changed"].sum()),
        "trend_direction_changes_all_topics": int(comparison["trend_changed"].sum()),
        "lifecycle_changes_all_topics": int(comparison["lifecycle_changed"].sum()),
    }
    return comparison, summary


def validate_full_reproduction(
    full_hmm: pd.DataFrame,
    full_lifecycle: pd.DataFrame,
    full_scores: pd.DataFrame,
) -> dict:
    frozen_hmm = pd.read_csv(FULL_HMM, encoding="utf-8-sig")
    frozen_lifecycle = pd.read_csv(FULL_LIFECYCLE, encoding="utf-8-sig")
    frozen_scores = pd.read_csv(FULL_SCORES, encoding="utf-8-sig")
    hmm_check = full_hmm.merge(
        frozen_hmm[
            ["bertopic_id", "decay_probability", "trend_direction"]
        ],
        on="bertopic_id",
        suffixes=("_new", "_frozen"),
        validate="1:1",
    )
    lifecycle_check = full_lifecycle.merge(
        frozen_lifecycle[["bertopic_id", "lifecycle_stage"]],
        on="bertopic_id",
        suffixes=("_new", "_frozen"),
        validate="1:1",
    )
    score_check = full_scores.merge(
        frozen_scores[["bertopic_id", "cascade_score", "risk_level"]],
        on="bertopic_id",
        suffixes=("_new", "_frozen"),
        validate="1:1",
    )
    result = {
        "hmm_direction_mismatches": int(
            (hmm_check["trend_direction_new"] != hmm_check["trend_direction_frozen"]).sum()
        ),
        "hmm_decay_max_abs_diff": float(
            np.max(
                np.abs(
                    hmm_check["decay_probability_new"]
                    - hmm_check["decay_probability_frozen"]
                )
            )
        ),
        "lifecycle_stage_mismatches": int(
            (
                lifecycle_check["lifecycle_stage_new"]
                != lifecycle_check["lifecycle_stage_frozen"]
            ).sum()
        ),
        "score_max_abs_diff": float(
            np.max(
                np.abs(
                    score_check["cascade_score_new"]
                    - score_check["cascade_score_frozen"]
                )
            )
        ),
        "risk_level_mismatches": int(
            (score_check["risk_level_new"] != score_check["risk_level_frozen"]).sum()
        ),
    }
    if any(
        [
            result["hmm_direction_mismatches"],
            result["lifecycle_stage_mismatches"],
            result["risk_level_mismatches"],
        ]
    ) or result["hmm_decay_max_abs_diff"] > 1e-10 or result["score_max_abs_diff"] > 1e-10:
        raise AssertionError(f"Full-corpus reproduction failed: {result}")
    return result


def write_primary_report(
    representative_stats: dict,
    reproduction: dict,
    comparison_summary: dict,
    comparison: pd.DataFrame,
) -> None:
    changed = comparison[comparison["risk_changed"]].copy()
    changed_rows = "\n".join(
        f"| T{int(row.bertopic_id)} | {row.risk_level_full} | {row.risk_level_family} | "
        f"{row.cascade_score_full:.4f} | {row.cascade_score_family:.4f} |"
        for row in changed.itertuples()
    ) or "| none | — | — | — | — |"
    text = f"""# Family-normalized primary re-estimation

## Corpus and reproducibility

- Publication corpus: {representative_stats['n_publications']:,} records.
- Simple-family primary corpus: {representative_stats['n_simple_families']:,} unique families ({representative_stats['rows_removed']:,} publication rows removed).
- Earliest-application selection differs from the earlier first-returned-record rule for {representative_stats['representative_row_changed']} families, changes the representative BERTopic label for {representative_stats['representative_topic_changed']}, and changes application year for {representative_stats['representative_year_changed']}.
- The independent reimplementation reproduces the frozen publication-level HMM, lifecycle, score, and risk labels exactly: {json.dumps(reproduction, ensure_ascii=False)}.

## Main score result

- Publication-level HIGH topics: {comparison_summary['full_high_topics']}.
- Family-normalized HIGH topics: {comparison_summary['family_high_topics']}.
- Retained: {comparison_summary['high_retained']}; lost: {comparison_summary['high_lost']}; gained: {comparison_summary['high_gained']}.
- Rank correlation across the 20 safety candidates: Spearman rho = {comparison_summary['safety_score_rank_spearman_rho']:.4f}, p = {comparison_summary['safety_score_rank_spearman_p']:.4g}.
- Risk-level changes among safety candidates: {comparison_summary['risk_level_changes_safety_topics']}.

| Topic | Full label | Family label | Full score | Family score |
|---|---:|---:|---:|---:|
{changed_rows}

## Interpretation boundary

This is a primary re-estimation of temporal counts, five-state HMM decay, logistic S-curve lifecycle, and the published review-priority score in the frozen BERTopic topic space. It does not retrain BERTopic and does not convert patent-family trends into accident probabilities. The held-out family-normalized STM result is reported separately after the R fit completes.
"""
    (OUT / "family_primary_report.md").write_text(text, encoding="utf-8")


def run_primary() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    STM_OUT.mkdir(parents=True, exist_ok=True)
    joined, _ = load_joined_data()
    family, selection_audit, representative_stats = select_representatives(joined)

    topics = pd.read_csv(TOPIC_SUMMARY, encoding="utf-8-sig")
    labels = pd.read_csv(LLM_LABELS, encoding="utf-8-sig")
    name_map = {
        int(row.Topic): str(row.Name)
        for row in topics.itertuples()
        if int(row.Topic) >= 0
    }
    safety_map = {
        int(row.bertopic_id): int(row.safety_score) for row in labels.itertuples()
    }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        full_pivot = build_pivot(joined)
        family_pivot = build_pivot(family)
        full_hmm = estimate_hmm(full_pivot, name_map)
        family_hmm = estimate_hmm(family_pivot, name_map)
        full_lifecycle = estimate_lifecycle(full_pivot, name_map, safety_map)
        family_lifecycle = estimate_lifecycle(family_pivot, name_map, safety_map)
        full_scores = compute_scores(full_hmm, full_lifecycle, labels)
        family_scores = compute_scores(family_hmm, family_lifecycle, labels)

    reproduction = validate_full_reproduction(full_hmm, full_lifecycle, full_scores)
    comparison, comparison_summary = compare_outputs(
        full_scores,
        family_scores,
        full_hmm,
        family_hmm,
        full_lifecycle,
        family_lifecycle,
    )
    family_stm, family_map = prepare_family_stm_input(family)

    representatives_out = family[
        [
            "简单同族ID",
            "Publication No",
            "Application Date",
            "application_date",
            "source_row",
            "topic",
            "app_year",
        ]
    ].copy()
    representatives_out.insert(0, "family_doc_id", np.arange(len(family), dtype=int))
    representatives_out.to_csv(
        OUT / "family_representatives.csv", index=False, encoding="utf-8-sig"
    )
    selection_audit.to_csv(
        OUT / "representative_selection_audit.csv", index=False, encoding="utf-8-sig"
    )
    family_hmm.to_csv(OUT / "family_hmm_trends.csv", index=False, encoding="utf-8-sig")
    family_lifecycle.to_csv(
        OUT / "family_topic_lifecycle.csv", index=False, encoding="utf-8-sig"
    )
    family_scores.to_csv(
        OUT / "family_cascade_signals.csv", index=False, encoding="utf-8-sig"
    )
    comparison.to_csv(
        OUT / "full_vs_family_comparison.csv", index=False, encoding="utf-8-sig"
    )
    family_stm.to_csv(
        STM_OUT / "stm_input_family.csv", index=False, encoding="utf-8-sig"
    )
    family_map.to_csv(
        OUT / "family_document_map.csv", index=False, encoding="utf-8-sig"
    )
    family_pivot.to_csv(OUT / "family_topic_year_counts.csv", encoding="utf-8-sig")

    manifest = {
        "source_hashes": {
            str(DATA_XLSX): sha256(DATA_XLSX),
            str(DOC_TOPIC): sha256(DOC_TOPIC),
            str(STM_INPUT): sha256(STM_INPUT),
            str(LLM_LABELS): sha256(LLM_LABELS),
        },
        "representative_stats": representative_stats,
        "full_reproduction": reproduction,
        "comparison": comparison_summary,
        "hmm_seed": 42,
        "stm_seed": 12345,
        "stm_k": 12,
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_primary_report(
        representative_stats, reproduction, comparison_summary, comparison
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Family STM input: {STM_OUT / 'stm_input_family.csv'}")


def postprocess_stm() -> None:
    effects_path = STM_OUT / "stm_egami_effects.csv"
    train_path = STM_OUT / "stm_theta_train.csv"
    test_path = STM_OUT / "stm_theta_test.csv"
    if not all(path.exists() for path in (effects_path, train_path, test_path)):
        raise FileNotFoundError("Family STM outputs are incomplete; run the R script first")

    effects = pd.read_csv(effects_path)
    effects["q_value"] = multipletests(
        effects["p_value"].to_numpy(), method="fdr_bh"
    )[1]
    effects["nominal"] = effects["p_value"] < 0.05
    effects["bh_retained"] = effects["q_value"] <= 0.05
    effects.to_csv(
        STM_OUT / "stm_egami_effects_with_bh.csv", index=False, encoding="utf-8-sig"
    )

    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    theta = pd.concat([train, test], ignore_index=True)
    if theta["doc_id"].duplicated().any():
        raise AssertionError("Duplicate family doc IDs in STM theta")
    theta = theta.sort_values("doc_id").reset_index(drop=True)
    family_map = pd.read_csv(OUT / "family_document_map.csv")
    merged = family_map.merge(theta, on="doc_id", how="inner", validate="1:1")
    if len(merged) != EXPECTED_FAMILY_N:
        raise AssertionError(
            f"STM theta covers {len(merged)} of {EXPECTED_FAMILY_N} families"
        )
    topic_cols = [column for column in theta.columns if column.startswith("topic_")]
    lookup = {
        (int(row.topic), str(row.covariate)): row
        for row in effects.itertuples()
    }
    scores = pd.read_csv(OUT / "family_cascade_signals.csv", encoding="utf-8-sig")
    human = pd.read_csv(HUMAN_REVIEW, encoding="utf-8-sig") if HUMAN_REVIEW.exists() else pd.DataFrame()

    rows = []
    for bertopic_id, group in merged[merged["bertopic_topic"] >= 0].groupby(
        "bertopic_topic"
    ):
        mean_theta = group[topic_cols].mean().to_numpy(dtype=float)
        dominant = int(np.argmax(mean_theta)) + 1
        c2 = lookup[(dominant, "C2_std")]
        c10 = lookup[(dominant, "C10_std")]
        nominal_decay = bool(
            (c2.coefficient < 0 and c2.p_value < 0.05)
            or (c10.coefficient < 0 and c10.p_value < 0.05)
        )
        bh_decay = bool(
            (c2.coefficient < 0 and c2.q_value <= 0.05)
            or (c10.coefficient < 0 and c10.q_value <= 0.05)
        )
        rows.append(
            {
                "bertopic_id": int(bertopic_id),
                "n_families": int(len(group)),
                "dominant_stm_topic": dominant,
                "stm_theta_mean": float(mean_theta[dominant - 1]),
                "c2_effect": float(c2.coefficient),
                "c2_pvalue": float(c2.p_value),
                "c2_qvalue": float(c2.q_value),
                "c10_effect": float(c10.coefficient),
                "c10_pvalue": float(c10.p_value),
                "c10_qvalue": float(c10.q_value),
                "stm_nominal_decay": nominal_decay,
                "stm_bh_decay": bh_decay,
            }
        )
    cross = pd.DataFrame(rows).merge(
        scores[
            ["bertopic_id", "bertopic_name", "safety_score", "cascade_score", "risk_level"]
        ],
        on="bertopic_id",
        how="left",
        validate="1:1",
    )
    if not human.empty:
        cross = cross.merge(
            human[
                ["bertopic_id", "human_safety_judgment", "cascade_role", "scope_limitation"]
            ],
            on="bertopic_id",
            how="left",
        )
        cross["reviewed_humanoid_scope"] = (
            cross["human_safety_judgment"].isin(["DIRECT", "PARTIAL"])
            & (cross["cascade_role"] != "OUT_OF_SCOPE")
        )
    else:
        cross["reviewed_humanoid_scope"] = False
    cross["nominal_cross_model_candidate"] = (
        (cross["risk_level"] == "HIGH") & cross["stm_nominal_decay"]
    )
    cross["strict_scope_multiplicity_confirmation"] = (
        (cross["risk_level"] == "HIGH")
        & cross["stm_bh_decay"]
        & cross["reviewed_humanoid_scope"]
    )
    cross.to_csv(
        OUT / "family_cross_model_validation.csv", index=False, encoding="utf-8-sig"
    )

    nominal = int(effects["nominal"].sum())
    bh = int(effects["bh_retained"].sum())
    nominal_candidates = cross.loc[
        cross["nominal_cross_model_candidate"], "bertopic_id"
    ].astype(int).tolist()
    strict = cross.loc[
        cross["strict_scope_multiplicity_confirmation"], "bertopic_id"
    ].astype(int).tolist()
    summary = {
        "n_family_documents": int(len(theta)),
        "n_effect_tests": int(len(effects)),
        "nominal_effects": nominal,
        "bh_retained_effects": bh,
        "nominal_cross_model_candidates": nominal_candidates,
        "strict_scope_multiplicity_confirmations": strict,
    }
    (STM_OUT / "family_stm_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    report = f"""# Family-normalized held-out STM

- Input: {summary['n_family_documents']:,} unique simple-family representatives.
- Design: K=12, 70/30 split, seed 12345, same prevalence/content formulas as the publication-level model.
- Held-out covariate tests: {summary['n_effect_tests']}.
- Nominal p<0.05: {summary['nominal_effects']}.
- Benjamini-Hochberg q<=0.05: {summary['bh_retained_effects']}.
- Family HIGH topics with a nominal negative C2/C10 mirror: {summary['nominal_cross_model_candidates']}.
- Reviewed humanoid HIGH topics passing both scope and BH multiplicity gates: {summary['strict_scope_multiplicity_confirmations']}.

STM topic numbers are not compared one-to-one with the publication-level fit because independently fitted topic labels are permutation-invariant. The valid comparison is the number of held-out effects and the downstream BERTopic-to-STM document projection gate.
"""
    (STM_OUT / "family_stm_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-stm-only", action="store_true")
    args = parser.parse_args()
    if args.post_stm_only:
        postprocess_stm()
    else:
        run_primary()
        if (STM_OUT / "stm_egami_effects.csv").exists():
            postprocess_stm()


if __name__ == "__main__":
    main()

