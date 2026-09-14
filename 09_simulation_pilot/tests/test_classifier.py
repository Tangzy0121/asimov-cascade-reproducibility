"""Failing-first tests for the frozen event classifier (Task 4)."""
import numpy as np
import pandas as pd

from config import load_config
from classify import classify_trial


def _base_trace(n=1000, dt=0.002):
    t = np.arange(n) * dt
    return pd.DataFrame({
        "t": t,
        "gap": np.full(n, 0.5),
        "v": np.full(n, 0.3),
        "v_cmd": np.full(n, 0.3),
        "monitor_triggered": np.zeros(n, dtype=bool),
        "mismatch_present": np.zeros(n, dtype=bool),
        "perception_abs_error_at_sample": np.full(n, 0.001),
        "planner_v_cmd": np.full(n, 0.3),
        "monitor_rule_ok": np.ones(n, dtype=bool),
        "controller_abs_vel_error": np.full(n, 0.01),
        "dropout": np.zeros(n, dtype=bool),
        "nan": np.zeros(n, dtype=bool),
        "oob_command": np.zeros(n, dtype=bool),
        "numeric_unstable": np.zeros(n, dtype=bool),
        "contact_force": np.zeros(n),
    })


def _make_propagated_trace():
    """mismatch from t=0; baseline trigger at 1.000 s; actual trigger at
    1.200 s; positive command during the delay; margin breach from 1.300 s."""
    tr = _base_trace()
    cfg = load_config()
    tr["mismatch_present"] = tr["t"] >= 0.0
    tr["monitor_triggered"] = tr["t"] >= 1.200
    breach = tr["t"] >= 1.300
    tr.loc[breach, "gap"] = cfg.dynamics["d_safe_m"] - 0.02  # margin < 0 sustained
    return tr


def test_propagated_label_requires_full_ordered_chain():
    cfg = load_config()
    tr = _make_propagated_trace()
    res = classify_trial(tr, cfg, baseline_trigger_t=1.000)
    assert res.label == "PROPAGATED"
    assert res.local_pass is True
    assert res.ordered_events is True
    assert res.margin_breach is True
    assert abs(res.trigger_t - 1.200) < 1e-9
    assert abs(res.breach_start_t - 1.300) < 1e-9


def test_local_contract_failure_forbids_propagated():
    cfg = load_config()
    tr = _make_propagated_trace()
    tr["perception_abs_error_at_sample"] = 0.08  # C3-style fault
    res = classify_trial(tr, cfg, baseline_trigger_t=1.000)
    assert res.label == "ORDINARY_FAILURE"
    assert res.local_pass is False


def test_no_breach_is_contained_not_propagated():
    cfg = load_config()
    tr = _base_trace()
    tr["mismatch_present"] = True
    tr["monitor_triggered"] = tr["t"] >= 1.2
    res = classify_trial(tr, cfg, baseline_trigger_t=1.0)
    assert res.label == "CONTAINED"
    assert res.margin_breach is False


def test_breach_without_delay_order_is_not_propagated():
    cfg = load_config()
    tr = _make_propagated_trace()
    # trigger EARLIER than the matched baseline -> event order broken
    tr["monitor_triggered"] = tr["t"] >= 0.900
    res = classify_trial(tr, cfg, baseline_trigger_t=1.000)
    assert res.label != "PROPAGATED"
    assert res.margin_breach is True
    assert res.ordered_events is False


def test_breach_without_positive_command_during_delay_is_not_propagated():
    cfg = load_config()
    tr = _make_propagated_trace()
    delay_window = (tr["t"] > 1.000) & (tr["t"] <= 1.200)
    tr.loc[delay_window, "v_cmd"] = 0.0
    res = classify_trial(tr, cfg, baseline_trigger_t=1.000)
    assert res.label != "PROPAGATED"


def test_nan_flags_yield_unresolved():
    cfg = load_config()
    tr = _make_propagated_trace()
    tr.loc[tr.index[5], "nan"] = True
    res = classify_trial(tr, cfg, baseline_trigger_t=1.000)
    assert res.label == "UNRESOLVED"


def test_short_margin_dip_is_not_a_breach():
    cfg = load_config()
    tr = _make_propagated_trace()
    # only 2 steps (4 ms) below zero: shorter than the 10 ms minimum
    tr["gap"] = cfg.dynamics["d_safe_m"] + 0.05
    dip = (tr["t"] >= 1.300) & (tr["t"] < 1.304)
    tr.loc[dip, "gap"] = cfg.dynamics["d_safe_m"] - 0.02
    res = classify_trial(tr, cfg, baseline_trigger_t=1.000)
    assert res.margin_breach is False
    assert res.label == "CONTAINED"
