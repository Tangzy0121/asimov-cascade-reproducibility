"""C0-only calibration (plan Task 5). Uses ONLY the frozen calibration seeds
(1000-1009) under condition C0. Checks numerical stability, controller
convergence, baseline margin non-negativity, and that the full approach phase
is observed (safety trigger fires before trial end at every speed).

Calibration may never inspect C1/C2 and may change only the numerical items
whitelisted by the calibration-change rule; any change requires a written
reason, a new configuration hash, and a full calibration restart.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from config import load_config
from simulator import run_trial

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "calibration")


def main():
    cfg = load_config()
    rows = []
    for speed in cfg.grids["approach_speed_mps"]:
        for seed in cfg.seeds["calibration_seeds"]:
            spec = {"condition": "C0", "speed": speed, "delay_ms": 0.0,
                    "offset_m": 0.0, "seed": seed, "rescue_c1": False,
                    "rescue_c2": False, "c3_fault": False}
            row, _ = run_trial(cfg, spec)
            rows.append(row)

    import pandas as pd
    df = pd.DataFrame(rows)
    os.makedirs(OUT_DIR, exist_ok=True)
    df.to_csv(os.path.join(OUT_DIR, "calibration_trials.csv"), index=False)

    checks = {
        "n_trials": int(len(df)),
        "all_local_contracts_pass": bool(df["all_pass"].all()),
        "no_numeric_unstable": bool((~df["nan_or_unstable"]).all()),
        "no_nan": bool((~df["nan_or_unstable"]).all()),
        "no_baseline_breach": bool((~df["margin_breach"]).all()),
        "min_margin_overall_m": float(df["min_margin_m"].min()),
        "trigger_fired_all_trials": bool(df["trigger_t_s"].notna().all()),
        "full_approach_observed": bool(
            (df["t_final_s"] < cfg.dynamics["trial_duration_s"] - 1e-9).all()),
        "per_speed": {
            str(s): {
                "min_margin_m": float(df.loc[df["speed_mps"] == s, "min_margin_m"].min()),
                "breaches": int(df.loc[df["speed_mps"] == s, "margin_breach"].sum()),
                "max_t_final_s": float(df.loc[df["speed_mps"] == s, "t_final_s"].max()),
                "trigger_missing": int(df.loc[df["speed_mps"] == s, "trigger_t_s"].isna().sum()),
            } for s in cfg.grids["approach_speed_mps"]
        },
        "config_sha256": cfg.sha256,
    }
    checks["baseline_valid"] = bool(
        checks["all_local_contracts_pass"] and checks["no_numeric_unstable"]
        and checks["no_nan"] and checks["no_baseline_breach"]
        and checks["trigger_fired_all_trials"]
        and checks["full_approach_observed"])
    with open(os.path.join(OUT_DIR, "calibration_checks.json"), "w") as f:
        json.dump(checks, f, indent=2)
    print(json.dumps(checks, indent=2))
    return checks


if __name__ == "__main__":
    main()
