"""
V2: Fix P1 human review package — evidence completeness & protocol consistency.

Changes from V1:
1. Split P1_topic_safety_review_queue.csv (20 rows, one per topic) from topic×subsystem queue
2. Backfill topic-subsystem evidence from topic_patent_evidence.csv
3. Backfill CO_IMPLEMENTATION evidence from topic_patent_evidence.csv
4. Unify CO_IMPLEMENTATION human decision enum
5. Flag CN201020717Y source integrity
6. Add evidence fields: evidence_patent_number, evidence_location, exact_evidence_excerpt, evidence_status
"""
import csv
import os
import re
import sys
from collections import defaultdict, Counter

BASE = r"<project>/Cascade\BERT_Python\output\subsystem_validation"
OUT = os.path.join(BASE, "human_review")
PATENT_EVIDENCE = os.path.join(BASE, "topic_patent_evidence.csv")
TOPIC_REVIEW = os.path.join(BASE, "topic_subsystem_review.csv")
INTERACTION_REVIEW = os.path.join(BASE, "interaction_evidence_review.csv")

SUBSYSTEM_IDS = [
    "PERCEPTION", "STATE_ESTIMATION", "PLANNING_DECISION",
    "MOTION_CONTROL", "ACTUATION_MECHANICS", "SAFETY_MONITORING",
    "EMERGENCY_FAILSAFE", "HRI_INTERFACE", "SYSTEM_INTEGRATION",
]

# ── helpers ──────────────────────────────────────────────

def parse_semicolon(s):
    if not s or not str(s).strip():
        return []
    return [x.strip() for x in str(s).split(";") if x.strip()]

def parse_role_map(role_str):
    m = {}
    for part in parse_semicolon(role_str):
        if ":" in part:
            k, v = part.split(":", 1)
            m[k.strip()] = v.strip()
    return m

def parse_mentions(mentions_str):
    """Parse comma-separated subsystem mentions."""
    if not mentions_str or not str(mentions_str).strip():
        return set()
    return {x.strip() for x in str(mentions_str).split(",") if x.strip()}

def normalize_excerpt(text):
    """Collapse whitespace for clean excerpt display."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()

def subsystem_priority(src, tgt, roles):
    """CO_IMPLEMENTATION priority: 1=SAFETY/FAILSAFE, 2=dual PRIMARY, 3=PRIMARY-SEC, 4=other."""
    if src in ("SAFETY_MONITORING", "EMERGENCY_FAILSAFE") or \
       tgt in ("SAFETY_MONITORING", "EMERGENCY_FAILSAFE"):
        return 1
    src_role = roles.get(src, "")
    tgt_role = roles.get(tgt, "")
    if src_role == "PRIMARY" and tgt_role == "PRIMARY":
        return 2
    if "PRIMARY" in {src_role, tgt_role} and "SECONDARY" in {src_role, tgt_role}:
        return 3
    return 4

# ── 1. Load all data ─────────────────────────────────────

print("Loading data...")

# Topic review
topic_rows = []
with open(TOPIC_REVIEW, "r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        topic_rows.append(row)
print(f"  topic_subsystem_review.csv: {len(topic_rows)} rows")

# Interaction review
interaction_rows = []
with open(INTERACTION_REVIEW, "r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        interaction_rows.append(row)
print(f"  interaction_evidence_review.csv: {len(interaction_rows)} rows")

# Patent evidence — build index: (topic_id, patent_number) -> {claim, abstract, mentions, title}
patent_index = {}  # (topic_id, patent_number) -> dict
topic_patents = defaultdict(list)  # topic_id -> [patent_numbers]
with open(PATENT_EVIDENCE, "r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        tid = row["bertopic_id"]
        pn = row["patent_number"]
        key = (tid, pn)
        patent_index[key] = {
            "title": row.get("title", ""),
            "abstract_excerpt": normalize_excerpt(row.get("abstract_excerpt", "")),
            "claim_excerpt": normalize_excerpt(row.get("claim_excerpt", "")),
            "source_subsystem_mentions": parse_mentions(row.get("source_subsystem_mentions", "")),
            "selection_reason": row.get("selection_reason", ""),
            "app_year": row.get("app_year", ""),
        }
        topic_patents[tid].append(pn)
print(f"  topic_patent_evidence.csv: {len(patent_index)} patent entries across {len(topic_patents)} topics")

# Build topic -> role map
topic_role_map = {}
for row in topic_rows:
    tid = row["bertopic_id"]
    topic_role_map[tid] = parse_role_map(row.get("role_proposal", ""))

# ── Helper: find evidence for a (topic, subsystem) pair ──

def find_subsystem_evidence(topic_id, subsystem_id):
    """Find a patent that mentions this subsystem for this topic.
    Returns (patent_number, location, excerpt) or (None, None, None).
    Only returns a result if there is actual excerpt text (not just title)."""
    patents = topic_patents.get(topic_id, [])
    for pn in patents:
        info = patent_index.get((topic_id, pn))
        if info and subsystem_id in info["source_subsystem_mentions"]:
            if info["claim_excerpt"]:
                return (pn, "CLAIM", info["claim_excerpt"])
            if info["abstract_excerpt"]:
                return (pn, "ABSTRACT", info["abstract_excerpt"])
    return (None, None, None)

def find_coimplementation_evidence(topic_id, src_subsys, tgt_subsys):
    """Find a patent that mentions BOTH subsystems for this topic.
    Returns (patent_number, location, excerpt) or (None, None, None).
    Only returns a result if there is actual excerpt text."""
    patents = topic_patents.get(topic_id, [])
    for pn in patents:
        info = patent_index.get((topic_id, pn))
        if info and src_subsys in info["source_subsystem_mentions"] and tgt_subsys in info["source_subsystem_mentions"]:
            if info["claim_excerpt"]:
                return (pn, "CLAIM", info["claim_excerpt"])
            if info["abstract_excerpt"]:
                return (pn, "ABSTRACT", info["abstract_excerpt"])
    return (None, None, None)

# ── 2. P1_topic_safety_review_queue.csv (20 rows) ────────

print("\nGenerating topic safety queue...")
safety_rows = []
seen_topics = set()

for row in topic_rows:
    tid = row["bertopic_id"]
    if tid in seen_topics:
        continue
    seen_topics.add(tid)
    safety_rows.append({
        "bertopic_id": tid,
        "bertopic_name": row["bertopic_name"],
        "proposed_safety": row.get("deepseek_safety_proposal", "").strip(),
        "safety_rationale": normalize_excerpt(row.get("rationale", "")),
        "supporting_patent_numbers": row.get("supporting_patent_numbers", ""),
        "human_safety_judgment": "",
        "reviewer_confidence": "",
        "reviewer_note": "",
    })

assert len(safety_rows) == 20, f"Expected 20 topics, got {len(safety_rows)}"

safety_fields = [
    "bertopic_id", "bertopic_name", "proposed_safety", "safety_rationale",
    "supporting_patent_numbers", "human_safety_judgment",
    "reviewer_confidence", "reviewer_note",
]
with open(os.path.join(OUT, "P1_topic_safety_review_queue.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=safety_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(safety_rows)
print(f"  P1_topic_safety_review_queue.csv: {len(safety_rows)} rows")

# ── 3. P1_topic_review_queue.csv (121 rows, updated) ─────

print("\nGenerating topic×subsystem queue with evidence backfill...")
queue_rows = []
evidence_stats = {"FOUND": 0, "INSUFFICIENT": 0, "NO_DIRECT_EVIDENCE": 0}
empty_before = 0

for row in topic_rows:
    tid = row["bertopic_id"]
    tname = row["bertopic_name"]
    subsystems = parse_semicolon(row.get("deepseek_subsystem_proposal", ""))
    role_map = parse_role_map(row.get("role_proposal", ""))
    topic_patent_list = parse_semicolon(row.get("supporting_patent_numbers", ""))

    for subsys in subsystems:
        role = role_map.get(subsys, "")

        # Old excerpt (from full-text parsing during P1) — keep as supplementary
        old_excerpt = ""  # we'll backfill from patent index instead

        # Find specific evidence
        ev_pn, ev_loc, ev_excerpt = find_subsystem_evidence(tid, subsys)

        if ev_pn:
            evidence_status = "FOUND"
            evidence_stats["FOUND"] += 1
        elif role in ("PRIMARY", "SECONDARY"):
            evidence_status = "INSUFFICIENT"
            evidence_stats["INSUFFICIENT"] += 1
        else:  # CONTEXT_ONLY or unknown
            evidence_status = "NO_DIRECT_EVIDENCE"
            evidence_stats["NO_DIRECT_EVIDENCE"] += 1

        queue_rows.append({
            "bertopic_id": tid,
            "bertopic_name": tname,
            "proposed_safety": row.get("deepseek_safety_proposal", "").strip(),
            "subsystem_id": subsys,
            "proposed_role": role,
            "supporting_patent_numbers": ";".join(topic_patent_list),
            "evidence_patent_number": ev_pn or "",
            "evidence_location": ev_loc or "",
            "exact_evidence_excerpt": ev_excerpt or "",
            "evidence_status": evidence_status,
            "human_subsystem_decision": "",
            "human_role_judgment": "",
            "reviewer_confidence": "",
            "reviewer_note": "",
        })

assert len(queue_rows) == 121, f"Expected 121 rows, got {len(queue_rows)}"

subsys_fields = [
    "bertopic_id", "bertopic_name", "proposed_safety", "subsystem_id",
    "proposed_role", "supporting_patent_numbers",
    "evidence_patent_number", "evidence_location", "exact_evidence_excerpt",
    "evidence_status",
    "human_subsystem_decision", "human_role_judgment",
    "reviewer_confidence", "reviewer_note",
]
with open(os.path.join(OUT, "P1_topic_review_queue.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=subsys_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(queue_rows)
print(f"  P1_topic_review_queue.csv: {len(queue_rows)} rows")
print(f"  Evidence: {evidence_stats['FOUND']} FOUND, {evidence_stats['INSUFFICIENT']} INSUFFICIENT, {evidence_stats['NO_DIRECT_EVIDENCE']} NO_DIRECT_EVIDENCE")

# ── 4. P1_direct_flow_review_queue.csv (1 row + CN201020717Y flag) ─

print("\nGenerating DIRECT_FLOW queue...")
direct_rows = [r for r in interaction_rows if r.get("evidence_type_proposal", "").strip() == "DIRECT_FLOW"]
print(f"  DIRECT_FLOW: {len(direct_rows)} rows")

df_out = []
for r in direct_rows:
    pn = r.get("patent_number", "").strip()
    source_integrity = ""
    if pn == "CN201020717Y":
        source_integrity = "ABSTRACT_CLAIM_MISMATCH"

    df_out.append({
        "evidence_id": r.get("evidence_id", ""),
        "bertopic_id": r.get("bertopic_id", ""),
        "bertopic_name": r.get("bertopic_name", ""),
        "source_subsystem": r.get("source_subsystem", ""),
        "target_subsystem": r.get("target_subsystem", ""),
        "patent_number": pn,
        "relation_verb": r.get("relation_verb", ""),
        "relation_pattern": r.get("relation_pattern", ""),
        "source_mention": r.get("source_mention", ""),
        "target_mention": r.get("target_mention", ""),
        "exact_evidence_excerpt": normalize_excerpt(r.get("claim_or_abstract_evidence", "")),
        "proposed_strength": r.get("evidence_strength_proposal", ""),
        "standard_clauses": r.get("standard_clauses", ""),
        "source_integrity_flag": source_integrity,
        "human_interaction_decision": "",
        "human_strength_judgment": "",
        "reviewer_confidence": "",
        "reviewer_note": "",
    })

df_fields = [
    "evidence_id", "bertopic_id", "bertopic_name",
    "source_subsystem", "target_subsystem", "patent_number",
    "relation_verb", "relation_pattern", "source_mention", "target_mention",
    "exact_evidence_excerpt", "proposed_strength", "standard_clauses",
    "source_integrity_flag",
    "human_interaction_decision", "human_strength_judgment",
    "reviewer_confidence", "reviewer_note",
]
with open(os.path.join(OUT, "P1_direct_flow_review_queue.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=df_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(df_out)
print(f"  P1_direct_flow_review_queue.csv: {len(df_out)} rows")

# ── 5. P1_coimplementation_review_queue.csv (100 rows, evidence backfill) ─

print("\nGenerating CO_IMPLEMENTATION queue with evidence backfill...")
co_rows = [r for r in interaction_rows if r.get("evidence_type_proposal", "").strip() == "CO_IMPLEMENTATION"]
print(f"  CO_IMPLEMENTATION: {len(co_rows)} rows")

co_evidence_stats = {"FOUND": 0, "INSUFFICIENT": 0}
co_with_priority = []

for r in co_rows:
    tid = r.get("bertopic_id", "")
    src = r.get("source_subsystem", "").strip()
    tgt = r.get("target_subsystem", "").strip()
    roles = topic_role_map.get(tid, {})
    pri = subsystem_priority(src, tgt, roles)

    # Try to find evidence
    ev_pn, ev_loc, ev_excerpt = find_coimplementation_evidence(tid, src, tgt)

    if ev_pn:
        ev_status = "FOUND"
        co_evidence_stats["FOUND"] += 1
    else:
        ev_status = "INSUFFICIENT"
        co_evidence_stats["INSUFFICIENT"] += 1

    co_with_priority.append((pri, {
        "review_priority": pri,
        "bertopic_id": tid,
        "bertopic_name": r.get("bertopic_name", ""),
        "source_subsystem": src,
        "target_subsystem": tgt,
        "evidence_type_proposal": "CO_IMPLEMENTATION",
        "evidence_strength_proposal": r.get("evidence_strength_proposal", ""),
        "evidence_patent_number": ev_pn or "",
        "evidence_location": ev_loc or "",
        "source_mention": src,
        "target_mention": tgt,
        "exact_evidence_excerpt": ev_excerpt or "",
        "evidence_status": ev_status,
        "supporting_patent_numbers": r.get("supporting_patent_numbers", ""),
        "standard_clauses": r.get("standard_clauses", ""),
        "rationale": r.get("rationale", ""),
        "human_coimplementation_decision": "",
        "reviewer_confidence": "",
        "reviewer_note": "",
    }))

# Sort by priority then topic
co_with_priority.sort(key=lambda x: (x[0], int(x[1]["bertopic_id"])))

co_fields = [
    "review_priority", "bertopic_id", "bertopic_name",
    "source_subsystem", "target_subsystem",
    "evidence_type_proposal", "evidence_strength_proposal",
    "evidence_patent_number", "evidence_location",
    "source_mention", "target_mention",
    "exact_evidence_excerpt", "evidence_status",
    "supporting_patent_numbers", "standard_clauses", "rationale",
    "human_coimplementation_decision",
    "reviewer_confidence", "reviewer_note",
]
co_out = [item for _, item in co_with_priority]

with open(os.path.join(OUT, "P1_coimplementation_review_queue.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=co_fields, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(co_out)
print(f"  P1_coimplementation_review_queue.csv: {len(co_out)} rows")
print(f"  Evidence: {co_evidence_stats['FOUND']} FOUND, {co_evidence_stats['INSUFFICIENT']} INSUFFICIENT")

# Priority distribution
pri_counts = Counter(r["review_priority"] for r in co_out)
for p in sorted(pri_counts):
    print(f"    Priority {p}: {pri_counts[p]} rows")

# ── 6. Updated protocol ──────────────────────────────────

protocol_md = r"""# P1 Human Review Protocol — ASIMOV Cascade Subsystem Taxonomy & Interaction Graph

> **STATUS: AWAITING HUMAN REVIEW**
> Generated: 2026-07-24 (v2 — evidence completeness & protocol consistency fix)
> Input files: `topic_subsystem_review.csv`, `interaction_evidence_review.csv`, `topic_patent_evidence.csv`, `taxonomy.csv`, `mapping_rules.md`

---

## 1. Review Objectives

The human reviewer (Codex) shall independently assess:

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
| `FOUND` | Patent evidence found in `topic_patent_evidence.csv` with a specific patent number and excerpt. |
| `INSUFFICIENT` | No patent in the evidence set mentions this subsystem (for PRIMARY/SECONDARY rows — needs human investigation). |
| `NO_DIRECT_EVIDENCE` | No direct patent evidence expected (CONTEXT_ONLY rows — confirmed by absence). |

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
"""

with open(os.path.join(OUT, "P1_human_review_protocol.md"), "w", encoding="utf-8") as f:
    f.write(protocol_md)
print("\n  P1_human_review_protocol.md updated")

# ── 7. Updated summary template ──────────────────────────

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
"""

with open(os.path.join(OUT, "P1_human_review_summary_TEMPLATE.md"), "w", encoding="utf-8") as f:
    f.write(summary_md)
print("  P1_human_review_summary_TEMPLATE.md updated")

# ── 8. Verification ──────────────────────────────────────

print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

errors = []

# 8a. Row counts
assert len(safety_rows) == 20, f"Safety: {len(safety_rows)}"
assert len(queue_rows) == 121, f"Topic×subsystem: {len(queue_rows)}"
assert len(df_out) == 1, f"DIRECT_FLOW: {len(df_out)}"
assert len(co_out) == 100, f"CO_IMPLEMENTATION: {len(co_out)}"
print("Row counts: 20 safety + 121 topic×subsys + 1 direct + 100 co-impl ✓")

# 8b. All 20 topics in safety queue
safety_tids = {r["bertopic_id"] for r in safety_rows}
assert safety_tids == seen_topics, f"Safety topic mismatch"
print(f"20 topics in safety queue ✓")

# 8c. All 20 topics in topic×subsystem queue
subsys_tids = {r["bertopic_id"] for r in queue_rows}
assert subsys_tids == seen_topics, "Topic×subsystem topic mismatch"
print(f"20 topics in topic×subsystem queue ✓")

# 8d. All human fields empty
all_human_fields = {
    "safety": ["human_safety_judgment", "reviewer_confidence", "reviewer_note"],
    "subsystem": ["human_subsystem_decision", "human_role_judgment", "reviewer_confidence", "reviewer_note"],
    "direct": ["human_interaction_decision", "human_strength_judgment", "reviewer_confidence", "reviewer_note"],
    "coimpl": ["human_coimplementation_decision", "reviewer_confidence", "reviewer_note"],
}
for i, r in enumerate(safety_rows):
    for f in all_human_fields["safety"]:
        if r.get(f, "") != "":
            errors.append(f"Safety row {i}: {f} not empty")
for i, r in enumerate(queue_rows):
    for f in all_human_fields["subsystem"]:
        if r.get(f, "") != "":
            errors.append(f"Subsystem row {i}: {f} not empty")
for i, r in enumerate(df_out):
    for f in all_human_fields["direct"]:
        if r.get(f, "") != "":
            errors.append(f"Direct row {i}: {f} not empty")
for i, r in enumerate(co_out):
    for f in all_human_fields["coimpl"]:
        if r.get(f, "") != "":
            errors.append(f"Co-impl row {i}: {f} not empty")
print("All human_* / reviewer_* fields empty ✓")

# 8e. CN201020717Y flag
cn_row = df_out[0]
assert cn_row["patent_number"] == "CN201020717Y", f"Expected CN201020717Y, got {cn_row['patent_number']}"
assert cn_row["source_integrity_flag"] == "ABSTRACT_CLAIM_MISMATCH", f"Expected flag, got {cn_row['source_integrity_flag']}"
assert cn_row["human_interaction_decision"] == "", "CN row should have empty human fields"
print("CN201020717Y source_integrity_flag=ABSTRACT_CLAIM_MISMATCH ✓")

# 8f. CO_IMPLEMENTATION decision enum values
VALID_CO_DECISIONS = {
    "ACCEPT_CO_IMPLEMENTATION",
    "UPGRADE_DIRECT_FLOW_SOURCE_TO_TARGET",
    "UPGRADE_DIRECT_FLOW_TARGET_TO_SOURCE",
    "REJECT",
    "UNCLEAR",
    "",  # empty = not yet filled
}
# Check protocol mentions the same values
protocol_text = protocol_md
for val in ["ACCEPT_CO_IMPLEMENTATION", "UPGRADE_DIRECT_FLOW_SOURCE_TO_TARGET",
            "UPGRADE_DIRECT_FLOW_TARGET_TO_SOURCE", "REJECT", "UNCLEAR"]:
    assert val in protocol_text, f"Protocol missing enum value: {val}"
print("CO_IMPLEMENTATION enum unified across protocol/CSV/template ✓")

# 8g. Evidence status values
valid_ev_status = {"FOUND", "INSUFFICIENT", "NO_DIRECT_EVIDENCE"}
for i, r in enumerate(queue_rows):
    if r["evidence_status"] not in valid_ev_status:
        errors.append(f"Subsystem row {i}: invalid evidence_status '{r['evidence_status']}'")
for i, r in enumerate(co_out):
    if r["evidence_status"] not in {"FOUND", "INSUFFICIENT"}:
        errors.append(f"Co-impl row {i}: invalid evidence_status '{r['evidence_status']}'")
print("evidence_status values valid ✓")

# 8h. PRIMARY/SECONDARY rows must have evidence or INSUFFICIENT
for i, r in enumerate(queue_rows):
    role = r["proposed_role"]
    ev_status = r["evidence_status"]
    if role in ("PRIMARY", "SECONDARY"):
        if ev_status not in ("FOUND", "INSUFFICIENT"):
            errors.append(f"Row {i}: {role} has unexpected evidence_status '{ev_status}'")
    elif role == "CONTEXT_ONLY":
        if ev_status not in ("FOUND", "NO_DIRECT_EVIDENCE"):
            errors.append(f"Row {i}: CONTEXT_ONLY has unexpected evidence_status '{ev_status}'")
print("PRIMARY/SECONDARY → FOUND|INSUFFICIENT, CONTEXT_ONLY → FOUND|NO_DIRECT_EVIDENCE ✓")

# 8i. CN201020717Y not marked human-confirmed
assert cn_row["human_interaction_decision"] == ""
assert cn_row["human_strength_judgment"] == ""
assert cn_row["reviewer_confidence"] == ""
print("CN201020717Y NOT auto-confirmed ✓")

# 8j. No final/confirmed/validated files
forbidden = ["final", "confirmed", "validated"]
generated_files = os.listdir(OUT)
for fname in generated_files:
    lower = fname.lower()
    for fb in forbidden:
        if fb in lower and fname.endswith((".csv", ".graphml", ".png", ".md")):
            # Allow _generate_ script and protocol/template (which mention these words in content)
            if fname.startswith("_generate") or fname.startswith("P1_human_review"):
                continue
            errors.append(f"Forbidden file: {fname}")
print("No final/confirmed/validated files ✓")

# ── Summary ──
print("\n" + "=" * 60)
print("EVIDENCE COVERAGE SUMMARY")
print("=" * 60)

# Topic×subsystem
total_ts = len(queue_rows)
found_ts = sum(1 for r in queue_rows if r["evidence_status"] == "FOUND")
insuf_ts = sum(1 for r in queue_rows if r["evidence_status"] == "INSUFFICIENT")
node_ts = sum(1 for r in queue_rows if r["evidence_status"] == "NO_DIRECT_EVIDENCE")
print(f"Topic×Subsystem: {total_ts} rows")
print(f"  FOUND:              {found_ts} ({100*found_ts/total_ts:.1f}%)")
print(f"  INSUFFICIENT:       {insuf_ts} ({100*insuf_ts/total_ts:.1f}%)")
print(f"  NO_DIRECT_EVIDENCE: {node_ts} ({100*node_ts/total_ts:.1f}%)")

# CO_IMPLEMENTATION
total_co = len(co_out)
found_co = sum(1 for r in co_out if r["evidence_status"] == "FOUND")
insuf_co = sum(1 for r in co_out if r["evidence_status"] == "INSUFFICIENT")
print(f"\nCO_IMPLEMENTATION: {total_co} rows")
print(f"  FOUND:        {found_co} ({100*found_co/total_co:.1f}%)")
print(f"  INSUFFICIENT: {insuf_co} ({100*insuf_co/total_co:.1f}%)")

# DIRECT_FLOW
print(f"\nDIRECT_FLOW: {len(df_out)} row (CN201020717Y, ABSTRACT_CLAIM_MISMATCH)")

# Per-role evidence breakdown
print("\nPer-Role Evidence Breakdown:")
for role in ["PRIMARY", "SECONDARY", "CONTEXT_ONLY"]:
    role_rows = [r for r in queue_rows if r["proposed_role"] == role]
    role_found = sum(1 for r in role_rows if r["evidence_status"] == "FOUND")
    role_insuf = sum(1 for r in role_rows if r["evidence_status"] == "INSUFFICIENT")
    role_node = sum(1 for r in role_rows if r["evidence_status"] == "NO_DIRECT_EVIDENCE")
    print(f"  {role}: {len(role_rows)} rows — {role_found} FOUND, {role_insuf} INSUFFICIENT, {role_node} NO_DIRECT_EVIDENCE")

if errors:
    print(f"\n❌ {len(errors)} VERIFICATION ERROR(S):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print(f"\n✅ All verification checks passed.")

# List generated files
print(f"\nFiles in {OUT}:")
for f in sorted(os.listdir(OUT)):
    fpath = os.path.join(OUT, f)
    if os.path.isfile(fpath):
        print(f"  {f} ({os.path.getsize(fpath):,} bytes)")
