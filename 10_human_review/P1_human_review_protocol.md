# P1 Human Review Protocol — ASIMOV Cascade Subsystem Taxonomy & Interaction Graph

> **STATUS: AWAITING HUMAN REVIEW**
> Generated: 2026-07-24 (v3 — location-level evidence fix: per-location subsystem detection, same-excerpt co-occurrence requirement, actual mention extraction, patent binding enforcement)
> Input files: `topic_subsystem_review.csv`, `interaction_evidence_review.csv`, `topic_patent_evidence.csv`, `taxonomy.csv`, `mapping_rules.md`

---

## 1. Review Objectives

The human reviewer shall independently assess:

1. **Topic Safety** (in `P1_topic_safety_review_queue.csv`, 20 rows): Whether each BERTopic candidate genuinely concerns robot safety.
2. **Subsystem Assignment** (in `P1_topic_review_queue.csv`, 121 rows): Whether each proposed subsystem assignment is reasonable.
3. **Role Assignment**: Whether PRIMARY, SECONDARY, or CONTEXT_ONLY roles are justified by the evidence.
4. **Interaction Evidence**: Whether DIRECT_FLOW or CO_IMPLEMENTATION evidence genuinely supports the proposed relationship.

**This review does NOT modify:**
- BERTopic / STM / HMM / Cascade Score outputs
- Paper text or conclusions
- Existing provisional files (these remain untouched)

---

## 2. Queue File Overview

| File | Rows | Purpose |
|------|------|---------|
| `P1_topic_safety_review_queue.csv` | **20** | One row per BERTopic — safety judgment only |
| `P1_topic_review_queue.csv` | **121** | Topic × subsystem — subsystem + role review |
| `P1_direct_flow_review_queue.csv` | **1** | DIRECT_FLOW directional review |
| `P1_coimplementation_review_queue.csv` | **100** | CO_IMPLEMENTATION pair review (sorted by priority) |
| `P1_human_review_summary_TEMPLATE.md` | — | Blank summary template |

---

## 3. Decision Values

### 3.1 Topic Safety (`human_safety_judgment` — in topic safety queue only)

| Value | Definition |
|-------|-----------|
| `DIRECT` | Human protection, hazard reduction, safe control, fault response, collision prevention, stability protection, or another explicit safety mechanism is a principal technical function. |
| `PARTIAL` | A substantial part of the topic concerns safety, but the topic also mixes non-safety mechanisms. |
| `INCIDENTAL` | Safety language appears, but the claimed invention primarily serves performance, convenience, or mechanical design. |
| `NOT_SAFETY` | Representative evidence does not support a safety-mechanism interpretation. |
| `UNCLEAR` | Evidence is insufficient or internally inconsistent. |

### 3.1a Human Harm Link (`human_harm_link`)

Whether the topic's mechanism has a traceable link to human injury or harm. Part of the topic safety review queue only.

| Value | Definition |
|-------|-----------|
| `DIRECT` | Patent text explicitly describes a mechanism that can cause human injury (e.g., crushing fingers, collision impact). |
| `INDIRECT` | Injury is a plausible downstream consequence but not explicitly described in the patent (e.g., fall → impact on nearby person). |
| `NONE` | No plausible link to human injury can be established from the evidence. |
| `UNCLEAR` | Evidence is insufficient to determine harm linkage. |

### 3.1b Cascade Role (`cascade_role`)

The topic's position in the ASIMOV Cascade failure propagation chain. Part of the topic safety review queue only.

| Value | Definition |
|-------|-----------|
| `HAZARD_ENDPOINT` | The topic directly describes the physical hazard or injury outcome (the end of the cascade chain). |
| `PROPAGATION_NODE` | The topic describes an intermediate step that propagates errors or failures between subsystems. |
| `SAFETY_BARRIER` | The topic describes a mechanism that blocks, interrupts, or mitigates cascade propagation. |
| `CONTEXT_ONLY` | The topic provides background context but is not a cascade participant. |
| `OUT_OF_SCOPE` | The topic is outside the ASIMOV Cascade framework entirely. |
| `UNCLEAR` | Insufficient evidence to determine cascade role. |

### 3.1c Plausible Cascade Path (`plausible_cascade_path`)

A reviewer-proposed, testable mechanistic hypothesis describing how failures could propagate through the topic's subsystems to cause harm. **This is NOT a claim of proven causation** — it is a structured hypothesis to guide further investigation. Format: `subsystem_A → subsystem_B → ... → harm_outcome; conditions_that_enable_propagation; barriers_that_interrupt`.

### 3.1d Scope Limitation (`scope_limitation`)

Known boundary conditions or limitations of the topic's evidence. Examples: non-humanoid robot patents, indirect injury inference, mixed topic composition, domain mismatch. Used to qualify confidence and identify evidence gaps.

### 3.2 Subsystem Decision (`human_subsystem_decision`)

| Value | Definition |
|-------|-----------|
| `ACCEPT` | The proposed subsystem assignment is correct based on the evidence. |
| `REMOVE` | The subsystem should be removed — evidence does not support it. |
| `ADD` | A subsystem not currently proposed should be added. (Specify in `reviewer_note`.) |
| `UNCLEAR` | Cannot decide from the provided evidence alone. |

### 3.3 Role Judgment (`human_role_judgment`)

| Value | Definition |
|-------|-----------|
| `PRIMARY` | The subsystem is a principal focus of the patent claims or abstract. |
| `SECONDARY` | The subsystem appears in the claims or abstract but plays a supporting role. |
| `CONTEXT_ONLY` | Mentioned in the patent body but not essential to the claimed invention. |
| `REJECT` | No evidence supports any involvement of this subsystem. |

### 3.4 DIRECT_FLOW Interaction Decision (`human_interaction_decision`)

| Value | Definition |
|-------|-----------|
| `ACCEPT_DIRECTION` | The directed flow is correct as proposed. |
| `REVERSE_DIRECTION` | The flow exists but in the opposite direction. |
| `CO_IMPLEMENTATION_ONLY` | The subsystems co-occur but no directional flow is justified. |
| `REJECT` | The interaction is not supported by the evidence. |
| `UNCLEAR` | Cannot decide from the provided evidence alone. |

### 3.5 CO_IMPLEMENTATION Decision (`human_coimplementation_decision`)

| Value | Definition |
|-------|-----------|
| `ACCEPT_CO_IMPLEMENTATION` | The two subsystems genuinely co-occur in the same patent mechanism — accept as undirected co-implementation. |
| `UPGRADE_DIRECT_FLOW_SOURCE_TO_TARGET` | Evidence supports upgrading to a directed flow: source → target. |
| `UPGRADE_DIRECT_FLOW_TARGET_TO_SOURCE` | Evidence supports upgrading to a directed flow: target → source. |
| `REJECT` | The co-implementation is not supported by the evidence. |
| `UNCLEAR` | Cannot decide from the provided evidence alone. |

### 3.6 Strength Judgment (`human_strength_judgment`)

| Value | Definition |
|-------|-----------|
| `STRONG` | At least 2 independent patent publications provide DIRECT_FLOW, or 1 DIRECT_FLOW + 1 COORDINATION_REQUIREMENT standard. |
| `MODERATE` | 1 DIRECT_FLOW patent, or ≥2 CO_IMPLEMENTATION patents + 1 supporting standard. |
| `WEAK` | Co-implementation, co-occurrence, or semantic evidence without a direct flow. |
| `INSUFFICIENT` | No traceable cross-subsystem evidence. |

### 3.7 Evidence Status (automated, not for human fill)

| Value | Definition |
|-------|-----------|
| `FOUND` | Patent evidence found at the specified `evidence_location` (CLAIM/ABSTRACT/TITLE) — the excerpt at that location contains the target subsystem(s). CO_IMPLEMENTATION requires BOTH subsystems in the SAME excerpt. |
| `INSUFFICIENT` | No single patent excerpt at any location contains the required subsystem(s). For PRIMARY/SECONDARY rows and CO_IMPLEMENTATION, this means the evidence must be sought from the original patent full text. |
| `NO_DIRECT_EVIDENCE` | No direct patent evidence expected (CONTEXT_ONLY rows only). |

**Location priority**: CLAIM > ABSTRACT > TITLE. A CLAIM excerpt is only returned if the target subsystem IS detected in that CLAIM. If the subsystem only appears in the ABSTRACT, the evidence_location is ABSTRACT, not CLAIM. This prevents location-level evidence mismatches.

---

## 4. CN201020717Y Data Anomaly

**Patent CN201020717Y** is the sole DIRECT_FLOW evidence (MOTION_CONTROL → ACTUATION_MECHANICS).

- **Claim text** supports the directional flow: "joint controller adopts single chip machine to control scheduled movement of leg joint electric motor according to movement data delivered by main body"
- **Abstract/title** are inconsistent with the robot safety domain — the patent's abstract describes a general-purpose leg mechanism, not specifically a safety-critical robot subsystem interaction.
- **source_integrity_flag** is set to `ABSTRACT_CLAIM_MISMATCH` in the DIRECT_FLOW queue.
- **Reviewer action**: Before confirming this edge, verify the original patent record (CN201020717Y) to confirm the claim-abstract discrepancy does not invalidate the evidence.

**This edge MUST NOT be auto-marked as human-confirmed.**

---

## 5. Review Principles

1. **Evidence-only**: Decisions must be based solely on the provided `exact_evidence_excerpt` and `evidence_patent_number`. Do not infer from topic names or BERTopic embeddings.
2. **Standards ≠ Patent Evidence**: Standards clauses (ISO, IEC) supplement but do not replace patent evidence. A standards clause alone cannot establish a DIRECT_FLOW — it needs corroborating patent text.
3. **When Uncertain, Say UNCLEAR**: If the provided excerpt is insufficient to make a confident judgment, choose `UNCLEAR`. Do not guess.
4. **No Auto-Fill**: Every `human_*` and `reviewer_*` field starts empty. The reviewer fills them manually.
5. **evidence_status=INSUFFICIENT**: Rows with this flag require the reviewer to consult the original patent documents (by `supporting_patent_numbers`) to find supporting evidence. The automated system could not locate a matching excerpt.
6. **Preserve Original Patent Context**: When an excerpt seems ambiguous, consult the original patent document before making a final decision.

---

## 6. Review Workflow

### Step 1: Topic Safety Review
Open `P1_topic_safety_review_queue.csv` (20 rows).
1. Read `safety_rationale` and `supporting_patent_numbers`.
2. Fill `human_safety_judgment` for each topic.
3. Set `reviewer_confidence` (HIGH / MEDIUM / LOW).

### Step 2: Subsystem & Role Review
Open `P1_topic_review_queue.csv` (121 rows).
1. Check `evidence_status` — prioritize rows marked `INSUFFICIENT` (need patent lookup).
2. For `FOUND` rows: read `exact_evidence_excerpt` — does it support `proposed_role`?
3. Fill `human_subsystem_decision` and `human_role_judgment`.

### Step 3: DIRECT_FLOW Review
Open `P1_direct_flow_review_queue.csv` (1 row).
1. Note `source_integrity_flag=ABSTRACT_CLAIM_MISMATCH`.
2. Verify the claim text supports MOTION_CONTROL → ACTUATION_MECHANICS.
3. Fill `human_interaction_decision` and `human_strength_judgment`.

### Step 4: CO_IMPLEMENTATION Review
Open `P1_coimplementation_review_queue.csv` (100 rows). Review in priority order.
1. Priority 1 first (SAFETY_MONITORING / EMERGENCY_FAILSAFE).
2. Check `evidence_status` — `INSUFFICIENT` rows need patent lookup.
3. For `FOUND` rows: verify both subsystems appear in `exact_evidence_excerpt`.
4. Fill `human_coimplementation_decision` using the unified enum.

### Step 5: Complete Summary
Fill `P1_human_review_summary_TEMPLATE.md`.

---

## 7. Subsystem Taxonomy Reference

| Subsystem ID | Name | Definition |
|-------------|------|-----------|
| PERCEPTION | Perception and sensing | Sensors or algorithms acquire environmental, human, contact, force, vision, proximity, or obstacle observations. |
| STATE_ESTIMATION | State estimation and world modelling | Observations are fused or interpreted into robot, human, or environment state. |
| PLANNING_DECISION | Planning and decision | Goals, paths, tasks, behaviours, priorities, or action sequences are selected. |
| MOTION_CONTROL | Motion and force control | Desired actions are converted into trajectories, torques, velocities, impedance, balance, or feedback-control commands. |
| ACTUATION_MECHANICS | Actuation and mechanics | Motors, joints, transmissions, limbs, end effectors, brakes, or mechanical structures physically execute or constrain motion. |
| SAFETY_MONITORING | Safety monitoring and protective control | Hazards, limits, separation, collisions, instability, or safety states are monitored and protective constraints are applied. |
| EMERGENCY_FAILSAFE | Emergency and fail-safe response | Emergency stop, safe stop, power isolation, fallback, redundancy, fault containment, or recovery is triggered. |
| HRI_INTERFACE | Human-robot interaction and operator interface | Human intent, commands, communication, physical collaboration, warnings, or operator interaction affects behaviour. |
| SYSTEM_INTEGRATION | System integration and communication | Middleware, arbitration, communication, timing, mode management, shared state, or subsystem priority resolution coordinates modules. |

---

> **All human-review fields are empty. No decisions have been pre-filled.**
> **No final, confirmed, or validated graphs have been generated.**
