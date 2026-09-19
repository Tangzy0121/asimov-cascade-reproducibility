"""
Generate P1 human review package from provisional outputs.
Reads topic_subsystem_review.csv and interaction_evidence_review.csv,
creates 5 review-package files in the same directory.
"""
import csv
import os
import re
from collections import defaultdict

BASE = r"<project>/<pipeline>\output\subsystem_validation"
OUT = os.path.join(BASE, "human_review")

# --- helpers ---

def parse_semicolon(s):
    """Split semicolon-separated string, strip whitespace, drop empties."""
    if not s or not str(s).strip():
        return []
    return [x.strip() for x in str(s).split(";") if x.strip()]

def parse_role_map(role_str):
    """'PERCEPTION:SECONDARY;MOTION_CONTROL:PRIMARY' -> {subsys: role}"""
    m = {}
    for part in parse_semicolon(role_str):
        if ":" in part:
            k, v = part.split(":", 1)
            m[k.strip()] = v.strip()
    return m

def parse_excerpts_by_subsystem(excerpts_str):
    """Parse '[SUBSYS] text | [SUBSYS] text' into {subsys: [excerpts]}."""
    result = defaultdict(list)
    if not excerpts_str or not str(excerpts_str).strip():
        return result
    text = str(excerpts_str)
    # Split on ' | [' pattern (space-pipe-space followed by opening bracket)
    # But first, normalize: the separator between subsystem blocks is " | ["
    # Replace " | [" with a unique delimiter
    parts = re.split(r'\s*\|\s*(?=\[)', text)
    for part in parts:
        part = part.strip()
        m = re.match(r'\[([A-Z_]+)\]\s*(.*)', part, re.DOTALL)
        if m:
            subsys = m.group(1)
            excerpt = m.group(2).strip()
            # Clean up leading newlines and extra whitespace
            excerpt = re.sub(r'\s+', ' ', excerpt).strip()
            if excerpt:
                result[subsys].append(excerpt)
    return result

def subsystem_priority(subsys, roles):
    """Get sort priority for a CO_IMPLEMENTATION edge."""
    src, tgt = subsys
    src_role = roles.get(src, "")
    tgt_role = roles.get(tgt, "")

    # Priority 1: involves SAFETY_MONITORING or EMERGENCY_FAILSAFE
    if src in ("SAFETY_MONITORING", "EMERGENCY_FAILSAFE") or \
       tgt in ("SAFETY_MONITORING", "EMERGENCY_FAILSAFE"):
        return 1
    # Priority 2: both PRIMARY
    if src_role == "PRIMARY" and tgt_role == "PRIMARY":
        return 2
    # Priority 3: PRIMARY-SECONDARY (either direction)
    roles_set = {src_role, tgt_role}
    if "PRIMARY" in roles_set and "SECONDARY" in roles_set:
        return 3
    # Priority 4: everything else
    return 4

# ============================================================
# 1. Load data
# ============================================================

# Load topic_subsystem_review.csv
topic_rows = []
with open(os.path.join(BASE, "topic_subsystem_review.csv"), "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        topic_rows.append(row)

# Load interaction_evidence_review.csv
interaction_rows = []
with open(os.path.join(BASE, "interaction_evidence_review.csv"), "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        interaction_rows.append(row)

# Build topic->role map for priority sorting
topic_role_map = {}
for row in topic_rows:
    tid = row["bertopic_id"]
    topic_role_map[tid] = parse_role_map(row.get("role_proposal", ""))

# Build topic->excerpts map
topic_excerpt_map = {}
for row in topic_rows:
    tid = row["bertopic_id"]
    topic_excerpt_map[tid] = parse_excerpts_by_subsystem(row.get("subsystem_evidence_excerpts", ""))

print(f"Loaded {len(topic_rows)} topic rows, {len(interaction_rows)} interaction rows")

# ============================================================
# 2. P1_human_review_protocol.md
# ============================================================

protocol_md = r"""# P1 Human Review Protocol — ASIMOV Cascade Subsystem Taxonomy & Interaction Graph

> **STATUS: AWAITING HUMAN REVIEW**
> Generated: 2026-07-24
> Input files: `topic_subsystem_review.csv`, `interaction_evidence_review.csv`, `topic_patent_evidence.csv`, `taxonomy.csv`, `mapping_rules.md`

---

## 1. Review Objectives

The human reviewer shall independently assess:

1. **Topic Safety**: Whether each of the 20 BERTopic candidates genuinely concerns robot safety, using only the provided patent excerpts and original patent numbers.
2. **Subsystem Assignment**: Whether each proposed subsystem assignment is reasonable given the patent evidence.
3. **Role Assignment**: Whether PRIMARY, SECONDARY, or CONTEXT_ONLY roles are justified by the evidence.
4. **Interaction Evidence**: Whether cross-subsystem evidence (DIRECT_FLOW or CO_IMPLEMENTATION) genuinely supports the proposed relationship.

**This review does NOT modify:**
- BERTopic / STM / HMM / Cascade Score outputs
- Paper text or conclusions
- Existing provisional files (these remain untouched)

---

## 2. Decision Values

### 2.1 Topic Safety (`human_safety_judgment`)

| Value | Definition |
|-------|-----------|
| `DIRECT` | Human protection, hazard reduction, safe control, fault response, collision prevention, stability protection, or another explicit safety mechanism is a principal technical function. |
| `PARTIAL` | A substantial part of the topic concerns safety, but the topic also mixes non-safety mechanisms. |
| `INCIDENTAL` | Safety language appears, but the claimed invention primarily serves performance, convenience, or mechanical design. |
| `NOT_SAFETY` | Representative evidence does not support a safety-mechanism interpretation. |
| `UNCLEAR` | Evidence is insufficient or internally inconsistent. |

### 2.2 Subsystem Decision (`human_subsystem_decision`)

| Value | Definition |
|-------|-----------|
| `ACCEPT` | The proposed subsystem assignment is correct based on the evidence. |
| `REMOVE` | The subsystem should be removed — evidence does not support it. |
| `ADD` | A subsystem not currently proposed should be added. (Specify in `reviewer_note`.) |
| `UNCLEAR` | Cannot decide from the provided evidence alone. |

### 2.3 Role Judgment (`human_role_judgment`)

| Value | Definition |
|-------|-----------|
| `PRIMARY` | The subsystem is a principal focus of the patent claims or abstract. |
| `SECONDARY` | The subsystem appears in the claims or abstract but plays a supporting role. |
| `CONTEXT_ONLY` | Mentioned in the patent body but not essential to the claimed invention. |
| `REJECT` | No evidence supports any involvement of this subsystem. |

### 2.4 Interaction Decision (`human_interaction_decision` / `human_coimplementation_decision`)

| Value | Definition |
|-------|-----------|
| `ACCEPT_DIRECTION` | The directed flow is correct as proposed. |
| `REVERSE_DIRECTION` | The flow exists but in the opposite direction. |
| `CO_IMPLEMENTATION_ONLY` | The subsystems co-occur but no directional flow is justified. |
| `REJECT` | The interaction is not supported by the evidence. |
| `UNCLEAR` | Cannot decide from the provided evidence alone. |

### 2.5 Strength Judgment (`human_strength_judgment`)

| Value | Definition |
|-------|-----------|
| `STRONG` | At least 2 independent patent publications provide DIRECT_FLOW, or 1 DIRECT_FLOW + 1 COORDINATION_REQUIREMENT standard. |
| `MODERATE` | 1 DIRECT_FLOW patent, or ≥2 CO_IMPLEMENTATION patents + 1 supporting standard. |
| `WEAK` | Co-implementation, co-occurrence, or semantic evidence without a direct flow. |
| `INSUFFICIENT` | No traceable cross-subsystem evidence. |

---

## 3. Review Principles

1. **Evidence-only**: Decisions must be based solely on the provided `evidence_excerpt`, `exact_evidence_excerpt`, or `claim_or_abstract_evidence` fields and the original patent numbers. Do not infer from topic names or BERTopic embeddings.
2. **Standards ≠ Patent Evidence**: Standards clauses (ISO, IEC) supplement but do not replace patent evidence. A standards clause alone cannot establish a DIRECT_FLOW — it needs corroborating patent text.
3. **When Uncertain, Say UNCLEAR**: If the provided excerpt is insufficient to make a confident judgment, choose `UNCLEAR`. Do not guess.
4. **No Auto-Fill**: Every `human_*` and `reviewer_*` field in the queue CSVs starts empty. The reviewer fills them manually. No automated system may populate these fields.
5. **Preserve Original Patent Context**: When an excerpt seems ambiguous, consult the original patent document (by patent number) before making a final decision. The excerpt alone may be a truncated fragment.

---

## 4. Review Workflow

### Step 1: Topic Safety & Subsystem Review
Open `P1_topic_review_queue.csv`. For each row (topic × subsystem):
1. Read `evidence_excerpt` — does it support the proposed subsystem role?
2. Fill `human_safety_judgment`, `human_subsystem_decision`, `human_role_judgment`.
3. Set `reviewer_confidence` (HIGH / MEDIUM / LOW).
4. Add notes in `reviewer_note` if needed.

### Step 2: DIRECT_FLOW Review
Open `P1_direct_flow_review_queue.csv`. For each row:
1. Read `exact_evidence_excerpt` — does the source subsystem's output genuinely flow to the target?
2. Check `source_mention` and `target_mention` are correctly identified.
3. Fill `human_interaction_decision` and `human_strength_judgment`.

### Step 3: CO_IMPLEMENTATION Review
Open `P1_coimplementation_review_queue.csv`. Review in priority order:
1. Priority 1 rows first (involving SAFETY_MONITORING or EMERGENCY_FAILSAFE).
2. Verify that both subsystems genuinely appear in the same patent text.
3. Fill `human_coimplementation_decision`.

### Step 4: Complete Summary
Fill `P1_human_review_summary_TEMPLATE.md` with final counts, decisions, and unresolved items.

---

## 5. Subsystem Taxonomy Reference

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

## 6. File Index

| File | Description |
|------|-------------|
| `P1_human_review_protocol.md` | This document — review instructions and decision values |
| `P1_topic_review_queue.csv` | Topic × subsystem rows for safety + role review |
| `P1_direct_flow_review_queue.csv` | DIRECT_FLOW evidence rows for directional review |
| `P1_coimplementation_review_queue.csv` | CO_IMPLEMENTATION pairs sorted by review priority |
| `P1_human_review_summary_TEMPLATE.md` | Blank summary template to fill after review |

> **All human-review fields are empty. No decisions have been pre-filled.**
> **No final, confirmed, or validated graphs have been generated.**
"""

with open(os.path.join(OUT, "P1_human_review_protocol.md"), "w", encoding="utf-8") as f:
    f.write(protocol_md)
print("Created P1_human_review_protocol.md")

# ============================================================
# 3. P1_topic_review_queue.csv
# ============================================================

queue_rows = []
seen_topics = set()

for row in topic_rows:
    tid = row["bertopic_id"]
    tname = row["bertopic_name"]
    safety = row.get("deepseek_safety_proposal", "").strip()
    seen_topics.add(tid)

    subsystems = parse_semicolon(row.get("deepseek_subsystem_proposal", ""))
    role_map = parse_role_map(row.get("role_proposal", ""))
    patent_numbers = parse_semicolon(row.get("supporting_patent_numbers", ""))
    excerpts_map = topic_excerpt_map.get(tid, {})

    for subsys in subsystems:
        role = role_map.get(subsys, "")
        # Collect excerpts for this subsystem
        excerpts = excerpts_map.get(subsys, [])
        excerpt_joined = " | ".join(excerpts) if excerpts else ""
        # Supporting patent numbers for this topic
        patent_str = ";".join(patent_numbers)

        queue_rows.append({
            "bertopic_id": tid,
            "bertopic_name": tname,
            "proposed_safety": safety,
            "subsystem_id": subsys,
            "proposed_role": role,
            "supporting_patent_numbers": patent_str,
            "evidence_excerpt": excerpt_joined,
            "proposal_rationale": "",  # leave rationale to topic-level, not per-subsystem
            "human_safety_judgment": "",
            "human_subsystem_decision": "",
            "human_role_judgment": "",
            "reviewer_confidence": "",
            "reviewer_note": "",
        })

# Verify all 20 topics covered
assert len(seen_topics) == 20, f"Expected 20 topics, got {len(seen_topics)}"

fieldnames = [
    "bertopic_id", "bertopic_name", "proposed_safety", "subsystem_id",
    "proposed_role", "supporting_patent_numbers", "evidence_excerpt",
    "proposal_rationale", "human_safety_judgment", "human_subsystem_decision",
    "human_role_judgment", "reviewer_confidence", "reviewer_note",
]

with open(os.path.join(OUT, "P1_topic_review_queue.csv"), "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(queue_rows)

print(f"Created P1_topic_review_queue.csv: {len(queue_rows)} rows")

# ============================================================
# 4. P1_direct_flow_review_queue.csv
# ============================================================

direct_flow_rows = [r for r in interaction_rows if r.get("evidence_type_proposal", "").strip() == "DIRECT_FLOW"]
print(f"DIRECT_FLOW rows: {len(direct_flow_rows)}")

df_fieldnames = [
    "evidence_id", "bertopic_id", "bertopic_name",
    "source_subsystem", "target_subsystem", "patent_number",
    "relation_verb", "relation_pattern", "source_mention", "target_mention",
    "exact_evidence_excerpt", "proposed_strength", "standard_clauses",
    "human_interaction_decision", "human_strength_judgment",
    "reviewer_confidence", "reviewer_note",
]

df_out = []
for r in direct_flow_rows:
    df_out.append({
        "evidence_id": r.get("evidence_id", ""),
        "bertopic_id": r.get("bertopic_id", ""),
        "bertopic_name": r.get("bertopic_name", ""),
        "source_subsystem": r.get("source_subsystem", ""),
        "target_subsystem": r.get("target_subsystem", ""),
        "patent_number": r.get("patent_number", ""),
        "relation_verb": r.get("relation_verb", ""),
        "relation_pattern": r.get("relation_pattern", ""),
        "source_mention": r.get("source_mention", ""),
        "target_mention": r.get("target_mention", ""),
        "exact_evidence_excerpt": r.get("claim_or_abstract_evidence", ""),
        "proposed_strength": r.get("evidence_strength_proposal", ""),
        "standard_clauses": r.get("standard_clauses", ""),
        "human_interaction_decision": "",
        "human_strength_judgment": "",
        "reviewer_confidence": "",
        "reviewer_note": "",
    })

with open(os.path.join(OUT, "P1_direct_flow_review_queue.csv"), "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=df_fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(df_out)

print(f"Created P1_direct_flow_review_queue.csv: {len(df_out)} rows")

# ============================================================
# 5. P1_coimplementation_review_queue.csv
# ============================================================

co_rows = [r for r in interaction_rows if r.get("evidence_type_proposal", "").strip() == "CO_IMPLEMENTATION"]
print(f"CO_IMPLEMENTATION rows: {len(co_rows)}")

# Assign priority
co_with_priority = []
for r in co_rows:
    tid = r.get("bertopic_id", "")
    src = r.get("source_subsystem", "")
    tgt = r.get("target_subsystem", "")
    roles = topic_role_map.get(tid, {})
    pri = subsystem_priority((src, tgt), roles)
    co_with_priority.append((pri, r))

# Sort by priority, then by bertopic_id for stable ordering
co_with_priority.sort(key=lambda x: (x[0], int(x[1].get("bertopic_id", "0"))))

co_fieldnames = [
    "review_priority", "bertopic_id", "bertopic_name",
    "source_subsystem", "target_subsystem",
    "evidence_type_proposal", "evidence_strength_proposal",
    "claim_or_abstract_evidence", "supporting_patent_numbers",
    "standard_clauses", "rationale",
    "human_coimplementation_decision",
    "reviewer_confidence", "reviewer_note",
]

co_out = []
for pri, r in co_with_priority:
    co_out.append({
        "review_priority": pri,
        "bertopic_id": r.get("bertopic_id", ""),
        "bertopic_name": r.get("bertopic_name", ""),
        "source_subsystem": r.get("source_subsystem", ""),
        "target_subsystem": r.get("target_subsystem", ""),
        "evidence_type_proposal": r.get("evidence_type_proposal", ""),
        "evidence_strength_proposal": r.get("evidence_strength_proposal", ""),
        "claim_or_abstract_evidence": r.get("claim_or_abstract_evidence", ""),
        "supporting_patent_numbers": r.get("supporting_patent_numbers", ""),
        "standard_clauses": r.get("standard_clauses", ""),
        "rationale": r.get("rationale", ""),
        "human_coimplementation_decision": "",
        "reviewer_confidence": "",
        "reviewer_note": "",
    })

with open(os.path.join(OUT, "P1_coimplementation_review_queue.csv"), "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=co_fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(co_out)

print(f"Created P1_coimplementation_review_queue.csv: {len(co_out)} rows")

# Priority distribution
from collections import Counter
pri_counts = Counter(r["review_priority"] for r in co_out)
for p in sorted(pri_counts):
    print(f"  Priority {p}: {pri_counts[p]} rows")

# ============================================================
# 6. P1_human_review_summary_TEMPLATE.md
# ============================================================

summary_md = r"""# P1 Human Review Summary

> **Fill this template after completing all review queues.**
> Do NOT fill before review.

---

## Review Metadata

- **Review date:** _______________
- **Reviewer:** _______________
- **Review duration (hours):** _______________
- **Provisional data generated:** 2026-07-24

---

## Topic Safety Review

| Judgment | Count |
|----------|-------|
| DIRECT (accepted) | __ |
| DIRECT (changed) | __ |
| PARTIAL (accepted) | __ |
| PARTIAL (changed) | __ |
| INCIDENTAL (changed from DIRECT/PARTIAL) | __ |
| NOT_SAFETY (accepted) | __ |
| NOT_SAFETY (changed) | __ |
| UNCLEAR | __ |
| **Total** | **20** |

---

## Subsystem Assignment Review

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

## Role Review

| Role | ACCEPT | Changed to PRIMARY | Changed to SECONDARY | Changed to CONTEXT_ONLY | REJECT |
|------|--------|--------------------|-----------------------|--------------------------|--------|
| Count | __ | __ | __ | __ | __ |

---

## DIRECT_FLOW Review

| Decision | Count |
|----------|-------|
| ACCEPT_DIRECTION | __ |
| REVERSE_DIRECTION | __ |
| CO_IMPLEMENTATION_ONLY | __ |
| REJECT | __ |
| UNCLEAR | __ |
| **Total** | **1** |

### DIRECT_FLOW Details

| Evidence ID | Source → Target | Patent | Decision | Notes |
|-------------|-----------------|--------|----------|-------|
| (fill) | (fill) | (fill) | (fill) | (fill) |

---

## CO_IMPLEMENTATION Review

| Decision | Count |
|----------|-------|
| ACCEPT (as CO_IMPLEMENTATION) | __ |
| UPGRADE to DIRECT_FLOW (specify direction) | __ |
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
"""

with open(os.path.join(OUT, "P1_human_review_summary_TEMPLATE.md"), "w", encoding="utf-8") as f:
    f.write(summary_md)
print("Created P1_human_review_summary_TEMPLATE.md")

# ============================================================
# 7. Verification
# ============================================================

print("\n=== VERIFICATION ===")

# Topic queue
print(f"\nTopic review queue: {len(queue_rows)} rows")
print(f"Unique topics: {len(seen_topics)} (expect 20)")
assert len(seen_topics) == 20

# Direct flow
print(f"Direct-flow queue: {len(df_out)} rows")

# Co-implementation
print(f"Co-implementation queue: {len(co_out)} rows")

# All 20 topics covered?
topic_ids_in_queue = set(r["bertopic_id"] for r in queue_rows)
print(f"Topics in queue: {sorted(topic_ids_in_queue, key=int)}")
assert topic_ids_in_queue == seen_topics, "Topic coverage mismatch"

# Human fields empty?
for i, r in enumerate(queue_rows):
    human_fields = ["human_safety_judgment", "human_subsystem_decision", "human_role_judgment", "reviewer_confidence", "reviewer_note"]
    for f in human_fields:
        assert r.get(f, "") == "", f"Topic queue row {i}: {f} is not empty: {r.get(f)}"

for i, r in enumerate(df_out):
    human_fields = ["human_interaction_decision", "human_strength_judgment", "reviewer_confidence", "reviewer_note"]
    for f in human_fields:
        assert r.get(f, "") == "", f"Direct flow row {i}: {f} is not empty: {r.get(f)}"

for i, r in enumerate(co_out):
    human_fields = ["human_coimplementation_decision", "reviewer_confidence", "reviewer_note"]
    for f in human_fields:
        assert r.get(f, "") == "", f"Co-impl row {i}: {f} is not empty: {r.get(f)}"

print("\nAll human fields verified empty.")
print("All checks passed.")

# Check no provisional files were modified (just listing what we created)
print(f"\nFiles created in {OUT}:")
for f in sorted(os.listdir(OUT)):
    fpath = os.path.join(OUT, f)
    if os.path.isfile(fpath):
        print(f"  {f} ({os.path.getsize(fpath):,} bytes)")
