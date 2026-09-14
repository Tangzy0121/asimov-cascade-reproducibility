# Calibration decision record

## Calibration run 1 — 2026-09-02T03:55:59Z (config hash 99e784f7…9580)

C0-only, seeds 1000–1009, 3 speeds, 30 trials, config exactly as preregistered.

**Findings:**
- All local contracts passed; no NaN/instability; zero baseline breaches at every speed.
- Minimum baseline margin: +0.0092 m (overall), +0.0157 m at 0.15 m/s.
- **Failure:** at 0.15 m/s, 2/10 trials never reached the safety trigger within
  `trial_duration_s = 4.0` (`full_approach_observed = false`). The approach phase
  is truncated for the slowest speed.

**Permitted change applied (calibration-change rule, "trial duration to a larger value"):**
- `trial_duration_s: 4.0 → 8.0`.
- Reason: observe the full approach phase at 0.15 m/s. No other parameter touched;
  `d_safe`, grids, contracts, event ordering, breach duration, and classification
  rules unchanged.
- New configuration hash generated; calibration restarted from scratch.

No C1/C2 cell was run or inspected at any point during calibration.
