"""Frozen event classifier (spec section 8; do not modify after freeze).

A trial is PROPAGATED only when ALL of the following hold, in strict temporal
order, with every local contract passing:
  1. the preregistered interface mismatch is present (t_mismatch);
  2. the safety trigger is delayed relative to the speed/seed-matched C0
     baseline (trigger_t > baseline_trigger_t);
  3. positive (approach) control output persists during that delay window;
  4. a global safety-margin breach follows (margin < 0 sustained for at least
     margin_breach_min_duration_s, with approach speed >= the frozen minimum
     at the crossing);
  5. all local contracts pass.

Any local-contract failure forbids PROPAGATED. A breach without the strict
event order is never counted as propagation. C3-style faults are always
ORDINARY_FAILURE, however large their effect.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np

from contracts import evaluate_local_contracts


@dataclass
class TrialClassification:
    label: str                      # PROPAGATED / CONTAINED / ORDINARY_FAILURE / BREACH_UNORDERED / UNRESOLVED
    local_pass: bool
    ordered_events: bool
    margin_breach: bool
    t_mismatch: Optional[float]
    baseline_trigger_t: Optional[float]
    trigger_t: Optional[float]
    breach_start_t: Optional[float]
    positive_cmd_during_delay: bool
    stop_latency_s: Optional[float]  # trigger_t - baseline_trigger_t


def find_breach_start(t, gap, v, cfg):
    """First start of a continuous margin<0 run spanning at least
    margin_breach_min_duration_s, with approach speed >= the frozen minimum at
    the crossing. Returns None if no such run exists."""
    margin = np.asarray(gap) - cfg.dynamics["d_safe_m"]
    below = margin < 0.0
    dt = cfg.dynamics["dt_s"]
    n_consec = int(round(cfg.contracts["margin_breach_min_duration_s"] / dt)) + 1
    v_min = cfg.contracts["approach_velocity_min_for_breach_mps"]
    v = np.asarray(v)
    idx = np.flatnonzero(below)
    if len(idx) < n_consec:
        return None
    i = idx[0]
    while i < len(below):
        if not below[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(below) and below[j + 1]:
            j += 1
        # run is [i, j]; need span >= min_duration and approach at crossing
        if (t[j] - t[i]) >= cfg.contracts["margin_breach_min_duration_s"] - 1e-12 \
                and v[i] >= v_min:
            return float(t[i])
        i = j + 1
    return None


def extract_events(trace, cfg):
    """Extract the frozen event quantities from a trace. Single source of
    truth shared by classify_trial (tests) and the experiment runner."""
    t = np.asarray(trace["t"])
    mismatch_idx = np.flatnonzero(np.asarray(trace["mismatch_present"]))
    trig_idx = np.flatnonzero(np.asarray(trace["monitor_triggered"]))
    pos = np.asarray(trace["v_cmd"]) > 1e-9
    pos_idx = np.flatnonzero(pos)
    # exact list of positive-command runs [(start_t, end_t), ...]; a run may be
    # interrupted (e.g. command withdrawn mid-delay), which the frozen order
    # rule must see through — a single (first,last) interval would not.
    pos_runs = []
    if len(pos_idx):
        run_start = pos_idx[0]
        for a, b in zip(pos_idx[:-1], pos_idx[1:]):
            if b != a + 1:
                pos_runs.append((float(t[run_start]), float(t[a])))
                run_start = b
        pos_runs.append((float(t[run_start]), float(t[pos_idx[-1]])))
    return {
        "t_mismatch": float(t[mismatch_idx[0]]) if len(mismatch_idx) else None,
        "trigger_t": float(t[trig_idx[0]]) if len(trig_idx) else None,
        "breach_start_t": find_breach_start(t, trace["gap"], trace["v"], cfg),
        "pos_cmd_runs": pos_runs,
        "nan_or_unstable": bool(trace["nan"].any() or trace["numeric_unstable"].any()),
    }


def decide_label(events, local_pass, baseline_trigger_t, cfg):
    """Pure frozen decision logic. events: dict from extract_events."""
    eps = 1e-9
    trigger_t = events["trigger_t"]
    breach_start_t = events["breach_start_t"]
    margin_breach = breach_start_t is not None
    delayed = (baseline_trigger_t is not None and trigger_t is not None
               and trigger_t > baseline_trigger_t + eps)
    if delayed:
        lo, hi = baseline_trigger_t + eps, trigger_t + eps
        positive_cmd = any(start <= hi and end >= lo
                           for start, end in events["pos_cmd_runs"])
    else:
        positive_cmd = False
    ordered = bool(
        events["t_mismatch"] is not None and delayed and positive_cmd
        and margin_breach and trigger_t <= breach_start_t + eps
        and events["t_mismatch"] <= baseline_trigger_t + eps)

    if events["nan_or_unstable"]:
        label = "UNRESOLVED"
    elif not local_pass:
        label = "ORDINARY_FAILURE"
    elif margin_breach and ordered:
        label = "PROPAGATED"
    elif margin_breach:
        label = "BREACH_UNORDERED"
    else:
        label = "CONTAINED"
    stop_latency = (trigger_t - baseline_trigger_t
                    if (trigger_t is not None and baseline_trigger_t is not None)
                    else None)
    return TrialClassification(
        label=label, local_pass=local_pass, ordered_events=ordered,
        margin_breach=margin_breach, t_mismatch=events["t_mismatch"],
        baseline_trigger_t=baseline_trigger_t, trigger_t=trigger_t,
        breach_start_t=breach_start_t,
        positive_cmd_during_delay=positive_cmd, stop_latency_s=stop_latency)


def classify_trial(trace, cfg, baseline_trigger_t=None, approach_speed=None):
    if approach_speed is None:
        approach_speed = float(np.max(trace["planner_v_cmd"]))
    contracts = evaluate_local_contracts(trace, cfg, approach_speed)
    events = extract_events(trace, cfg)
    return decide_label(events, contracts["all_pass"], baseline_trigger_t, cfg)
