"""Predefined statistical analysis (plan Task 7). Consumes ONLY the frozen
outputs/raw_trials.csv — never reruns the simulator.

- Per-cell propagation count/rate with Wilson 95% CI.
- C1 family: 18 speed x delay exact McNemar tests vs the speed/seed-matched C0,
  BH-corrected within the family.
- C2 family: 12 speed x offset exact McNemar tests, BH-corrected separately.
- Paired risk differences with seed-level bootstrap 95% CIs.
- Fisher exact tests appear ONLY as unpaired sensitivity analyses.
- Cochran-Armitage delay-response trend per speed (preregistered trend check;
  monotonicity alone is not treated as causal proof).
- Matched rescue (C4) effectiveness vs its mismatch parent.
- Frozen outcome classification (PILOT_SUPPORT / CONTAINED / ORDINARY_FAILURE /
  UNRESOLVED) applied mechanically.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import binomtest, chi2, norm, fisher_exact

WORK = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(WORK, "outputs")
BOOTSTRAP_B = 10000
BOOTSTRAP_SEED = 9101  # documented administrative seed for the CI resampling
Z95 = norm.ppf(0.975)


def wilson_ci(k, n, z=Z95):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return (center - half, center + half)


def bh_adjust(pvals):
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    m = len(p)
    q = ranked * m / (np.arange(m) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.clip(q, 0, 1)
    return out


def exact_mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return float(binomtest(min(b, c), n, 0.5).pvalue)


def bootstrap_rd_ci(diffs, B=BOOTSTRAP_B, seed=BOOTSTRAP_SEED):
    """Seed-level bootstrap of the paired risk difference (percentile CI)."""
    diffs = np.asarray(diffs, dtype=float)
    rng = np.random.default_rng(seed)
    n = len(diffs)
    stats = np.empty(B)
    for i in range(B):
        stats[i] = diffs[rng.integers(0, n, n)].mean()
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def cochran_armitage(scores, successes, totals):
    """Cochran-Armitage trend test, normal approximation, two-sided p."""
    scores = np.asarray(scores, float)
    r = np.asarray(successes, float)
    n = np.asarray(totals, float)
    N = n.sum()
    if N == 0:
        return np.nan, np.nan
    p_hat = r.sum() / N
    w = scores - (n * scores).sum() / N
    T = (w * r).sum()
    varT = p_hat * (1 - p_hat) * (n * w ** 2).sum()
    if varT <= 0:
        return np.nan, np.nan
    Z = T / np.sqrt(varT)
    return float(Z), float(2 * (1 - norm.cdf(abs(Z))))


def paired_compare(df, cond_mask, base_df, level_col):
    """Exact McNemar + RD + bootstrap for one cell vs matched C0."""
    b = c = 0
    diffs = []
    merged = cond_mask[["seed", "label"]].merge(
        base_df[["seed", "label"]], on="seed", suffixes=("_x", "_0"))
    prop_x = (merged["label_x"] == "PROPAGATED").astype(int)
    prop_0 = (merged["label_0"] == "PROPAGATED").astype(int)
    b = int(((prop_0 == 0) & (prop_x == 1)).sum())
    c = int(((prop_0 == 1) & (prop_x == 0)).sum())
    diffs = (prop_x - prop_0).to_numpy()
    p = exact_mcnemar(b, c)
    rd = float(diffs.mean())
    lo, hi = bootstrap_rd_ci(diffs)
    # unpaired sensitivity only
    tab = [[int(prop_x.sum()), int((1 - prop_x).sum())],
           [int(prop_0.sum()), int((1 - prop_0).sum())]]
    fisher_p = float(fisher_exact(tab)[1])
    return {"b": b, "c": c, "mcnemar_p": p, "risk_diff": rd,
            "rd_ci_lo": lo, "rd_ci_hi": hi, "fisher_p_sensitivity": fisher_p}


def main():
    raw = pd.read_csv(os.path.join(OUT, "raw_trials.csv"),
                      float_precision="round_trip")
    table = pd.read_csv(os.path.join(OUT, "trial_table.csv"))

    # --- completeness validation
    assert len(raw) == 3300 and raw["trial_id"].is_unique
    assert set(raw["condition"].unique()) == {"C0", "C1", "C2", "C3", "C4"}
    planned = table["trial_id"]
    assert set(raw["trial_id"]) == set(planned)
    for (cond, s, d, o), grp in raw.groupby(
            ["condition", "speed_mps", "delay_ms", "offset_m"]):
        assert grp["seed"].is_unique and len(grp) == 50, (cond, s, d, o)

    labels = ["PROPAGATED", "CONTAINED", "ORDINARY_FAILURE", "BREACH_UNORDERED",
              "UNRESOLVED"]

    # --- descriptive per cell
    desc_rows = []
    cell_cols = ["condition", "speed_mps", "delay_ms", "offset_m", "rescue_c1",
                 "rescue_c2"]
    for keys, cell in raw.groupby(cell_cols):
        cond, s, d, o, r1, r2 = keys
        n = len(cell)
        k = int((cell["label"] == "PROPAGATED").sum())
        lo, hi = wilson_ci(k, n)
        row = {"condition": cond, "speed_mps": s, "delay_ms": d, "offset_m": o,
               "rescue_c1": bool(r1), "rescue_c2": bool(r2), "n": n,
               "n_propagated": k, "rate": k / n,
               "wilson_lo": lo, "wilson_hi": hi,
               "local_pass_rate": float(cell["all_pass"].mean()),
               "min_margin_median_m": float(cell["min_margin_m"].median()),
               "min_margin_p05_m": float(cell["min_margin_m"].quantile(0.05)),
               "stop_latency_median_s": float(cell["stop_latency_s"].median(skipna=True))
               if cell["stop_latency_s"].notna().any() else np.nan,
               "peak_force_median_n": float(cell["peak_contact_force_n"].median()),
               "peak_force_max_n": float(cell["peak_contact_force_n"].max())}
        for lab in labels:
            row[f"n_{lab.lower()}"] = int((cell["label"] == lab).sum())
        desc_rows.append(row)
    desc = pd.DataFrame(desc_rows).sort_values(cell_cols)
    desc.to_csv(os.path.join(OUT, "descriptive_results.csv"), index=False)

    # --- inferential: C1 and C2 families vs matched C0
    base = raw[raw["condition"] == "C0"]
    inf_rows = []
    for family, cond, level_col in (("C1", "C1", "delay_ms"), ("C2", "C2", "offset_m")):
        fam_rows = []
        for (s, lvl), cell in raw[raw["condition"] == cond].groupby(
                ["speed_mps", level_col]):
            base_s = base[base["speed_mps"] == s]
            cmp_ = paired_compare(raw, cell, base_s, level_col)
            fam_rows.append({"family": family, "kind": f"{cond.lower()}_vs_c0",
                             "speed_mps": s, level_col: lvl, **cmp_})
        qs = bh_adjust([r["mcnemar_p"] for r in fam_rows])
        for r, q in zip(fam_rows, qs):
            r["bh_q"] = float(q)
        inf_rows.extend(fam_rows)

    # --- rescue effectiveness: C4 vs matched mismatch parent (paired)
    c4 = raw[raw["condition"] == "C4"]
    for rescue_kind, parent_cond, level_col, rcol in (
            ("rescue_c1", "C1", "delay_ms", "rescue_c1"),
            ("rescue_c2", "C2", "offset_m", "rescue_c2")):
        fam_rows = []
        for (s, lvl), cell in c4[c4[rcol]].groupby(["speed_mps", level_col]):
            parent = raw[(raw["condition"] == parent_cond)
                         & (raw["speed_mps"] == s) & (raw[level_col] == lvl)]
            merged = parent[["seed", "label"]].merge(
                cell[["seed", "label"]], on="seed", suffixes=("_p", "_r"))
            prop_p = (merged["label_p"] == "PROPAGATED").astype(int)
            prop_r = (merged["label_r"] == "PROPAGATED").astype(int)
            b = int(((prop_p == 1) & (prop_r == 0)).sum())  # fixed by rescue
            c = int(((prop_p == 0) & (prop_r == 1)).sum())
            diffs = (prop_p - prop_r).to_numpy()
            lo, hi = bootstrap_rd_ci(diffs)
            fam_rows.append({"family": "C4", "kind": rescue_kind, "speed_mps": s,
                             level_col: lvl, "b": b, "c": c,
                             "mcnemar_p": exact_mcnemar(b, c),
                             "risk_diff": float(diffs.mean()),
                             "rd_ci_lo": lo, "rd_ci_hi": hi,
                             "fisher_p_sensitivity": np.nan})
        qs = bh_adjust([r["mcnemar_p"] for r in fam_rows])
        for r, q in zip(fam_rows, qs):
            r["bh_q"] = float(q)
        inf_rows.extend(fam_rows)

    # --- delay-response trend per speed (C1, including the C0 zero-delay level)
    for s, grp in raw[(raw["condition"].isin(["C0", "C1"]))
                      & (raw["delay_ms"].notna())].groupby("speed_mps"):
        sub = grp[grp["condition"].isin(["C0", "C1"])]
        levels, succ, tot = [], [], []
        for lvl in sorted(sub["delay_ms"].unique()):
            cell = sub[sub["delay_ms"] == lvl]
            levels.append(lvl)
            succ.append(int((cell["label"] == "PROPAGATED").sum()))
            tot.append(len(cell))
        Z, p = cochran_armitage(levels, succ, tot)
        inf_rows.append({"family": "C1", "kind": "trend_cochran_armitage",
                         "speed_mps": s, "delay_ms": np.nan, "offset_m": np.nan,
                         "b": np.nan, "c": np.nan, "mcnemar_p": np.nan,
                         "risk_diff": np.nan, "rd_ci_lo": np.nan,
                         "rd_ci_hi": np.nan, "fisher_p_sensitivity": np.nan,
                         "bh_q": np.nan, "trend_Z": Z, "trend_p": p})
    inf = pd.DataFrame(inf_rows)
    inf.to_csv(os.path.join(OUT, "inferential_results.csv"), index=False)

    # --- frozen outcome classification
    c0 = raw[raw["condition"] == "C0"]
    baseline_valid = bool((~c0["margin_breach"]).all() and c0["all_pass"].all()
                          and (~c0["nan_or_unstable"]).all())
    prop = raw[raw["label"] == "PROPAGATED"]
    prop_local_pass = bool(prop["all_pass"].all()) if len(prop) else True
    ordered_share = (float(prop["ordered_events"].mean()) if len(prop) else np.nan)

    c1f = inf[(inf["family"] == "C1") & (inf["kind"] == "c1_vs_c0")]
    support_speeds = {}
    for s, grp in c1f.groupby("speed_mps"):
        grp = grp.sort_values("delay_ms")
        sig = ((grp["bh_q"] < 0.05) & (grp["rd_ci_lo"] > 0)).to_numpy()
        # at least two ADJACENT nonzero delays both significant
        adj = any(sig[i] and sig[i + 1] for i in range(len(sig) - 1))
        support_speeds[str(s)] = bool(adj)
    n_prop_mismatch = int(raw[(raw["condition"].isin(["C1", "C2"]))
                              & (raw["label"] == "PROPAGATED")].shape[0])
    breach_mismatch = raw[(raw["condition"].isin(["C1", "C2"]))
                          & (raw["margin_breach"])]
    all_breaches_contract_fail = bool((~breach_mismatch["all_pass"]).all()) \
        if len(breach_mismatch) else False

    if not baseline_valid:
        outcome, rule = "UNRESOLVED", "baseline itself unsafe or invalid"
    elif (any(support_speeds.values()) and prop_local_pass
          and (ordered_share >= 0.90 if len(prop) else False)):
        outcome = "PILOT_SUPPORT"
        rule = ("C0 valid; >=2 adjacent nonzero delays with BH q<0.05 and paired RD "
                "95% CI lower bound > 0 at the same speed; all propagated trials "
                "pass local contracts; >=90% satisfy the strict event order")
    elif n_prop_mismatch == 0:
        outcome, rule = "CONTAINED", "no propagation observed within the preregistered mismatch range"
    elif len(breach_mismatch) and all_breaches_contract_fail:
        outcome, rule = "ORDINARY_FAILURE", "all unsafe outcomes accompanied by local contract failure"
    else:
        outcome, rule = "UNRESOLVED", ("propagation observed but preregistered support "
                                       "criteria not fully met")
    classification = {
        "outcome": outcome, "rule_fired": rule,
        "baseline_valid": baseline_valid,
        "n_propagated_C1_C2": n_prop_mismatch,
        "n_propagated_total": int(len(prop)),
        "propagated_all_local_pass": prop_local_pass,
        "propagated_ordered_share": None if np.isnan(ordered_share) else ordered_share,
        "support_speeds": support_speeds,
        "n_ordinary_failure_C3": int(((raw["condition"] == "C3")
                                      & (raw["label"] == "ORDINARY_FAILURE")).sum()),
        "n_C3": int((raw["condition"] == "C3").sum()),
    }
    with open(os.path.join(OUT, "outcome_classification.json"), "w") as f:
        json.dump(classification, f, indent=2)
    print(json.dumps(classification, indent=2))


if __name__ == "__main__":
    main()
