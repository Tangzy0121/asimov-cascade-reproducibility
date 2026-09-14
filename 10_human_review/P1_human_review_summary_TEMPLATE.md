# P1 Human Review Summary

> **Fill this template after completing all review queues.**
> Do NOT fill before review.

---

## Review Metadata

- **Review date:** _______________
- **Reviewer:** _______________
- **Review duration (hours):** _______________
- **Provisional data generated:** 2026-07-24

---

## Topic Safety Review (20 topics)

| Judgment | Count |
|----------|-------|
| DIRECT (accepted) | __ |
| DIRECT (changed from proposal) | __ |
| PARTIAL (accepted) | __ |
| PARTIAL (changed from proposal) | __ |
| INCIDENTAL (changed from DIRECT/PARTIAL) | __ |
| NOT_SAFETY (accepted) | __ |
| NOT_SAFETY (changed from proposal) | __ |
| UNCLEAR | __ |
| **Total** | **20** |

---

## Subsystem Assignment Review (121 rows)

| Subsystem | ACCEPT | REMOVE | ADD | UNCLEAR |
|-----------|--------|--------|-----|---------|
| PERCEPTION | __ | __ | __ | __ |
| STATE_ESTIMATION | __ | __ | __ | __ |
| PLANNING_DECISION | __ | __ | __ | __ |
| MOTION_CONTROL | __ | __ | __ | __ |
| ACTUATION_MECHANICS | __ | __ | __ | __ |
| SAFETY_MONITORING | __ | __ | __ | __ |
| EMERGENCY_FAILSAFE | __ | __ | __ | __ |
| HRI_INTERFACE | __ | __ | __ | __ |
| SYSTEM_INTEGRATION | __ | __ | __ | __ |

---

## Role Review (121 rows)

| Role | ACCEPT | Changed to PRIMARY | Changed to SECONDARY | Changed to CONTEXT_ONLY | REJECT |
|------|--------|--------------------|-----------------------|--------------------------|--------|
| Count | __ | __ | __ | __ | __ |

---

## DIRECT_FLOW Review (1 row)

| Decision | Count |
|----------|-------|
| ACCEPT_DIRECTION | __ |
| REVERSE_DIRECTION | __ |
| CO_IMPLEMENTATION_ONLY | __ |
| REJECT | __ |
| UNCLEAR | __ |
| **Total** | **1** |

### DIRECT_FLOW Details

| Evidence ID | Source → Target | Patent | source_integrity_flag | Decision | Notes |
|-------------|-----------------|--------|-----------------------|----------|-------|
| 0\|CN201020717Y\|MOTION_CONTROL\|ACTUATION_MECHANICS\|15 | MOTION_CONTROL → ACTUATION_MECHANICS | CN201020717Y | ABSTRACT_CLAIM_MISMATCH | (fill) | (fill) |

---

## CO_IMPLEMENTATION Review (100 rows)

| Decision | Count |
|----------|-------|
| ACCEPT_CO_IMPLEMENTATION | __ |
| UPGRADE_DIRECT_FLOW_SOURCE_TO_TARGET | __ |
| UPGRADE_DIRECT_FLOW_TARGET_TO_SOURCE | __ |
| REJECT | __ |
| UNCLEAR | __ |
| **Total** | **100** |

---

## Disagreements and UNCLEAR Items

List all rows where:
- `reviewer_confidence` is LOW
- Decision is UNCLEAR
- Decision disagrees with proposal

| Queue | Row Identifier | Issue | Resolution Needed |
|-------|---------------|-------|-------------------|
| (fill) | (fill) | (fill) | (fill) |

---

## Gate Decision

- [ ] **All reviews complete** — human-confirmed graph may be generated
- [ ] **Reviews incomplete** — do NOT generate human-confirmed graph

If checked "complete", the human-confirmed graph generation script may be run.
Otherwise, the provisional graph remains the latest output and no `human_confirmed` or `final` graph shall be generated.

---

## Unresolved Questions

1. ___________________________________________
2. ___________________________________________
3. ___________________________________________

---

## Sign-off

- **Reviewer signature:** _______________
- **Date:** _______________
- **Second reviewer (if required):** _______________
