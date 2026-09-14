"""Trial simulator: event-scheduled module loop over the dynamics core.

Timing design (documented operational constants, not tuned):
- NOMINAL_COMMAND_START_S: mission approach command starts at 0.10 s plus the
  frozen +/-0.02 s command_start_jitter (paired seed variation).
- C3_FAULT_TRIGGER_GAP_M: the C3 +0.08 m perception bias is injected when the
  true gap first drops to/below 0.35 m, lasting the frozen 0.25 s.

Common random numbers: make_rng_streams(seed) draws, in a fixed order, the
initial gap jitter, the command start jitter, and the full perception noise
array. The same seed therefore reproduces identical physical variation and
noise in every matched condition cell.

The monitor/planner/controller chain: the safety monitor latches a stop; the
planner then commands v=0 at its next tick; the controller ramps its setpoint
within the accel/decel limits; physics integrates at dt_s. All module
correctness checks and event extraction reuse contracts.py and classify.py so
tests and production share one code path.
"""
import math

import numpy as np
import pandas as pd

from classify import decide_label, extract_events
from contracts import evaluate_local_contracts
from dynamics import DynamicsState, contact_force, step_dynamics
from modules import Controller, PerceptionModule, PlannerModule, SafetyMonitor

NOMINAL_COMMAND_START_S = 0.10
C3_FAULT_TRIGGER_GAP_M = 0.35


def make_rng_streams(seed, cfg):
    """Fixed-order draws so identical seeds give identical streams everywhere."""
    rng = np.random.default_rng(seed)
    d = cfg.dynamics
    initial_gap = d["initial_true_gap_m"] + rng.uniform(
        -d["initial_gap_jitter_m"], d["initial_gap_jitter_m"])
    t_start = NOMINAL_COMMAND_START_S + rng.uniform(
        -d["command_start_jitter_s"], d["command_start_jitter_s"])
    n_max = int(math.ceil(d["trial_duration_s"] / cfg.modules["perception_period_s"])) + 2
    noise = rng.normal(0.0, cfg.modules["perception_noise_sigma_m"], n_max)
    return {"initial_gap": float(initial_gap), "t_start": float(t_start),
            "noise": noise}


def run_trial(cfg, spec, baseline_trigger_t=None, keep_trace=False):
    """Run one trial. spec keys: condition, speed, delay_ms, offset_m, seed,
    rescue_c1, rescue_c2, c3_fault. Returns (row: dict, trace: DataFrame|None).
    """
    streams = make_rng_streams(spec["seed"], cfg)
    speed = spec["speed"]
    delay_s = spec["delay_ms"] / 1000.0
    offset = spec["offset_m"]
    rescue_c1 = bool(spec.get("rescue_c1", False))
    rescue_c2 = bool(spec.get("rescue_c2", False))
    c3_fault = bool(spec.get("c3_fault", False))
    mismatch_configured = (delay_s > 0.0) or (abs(offset) > 0.0)

    per = PerceptionModule(cfg, streams["noise"])
    planner = PlannerModule(cfg, speed)
    monitor = SafetyMonitor(cfg, threshold_offset_m=offset, rescue_c2=rescue_c2)
    controller = Controller(cfg)
    state = DynamicsState(t=0.0, gap=streams["initial_gap"], v=0.0)

    dt = cfg.dynamics["dt_s"]
    duration = cfg.dynamics["trial_duration_s"]
    n_steps = int(round(duration / dt))
    p_per = cfg.modules["perception_period_s"]
    p_pl = cfg.modules["planner_period_s"]
    p_mon = cfg.modules["safety_period_s"]
    p_ctl = cfg.modules["controller_period_s"]
    age_gate_s = cfg.c4_rescue["c1_age_gate_ms"] / 1000.0
    bias_mag = cfg.c3_fault["perception_bias_m"]
    bias_dur = cfg.c3_fault["bias_duration_s"]

    next_per = next_pl = next_mon = next_ctl = 0.0
    v_cmd = v_set = 0.0
    last_recv_gap = float("nan")
    last_age = float("nan")
    sample_err = 0.0
    ctl_err = 0.0
    rule_ok = True
    numeric_unstable = False
    fault_start = None
    gate_violations = 0
    first_gate_violation_t = None
    t_mismatch = None

    rec = {k: [] for k in (
        "t", "gap", "v", "v_cmd", "v_set", "monitor_triggered",
        "mismatch_present", "received_gap", "sample_age",
        "perception_abs_error_at_sample", "planner_v_cmd", "monitor_rule_ok",
        "controller_abs_vel_error", "dropout", "nan", "oob_command",
        "numeric_unstable", "contact_force")}

    for _ in range(n_steps):
        t = state.t
        # --- module ticks in fixed order: perception, safety, planner, controller
        if t >= next_per - 1e-9:
            bias = 0.0
            if c3_fault:
                if fault_start is None and state.gap <= C3_FAULT_TRIGGER_GAP_M:
                    fault_start = t
                if fault_start is not None and t < fault_start + bias_dur - 1e-12:
                    bias = bias_mag
            value = per.sample(next_per, state.gap, bias=bias)
            sample_err = abs(value - state.gap)
            next_per += p_per
        if t >= next_mon - 1e-9:
            res = per.latest_with_delay(t, delay_s)
            if res is not None:
                recv, age, _ts = res
                last_recv_gap, last_age = recv, age
                gate_violation = bool(rescue_c1 and age > age_gate_s + 1e-12)
                if gate_violation:
                    gate_violations += 1
                    if first_gate_violation_t is None:
                        first_gate_violation_t = t
                before = monitor.triggered
                fires = monitor.rule_fires(recv, state.v)
                monitor.evaluate(recv, state.v, t=t)
                if gate_violation and not monitor.triggered:
                    monitor.triggered = True
                    monitor.trigger_time = t
                rule_ok = bool(monitor.triggered == (before or fires or gate_violation))
                if mismatch_configured and t_mismatch is None:
                    t_mismatch = t
            next_mon += p_mon
        if t >= next_pl - 1e-9:
            v_cmd = planner.command(t, streams["t_start"], monitor.triggered)
            next_pl += p_pl
        if t >= next_ctl - 1e-9:
            v_set = controller.step(v_set, v_cmd)
            ctl_err = abs(state.v - v_set)
            next_ctl += p_ctl

        state = step_dynamics(state, v_set, cfg)
        force = contact_force(state, cfg)
        if not (math.isfinite(state.gap) and math.isfinite(state.v)):
            numeric_unstable = True

        rec["t"].append(state.t)
        rec["gap"].append(state.gap)
        rec["v"].append(state.v)
        rec["v_cmd"].append(v_cmd)
        rec["v_set"].append(v_set)
        rec["monitor_triggered"].append(bool(monitor.triggered))
        rec["mismatch_present"].append(bool(t_mismatch is not None))
        rec["received_gap"].append(last_recv_gap)
        rec["sample_age"].append(last_age)
        rec["perception_abs_error_at_sample"].append(sample_err)
        rec["planner_v_cmd"].append(v_cmd)
        rec["monitor_rule_ok"].append(rule_ok)
        rec["controller_abs_vel_error"].append(ctl_err)
        rec["dropout"].append(False)
        rec["nan"].append(numeric_unstable)
        rec["oob_command"].append(bool(v_cmd < 0.0 or v_cmd > speed + 1e-12))
        rec["numeric_unstable"].append(numeric_unstable)
        rec["contact_force"].append(force)

        if numeric_unstable:
            break
        if monitor.triggered and state.v < 1e-4 and v_set < 1e-4:
            break

    trace = pd.DataFrame(rec)
    contracts = evaluate_local_contracts(trace, cfg, speed)
    events = extract_events(trace, cfg)
    result = decide_label(events, contracts["all_pass"], baseline_trigger_t, cfg)

    row = {
        "condition": spec["condition"], "speed_mps": speed,
        "delay_ms": spec["delay_ms"], "offset_m": offset, "seed": spec["seed"],
        "rescue_c1": rescue_c1, "rescue_c2": rescue_c2, "c3_fault": c3_fault,
        "config_sha256": cfg.sha256,
        "initial_gap_m": streams["initial_gap"], "t_start_s": streams["t_start"],
        **contracts,
        "nan_or_unstable": bool(events["nan_or_unstable"]),
        "label": result.label, "ordered_events": result.ordered_events,
        "margin_breach": result.margin_breach,
        "t_mismatch_s": result.t_mismatch, "trigger_t_s": result.trigger_t,
        "breach_start_t_s": result.breach_start_t,
        "positive_cmd_during_delay": result.positive_cmd_during_delay,
        "pos_cmd_runs_json": repr(events["pos_cmd_runs"]),
        "min_margin_m": float(trace["gap"].min() - cfg.dynamics["d_safe_m"]),
        "peak_contact_force_n": float(trace["contact_force"].max()),
        "gate_violations": gate_violations,
        "first_gate_violation_t_s": first_gate_violation_t,
        "reconciliation_logged": bool(monitor.reconciliation_logged),
        "c3_fault_start_t_s": fault_start,
        "t_final_s": float(trace["t"].iloc[-1]),
    }
    return row, (trace if keep_trace else None)
