"""Failing-first tests for local contract evaluation (Task 3)."""
import numpy as np
import pandas as pd

from config import load_config
from contracts import evaluate_local_contracts


def _trace(perr=0.001, vmax_cmd=0.45, monitor_ok=True, ctrk=0.01, clean=True):
    n = 100
    d = {
        "perception_abs_error_at_sample": np.full(n, perr),
        "planner_v_cmd": np.full(n, vmax_cmd),
        "monitor_rule_ok": np.full(n, monitor_ok),
        "controller_abs_vel_error": np.full(n, ctrk),
        "dropout": np.full(n, not clean),
        "nan": np.full(n, not clean),
        "oob_command": np.full(n, not clean),
        "numeric_unstable": np.full(n, not clean),
    }
    return pd.DataFrame(d)


def test_all_contracts_pass_on_clean_trace():
    cfg = load_config()
    res = evaluate_local_contracts(_trace(), cfg, approach_speed=0.45)
    assert res["all_pass"] is True
    assert all(res[k] for k in (
        "perception_ok", "planner_ok", "monitor_ok", "controller_ok", "no_fault_flags"))


def test_perception_contract_failure_detected():
    cfg = load_config()
    res = evaluate_local_contracts(_trace(perr=0.08), cfg, approach_speed=0.45)
    assert res["perception_ok"] is False
    assert res["all_pass"] is False


def test_planner_speed_violation_detected():
    cfg = load_config()
    res = evaluate_local_contracts(_trace(vmax_cmd=0.50), cfg, approach_speed=0.45)
    assert res["planner_ok"] is False


def test_monitor_rule_violation_detected():
    cfg = load_config()
    res = evaluate_local_contracts(_trace(monitor_ok=False), cfg, approach_speed=0.45)
    assert res["monitor_ok"] is False


def test_controller_tracking_violation_detected():
    cfg = load_config()
    res = evaluate_local_contracts(_trace(ctrk=0.05), cfg, approach_speed=0.45)
    assert res["controller_ok"] is False


def test_fault_flags_fail_contract():
    cfg = load_config()
    res = evaluate_local_contracts(_trace(clean=False), cfg, approach_speed=0.45)
    assert res["no_fault_flags"] is False
    assert res["all_pass"] is False
