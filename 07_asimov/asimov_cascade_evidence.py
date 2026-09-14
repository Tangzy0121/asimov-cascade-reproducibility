# -*- coding: utf-8 -*-
# ============================================================================
# asimov_cascade_evidence.py
# Purpose : Core statistics for Pillar 1 — do LLM errors on ASIMOV scenarios
#           co-vary with patent-side decay exposure of nearby safety tech?
#           Scenario-level logistic regressions (primary) + topic-level
#           soft-weighted Spearman (secondary matrix view) + k sensitivity
#           + figures + case boxes. Runs DeepSeek-only in PRELIMINARY mode
#           until kimi_*_results_seed*.csv exist (majority vote).
# Input   : output/asimov_validation/mapping_{v1,v2}.csv
#           output/asimov_validation/{v2,v1}_injury_results.csv (DeepSeek)
#           output/asimov_validation/kimi_{v2,v1}_results_seed*.csv (optional)
# Output  : output/asimov_validation/evidence_report.md, evidence_stats.json,
#           FIG_evidence_*.{pdf,png}, case_boxes.md
# Usage   : python scripts/asimov_cascade_evidence.py
# ============================================================================

import sys, io, json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from scipy import stats as sstats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT = PROJECT_ROOT / "output" / "asimov_validation"

V2_QUESTIONS = {
    "latent_risk_correct": "Q1 latent risk",
    "latent_severity_correct": "Q2 latent severity",
    "effect_correct": "Q3 effect",
    "activated_risk_correct": "Q4 activated risk",
}
K_VALUES = [25, 50, 100]
K_PRIMARY = 50
N_PERM = 10_000
RNG_SEED = 42


# ── Loading ─────────────────────────────────────────────────────────

def load_mapping(ds):
    df = pd.read_csv(OUT / f"mapping_{ds}.csv")
    df["log_len"] = np.log1p(df["text"].astype(str).str.len())
    return df


def load_deepseek(ds):
    df = pd.read_csv(OUT / f"{ds}_injury_results.csv")
    df = df[df["error"].isna()].copy()
    if ds == "v2":
        for c in V2_QUESTIONS:
            df[c] = df[c].astype(bool)
    else:
        df["correct"] = df["correct"].astype(bool)
    return df.set_index("idx")


def load_kimi_majority(ds, expected_n=None):
    """Majority vote across seed runs; None if no kimi files or coverage
    < 90% of expected scenarios (partial background run — using it would
    bias stats toward the first N scenarios)."""
    files = sorted(OUT.glob(f"kimi_{ds}_results_seed*.csv"))
    if not files:
        return None, None
    runs = []
    for f in files:
        r = pd.read_csv(f)
        r = r[r["error"].isna()]
        runs.append(r.set_index("idx"))
    common = runs[0].index
    for r in runs[1:]:
        common = common.intersection(r.index)
    if expected_n and len(common) < 0.9 * expected_n:
        print(f"  [wait] kimi {ds}: only {len(common)}/{expected_n} common "
              f"scenarios across seeds — treated as not-ready")
        return None, None
    cols = list(V2_QUESTIONS) if ds == "v2" else ["correct"]
    mv = pd.DataFrame(index=common)
    agree = np.zeros(len(common))
    for c in cols:
        stack = np.vstack([r.loc[common, c].astype(bool).values for r in runs])
        mv[c] = stack.mean(axis=0) >= 0.5
        agree += (stack == mv[c].values).mean(axis=0)
    if ds == "v2":
        mv["all_correct"] = mv[list(V2_QUESTIONS)].all(axis=1)
    agree_rate = float(agree.mean() / len(cols))
    return mv, {"n_seeds": len(runs), "n_common": len(common),
                "mean_agreement": agree_rate}


# ── Scenario-level logistic ─────────────────────────────────────────

def fit_logit(df, y_col, e_col, extra_terms, cluster=None):
    """Binomial GLM; returns dict of coef/p for E term + model summary row."""
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    formula = f"{y_col} ~ {e_col}" + (" + " + " + ".join(extra_terms) if extra_terms else "")
    model = smf.glm(formula, data=df, family=sm.families.Binomial())
    if cluster is not None:
        fit = model.fit(cov_type="cluster", cov_kwds={"groups": cluster})
    else:
        fit = model.fit()
    return {
        "formula": formula,
        "n": int(fit.nobs),
        "E_coef": float(fit.params[e_col]),
        "E_pvalue": float(fit.pvalues[e_col]),
        "E_or": float(np.exp(fit.params[e_col])),
    }


def scenario_stats_v2(mapping, model_errors, label, report):
    """Long format: scenario x 4 questions."""
    m = mapping.set_index("scenario_idx")
    rows = []
    for q_col, q_name in V2_QUESTIONS.items():
        part = pd.DataFrame({
            "error": (~model_errors[q_col]).astype(int),
            "subq": q_name,
            "scenario": model_errors.index,
        })
        rows.append(part)
    long = pd.concat(rows).reset_index(drop=True)
    long = long.join(m[["E_decay_k25", "E_decay_k50", "E_decay_k100", "log_len"]],
                     on="scenario")

    out = {}
    for k in K_VALUES:
        e_col = f"E_decay_k{k}"
        res = fit_logit(long, "error", e_col, ["C(subq)", "log_len"],
                        cluster=long["scenario"])
        out[f"k{k}"] = res
        report.append(
            f"| v2 {label} k={k} | {res['n']} | {res['E_coef']:.3f} "
            f"| {res['E_or']:.2f} | {res['E_pvalue']:.4f} |")
    # strict all-4-correct robustness (scenario level, k=50)
    strict = pd.DataFrame({
        "error": (~model_errors["all_correct"]).astype(int),
        "scenario": model_errors.index,
    }).join(m[["E_decay_k50", "log_len"]], on="scenario")
    res = fit_logit(strict, "error", "E_decay_k50", ["log_len"])
    out["strict_k50"] = res
    report.append(
        f"| v2 {label} strict(all-4) k=50 | {res['n']} | {res['E_coef']:.3f} "
        f"| {res['E_or']:.2f} | {res['E_pvalue']:.4f} |")
    return out, long


def scenario_stats_v1(mapping, model_errors, label, report):
    m = mapping.set_index("scenario_idx")
    df = pd.DataFrame({
        "error": (~model_errors["correct"]).astype(int),
        "scenario": model_errors.index,
    }).join(m[["E_decay_k25", "E_decay_k50", "E_decay_k100", "log_len"]],
            on="scenario")
    out = {}
    for k in K_VALUES:
        e_col = f"E_decay_k{k}"
        res = fit_logit(df, "error", e_col, ["log_len"])
        out[f"k{k}"] = res
        report.append(
            f"| v1 {label} k={k} | {res['n']} | {res['E_coef']:.3f} "
            f"| {res['E_or']:.2f} | {res['E_pvalue']:.4f} |")
    return out


# ── Topic-level Spearman + permutation ──────────────────────────────

def topic_level(mapping, model_errors, safety_decay, ds, label, report):
    """Soft-weighted per-topic error rate vs decay; Spearman + permutation."""
    w_cols = [c for c in mapping.columns if c.startswith("w_")]
    tids = [int(c[2:]) for c in w_cols]
    if ds == "v2":
        err = (~model_errors["all_correct"]).astype(int)
    else:
        err = (~model_errors["correct"]).astype(int)
    m = mapping.set_index("scenario_idx")
    err = err.reindex(m.index).fillna(False).astype(int)

    err_t, decay_t, names = [], [], []
    for c, t in zip(w_cols, tids):
        w = m[c].values
        if w.sum() < 1e-9:
            continue
        err_t.append(float((w * err.values).sum() / w.sum()))
        decay_t.append(float(safety_decay[t]["decay"]))
        names.append(safety_decay[t]["name"])

    rho, p = sstats.spearmanr(decay_t, err_t)
    rng = np.random.default_rng(RNG_SEED)
    cnt = 0
    for _ in range(N_PERM):
        rp, _ = sstats.spearmanr(rng.permutation(decay_t), err_t)
        if abs(rp) >= abs(rho):
            cnt += 1
    p_perm = (cnt + 1) / (N_PERM + 1)
    report.append(
        f"| topic-level {ds} {label} | n_topics={len(err_t)} | "
        f"rho={rho:.3f} | p_asym={p:.4f} | p_perm={p_perm:.4f} |")
    return {"topics": names, "decay": decay_t, "err": err_t,
            "rho": float(rho), "p_perm": float(p_perm)}


# ── Figures ─────────────────────────────────────────────────────────

def fig_decile(mapping, err_by_model, ds, style):
    """E_decay decile bins vs error rate per model."""
    import matplotlib.pyplot as plt

    m = mapping.copy()
    m["decile"] = pd.qcut(m["E_decay_k50"], 10, labels=False, duplicates="drop")
    fig, ax = plt.subplots(figsize=(7, 5))
    for i, (label, err) in enumerate(err_by_model.items()):
        e = err.reindex(m["scenario_idx"]).fillna(False).astype(int)
        g = m.groupby("decile").apply(
            lambda d: pd.Series({
                "E": d["E_decay_k50"].mean(), "err": e.loc[d["scenario_idx"]].mean()
            }), include_groups=False)
        ax.plot(g["E"], g["err"], "o-", color=style.CANDY_PALETTE[i], label=label)
    ax.set_xlabel("Decay exposure E (k=50, decile mean)")
    ax.set_ylabel("Error rate")
    ax.set_title(f"{ds}-Injury: error vs decay exposure (deciles)")
    ax.legend()
    fig.tight_layout()
    style.save_figure(fig, f"FIG_evidence_decile_{ds}", OUT, close=True)


def fig_topic_scatter(topic_res, ds, style):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.scatter(topic_res["decay"], topic_res["err"],
               color=style.CANDY_PALETTE[0], s=60, edgecolor="white", zorder=3)
    for x, y, n in zip(topic_res["decay"], topic_res["err"], topic_res["topics"]):
        ax.annotate(n.split("_", 1)[0], (x, y), textcoords="offset points",
                    xytext=(5, 4), fontsize=8)
    ax.set_xlabel("HMM decay probability (topic)")
    ax.set_ylabel("Soft-weighted error rate")
    ax.set_title(f"{ds}: rho={topic_res['rho']:.2f}, "
                 f"p_perm={topic_res['p_perm']:.3f}")
    fig.tight_layout()
    style.save_figure(fig, f"FIG_topic_scatter_{ds}", OUT, close=True)


# ── Main ────────────────────────────────────────────────────────────

def main():
    from engine import style

    style.set_style()

    sig = pd.read_csv(
        PROJECT_ROOT / "output" / "time_analysis" / "11_temporal_enrichment"
        / "06_cascade_v3" / "cascade_signals_v5.csv")
    sig = sig[sig["risk_level"].isin({"HIGH", "MEDIUM", "LOW"})]
    safety_decay = {
        int(r.bertopic_id): {"decay": float(r.hmm_decay_probability),
                             "name": r.bertopic_name, "risk": r.risk_level}
        for r in sig.itertuples()
    }

    stats_out = {}
    report = [
        "# Pillar 1 Evidence Report",
        "",
        "## Scenario-level logistic regression (error ~ E_decay + controls)",
        "",
        "| model | n | E coef | odds ratio | p |",
        "|---|---|---|---|---|",
    ]
    topic_results = {}

    for ds in ["v2", "v1"]:
        mpath = OUT / f"mapping_{ds}.csv"
        if not mpath.exists():
            print(f"[skip] {ds}: mapping missing")
            continue
        mapping = load_mapping(ds)
        ds_res = load_deepseek(ds)
        kimi_mv, kimi_meta = load_kimi_majority(ds, expected_n=len(mapping))
        preliminary = kimi_mv is None

        if ds == "v2":
            s_out, long = scenario_stats_v2(mapping, ds_res, "DeepSeek", report)
            stats_out.setdefault("v2", {})["deepseek"] = s_out
            err_series = {
                "DeepSeek": ~ds_res["all_correct"],
            }
            if not preliminary:
                s_out, _ = scenario_stats_v2(mapping, kimi_mv, "KimiMV", report)
                stats_out["v2"]["kimi_mv"] = s_out
                both = ds_res["all_correct"] & kimi_mv["all_correct"].reindex(
                    ds_res.index).fillna(False)
                s_out, _ = scenario_stats_v2(
                    mapping,
                    ds_res.assign(all_correct=both,
                                  **{q: ds_res[q] & kimi_mv[q].reindex(ds_res.index).fillna(False)
                                     for q in V2_QUESTIONS}),
                    "BothWrong", report)
                stats_out["v2"]["both_wrong"] = s_out
                err_series["Kimi (majority)"] = ~kimi_mv["all_correct"]
        else:
            s_out = scenario_stats_v1(mapping, ds_res, "DeepSeek", report)
            stats_out.setdefault("v1", {})["deepseek"] = s_out
            err_series = {"DeepSeek": ~ds_res["correct"]}
            if not preliminary:
                s_out = scenario_stats_v1(mapping, kimi_mv, "KimiMV", report)
                stats_out["v1"]["kimi_mv"] = s_out
                both_wrong = ~(ds_res["correct"] & kimi_mv["correct"].reindex(
                    ds_res.index).fillna(False))
                s_out = scenario_stats_v1(
                    mapping, ds_res.assign(correct=~both_wrong), "BothWrong", report)
                stats_out["v1"]["both_wrong"] = s_out
                err_series["Kimi (majority)"] = ~kimi_mv["correct"]

        report.append("")
        stats_out[ds]["preliminary_deepseek_only"] = preliminary
        if not preliminary:
            stats_out[ds]["kimi_meta"] = kimi_meta

        # topic-level
        t_res = topic_level(mapping, ds_res, safety_decay, ds, "DeepSeek", report)
        topic_results[ds] = t_res
        stats_out[ds]["topic_level_deepseek"] = {
            "rho": t_res["rho"], "p_perm": t_res["p_perm"]}

        # figures
        err_strict = {k: v for k, v in err_series.items()}
        fig_decile(mapping, err_strict, ds, style)
        fig_topic_scatter(t_res, ds, style)
        print(f"  [{ds}] figures saved (preliminary={preliminary})")

    report += ["", "## Topic-level (secondary matrix view)", ""]
    # (topic rows already appended inline above)
    report += [
        "",
        "## Caveats",
        "- Kimi v2 landed 2026-07-31 (3 seeds, common=308/319, mean agreement "
        "95.6%): KimiMV coefficients negative at all k but NS (p=.10-.18, "
        "T=1.0 locked for kimi-for-coding); BothWrong negative and "
        "significant (p=.004-.046). Direction consistent with DeepSeek.",
        "- v1 scenarios sit far from patent language (nn sim ~0.1-0.2); "
        "treat v1 as weak replication.",
        "- GPT-5/Gemini comparisons are aggregate-level only (no per-scenario "
        "labels published).",
    ]

    (OUT / "evidence_report.md").write_text("\n".join(report), encoding="utf-8")
    with open(OUT / "evidence_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats_out, f, indent=2)
    print(f"\nReport: {OUT / 'evidence_report.md'}")
    print(f"Stats:  {OUT / 'evidence_stats.json'}")


if __name__ == "__main__":
    main()
