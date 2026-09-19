# AUDIT REPORT — Topic 22 Controlled Propagation Simulation

Date: 2026-09-02 | Execution environment: `<python>/envs/<env>/python.exe` (Python 3.12.13, Windows 11)

## 1. Final Outcome Classification

**PILOT_SUPPORT** (`outputs/outcome_classification.json`, determined mechanically by frozen rules, not hand-picked)

Determination evidence:
- C0 baseline is valid: no breaches in the full 150/150 formal runs, all local contracts passed; calibration (seeds 1000–1009) passed 30/30;
- Supporting speed tiers: 0.30 m/s (all three adjacent delays 50/75/100 ms show BH q<0.05 and RD 95% CI lower bound = 1.00 > 0) and 0.45 m/s (the adjacent delays 25/50/75/100 ms likewise satisfy the criteria); at 0.15 m/s only the single point at 150 ms is significant, which does not meet the adjacency requirement;
- All 518 PROPAGATED trials pass the local contracts (100%) and 100% satisfy the strict event ordering (requirement ≥90%).

## 2. Trial and Data Integrity

- Exactly 3300 formal trials: C0=150, C1=900, C2=600, C3=150, C4=1500; 66 cells × 50 seeds, with seeds 2000–2049 reused across conditions (common random numbers: same seed gives the same initial gap, the same noise stream, and the same command jitter).
- The trial table was generated and saved before the first simulation: `outputs/trial_table.csv` (SHA-256 `526dc9b8…130d4`); the execution order was randomized with the administrative seed 9001.
- Results were written incrementally, line by line, to `outputs/raw_results.jsonl` (resumable after interruption); labels were computed in a second pass using the frozen `classify.decide_label`.
- No seed was dropped, no selective reruns, and no results were hidden; the deterministic replays in phases 3/4 (66 representatives + 14 fixed subsets) all matched the original results bit for bit.

## 3. Deviations from the Preregistration (All Registered)

1. **trial_duration_s 4.0 → 8.0** (an item explicitly permitted by the calibration rules). Reason: in the 0.15 m/s tier, 2/10 calibration trials did not observe a complete approach segment within 4.0 s. The written justification is in `outputs/calibration/calibration_decision.md`; after the change, the configuration hash was regenerated (`99e784f7…` → `0bf3f035…`) and calibration was restarted from scratch. No other parameter was changed; d_safe, the grid, the contracts, the event ordering, the breach duration, and the classification rules were all left untouched.
2. **Figures delivered as vector PDF rather than PNG** (per an explicit instruction in this round: "figures should be vector graphics; deliver PDF instead of PNG"). All five figures were delivered as PDF, with no PNG artifacts (the PNGs under `logs/fig_preview/` are quality-check previews only, not deliverables). The scientific content requirements for the figures (dimensions, units, font sizes, colorblind-friendliness, panel labels, captions, no overstated causality) are unchanged.
3. Runtime defect fixes (changing neither any produced result nor any definition): a `trial_id` index-column bug (the first run crashed before executing any trial, so no data was produced); `pd.read_json`/`read_csv` floating-point parsing precision (`precise_float=True`/`round_trip`) — after the fix, the raw CSV was recomputed exactly from the original jsonl, with the label distribution unchanged; F3 figure yerr non-negativity clipping and legend placement (purely presentational).

## 4. Operational Definitions (Design Decisions, Fixed and Recorded in Code and Figure Captions)

- Nominal command onset time 0.10 s (with the frozen ±0.02 s jitter superimposed); the C3 +0.08 m bias is injected when the true gap first falls to ≤0.35 m and lasts 0.25 s.
- When no arrival sample exists (t < delay), the monitor neither evaluates nor triggers (no data is fabricated).
- Breach determination: margin < 0 sustained for ≥10 ms, with closing speed at the crossing moment ≥0.05 m/s.
- Stop delay = actual trigger time − trigger time of the matched C0 trial with the same speed and same seed.
- Representative trajectories: within each cell, the lower median of the minimum safety margin (ties broken by seed); the F2 triple: the C1 cell with the median propagation count → within it, the trial with the lower-median margin → the C0/C1/C4 trials with the same speed and same seed. The selected result is (0.45 m/s, 200 ms, seed 2029); that trial's label is BREACH_UNORDERED (under a large delay the breach precedes the delayed trigger), which the F2 caption states truthfully.
- Administrative seeds (not experimental factors): execution order 9001, bootstrap 9101.

## 5. Main Results (All Recomputable from the Frozen `outputs/raw_trials.csv`, Byte-Identical)

| Condition | n | PROPAGATED | CONTAINED | BREACH_UNORDERED | ORDINARY_FAILURE |
|---|---:|---:|---:|---:|---:|
| C0 | 150 | 0 | 150 | 0 | 0 |
| C1 | 900 | 369 (41.0%, Wilson 95% CI 37.8–44.2%) | 287 | 244 | 0 |
| C2 | 600 | 149 (24.8%, 21.5–28.4%) | 300 | 151 | 0 |
| C3 | 150 | 0 | 0 | 0 | 150 |
| C4 | 1500 | 0 (CI upper bound 0.26%) | 1500 | 0 | 0 |

- C1: 18 paired exact McNemar tests + BH; C2: 12 independent families + BH; paired risk differences + seed-level bootstrap CIs: see `outputs/inferential_results.csv`; Fisher's exact test is included only as an unpaired sensitivity analysis (column `fisher_p_sensitivity` in the same table).
- Delay–response trends (Cochran–Armitage): 0.15 m/s Z=+6.71 (p=1.9×10⁻¹¹); 0.30 m/s Z=−1.34 (p=0.18); 0.45 m/s Z=−4.68 (p=2.8×10⁻⁶). **Non-monotonic**: propagation concentrates in the intermediate delay range; under large delays the breach precedes the delayed trigger, violating the strict ordering and being counted as BREACH_UNORDERED. The trend itself is not offered as causal proof.
- Synthetic contact force: 0 N across all 3300 trials (minimum gap 0.1175 m > 0; no surface penetration occurred). This variable is a simulation quantity only and carries no injury interpretation.
- Repair effect: in every cell where the parent condition exhibited propagation, the C4 paired repair eliminated all propagation (RD = parent-condition rate, CI lower bound > 0); C4 overall 0/1500.

## 6. Compliance Confirmation

- All writes were confined to `work/`; the upstream project, the existing paper, and the PPT were untouched.
- Calibration used only C0 + seeds 1000–1009; calibration and formal seeds are disjoint; formal trials and inspection of C1/C2 began only after the hash was frozen.
- PyBullet/MuJoCo were not installed; the main experiment is the lightweight state-space model specified in the plan.
- TDD evidence (fail-first-then-pass) is preserved in full in `logs/tests.log`; the final clean-process run of the full suite passed 33/33.
- `src/verify_package.py` passed 20/20 in a clean process: 3300 unique trials, complete cells, no missing/duplicate seeds, correct hashes, statistics recomputable byte-identically from the frozen raw CSV, all five figures present, and classification conforming to the frozen rules.
- The forbidden-wording list is explicitly given in `page19_result_payload.md` §8.

## 7. Key Hashes

- Frozen configuration `config/preregistered.yaml`: `0bf3f0351d8e1622160b94b835b555fc6ffc44b79a077c2a4b6276e96c8d55e9`
- Trial table `outputs/trial_table.csv`: `526dc9b8a3e654b3c4bfe0facb562696c9a7cfad2d83a610623f657c76e130d4`
- Raw results `outputs/raw_trials.csv`: `39a733141082f6a8b7e677d2b74d18159001431157cb56a292c15a884dd70897`
- Hashes of all artifacts: `final_manifest.json`

## 8. Conclusion Wording

The only permitted, data-supported statement:
> "In a controlled simulation, a bounded interface mismatch produced ordered and repeatable safety-margin erosion while the modeled local contracts remained satisfied."

This experiment constitutes no evidence about real humanoid robots, accident prediction, or injury risk.
