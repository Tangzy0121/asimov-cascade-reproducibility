"""Failing-first tests for the simulator: determinism, common random numbers,
and trace/classifier consistency (Tasks 5-6)."""
import numpy as np

from config import load_config
from simulator import make_rng_streams, run_trial
from classify import classify_trial

C0_SPEC = {"condition": "C0", "speed": 0.30, "delay_ms": 0.0, "offset_m": 0.0,
           "seed": 2000, "rescue_c1": False, "rescue_c2": False, "c3_fault": False}
C1_SPEC = {"condition": "C1", "speed": 0.45, "delay_ms": 100.0, "offset_m": 0.0,
           "seed": 2001, "rescue_c1": False, "rescue_c2": False, "c3_fault": False}
C4_SPEC = {"condition": "C4", "speed": 0.45, "delay_ms": 100.0, "offset_m": 0.0,
           "seed": 2001, "rescue_c1": True, "rescue_c2": False, "c3_fault": False}
C3_SPEC = {"condition": "C3", "speed": 0.45, "delay_ms": 0.0, "offset_m": 0.0,
           "seed": 2002, "rescue_c1": False, "rescue_c2": False, "c3_fault": True}


def test_rng_streams_identical_across_conditions_for_same_seed():
    cfg = load_config()
    a = make_rng_streams(2000, cfg)
    b = make_rng_streams(2000, cfg)
    assert a["initial_gap"] == b["initial_gap"]
    assert a["t_start"] == b["t_start"]
    assert np.array_equal(a["noise"], b["noise"])


def test_trial_is_deterministic():
    cfg = load_config()
    r1, _ = run_trial(cfg, C1_SPEC)
    r2, _ = run_trial(cfg, C1_SPEC)
    for k in ("min_margin_m", "peak_contact_force_n", "trigger_t_s", "breach_start_t_s"):
        x, y = r1[k], r2[k]
        if x is None or (isinstance(x, float) and np.isnan(x)):
            assert y is None or (isinstance(y, float) and np.isnan(y))
        else:
            assert x == y


def test_trace_classifier_agrees_with_event_path():
    """The summary label computed from extracted events must equal the label
    computed by classify_trial on the full trace (single source of truth)."""
    cfg = load_config()
    row, trace = run_trial(cfg, C1_SPEC, keep_trace=True)
    assert trace is not None
    # matched C0 baseline trigger for the same speed+seed family
    base_spec = dict(C1_SPEC, condition="C0", delay_ms=0.0)
    base_row, _ = run_trial(cfg, base_spec)
    from classify import extract_events, decide_label
    from contracts import evaluate_local_contracts
    events = extract_events(trace, cfg)
    contracts = evaluate_local_contracts(trace, cfg, C1_SPEC["speed"])
    via_events = decide_label(events, contracts["all_pass"],
                              base_row["trigger_t_s"], cfg)
    via_trace = classify_trial(trace, cfg, baseline_trigger_t=base_row["trigger_t_s"],
                               approach_speed=C1_SPEC["speed"])
    assert via_events.label == via_trace.label


def test_c3_trial_fails_perception_contract():
    cfg = load_config()
    row, _ = run_trial(cfg, C3_SPEC)
    assert row["perception_ok"] is False
    assert row["all_pass"] is False


def test_c0_baseline_does_not_breach():
    cfg = load_config()
    row, _ = run_trial(cfg, C0_SPEC)
    assert row["all_pass"] is True
    assert row["margin_breach"] is False


def test_c4_rescue_contains_matched_c1():
    cfg = load_config()
    row, _ = run_trial(cfg, C4_SPEC)
    assert row["margin_breach"] is False
