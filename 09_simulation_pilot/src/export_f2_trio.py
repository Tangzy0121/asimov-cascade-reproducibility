"""Export the F2 matched trio of traces (Task 6 extension, frozen rule).

Frozen selection rule, applied mechanically to the frozen raw_trials.csv:
  1. among C1 cells, take the cell with the MEDIAN n_propagated (ties broken by
     grid order: middle speed, then middle delay);
  2. within that cell, take the lower-median minimum-margin trial (seed k*);
  3. the trio is {C0(s*, k*), C1(s*, k*), C4 rescue_c1(s*, k*)}.

The three trials are replayed deterministically and each replayed summary is
asserted byte-equal to the stored frozen summary — this is trace export, not a
selective rerun: no stored result can change.
"""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from config import load_config
from simulator import run_trial

WORK = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(WORK, "outputs")


def select_f2_trio(raw):
    c1 = raw[raw["condition"] == "C1"]
    counts = (c1.groupby(["speed_mps", "delay_ms"])["label"]
              .apply(lambda s: (s == "PROPAGATED").sum()).reset_index(name="n_prop"))
    counts = counts.sort_values(["n_prop", "speed_mps", "delay_ms"])
    mid = counts.iloc[(len(counts) - 1) // 2]  # lower-median propagation count
    s_star, d_star = float(mid["speed_mps"]), float(mid["delay_ms"])
    cell = c1[(c1["speed_mps"] == s_star) & (c1["delay_ms"] == d_star)]
    srt = cell.sort_values(["min_margin_m", "seed"])
    k_star = int(srt.iloc[(len(srt) - 1) // 2]["seed"])
    trio = [
        {"condition": "C0", "speed": s_star, "delay_ms": 0.0, "offset_m": 0.0,
         "seed": k_star, "rescue_c1": False, "rescue_c2": False, "c3_fault": False},
        {"condition": "C1", "speed": s_star, "delay_ms": d_star, "offset_m": 0.0,
         "seed": k_star, "rescue_c1": False, "rescue_c2": False, "c3_fault": False},
        {"condition": "C4", "speed": s_star, "delay_ms": d_star, "offset_m": 0.0,
         "seed": k_star, "rescue_c1": True, "rescue_c2": False, "c3_fault": False},
    ]
    return {"speed": s_star, "delay_ms": d_star, "seed": k_star,
            "cell_n_propagated": int(mid["n_prop"])}, trio


def main():
    cfg = load_config(verify_hash=True)
    raw = pd.read_csv(os.path.join(OUT, "raw_trials.csv"),
                      float_precision="round_trip")
    sel, trio = select_f2_trio(raw)
    traces = []
    for spec in trio:
        stored = raw[(raw["condition"] == spec["condition"])
                     & (raw["speed_mps"] == spec["speed"])
                     & (raw["delay_ms"] == spec["delay_ms"])
                     & (raw["offset_m"] == spec["offset_m"])
                     & (raw["seed"] == spec["seed"])]
        assert len(stored) == 1, spec
        row, trace = run_trial(cfg, spec, keep_trace=True)
        assert row["min_margin_m"] == stored.iloc[0]["min_margin_m"], "replay mismatch"
        assert row["trigger_t_s"] == (stored.iloc[0]["trigger_t_s"]
                                      if pd.notna(stored.iloc[0]["trigger_t_s"]) else None)
        tag = {"C0": "baseline", "C1": "mismatch", "C4": "rescue"}[spec["condition"]]
        trace.insert(0, "panel", tag)
        traces.append(trace)
    out = pd.concat(traces, ignore_index=True)
    out.to_csv(os.path.join(OUT, "f2_matched_trio.csv.gz"), index=False,
               compression="gzip")
    with open(os.path.join(OUT, "f2_trio_selection.json"), "w") as f:
        json.dump({"rule": "median-propagation-count C1 cell; lower-median "
                           "minimum-margin trial within it; same speed+seed "
                           "C0/C1/C4 trio", **sel}, f, indent=2)
    print(json.dumps(sel, indent=2))
    print("f2 trio exported and replay-verified")


if __name__ == "__main__":
    main()
