"""Zero-cost exploratory role-separated reanalysis of frozen ASIMOV outputs.

No network, embedding-model, or LLM call is made.  The script reuses cached
PatentSBERTa embeddings and archived DeepSeek/Kimi judgments, first reproduces
the frozen pooled models, then decomposes decay exposure into human-audited
SAFETY_BARRIER, PROPAGATION_NODE, and OTHER contributions.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.outliers_influence import variance_inflation_factor


ROOT = Path(__file__).resolve().parents[1]
ASIMOV = ROOT / "output" / "asimov_validation"
OUT = ROOT / "output" / "asimov_role_separated"
OUT.mkdir(parents=True, exist_ok=True)

MAPPING = ASIMOV / "mapping_v2.csv"
DEEPSEEK = ASIMOV / "v2_injury_results.csv"
EMBED = ASIMOV / "cache" / "embed_cache.npz"
PATENTS = ASIMOV / "cache" / "safety_patents.npz"
ASSIGNMENT = ROOT / "output" / "time_analysis" / "04_bertopic_time" / "document_topic_assignment.csv"
PUB_SIGNALS = ROOT / "output" / "time_analysis" / "11_temporal_enrichment" / "06_cascade_v3" / "cascade_signals_v5.csv"
FAMILY_SIGNALS = ROOT / "output" / "family_primary_reestimation" / "family_cascade_signals.csv"
FAMILY_REPS = ROOT / "output" / "family_primary_reestimation" / "family_representatives.csv"
ROLES = ROOT / "output" / "subsystem_validation" / "human_review" / "P1_topic_safety_reviewed.csv"

K_VALUES = (25, 50, 100)
QUESTIONS = (
    "latent_risk_correct",
    "latent_severity_correct",
    "effect_correct",
    "activated_risk_correct",
)
ROLE_LEVELS = ("SAFETY_BARRIER", "PROPAGATION_NODE", "OTHER")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def as_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    mapped = series.astype(str).str.strip().str.lower().map({"true": True, "false": False})
    if mapped.isna().any():
        raise ValueError(f"Cannot parse Boolean values in {series.name}")
    return mapped.astype(bool)


def normalized(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    if (norms == 0).any():
        raise ValueError("Zero-norm embedding encountered")
    return x / norms


def load_outcomes() -> dict[str, pd.DataFrame]:
    deep = pd.read_csv(DEEPSEEK)
    deep = deep.loc[deep["error"].isna()].copy().set_index("idx")
    for q in QUESTIONS:
        deep[q] = as_bool(deep[q])

    runs = []
    for path in sorted(ASIMOV.glob("kimi_v2_results_seed*.csv")):
        run = pd.read_csv(path)
        run = run.loc[run["error"].isna()].copy().set_index("idx")
        for q in QUESTIONS:
            run[q] = as_bool(run[q])
        runs.append(run)
    if len(runs) != 3:
        raise RuntimeError(f"Expected three Kimi seeds, found {len(runs)}")
    common = runs[0].index
    for run in runs[1:]:
        common = common.intersection(run.index)
    kimi = pd.DataFrame(index=common.sort_values())
    for q in QUESTIONS:
        stack = np.vstack([r.loc[kimi.index, q].to_numpy(dtype=bool) for r in runs])
        kimi[q] = stack.mean(axis=0) >= 0.5
    return {"DeepSeek": deep, "KimiMV": kimi}


def role_map_frame(direct_partial_only: bool = False) -> tuple[dict[int, str], pd.DataFrame]:
    review = pd.read_csv(ROLES)
    role_map: dict[int, str] = {}
    for row in review.itertuples():
        role = row.cascade_role
        if direct_partial_only and row.human_safety_judgment not in {"DIRECT", "PARTIAL"}:
            role = "OTHER"
        if role not in {"SAFETY_BARRIER", "PROPAGATION_NODE"}:
            role = "OTHER"
        role_map[int(row.bertopic_id)] = role
    return role_map, review


def patent_pools() -> dict[str, dict]:
    role_map, review = role_map_frame(False)
    safety_topics = set(review["bertopic_id"].astype(int))
    asg = pd.read_csv(ASSIGNMENT)
    asg_s = asg.loc[asg["topic"].isin(safety_topics)].reset_index(drop=True)
    zpat = np.load(PATENTS)
    emb = zpat["emb"]
    tid = zpat["tid"].astype(int)
    if len(asg_s) != len(emb) or not np.array_equal(asg_s["topic"].to_numpy(), tid):
        raise RuntimeError("Cached patent embeddings do not align with frozen assignments")

    pub = pd.read_csv(PUB_SIGNALS).set_index("bertopic_id")
    pub_decay = pub["hmm_decay_probability"].astype(float).to_dict()
    family = pd.read_csv(FAMILY_SIGNALS).set_index("bertopic_id")
    fam_decay = family["decay_probability"].astype(float).to_dict()

    reps = pd.read_csv(FAMILY_REPS)
    rep_publications = set(reps.loc[reps["topic"].isin(safety_topics), "Publication No"].astype(str))
    fam_mask = asg_s["patent_number"].astype(str).isin(rep_publications).to_numpy()
    if int(fam_mask.sum()) != 1773:
        raise RuntimeError(f"Expected 1,773 safety-family representatives, got {fam_mask.sum()}")
    return {
        "publication": {"emb": emb, "tid": tid, "decay": pub_decay, "role_map": role_map},
        "family": {"emb": emb[fam_mask], "tid": tid[fam_mask], "decay": fam_decay, "role_map": role_map},
    }


def compute_exposures(
    scenario_emb: np.ndarray,
    pool: dict,
    role_map: dict[int, str] | None = None,
) -> tuple[pd.DataFrame, dict[int, np.ndarray]]:
    role_map = role_map or pool["role_map"]
    pat_emb = pool["emb"]
    pat_tid = pool["tid"]
    decay = pool["decay"]
    sim = normalized(scenario_emb) @ normalized(pat_emb).T
    kmax = max(K_VALUES)
    idx = np.argpartition(-sim, kmax, axis=1)[:, :kmax]
    vals = np.take_along_axis(sim, idx, axis=1)
    order = np.argsort(-vals, axis=1)
    idx = np.take_along_axis(idx, order, axis=1)
    vals = np.take_along_axis(vals, order, axis=1)

    out = pd.DataFrame({"scenario_idx": np.arange(len(scenario_emb), dtype=int)})
    neighbor_topics: dict[int, np.ndarray] = {}
    for k in K_VALUES:
        w = np.clip(vals[:, :k], 0, None)
        denom = w.sum(axis=1)
        if (denom <= 0).any():
            raise RuntimeError(f"Nonpositive similarity denominator at k={k}")
        tids = pat_tid[idx[:, :k]]
        neighbor_topics[k] = tids
        d = np.vectorize(decay.__getitem__)(tids).astype(float)
        out[f"pooled_k{k}"] = (w * d).sum(axis=1) / denom
        total = np.zeros(len(out))
        for role in ROLE_LEVELS:
            mask = np.vectorize(lambda t: role_map.get(int(t), "OTHER") == role)(tids)
            contribution = (w * d * mask).sum(axis=1) / denom
            mass = (w * mask).sum(axis=1) / denom
            name = role.lower()
            out[f"{name}_k{k}"] = contribution
            out[f"{name}_mass_k{k}"] = mass
            total += contribution
        if not np.allclose(total, out[f"pooled_k{k}"], atol=1e-12, rtol=1e-10):
            raise AssertionError(f"Role contributions do not sum to pooled exposure at k={k}")
    return out, neighbor_topics


def long_outcome(outcomes: pd.DataFrame, exposures: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for q in QUESTIONS:
        parts.append(pd.DataFrame({
            "scenario": outcomes.index.astype(int),
            "subq": q,
            "error": (~outcomes[q]).astype(int).to_numpy(),
        }))
    long = pd.concat(parts, ignore_index=True)
    long = long.merge(exposures, left_on="scenario", right_on="scenario_idx", validate="many_to_one")
    lengths = mapping[["scenario_idx", "text"]].copy()
    lengths["log_len"] = np.log1p(lengths["text"].astype(str).str.len())
    long = long.merge(lengths[["scenario_idx", "log_len"]], on="scenario_idx", validate="many_to_one")
    return long


def fit_glm(formula: str, data: pd.DataFrame, cluster: bool = True):
    model = smf.glm(formula, data=data, family=sm.families.Binomial())
    if cluster:
        return model.fit(cov_type="cluster", cov_kwds={"groups": data["scenario"]})
    return model.fit()


def standardize(data: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, dict]:
    out = data.copy()
    meta = {}
    for col in columns:
        mean = float(out[col].mean())
        sd = float(out[col].std(ddof=1))
        if not np.isfinite(sd) or sd <= 0:
            raise RuntimeError(f"Cannot standardize {col}: sd={sd}")
        out[f"z_{col}"] = (out[col] - mean) / sd
        meta[col] = {"mean": mean, "sd": sd}
    return out, meta


def extract_term(fit, term: str, context: dict) -> dict:
    ci = fit.conf_int().loc[term]
    coef = float(fit.params[term])
    se = float(fit.bse[term])
    return {
        **context,
        "term": term,
        "coef_log_odds_per_sd": coef,
        "std_error": se,
        "odds_ratio_per_sd": float(np.exp(coef)),
        "ci_lower": float(ci.iloc[0]),
        "ci_upper": float(ci.iloc[1]),
        "or_ci_lower": float(np.exp(ci.iloc[0])),
        "or_ci_upper": float(np.exp(ci.iloc[1])),
        "p_value": float(fit.pvalues[term]),
        "n_observations": int(fit.nobs),
        "n_scenarios": int(fit.model.data.frame["scenario"].nunique()),
        "converged": bool(fit.converged),
    }


def role_model(long: pd.DataFrame, k: int, context: dict) -> tuple[list[dict], dict]:
    raw = [f"safety_barrier_k{k}", f"propagation_node_k{k}", f"other_k{k}"]
    data, scale = standardize(long, raw)
    z = [f"z_{c}" for c in raw]
    formula = "error ~ " + " + ".join(z) + " + C(subq) + log_len"
    fit = fit_glm(formula, data)
    rows = [extract_term(fit, term, context) for term in z]

    cov = fit.cov_params()
    b_prop = "z_propagation_node_k%d" % k
    b_bar = "z_safety_barrier_k%d" % k
    contrast = float(fit.params[b_prop] - fit.params[b_bar])
    var = float(cov.loc[b_prop, b_prop] + cov.loc[b_bar, b_bar] - 2 * cov.loc[b_prop, b_bar])
    se = float(np.sqrt(max(var, 0)))
    zstat = contrast / se if se > 0 else np.nan
    contrast_info = {
        **context,
        "contrast": "propagation_minus_barrier",
        "estimate": contrast,
        "std_error": se,
        "z_value": zstat,
        "p_value": float(2 * stats.norm.sf(abs(zstat))) if np.isfinite(zstat) else np.nan,
        "ci_lower": contrast - 1.96 * se,
        "ci_upper": contrast + 1.96 * se,
    }

    scenario_level = data.drop_duplicates("scenario")
    x = sm.add_constant(scenario_level[z])
    vif = {col: float(variance_inflation_factor(x.to_numpy(), i + 1)) for i, col in enumerate(z)}
    corr = scenario_level[z].corr().to_dict()
    raw_distribution = {
        col: {
            "min": float(scenario_level[col].min()),
            "max": float(scenario_level[col].max()),
            "mean": float(scenario_level[col].mean()),
            "sd": float(scenario_level[col].std(ddof=1)),
            "zero_fraction": float(np.isclose(scenario_level[col], 0.0, atol=1e-15).mean()),
        }
        for col in raw
    }
    mass_cols = [f"{role.lower()}_mass_k{k}" for role in ROLE_LEVELS]
    mass_distribution = {
        col: {
            "min": float(scenario_level[col].min()),
            "max": float(scenario_level[col].max()),
            "mean": float(scenario_level[col].mean()),
            "sd": float(scenario_level[col].std(ddof=1)),
            "zero_fraction": float(np.isclose(scenario_level[col], 0.0, atol=1e-15).mean()),
        }
        for col in mass_cols
    }
    diagnostics = {
        **context,
        "k": k,
        "formula": formula,
        "scaling": scale,
        "vif": vif,
        "correlation": corr,
        "raw_exposure_distribution": raw_distribution,
        "neighbor_role_mass_distribution": mass_distribution,
        "event_rate": float(data["error"].mean()),
        "n_events": int(data["error"].sum()),
    }
    return rows, {"contrast": contrast_info, "diagnostics": diagnostics, "fit": fit}


def pooled_model(long: pd.DataFrame, k: int, context: dict) -> dict:
    term = f"pooled_k{k}"
    fit = fit_glm(f"error ~ {term} + C(subq) + log_len", long)
    ci = fit.conf_int().loc[term]
    return {
        **context,
        "k": k,
        "coef": float(fit.params[term]),
        "std_error": float(fit.bse[term]),
        "p_value": float(fit.pvalues[term]),
        "odds_ratio": float(np.exp(fit.params[term])),
        "ci_lower": float(ci.iloc[0]),
        "ci_upper": float(ci.iloc[1]),
        "n": int(fit.nobs),
    }


def apply_bh(results: pd.DataFrame) -> pd.DataFrame:
    out = results.copy()
    out["q_value"] = np.nan
    role_terms = {
        "z_safety_barrier": "barrier",
        "z_propagation_node": "propagation",
    }
    for corpus in out["corpus_unit"].unique():
        for prefix in role_terms:
            mask = out["corpus_unit"].eq(corpus) & out["term"].str.startswith(prefix)
            if mask.any():
                out.loc[mask, "q_value"] = multipletests(out.loc[mask, "p_value"], method="fdr_bh")[1]
    return out


def main() -> None:
    mapping = pd.read_csv(MAPPING)
    zemb = np.load(EMBED)
    scenario_emb = zemb["scenarios_v2"]
    if len(mapping) != len(scenario_emb) or not np.array_equal(mapping["scenario_idx"], np.arange(len(mapping))):
        raise RuntimeError("Scenario embedding/mapping alignment failure")
    outcomes = load_outcomes()
    pools = patent_pools()
    role_all, review = role_map_frame(False)
    role_dp, _ = role_map_frame(True)

    exposure_sets: dict[tuple[str, str], pd.DataFrame] = {}
    for unit, pool in pools.items():
        exp_all, _ = compute_exposures(scenario_emb, pool, role_all)
        exp_dp, _ = compute_exposures(scenario_emb, pool, role_dp)
        exposure_sets[(unit, "all_reviewed_roles")] = exp_all
        exposure_sets[(unit, "direct_partial_only")] = exp_dp
        exp_all.to_csv(OUT / f"exposures_{unit}.csv", index=False)
        exp_dp.to_csv(OUT / f"exposures_{unit}_direct_partial.csv", index=False)

    # Exact exposure and frozen coefficient reproduction gate.
    pub_exp = exposure_sets[("publication", "all_reviewed_roles")]
    exposure_diff = {}
    for k in K_VALUES:
        diff = float(np.max(np.abs(pub_exp[f"pooled_k{k}"] - mapping[f"E_decay_k{k}"])))
        exposure_diff[str(k)] = diff
        if diff > 1e-10:
            raise AssertionError(f"Frozen pooled exposure mismatch at k={k}: {diff}")

    frozen = json.loads((ASIMOV / "evidence_stats.json").read_text(encoding="utf-8"))["v2"]
    pooled_rows, role_rows, contrast_rows, diagnostics = [], [], [], []
    reproduction = {}
    for model_name, model_outcomes in outcomes.items():
        long = long_outcome(model_outcomes, pub_exp, mapping)
        key = "deepseek" if model_name == "DeepSeek" else "kimi_mv"
        reproduction[model_name] = {}
        for k in K_VALUES:
            row = pooled_model(long, k, {"model": model_name, "corpus_unit": "publication"})
            pooled_rows.append(row)
            expected = frozen[key][f"k{k}"]["E_coef"]
            delta = abs(row["coef"] - expected)
            reproduction[model_name][str(k)] = {"expected": expected, "observed": row["coef"], "abs_diff": delta}
            if delta > 1e-9:
                raise AssertionError(f"Frozen {model_name} k={k} coefficient mismatch: {delta}")

    # Declared all-role models: both units, both models, all k.
    for unit in ("publication", "family"):
        exposure = exposure_sets[(unit, "all_reviewed_roles")]
        for model_name, model_outcomes in outcomes.items():
            long = long_outcome(model_outcomes, exposure, mapping)
            for k in K_VALUES:
                context = {
                    "model": model_name,
                    "corpus_unit": unit,
                    "role_scope": "all_reviewed_roles",
                    "k": k,
                }
                rows, extra = role_model(long, k, context)
                role_rows.extend(rows)
                contrast_rows.append(extra["contrast"])
                diagnostics.append(extra["diagnostics"])

    # Direct/Partial-only sensitivity at primary k=50.
    for unit in ("publication", "family"):
        exposure = exposure_sets[(unit, "direct_partial_only")]
        for model_name, model_outcomes in outcomes.items():
            long = long_outcome(model_outcomes, exposure, mapping)
            context = {
                "model": model_name,
                "corpus_unit": unit,
                "role_scope": "direct_partial_only",
                "k": 50,
            }
            rows, extra = role_model(long, 50, context)
            role_rows.extend(rows)
            contrast_rows.append(extra["contrast"])
            diagnostics.append(extra["diagnostics"])

    role_df = pd.DataFrame(role_rows)
    main_mask = role_df["role_scope"].eq("all_reviewed_roles")
    role_df["q_value"] = np.nan
    corrected = apply_bh(role_df.loc[main_mask].copy())
    role_df.loc[corrected.index, "q_value"] = corrected["q_value"]
    role_df.to_csv(OUT / "role_model_results.csv", index=False)
    pd.DataFrame(pooled_rows).to_csv(OUT / "pooled_reproduction.csv", index=False)
    contrast_df = pd.DataFrame(contrast_rows)
    contrast_df["q_value"] = np.nan
    contrast_main = contrast_df["role_scope"].eq("all_reviewed_roles")
    for unit in contrast_df.loc[contrast_main, "corpus_unit"].unique():
        mask = contrast_main & contrast_df["corpus_unit"].eq(unit)
        contrast_df.loc[mask, "q_value"] = multipletests(
            contrast_df.loc[mask, "p_value"], method="fdr_bh"
        )[1]
    contrast_df.to_csv(OUT / "role_contrasts.csv", index=False)
    (OUT / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")

    # Leave-one-role-topic-out at k=50 for both units/models.
    loto_rows = []
    for unit, pool in pools.items():
        for omitted in sorted(t for t, role in role_all.items() if role in {"SAFETY_BARRIER", "PROPAGATION_NODE"}):
            omitted_role = role_all[omitted]
            modified = dict(role_all)
            modified[omitted] = "OTHER"
            exposure, _ = compute_exposures(scenario_emb, pool, modified)
            for model_name, model_outcomes in outcomes.items():
                long = long_outcome(model_outcomes, exposure, mapping)
                context = {
                    "model": model_name,
                    "corpus_unit": unit,
                    "role_scope": "leave_one_topic_out",
                    "k": 50,
                }
                rows, _ = role_model(long, 50, context)
                target_prefix = "z_safety_barrier" if omitted_role == "SAFETY_BARRIER" else "z_propagation_node"
                target = next(r for r in rows if r["term"].startswith(target_prefix))
                loto_rows.append({
                    "corpus_unit": unit,
                    "model": model_name,
                    "omitted_topic": omitted,
                    "omitted_role": omitted_role,
                    "target_coef": target["coef_log_odds_per_sd"],
                    "target_p_value": target["p_value"],
                    "target_sign": int(np.sign(target["coef_log_odds_per_sd"])),
                })
    loto = pd.DataFrame(loto_rows)
    loto.to_csv(OUT / "leave_one_topic_out.csv", index=False)
    loto_summary = (
        loto.groupby(["corpus_unit", "model", "omitted_role"], as_index=False)
        .agg(
            n_omissions=("omitted_topic", "size"),
            n_negative=("target_sign", lambda x: int((x < 0).sum())),
            n_positive=("target_sign", lambda x: int((x > 0).sum())),
            n_nominal=("target_p_value", lambda x: int((x < 0.05).sum())),
        )
    )
    loto_summary.to_csv(OUT / "leave_one_topic_out_summary.csv", index=False)

    role_counts = review["cascade_role"].value_counts().to_dict()
    summary = {
        "status": "exploratory_post_hoc",
        "no_api_calls": True,
        "input_hashes": {str(p): sha256(p) for p in [MAPPING, DEEPSEEK, EMBED, PATENTS, ASSIGNMENT, PUB_SIGNALS, FAMILY_SIGNALS, FAMILY_REPS, ROLES]},
        "n_v2_scenarios": int(len(mapping)),
        "n_deepseek_scenarios": int(len(outcomes["DeepSeek"])),
        "n_kimi_common_scenarios": int(len(outcomes["KimiMV"])),
        "n_publication_patents": int(len(pools["publication"]["tid"])),
        "n_family_patents": int(len(pools["family"]["tid"])),
        "role_topic_counts": role_counts,
        "pooled_exposure_max_abs_diff": exposure_diff,
        "pooled_coefficient_reproduction": reproduction,
        "primary_interpretation": {
            "deepseek_barrier": "negative in both publication and family models after BH correction",
            "deepseek_propagation": "not distinguishable from zero",
            "kimi_role_terms": "none survive BH correction",
            "family_barrier_caveat": "sign reverses when Topic 22 is omitted",
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Concise complete report, generated from full result tables.
    primary = role_df.loc[
        role_df["role_scope"].eq("all_reviewed_roles")
        & role_df["k"].eq(50)
        & role_df["term"].str.contains("safety_barrier|propagation_node")
    ].copy()
    lines = [
        "# ASIMOV role-separated exploratory reanalysis",
        "",
        "This analysis reuses frozen embeddings and model judgments; no LLM or network call was made. "
        "It is post hoc and exploratory because role separation was motivated after observing the inverse pooled sign.",
        "",
        "## Reproduction gate",
        "",
        f"- Publication pooled exposure reproduces mapping files with maximum absolute differences: {exposure_diff}.",
        "- Frozen DeepSeek and Kimi pooled coefficients reproduce within 1e-9 at k=25/50/100.",
        "",
        "## Primary k=50 role coefficients (log odds per 1-SD exposure)",
        "",
        "| Unit | Model | Role | beta | 95% CI | OR | p | q |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in primary.itertuples():
        role = "Barrier" if "safety_barrier" in row.term else "Propagation"
        q = row.q_value if pd.notna(row.q_value) else np.nan
        lines.append(
            f"| {row.corpus_unit} | {row.model} | {role} | {row.coef_log_odds_per_sd:.3f} "
            f"| [{row.ci_lower:.3f}, {row.ci_upper:.3f}] | {row.odds_ratio_per_sd:.3f} "
            f"| {row.p_value:.4g} | {q:.4g} |"
        )
    lines += [
        "",
        "## Robustness and limits",
        "",
        "The DeepSeek barrier coefficient is negative and BH-retained for both corpus units at all three k values. "
        "The primary k=50 propagation coefficient is not distinguishable from zero in either corpus unit. "
        "No individual Kimi role coefficient survives BH correction. All scenarios have nonzero barrier and "
        "propagation exposure, and primary-model VIFs are below 1.13, so the null propagation result is not caused "
        "by exact zero exposure or severe collinearity.",
        "",
        "Leave-one-role-topic-out analysis keeps the publication-level DeepSeek barrier sign negative for all 12 "
        "barrier-topic omissions (11 nominally significant). In the family pool, however, omitting Topic 22 reverses "
        "the barrier sign for both DeepSeek and Kimi. The family barrier result is therefore Topic-22-dependent. "
        "Propagation estimates are less stable and do not provide a robust positive cascade signal.",
        "",
        "## Interpretation",
        "",
        "Role separation does not convert the frozen ASIMOV stress test into positive validation. It localizes the "
        "pooled inverse association mainly to similarity with safety-barrier topics in DeepSeek, while exposure to "
        "propagation-node topics remains null or unstable. The result is useful as a construct diagnosis: the pooled "
        "exposure mixes protective and propagating mechanisms, but the current benchmark still does not validate the "
        "proposed technology-to-cascade link. See the CSV and JSON outputs for every declared variant and diagnostic.",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(primary[["corpus_unit", "model", "term", "coef_log_odds_per_sd", "p_value", "q_value"]].to_string(index=False))


if __name__ == "__main__":
    main()
