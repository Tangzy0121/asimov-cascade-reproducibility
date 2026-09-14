"""Package verification (plan Task 9). Runs from a clean process; every check
prints PASS/FAIL and the script exits nonzero on any failure. Read-only with
one exception: regenerates analysis outputs into a temp directory to prove the
statistics derive from the frozen raw CSV alone.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

import pandas as pd

WORK = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(WORK, "outputs")
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    raw = pd.read_csv(os.path.join(OUT, "raw_trials.csv"),
                      float_precision="round_trip")
    table = pd.read_csv(os.path.join(OUT, "trial_table.csv"))

    check("exactly 3300 trials", len(raw) == 3300, f"n={len(raw)}")
    check("trial_ids unique", raw["trial_id"].is_unique)
    check("raw matches planned trial table",
          set(raw["trial_id"]) == set(table["trial_id"]))
    counts = raw["condition"].value_counts().to_dict()
    check("condition counts C0=150 C1=900 C2=600 C3=150 C4=1500",
          counts == {"C0": 150, "C1": 900, "C2": 600, "C3": 150, "C4": 1500},
          str(counts))
    cells = raw.groupby(["condition", "speed_mps", "delay_ms", "offset_m",
                         "rescue_c1", "rescue_c2"])
    check("every preregistered cell has exactly 50 seeds, no duplicates",
          all(len(g) == 50 and g["seed"].is_unique for _, g in cells),
          f"n_cells={cells.ngroups}")
    check("seeds within frozen range 2000-2049",
          bool(raw["seed"].between(2000, 2049).all()))
    cfg_sha = sha(os.path.join(WORK, "config", "preregistered.yaml"))
    frozen = open(os.path.join(WORK, "config", "preregistered.sha256")).read().split()[0]
    check("config file hash matches frozen hash", cfg_sha == frozen,
          cfg_sha[:12])
    check("every raw row carries the frozen config hash",
          bool((raw["config_sha256"] == cfg_sha).all()))
    c0 = raw[raw["condition"] == "C0"]
    check("C0 baseline valid (no breach, contracts pass)",
          bool((~c0["margin_breach"]).all() and c0["all_pass"].all()))
    c3 = raw[raw["condition"] == "C3"]
    check("C3 all ORDINARY_FAILURE with contract failure",
          bool((c3["label"] == "ORDINARY_FAILURE").all()
               and (~c3["all_pass"]).all()))
    prop = raw[raw["label"] == "PROPAGATED"]
    check("all PROPAGATED trials pass local contracts and strict order",
          bool(prop["all_pass"].all() and prop["ordered_events"].all()),
          f"n={len(prop)}")
    check("no PROPAGATED in C0/C3/C4",
          bool((prop["condition"] == None).sum() == 0
               and set(prop["condition"]) <= {"C1", "C2"}))
    check("no UNRESOLVED trials", bool((raw["label"] != "UNRESOLVED").all()))
    # statistics regenerate from frozen raw CSV alone, byte-identical
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ)
        script = os.path.join(WORK, "src", "analyze.py")
        # run analyze.py with OUT redirected via a copied workspace layout
        for sub in ("outputs",):
            os.makedirs(os.path.join(tmp, sub), exist_ok=True)
        for fn in ("raw_trials.csv", "trial_table.csv"):
            with open(os.path.join(OUT, fn), "rb") as fsrc:
                data = fsrc.read()
            with open(os.path.join(tmp, "outputs", fn), "wb") as fdst:
                fdst.write(data)
        code = ("import sys, os; sys.path.insert(0, r'%s'); "
                "import analyze; analyze.OUT = os.path.join(r'%s', 'outputs'); "
                "analyze.main()") % (os.path.join(WORK, "src"), tmp)
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True)
        regen_ok = r.returncode == 0
        for fn in ("descriptive_results.csv", "inferential_results.csv",
                   "outcome_classification.json"):
            a = sha(os.path.join(OUT, fn))
            b = sha(os.path.join(tmp, "outputs", fn))
            regen_ok &= (a == b)
        check("statistics regenerate byte-identically from frozen raw CSV",
              regen_ok, r.stderr[-200:] if r.returncode else "")
    for fn in ("F1_propagation_heatmap.pdf", "F2_aligned_traces.pdf",
               "F3_condition_rates.pdf", "F4_contract_and_rescue.pdf",
               "code_excerpt.pdf"):
        check(f"figure exists: {fn}",
              os.path.exists(os.path.join(WORK, "figures", fn)))
    with open(os.path.join(OUT, "outcome_classification.json")) as f:
        oc = json.load(f)
    check("frozen outcome classification present",
          oc["outcome"] in ("PILOT_SUPPORT", "CONTAINED", "ORDINARY_FAILURE",
                            "UNRESOLVED"), oc["outcome"])

    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"\n{len(RESULTS) - n_fail}/{len(RESULTS)} checks passed")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
