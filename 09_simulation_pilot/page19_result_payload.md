# Result Payload — Topic 22 Controlled Propagation Simulation

## 1. Suggested title

**"Controlled propagation pilot: bounded interface mismatch erodes safety margin while local contracts hold (1-D simulation)"**

## 2. Status label

**PILOT RESULTS**

(Based on `outputs/outcome_classification.json`: outcome = `PILOT_SUPPORT`; frozen rules triggered: the C0 baseline is valid; each of the two speed levels, 0.30 and 0.45 m/s, contains ≥2 adjacent non-zero delay cells satisfying the BH-corrected exact McNemar q<0.05 with the lower bound of the paired risk-difference 95% CI > 0; local contracts passed in all 518 propagation trials, with 100% satisfying the strict event-order rule.)

## 3. Three key numbers ready for the slides

| # | Number | Meaning |
|---|--------|---------|
| 1 | **41.0% (369/900, Wilson 95% CI 37.8–44.2%)** | Propagation rate satisfying the strict event-order rule under the C1 timestamp-delay condition; peak cell 0.30 m/s × 75 ms reached 50/50 (RD=1.00 [1.00, 1.00], BH q=6.4×10⁻¹⁵) |
| 2 | **24.8% (149/600, Wilson 95% CI 21.5–28.4%)** | Propagation rate under the C2 threshold-offset condition; peak cell 0.45 m/s × −0.03 m reached 50/50 (RD=1.00 [1.00, 1.00], BH q=1.1×10⁻¹⁴) |
| 3 | **0/1500 (Wilson 95% CI upper bound 0.26%)** | Number of propagations after the C4 matching fix (25 ms timestamp-age gate + shared-threshold contract check); for every cell where propagation had occurred, the post-fix paired risk difference equals the parent-condition rate with CI lower bound > 0 |

Guardrail numbers (if needed): C0 baseline 150/150 all safe (minimum margin +0.0075 m); C3 component failure 150/150 all classified as ordinary component failures, 0 counted as propagation; synthetic contact force is 0 N in all 3300 trials (the d_safe threshold is breached but no surface contact occurs).

## 4. Provenance of the numbers (result tables and cells)

- Number 1: aggregated from `outputs/raw_trials.csv` (condition=C1, label=PROPAGATED); cell-level values in `outputs/descriptive_results.csv` (rows with condition=C1: `n_propagated`/`n`/`wilson_lo`/`wilson_hi`); peak-cell test in `outputs/inferential_results.csv` row `family=C1, kind=c1_vs_c0, speed_mps=0.30, delay_ms=75.0` (b=50, mcnemar_p=1.78×10⁻¹⁵, bh_q=6.39×10⁻¹⁵, risk_diff=1.00, rd_ci=[1.00,1.00]).
- Number 2: `outputs/inferential_results.csv` row `family=C2, kind=c2_vs_c0, speed_mps=0.45, offset_m=-0.03` (b=50, bh_q=1.07×10⁻¹⁴, risk_diff=1.00 [1.00,1.00]); aggregate rate computed from `descriptive_results.csv` (condition=C2).
- Number 3: counted from `outputs/raw_trials.csv` (condition=C4); paired post-fix effects in `outputs/inferential_results.csv` under `family=C4` (e.g. `rescue_c1, speed 0.45, delay 75 ms`: b=50, c=0, RD=1.00 [1.00,1.00]).

## 5. One-sentence main conclusion

"In a controlled simulation, a bounded interface mismatch produced ordered and repeatable safety-margin erosion while the modeled local contracts remained satisfied."

(Approved wording, supported by the data: propagation is concentrated in the intermediate-delay region — at 0.30 m/s the 50–100 ms cells and at 0.45 m/s the 25–150 ms cells, where each adjacent cell passes the frozen significance criteria.)

## 6. One-sentence limitation statement

This is a preregistered 1-D state-space simulation pilot of an interface mechanism only: the delay–response is non-monotone (at the largest delays the margin breach begins before the delayed trigger, so those breaches fail the strict event-order rule and are reported as unordered breaches, not propagation), the synthetic contact force is a simulation variable with no injury interpretation, and nothing here is evidence about real humanoid robots.

## 7. Recommended figure panels for the slides

- First choice: `figures/F1_propagation_heatmap.pdf` (speed × delay propagation heatmap with per-cell counts, making the structure of "propagation in the intermediate-delay region turning into unordered breaches at large delays" directly visible)
- Second choice: `figures/F3_condition_rates.pdf` (event rates for the five conditions + Wilson CI, including the note that C3 ordinary failures are excluded)
- Backup: `figures/F4_contract_and_rescue.pdf` (local-contract pass rate + paired forest plot of the fix effect)
- If space allows: `figures/F2_aligned_traces.pdf` (matched-triple trajectories; note that the mismatch panel was selected by the frozen median rule from BREACH_UNORDERED trials, and the caption states this faithfully)
- `figures/code_excerpt.pdf` serves as a traceability appendix only, not as evidence.

## 8. Statements that must not be used (prohibited)

- "Topic 22 proves an Asimov Cascade in real humanoid robots."
- "The patent trend predicts accidents."
- "The simulation validates injury risk."
- "No propagation was observed, therefore cascades do not exist." (This result does not support that sentence either — controlled propagation was observed, but reverse-inferring real-world accidents is likewise prohibited.)
- "Real-robot experiments have already been completed."
- "It has been proven that human injuries will occur in the real world."
- Any statement that converts the synthetic contact force into human-injury probabilities; any statement that treats Topic 25 as a same-scenario physical control; any characterization that goes beyond "controlled simulation pilot / mechanistic propagation test".
