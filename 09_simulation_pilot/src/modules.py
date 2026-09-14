"""Locally valid modules: perception, planner, safety monitor, controller.

Design invariant (spec section 5): each module is only ever judged on the
values it actually receives. Perception accuracy is evaluated at the SAMPLE
timestamp, not at the consumption timestamp, so a delayed interface can leave
every local contract satisfied while the system acts on stale data.
"""
import bisect


class PerceptionModule:
    """Timestamped distance samples with configurable consumption delay.

    noise: pre-drawn noise array (common random numbers); one entry per sample,
    indexed in sample order so the same seed yields the same stream in every
    matched condition.
    """

    def __init__(self, cfg, noise):
        self.cfg = cfg
        self.noise = noise
        self.t_samples = []
        self.values = []

    def sample(self, t, true_gap, bias=0.0):
        k = len(self.t_samples)
        value = true_gap + bias + self.noise[k]
        self.t_samples.append(t)
        self.values.append(value)
        return value

    def latest_with_delay(self, t, delay_s):
        """Return (value, age, t_sample) of the newest ARRIVED sample, i.e. with
        t_sample <= t - delay_s. Returns None when no sample has arrived yet
        (t < delay at trial start): the monitor then has no data and does not
        evaluate — it neither triggers nor fabricates a fresh value."""
        cutoff = t - delay_s
        i = bisect.bisect_right(self.t_samples, cutoff + 1e-12) - 1
        if i < 0:
            return None
        ts = self.t_samples[i]
        return self.values[i], t - ts, ts


class PlannerModule:
    """Bounded approach planner: commands the preregistered approach speed
    after the mission start time, or 0 once the safety monitor has stopped it."""

    def __init__(self, cfg, approach_speed):
        self.cfg = cfg
        self.approach_speed = approach_speed

    def command(self, t, t_start, safety_stop):
        if safety_stop or t < t_start:
            return 0.0
        return self.approach_speed


class SafetyMonitor:
    """Rule-based monitor, evaluated on the values it actually receives:
    trigger when received_gap <= d_trigger(v), with
    d_trigger = d_safe + v^2 / (2 * max_decel) + safety_buffer + offset.

    rescue_c2 (shared-threshold contract check): when planner and monitor
    thresholds differ, both use the MORE CONSERVATIVE (larger) trigger
    distance, and the reconciliation event is logged.
    """

    def __init__(self, cfg, threshold_offset_m=0.0, rescue_c2=False):
        self.cfg = cfg
        self.offset = threshold_offset_m
        self.rescue_c2 = rescue_c2
        self.triggered = False
        self.trigger_time = None
        self.reconciliation_logged = bool(rescue_c2 and abs(threshold_offset_m) > 0.0)

    def nominal_trigger(self, v):
        return (self.cfg.dynamics["d_safe_m"]
                + v ** 2 / (2.0 * self.cfg.dynamics["max_decel_mps2"])
                + self.cfg.contracts["safety_buffer_m"])

    def effective_trigger(self, v):
        base = self.nominal_trigger(v)
        if self.rescue_c2:
            return max(base, base + self.offset)
        return base + self.offset

    def rule_fires(self, received_gap, v_current):
        return received_gap <= self.effective_trigger(v_current)

    def evaluate(self, received_gap, v_current, t=None):
        if not self.triggered and self.rule_fires(received_gap, v_current):
            self.triggered = True
            self.trigger_time = t
        return self.triggered


class Controller:
    """Acceleration/deceleration-limited tracker of the latest command."""

    def __init__(self, cfg):
        self.cfg = cfg

    def step(self, v_actual, v_cmd):
        dt = self.cfg.modules["controller_period_s"]
        dv = v_cmd - v_actual
        if dv > 0.0:
            dv = min(dv, self.cfg.dynamics["max_accel_mps2"] * dt)
        else:
            dv = max(dv, -self.cfg.dynamics["max_decel_mps2"] * dt)
        return max(0.0, v_actual + dv)
