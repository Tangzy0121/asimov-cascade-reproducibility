"""Failing-first tests for perception/planner/safety/controller modules (Task 3)."""
import numpy as np

from config import load_config
from modules import PerceptionModule, PlannerModule, SafetyMonitor, Controller


def test_perception_accuracy_judged_at_sample_time_not_consumption_time():
    """A delayed sample can be stale at consumption yet contract-valid because
    it was accurate at its own sampling timestamp."""
    cfg = load_config()
    rng = np.random.default_rng(2000)
    noise = rng.normal(0.0, cfg.modules["perception_noise_sigma_m"], 201)
    p = PerceptionModule(cfg, noise)
    # sample at t=0.0 when the true gap is 0.50
    p.sample(t=0.0, true_gap=0.50, bias=0.0)
    # consumed at t=0.1 with a 100 ms delay while the true gap has moved to 0.40
    value, age, t_sample = p.latest_with_delay(t=0.1, delay_s=0.1)
    assert t_sample == 0.0
    assert abs(age - 0.1) < 1e-9
    # contract compares against the true gap at t_sample (0.50), not at t (0.40)
    assert abs(value - 0.50) <= cfg.contracts["perception_contract_abs_error_m"]


def test_perception_delay_selects_older_sample():
    cfg = load_config()
    noise = np.zeros(201)
    p = PerceptionModule(cfg, noise)
    for k in range(6):
        p.sample(t=k * 0.02, true_gap=0.8 - k * 0.01, bias=0.0)
    value, age, t_sample = p.latest_with_delay(t=0.10, delay_s=0.05)
    # newest sample with t_sample <= 0.10 - 0.05 = 0.05 -> sample at 0.04
    assert abs(t_sample - 0.04) < 1e-9


def test_planner_never_exceeds_speed_bound():
    cfg = load_config()
    pl = PlannerModule(cfg, approach_speed=0.45)
    assert pl.command(t=1.0, t_start=0.1, safety_stop=False) == 0.45
    assert pl.command(t=1.0, t_start=0.1, safety_stop=True) == 0.0
    assert pl.command(t=0.05, t_start=0.1, safety_stop=False) == 0.0


def test_safety_monitor_rule_on_received_values():
    cfg = load_config()
    mon = SafetyMonitor(cfg, threshold_offset_m=0.0)
    v = 0.45
    d_trig = (cfg.dynamics["d_safe_m"] + v ** 2 / (2 * cfg.dynamics["max_decel_mps2"])
              + cfg.contracts["safety_buffer_m"])
    # received gap just above trigger: no trigger
    assert mon.evaluate(received_gap=d_trig + 0.001, v_current=v) is False
    # received gap at/below trigger: trigger (latches)
    assert mon.evaluate(received_gap=d_trig - 0.001, v_current=v) is True
    # latched: stays triggered
    assert mon.evaluate(received_gap=d_trig + 5.0, v_current=v) is True


def test_safety_monitor_threshold_offset_shifts_trigger():
    cfg = load_config()
    v = 0.45
    base = (cfg.dynamics["d_safe_m"] + v ** 2 / (2 * cfg.dynamics["max_decel_mps2"])
            + cfg.contracts["safety_buffer_m"])
    mon_neg = SafetyMonitor(cfg, threshold_offset_m=-0.06)
    assert mon_neg.evaluate(received_gap=base - 0.03, v_current=v) is False
    mon_pos = SafetyMonitor(cfg, threshold_offset_m=0.06)
    assert mon_pos.evaluate(received_gap=base + 0.03, v_current=v) is True


def test_c2_rescue_uses_more_conservative_threshold():
    cfg = load_config()
    v = 0.45
    base = (cfg.dynamics["d_safe_m"] + v ** 2 / (2 * cfg.dynamics["max_decel_mps2"])
            + cfg.contracts["safety_buffer_m"])
    # offset -0.06: monitor would be LESS conservative; rescue pulls it back to nominal
    mon = SafetyMonitor(cfg, threshold_offset_m=-0.06, rescue_c2=True)
    assert abs(mon.effective_trigger(v) - base) < 1e-12
    assert mon.reconciliation_logged is True
    # offset +0.06: monitor is MORE conservative; rescue keeps monitor's
    mon2 = SafetyMonitor(cfg, threshold_offset_m=0.06, rescue_c2=True)
    assert abs(mon2.effective_trigger(v) - (base + 0.06)) < 1e-12


def test_controller_tracking_within_contract():
    cfg = load_config()
    c = Controller(cfg)
    v = 0.0
    for _ in range(200):
        v = c.step(v, v_cmd=0.45)
    assert abs(v - 0.45) <= cfg.contracts["controller_contract_abs_velocity_error_mps"]


def test_c3_fault_exceeds_perception_contract_by_construction():
    cfg = load_config()
    bias = cfg.c3_fault["perception_bias_m"]
    assert bias > cfg.contracts["perception_contract_abs_error_m"]
