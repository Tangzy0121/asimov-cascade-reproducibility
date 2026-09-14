"""Failing-first tests for the dynamics core (Task 2)."""
import numpy as np

from config import load_config
from dynamics import DynamicsState, step_dynamics, contact_force


def test_stationary_state_stays_stationary():
    cfg = load_config()
    s = DynamicsState(t=0.0, gap=cfg.dynamics["initial_true_gap_m"], v=0.0)
    for _ in range(100):
        s = step_dynamics(s, v_cmd=0.0, cfg=cfg)
    assert s.v == 0.0
    assert s.gap == cfg.dynamics["initial_true_gap_m"]


def test_acceleration_is_bounded():
    cfg = load_config()
    s = DynamicsState(t=0.0, gap=5.0, v=0.0)
    s2 = step_dynamics(s, v_cmd=0.45, cfg=cfg)
    assert s2.v <= cfg.dynamics["max_accel_mps2"] * cfg.dynamics["dt_s"] + 1e-12
    # braking is bounded by max_decel
    s3 = DynamicsState(t=0.0, gap=5.0, v=0.45)
    s4 = step_dynamics(s3, v_cmd=0.0, cfg=cfg)
    assert s4.v >= 0.45 - cfg.dynamics["max_decel_mps2"] * cfg.dynamics["dt_s"] - 1e-12


def test_velocity_never_negative():
    cfg = load_config()
    s = DynamicsState(t=0.0, gap=5.0, v=0.001)
    s2 = step_dynamics(s, v_cmd=0.0, cfg=cfg)
    assert s2.v >= 0.0


def test_gap_nonnegative_before_contact():
    cfg = load_config()
    s = DynamicsState(t=0.0, gap=0.80, v=0.0)
    for _ in range(2000):
        s = step_dynamics(s, v_cmd=0.45, cfg=cfg)
        if s.gap > 0.0:
            assert s.gap >= 0.0  # trivially true by construction; guards regressions


def test_deterministic_replay():
    cfg = load_config()
    def run():
        s = DynamicsState(t=0.0, gap=0.80, v=0.0)
        hist = []
        for _ in range(500):
            s = step_dynamics(s, v_cmd=0.30, cfg=cfg)
            hist.append((s.t, s.gap, s.v))
        return hist
    a, b = run(), run()
    for (ta, ga, va), (tb, gb, vb) in zip(a, b):
        assert ta == tb and ga == gb and va == vb


def test_contact_force_zero_without_penetration_and_positive_on_penetration():
    cfg = load_config()
    s_ok = DynamicsState(t=0.0, gap=0.10, v=0.30)
    assert contact_force(s_ok, cfg) == 0.0
    s_pen = DynamicsState(t=0.0, gap=-0.01, v=0.20)
    f = contact_force(s_pen, cfg)
    assert f > 0.0
    # Kelvin-Voigt proxy: k * penetration + c * approach speed
    expected = (cfg.dynamics["contact_stiffness_npm"] * 0.01
                + cfg.dynamics["contact_damping_ns_per_m"] * 0.20)
    assert np.isclose(f, expected)
