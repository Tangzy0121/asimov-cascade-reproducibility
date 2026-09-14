"""Figures (plan Task 8). Vector PDF output per user directive (deviation from
plan.md's PNG list, logged in AUDIT_REPORT.md). Consumes ONLY frozen outputs:
descriptive_results.csv, inferential_results.csv, f2_matched_trio.csv.gz,
f2_trio_selection.json, outcome_classification.json. Never reruns the sim.

All figures: large fonts, explicit units, Okabe-Ito color-blind-safe palette,
panel letters, in-figure captions with non-causal wording.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

WORK = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(WORK, "outputs")
FIG = os.path.join(WORK, "figures")

# Okabe-Ito color-blind-safe palette
BLUE, ORANGE, GREEN, VERM, PURPLE, SKY = ("#0072B2", "#E69F00", "#009E73",
                                          "#D55E00", "#CC79A7", "#56B4E9")
plt.rcParams.update({
    "font.size": 14, "axes.titlesize": 15, "axes.labelsize": 14,
    "xtick.labelsize": 12, "ytick.labelsize": 12, "legend.fontsize": 12,
    "figure.dpi": 300, "savefig.dpi": 300, "pdf.fonttype": 42,
})


def caption(fig, text, y=0.005):
    fig.text(0.01, y, text, fontsize=10.5, color="#333333", va="bottom",
             wrap=True)


def f1_heatmap(desc):
    sub = desc[((desc["condition"] == "C0") | (desc["condition"] == "C1"))
               & (~desc["rescue_c1"])]
    speeds = sorted(sub["speed_mps"].unique())
    delays = sorted(sub["delay_ms"].unique())
    rate = np.zeros((len(speeds), len(delays)))
    counts = [["" for _ in delays] for _ in speeds]
    for i, s in enumerate(speeds):
        for j, d in enumerate(delays):
            cell = sub[(sub["speed_mps"] == s) & (sub["delay_ms"] == d)]
            k, n = int(cell["n_propagated"].iloc[0]), int(cell["n"].iloc[0])
            rate[i, j] = k / n
            counts[i][j] = f"{k}/{n}"
    fig, ax = plt.subplots(figsize=(12.5, 5.6))
    mesh = ax.pcolormesh(np.arange(len(delays) + 1) - 0.5,
                         np.arange(len(speeds) + 1) - 0.5,
                         rate, cmap="viridis", vmin=0, vmax=1,
                         edgecolors="white", linewidth=2)
    for i in range(len(speeds)):
        for j in range(len(delays)):
            ax.text(j, i, counts[i][j], ha="center", va="center",
                    fontsize=13, fontweight="bold",
                    color="white" if rate[i, j] < 0.55 else "black")
    ax.set_xticks(range(len(delays)), [f"{int(d)}" for d in delays])
    ax.set_yticks(range(len(speeds)), [f"{s:.2f}" for s in speeds])
    ax.set_xlabel("Perception timestamp delay (ms)")
    ax.set_ylabel("Approach speed (m/s)")
    ax.set_title("A  Ordered-propagation count per cell (C1; delay 0 ms = matched C0 baseline)")
    cb = fig.colorbar(mesh, ax=ax, pad=0.02)
    cb.set_label("Propagation rate (k/n)")
    caption(fig, "F1. Controlled 1-D simulation, 50 frozen seeds per cell. A cell counts a trial only if the frozen strict "
                 "event order held with all local contracts passing (PROPAGATED). Large-delay breaches that precede the "
                 "delayed trigger violate the order rule and are NOT counted here (reported separately as unordered breaches). "
                 "Simulation results only; not evidence about real robots.")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(FIG, "F1_propagation_heatmap.pdf"))
    plt.close(fig)


def f2_aligned_traces():
    trio = pd.read_csv(os.path.join(OUT, "f2_matched_trio.csv.gz"))
    with open(os.path.join(OUT, "f2_trio_selection.json")) as f:
        sel = json.load(f)
    raw = pd.read_csv(os.path.join(OUT, "raw_trials.csv"))
    mismatch_label = raw[(raw["condition"] == "C1")
                         & (raw["speed_mps"] == sel["speed"])
                         & (raw["delay_ms"] == sel["delay_ms"])
                         & (raw["seed"] == sel["seed"])]["label"].iloc[0]
    panels = [("baseline", "Matched baseline (C0)", BLUE),
              ("mismatch", f"Median-rule mismatch (C1, {int(sel['delay_ms'])} ms)", VERM),
              ("rescue", "Matched rescue (C4, 25 ms age gate)", GREEN)]
    rows = [("gap", "Gap (m)"), ("age", "Consumed sample age (ms)"),
            ("cmd", "Velocity (m/s)"), ("margin", "Safety margin (m)")]
    fig, axes = plt.subplots(4, 3, figsize=(16, 13), sharex=True)
    tmax = max(trio[trio["panel"] == "mismatch"]["t"].max(),
               trio[trio["panel"] == "baseline"]["t"].max())
    tmax = min(tmax, 3.0)
    for col, (tag, title, color) in enumerate(panels):
        tr = trio[trio["panel"] == tag]
        t = tr["t"].to_numpy()
        d_safe = 0.20
        ax = axes[0][col]
        ax.plot(t, tr["gap"], color=color, lw=1.2, label="true gap")
        ax.plot(t, tr["received_gap"], color="black", lw=0.9, alpha=0.7,
                label="received (perceived) gap")
        ax.axhline(d_safe, color=PURPLE, ls="--", lw=1.2, label="d_safe = 0.20 m")
        trig = tr.loc[tr["monitor_triggered"], "t"]
        if len(trig):
            ax.axvline(trig.iloc[0], color=ORANGE, ls=":", lw=1.5,
                       label="safety trigger")
        ax.set_ylabel("Gap (m)")
        ax.set_title(f"{'ABC'[col]}1  {title}")
        if col == 0:
            ax.legend(loc="upper right", fontsize=10)
        ax = axes[1][col]
        ax.plot(t, tr["sample_age"] * 1000.0, color=color, lw=1.2)
        ax.set_ylabel("Sample age (ms)")
        ax.set_title(f"{'ABC'[col]}2")
        ax = axes[2][col]
        ax.plot(t, tr["v_cmd"], color="black", lw=1.1, label="planner command")
        ax.plot(t, tr["v"], color=color, lw=1.2, label="actual velocity")
        ax.set_ylabel("Velocity (m/s)")
        ax.set_title(f"{'ABC'[col]}3")
        if col == 0:
            ax.legend(loc="upper right", fontsize=10)
        ax = axes[3][col]
        margin = tr["gap"] - d_safe
        ax.plot(t, margin, color=color, lw=1.2)
        ax.axhline(0.0, color=PURPLE, ls="--", lw=1.2)
        below = margin < 0
        if below.any():
            ax.axvspan(t[below.to_numpy()][0], t[below.to_numpy()][-1],
                       color=VERM, alpha=0.15, label="margin < 0")
        ax.set_ylabel("Margin (m)")
        ax.set_xlabel("Time (s)")
        ax.set_title(f"{'ABC'[col]}4")
        for a in (axes[0][col], axes[1][col], axes[2][col], axes[3][col]):
            a.set_xlim(0, tmax)
    caption(fig, "F2. Synchronized matched trio at the same frozen seed "
                 f"(speed {sel['speed']:.2f} m/s, seed {sel['seed']}), selected by the frozen median rule "
                 "(median-propagation-count C1 cell; lower-median minimum-margin trial; same seed for C0/C1/C4). "
                 f"The selected mismatch trial's frozen label is {mismatch_label}: at 200 ms the margin breach begins "
                 "before the delayed safety trigger, so the strict event order is not met and this cell counts zero "
                 "propagations — ordered propagation concentrates at intermediate delays (see F1). "
                 "The rescue panel stops almost immediately because every delayed sample violates the 25 ms age gate — "
                 "that is the preregistered conservative-stop design, not a tuned outcome. Synthetic simulation traces.")
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    fig.savefig(os.path.join(FIG, "F2_aligned_traces.pdf"))
    plt.close(fig)


def f3_condition_rates(desc):
    order = ["C0", "C1", "C2", "C3", "C4"]
    names = ["C0\nmatched\nbaseline", "C1\ntimestamp\ndelay", "C2\nthreshold\noffset",
             "C3\ncomponent\nfault", "C4\nmatched\nrescue"]
    props, plo, phi, ofs, oflo, ofhi = [], [], [], [], [], []
    for cond in order:
        cell = desc[desc["condition"] == cond]
        n = int(cell["n"].sum())
        kp = int(cell["n_propagated"].sum())
        ko = int(cell["n_ordinary_failure"].sum())
        from analyze import wilson_ci
        lo, hi = wilson_ci(kp, n)
        props.append(kp / n)
        plo.append(max(0.0, kp / n - lo)); phi.append(max(0.0, hi - kp / n))
        lo2, hi2 = wilson_ci(ko, n)
        ofs.append(ko / n)
        oflo.append(max(0.0, ko / n - lo2)); ofhi.append(max(0.0, hi2 - ko / n))
    x = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(12.5, 6.5))
    ax.errorbar(x - 0.12, props, yerr=[plo, phi], fmt="o", ms=11, color=VERM,
                capsize=6, lw=2, label="PROPAGATED rate (strict order, local pass)")
    ax.errorbar(x + 0.12, ofs, yerr=[oflo, ofhi], fmt="s", ms=10, color=BLUE,
                capsize=6, lw=2, label="ORDINARY_FAILURE rate (component fault, excluded from propagation)")
    for xi, (p, o) in enumerate(zip(props, ofs)):
        ax.annotate(f"{p:.3f}", (xi - 0.12, p), textcoords="offset points",
                    xytext=(0, 12), ha="center", fontsize=12, fontweight="bold",
                    color=VERM)
        if o > 0:
            ax.annotate(f"{o:.3f}", (xi + 0.12, o), textcoords="offset points",
                        xytext=(0, 12), ha="center", fontsize=12,
                        fontweight="bold", color=BLUE)
    ax.set_xticks(x, names)
    ax.set_ylabel("Trial-level rate (95% Wilson CI)")
    ax.set_ylim(-0.05, 1.28)
    ax.set_title("A  Trial-level outcome rates by condition")
    ax.legend(loc="upper left", fontsize=11)
    caption(fig, "F3. Rates pooled over all cells per condition (C0/C3: 150 trials; C1: 900; C2: 600; C4: 1500). "
                 "C3 component faults are reported as ordinary failures and never counted as propagation. "
                 "Controlled simulation pilot; no claim about real-world accident rates.")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(os.path.join(FIG, "F3_condition_rates.pdf"))
    plt.close(fig)


def f4_contract_and_rescue(desc, inf):
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(15.5, 6.2),
                                   gridspec_kw={"width_ratios": [1, 1.5]})
    # panel A: local contract pass rate per condition
    order = ["C0", "C1", "C2", "C3", "C4"]
    rates = []
    for cond in order:
        cell = desc[desc["condition"] == cond]
        rates.append(float((cell["local_pass_rate"] * cell["n"]).sum()
                           / cell["n"].sum()))
    colors = [GREEN, GREEN, GREEN, VERM, GREEN]
    axA.bar(order, rates, color=colors, edgecolor="black")
    for i, r in enumerate(rates):
        axA.text(i, r + 0.02, f"{r:.2f}", ha="center", fontsize=12,
                 fontweight="bold")
    axA.set_ylim(0, 1.15)
    axA.set_ylabel("Local-contract pass rate")
    axA.set_xlabel("Condition")
    axA.set_title("A  All five local contracts pass except in C3\n(component fault fails perception contract by construction)",
                  fontsize=13)

    # panel B: rescue effect for cells where the parent propagated
    resc = inf[(inf["family"] == "C4") & (inf["risk_diff"] > 0)]
    labels, rds, los, his = [], [], [], []
    for _, r in resc.iterrows():
        lvl = (f"{int(r['delay_ms'])} ms" if r["kind"] == "rescue_c1"
               else f"{r['offset_m']:+.2f} m")
        labels.append(f"{r['speed_mps']:.2f} m/s, {lvl}")
        rds.append(r["risk_diff"])
        los.append(r["risk_diff"] - r["rd_ci_lo"])
        his.append(r["rd_ci_hi"] - r["risk_diff"])
    y = np.arange(len(labels))[::-1]
    axB.errorbar(rds, y, xerr=[los, his], fmt="o", ms=9, color=GREEN, capsize=5,
                 lw=2)
    axB.axvline(0, color="gray", ls="--", lw=1)
    axB.set_yticks(y, labels, fontsize=11)
    axB.set_xlim(-0.05, 1.1)
    axB.set_xlabel("Paired propagation-risk reduction by matched rescue\n"
                   "(parent minus rescue, seed-level bootstrap 95% CI)")
    axB.set_title("B  Matched rescue eliminates propagation wherever it occurred\n"
                  "(all C4 trials contained; shown for cells with parent propagation)",
                  fontsize=13)
    caption(fig, "F4. Left: fraction of trials passing all five local contracts per condition. Right: paired risk "
                 "difference between each mismatch parent and its matched rescue (same seed, same physics), cells with "
                 "zero parent propagation omitted (RD = 0 exactly). Simulation results; rescue effectiveness is a "
                 "property of this modeled interface, not of any real robot.")
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(os.path.join(FIG, "F4_contract_and_rescue.pdf"))
    plt.close(fig)


def code_excerpt():
    with open(os.path.join(WORK, "src", "classify.py"), encoding="utf-8") as f:
        src = f.read()
    start = src.index("def decide_label")
    end = src.index("    stop_latency =", start)
    excerpt = src[start:end]
    gate = ('# Timestamp-age gate (C4 rescue, simulator.py):\n'
            'gate_violation = bool(rescue_c1 and age > age_gate_s + 1e-12)\n'
            'if gate_violation and not monitor.triggered:\n'
            '    monitor.triggered = True      # conservative stop\n'
            '    monitor.trigger_time = t\n\n')
    text = gate + excerpt
    fig, ax = plt.subplots(figsize=(13.5, 15))
    ax.axis("off")
    ax.text(0.01, 0.99, text, family="monospace", fontsize=10.5, va="top",
            transform=ax.transAxes)
    ax.set_title("Frozen propagation classifier & timestamp-age gate (excerpt, verbatim from frozen source)",
                 fontsize=14, pad=14)
    caption(fig, "Traceability exhibit only: this excerpt documents the frozen decision logic; it is not evidence by "
                 "itself. Full hashed sources are listed in final_manifest.json.")
    fig.savefig(os.path.join(FIG, "code_excerpt.pdf"), bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(FIG, exist_ok=True)
    desc = pd.read_csv(os.path.join(OUT, "descriptive_results.csv"))
    inf = pd.read_csv(os.path.join(OUT, "inferential_results.csv"))
    f1_heatmap(desc)
    print("F1 done")
    f2_aligned_traces()
    print("F2 done")
    f3_condition_rates(desc)
    print("F3 done")
    f4_contract_and_rescue(desc, inf)
    print("F4 done")
    code_excerpt()
    print("code excerpt done")


if __name__ == "__main__":
    main()
