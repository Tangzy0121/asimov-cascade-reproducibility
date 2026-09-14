"""Local contract evaluation (spec section 8, 'local contracts pass').

All five contracts must hold simultaneously:
 1. perception error vs its OWN sampling timestamp within tolerance;
 2. planner speed never exceeds the bound;
 3. safety monitor triggered exactly per rule on the values it received;
 4. controller tracking error within tolerance;
 5. no dropout / NaN / out-of-bounds command / numerical instability.

A trial-level local-contract failure forbids the PROPAGATED label.
"""

_FAULT_FLAG_COLUMNS = ("dropout", "nan", "oob_command", "numeric_unstable")


def evaluate_local_contracts(trace, cfg, approach_speed):
    eps = 1e-12
    perception_ok = bool(
        (trace["perception_abs_error_at_sample"]
         <= cfg.contracts["perception_contract_abs_error_m"] + eps).all())
    planner_ok = bool(
        (trace["planner_v_cmd"] <= approach_speed + eps).all()
        and (trace["planner_v_cmd"] >= -eps).all())
    monitor_ok = bool(trace["monitor_rule_ok"].all())
    controller_ok = bool(
        (trace["controller_abs_vel_error"]
         <= cfg.contracts["controller_contract_abs_velocity_error_mps"] + eps).all())
    no_fault_flags = not any(bool(trace[c].any()) for c in _FAULT_FLAG_COLUMNS)
    return {
        "perception_ok": perception_ok,
        "planner_ok": planner_ok,
        "monitor_ok": monitor_ok,
        "controller_ok": controller_ok,
        "no_fault_flags": no_fault_flags,
        "all_pass": (perception_ok and planner_ok and monitor_ok
                     and controller_ok and no_fault_flags),
    }
