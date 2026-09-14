"""One-dimensional approach/contact dynamics core.

Ground truth: surface-to-surface gap (m) and approach velocity v (m/s,
positive = closing). Semi-implicit Euler at the frozen step dt_s. Velocity is
clamped to [0, +inf): the robot never retreats in this model. Penetration
(gap < 0) is allowed so the synthetic contact model can quantify a
post-penetration proxy force; this force is a simulation variable only and is
never interpreted as human injury.
"""
from dataclasses import dataclass


@dataclass
class DynamicsState:
    t: float
    gap: float
    v: float


def step_dynamics(state: DynamicsState, v_cmd: float, cfg) -> DynamicsState:
    """Advance one step: accelerate v toward v_cmd within accel/decel limits,
    then advance the gap with the new velocity (semi-implicit Euler)."""
    dt = cfg.dynamics["dt_s"]
    dv = v_cmd - state.v
    if dv > 0.0:
        dv = min(dv, cfg.dynamics["max_accel_mps2"] * dt)
    else:
        dv = max(dv, -cfg.dynamics["max_decel_mps2"] * dt)
    v_new = max(0.0, state.v + dv)
    gap_new = state.gap - v_new * dt
    return DynamicsState(t=state.t + dt, gap=gap_new, v=v_new)


def contact_force(state: DynamicsState, cfg) -> float:
    """Synthetic Kelvin-Voigt proxy force (N). Simulation variable only."""
    if state.gap >= 0.0:
        return 0.0
    penetration = -state.gap
    return (cfg.dynamics["contact_stiffness_npm"] * penetration
            + cfg.dynamics["contact_damping_ns_per_m"] * max(state.v, 0.0))
