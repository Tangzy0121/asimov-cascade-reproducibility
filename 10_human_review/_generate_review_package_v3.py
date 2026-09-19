"""
V3: Fix location-level evidence mismatches in P1 human review package.

Key changes from V2:
1. Per-location subsystem detection (title/abstract/claim separately)
2. Evidence excerpt must contain the target subsystem at that location
3. CO_IMPLEMENTATION: both subsystems in SAME excerpt, actual mention text
4. evidence_patent_number must be in supporting_patent_numbers
5. Safety queue gets patent evidence fields
6. Content-level regression self-tests
"""
import csv
import os
import re
import sys
from collections import defaultdict, Counter

# ── Paths ──────────────────────────────────────────────────
BASE = r"<project>/<pipeline>\output\subsystem_validation"
OUT = os.path.join(BASE, "human_review")
PATENT_EVIDENCE = os.path.join(BASE, "topic_patent_evidence.csv")
TOPIC_REVIEW = os.path.join(BASE, "topic_subsystem_review.csv")
INTERACTION_REVIEW = os.path.join(BASE, "interaction_evidence_review.csv")

# ── Keyword data (mirrors build_subsystem_interaction_graph.py, avoids import side-effects) ─

SUBSYSTEM_IDS = [
    "PERCEPTION", "STATE_ESTIMATION", "PLANNING_DECISION",
    "MOTION_CONTROL", "ACTUATION_MECHANICS", "SAFETY_MONITORING",
    "EMERGENCY_FAILSAFE", "HRI_INTERFACE", "SYSTEM_INTEGRATION",
]

SUBSYSTEM_KEYWORDS = {
    "PERCEPTION": {"include": [
        "sensor", "camera", "vision", "lidar", "radar", "proximity",
        "detect", "obstacle", "observation", "depth", "image", "point cloud",
        "perception", "acoustic", "ultrasonic", "infrared", "scanning",
        "environmental", "surveillance",
    ]},
    "STATE_ESTIMATION": {"include": [
        "state estim", "world model", "fusion", "kalman", "localization",
        "pose estim", "mapping", "slam", "tracking", "predict state",
        "bayesian", "particle filter", "odometry", "state prediction",
        "trajectory estim", "situation awareness", "scene understanding",
    ]},
    "PLANNING_DECISION": {"include": [
        "path plan", "trajectory plan", "motion plan", "task plan",
        "decision", "behavior", "policy", "select", "goal", "planner",
        "route", "navigation plan", "mission plan", "replan",
        "optimization", "optimal", "strategy select",
    ]},
    "MOTION_CONTROL": {"include": [
        "torque control", "impedance control", "force control",
        "feedback control", "pid", "velocity control", "position control",
        "servo", "trajectory track", "balance control", "motion control",
        "admittance", "compliance control", "joint control",
        "inverse dynamics", "operational space",
    ]},
    "ACTUATION_MECHANICS": {"include": [
        "actuator", "motor", "joint", "transmission", "gearbox",
        "end effector", "gripper", "limb", "brake", "mechanical",
        "hydraulic", "pneumatic", "tendon", "linkage", "harmonic drive",
        "encoder", "torque sensor", "series elastic",
    ]},
    "SAFETY_MONITORING": {"include": [
        "safety", "safety monit", "safety check", "safety limit", "hazard detect",
        "collision detect", "collision predict", "safety zone",
        "safety barrier", "protective stop", "safe distance",
        "separation monit", "speed monit", "force limit",
        "power limit", "safety control", "safety-rated",
        "functional safety", "safety integrity", "risk assess",
        "safety state", "protective field",
    ]},
    "EMERGENCY_FAILSAFE": {"include": [
        "emergency stop", "safe stop", "e-stop", "power isolat",
        "fallback", "fault contain", "redundant", "fail-safe",
        "fail operat", "safe torque off", "sto", "category stop",
        "degraded mode", "recovery mode", "fault toler",
        "watchdog", "trip", "shutdown",
    ]},
    "HRI_INTERFACE": {"include": [
        "human-robot", "operator", "teach pendant", "user interface",
        "collaborative", "cobot", "hand guiding", "voice command",
        "gesture", "manual", "remote control", "teleoperation",
        "human intent", "human aware", "human detection",
        "human follow", "worker safety", "personal protective",
        "warning", "alarm", "alert operator",
    ]},
    "SYSTEM_INTEGRATION": {"include": [
        "arbitrat", "middleware", "coordina", "interlock",
        "mode manag", "priority resol", "shared state",
        "inter-module", "subsystem", "bus", "protocol",
        "ros", "communication", "synchroni", "task schedul",
        "resource allocat",
    ]},
}

SAFETY_DIRECT_KEYWORDS = [
    "safety", "safe ", "collision", "protect", "hazard", "risk",
    "emergency stop", "fail-safe", "fail safe", "fault", "stability",
    "balance", "injury", "harm", "dangerous", "warning", "isolation",
    "barrier", "guard", "interlock", "safeguard", "protective",
]
SAFETY_PARTIAL_KEYWORDS = [
    "impedance", "compliance", "force control", "torque limit",
    "collision", "avoidance", "obstacle", "monitor", "supervision",
]

# High-precision edge entity terms (compiled regex)
EDGE_ENTITY_TERMS = {
    "PERCEPTION": [
        r"\bcamera sensor\b", r"\bforce sensor\b", r"\blidar\b", r"\bradar\b",
        r"\bperception module\b", r"\bvision module\b", r"\bobstacle detection\b",
        r"\btorque sensor\b", r"\bproximity sensor\b", r"\bdepth camera\b",
        r"\bimage sensor\b", r"\binfrared sensor\b",
    ],
    "STATE_ESTIMATION": [
        r"\bstate estimator\b", r"\bstate estimation module\b",
        r"\bsensor fusion module\b", r"\blocalization module\b",
        r"\bkalman filter\b", r"\bparticle filter\b", r"\bworld model\b",
        r"\bbayesian estimator\b", r"\bslam module\b",
    ],
    "PLANNING_DECISION": [
        r"\bpath planner\b", r"\btrajectory planner\b", r"\bplanning module\b",
        r"\bdecision module\b", r"\btask planner\b", r"\bmotion planner\b",
        r"\bnavigation planner\b", r"\bbehavior planner\b",
    ],
    "MOTION_CONTROL": [
        r"\bmotion controller\b", r"\bjoint controller\b",
        r"\bservo controller\b", r"\bcontrol module\b",
        r"\bimpedance controller\b", r"\btorque controller\b",
        r"\bvelocity controller\b", r"\bposition controller\b",
    ],
    "ACTUATION_MECHANICS": [
        r"\bactuator\b", r"\bjoint actuator\b", r"\bmotor\b",
        r"\bjoint mechanism\b", r"\bbrake\b", r"\bgripper\b",
        r"\bend effector\b", r"\bgearbox\b", r"\bservo motor\b",
    ],
    "SAFETY_MONITORING": [
        r"\bsafety monitor\b", r"\bsafety monitoring module\b",
        r"\bsafety controller\b", r"\bsafety plc\b",
        r"\bprotective field\b", r"\bsafety zone\b",
        r"\bcollision detector\b",
    ],
    "EMERGENCY_FAILSAFE": [
        r"\bemergency stop module\b", r"\bfail-safe module\b",
        r"\bshutdown controller\b", r"\bemergency stop\b",
        r"\bsafe torque off\b", r"\bsafety relay\b",
    ],
    "HRI_INTERFACE": [
        r"\boperator interface\b", r"\bteach pendant\b",
        r"\bhuman interface\b", r"\bremote controller\b",
        r"\bhuman-robot interface\b", r"\bhand guiding\b",
    ],
    "SYSTEM_INTEGRATION": [
        r"\bmiddleware\b", r"\bcommunication bus\b",
        r"\bsystem coordinator\b", r"\bmain controller\b",
        r"\barbitration module\b", r"\bmode manager\b",
    ],
}
# Compile regex patterns
for sid in list(EDGE_ENTITY_TERMS.keys()):
    EDGE_ENTITY_TERMS[sid] = [re.compile(p) for p in EDGE_ENTITY_TERMS[sid]]

REQUIRED_SUBSYSTEM_IDS = SUBSYSTEM_IDS

# (SUBSYSTEM_IDS already defined above with keyword data)


# ── Helpers ───────────────────────────────────────────────

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

def normalize_excerpt(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()

def _detect_subsystems_in_text(text):
    """Return set of subsystem IDs whose SUBSYSTEM_KEYWORDS appear in text."""
    if not text:
        return set()
    text_lower = text.lower()
    found = set()
    for sid in SUBSYSTEM_IDS:
        for kw in SUBSYSTEM_KEYWORDS.get(sid, {}).get("include", []):
            if kw in text_lower:
                found.add(sid)
                break
    return found

def _detect_safety_keywords(text):
    """Return list of safety keywords found in text."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for kw in SAFETY_DIRECT_KEYWORDS + SAFETY_PARTIAL_KEYWORDS:
        if kw in text_lower:
            found.append(kw)
    return found

def _extract_mention(text, subsystem_id):
    """Extract first matching EDGE_ENTITY_TERMS phrase from text."""
    if not text:
        return ""
    text_lower = text.lower()
    patterns = EDGE_ENTITY_TERMS.get(subsystem_id, [])
    for pat in patterns:
        m = pat.search(text_lower)
        if m:
            return text_lower[m.start():m.end()]
    return ""

# ── 1. Load data ──────────────────────────────────────────

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

# Patent evidence — build per-location index
patent_index = {}  # (topic_id, patent_number) -> {title, title_mentions, abstract, abstract_mentions, claim, claim_mentions, ...}
topic_patents = defaultdict(list)
with open(PATENT_EVIDENCE, "r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        tid = row["bertopic_id"]
        pn = row["patent_number"]
        title = normalize_excerpt(row.get("title", ""))
        abstract = normalize_excerpt(row.get("abstract_excerpt", ""))
        claim = normalize_excerpt(row.get("claim_excerpt", ""))
        key = (tid, pn)
        patent_index[key] = {
            "title": title,
            "title_mentions": _detect_subsystems_in_text(title),
            "abstract_excerpt": abstract,
            "abstract_mentions": _detect_subsystems_in_text(abstract),
            "claim_excerpt": claim,
            "claim_mentions": _detect_subsystems_in_text(claim),
            "selection_reason": row.get("selection_reason", ""),
            "source_file": row.get("source_file", ""),
            "app_year": row.get("app_year", ""),
        }
        topic_patents[tid].append(pn)
print(f"  topic_patent_evidence.csv: {len(patent_index)} entries across {len(topic_patents)} topics")

# Build topic -> role map
topic_role_map = {}
for row in topic_rows:
    tid = row["bertopic_id"]
    topic_role_map[tid] = parse_role_map(row.get("role_proposal", ""))

# ── Evidence lookup functions (location-aware) ────────────

def find_subsystem_evidence(topic_id, subsystem_id, allowed_patents):
    """Find a patent whose CLAIM/ABSTRACT/TITLE contains the target subsystem.
    allowed_patents: set of patent numbers to search within.
    Returns (patent_number, location, excerpt) or (None, None, None)."""
    for pn in topic_patents.get(topic_id, []):
        if allowed_patents and pn not in allowed_patents:
            continue
        info = patent_index.get((topic_id, pn))
        if not info:
            continue
        if subsystem_id in info["claim_mentions"] and info["claim_excerpt"]:
            return (pn, "CLAIM", info["claim_excerpt"])
    for pn in topic_patents.get(topic_id, []):
        if allowed_patents and pn not in allowed_patents:
            continue
        info = patent_index.get((topic_id, pn))
        if not info:
            continue
        if subsystem_id in info["abstract_mentions"] and info["abstract_excerpt"]:
            return (pn, "ABSTRACT", info["abstract_excerpt"])
    for pn in topic_patents.get(topic_id, []):
        if allowed_patents and pn not in allowed_patents:
            continue
        info = patent_index.get((topic_id, pn))
        if not info:
            continue
        if subsystem_id in info["title_mentions"] and info["title"]:
            return (pn, "TITLE", info["title"])
    return (None, None, None)

def find_coimplementation_evidence(topic_id, src_subsys, tgt_subsys, allowed_patents):
    """Find a patent whose CLAIM or ABSTRACT contains BOTH subsystems in the SAME excerpt.
    Returns (pn, location, excerpt, src_mention, tgt_mention) or (None,)*5."""
    # Check CLAIM first (both in same claim)
    for pn in topic_patents.get(topic_id, []):
        if allowed_patents and pn not in allowed_patents:
            continue
        info = patent_index.get((topic_id, pn))
        if not info:
            continue
        if src_subsys in info["claim_mentions"] and tgt_subsys in info["claim_mentions"] and info["claim_excerpt"]:
            src_m = _extract_mention(info["claim_excerpt"], src_subsys)
            tgt_m = _extract_mention(info["claim_excerpt"], tgt_subsys)
            if src_m and tgt_m:
                return (pn, "CLAIM", info["claim_excerpt"], src_m, tgt_m)
    # Check ABSTRACT (both in same abstract)
    for pn in topic_patents.get(topic_id, []):
        if allowed_patents and pn not in allowed_patents:
            continue
        info = patent_index.get((topic_id, pn))
        if not info:
            continue
        if src_subsys in info["abstract_mentions"] and tgt_subsys in info["abstract_mentions"] and info["abstract_excerpt"]:
            src_m = _extract_mention(info["abstract_excerpt"], src_subsys)
            tgt_m = _extract_mention(info["abstract_excerpt"], tgt_subsys)
            if src_m and tgt_m:
                return (pn, "ABSTRACT", info["abstract_excerpt"], src_m, tgt_m)
    return (None, None, None, "", "")

def find_safety_evidence(topic_id):
    """Find a patent whose claim/abstract contains safety keywords.
    Returns (pn, location, excerpt, safety_terms, selection_reason, source_file) or (None,)*6."""
    for pn in topic_patents.get(topic_id, []):
        info = patent_index.get((topic_id, pn))
        if not info:
            continue
        for location, excerpt in [("CLAIM", info["claim_excerpt"]), ("ABSTRACT", info["abstract_excerpt"])]:
            if not excerpt:
                continue
            terms = _detect_safety_keywords(excerpt)
            if terms:
                return (pn, location, excerpt, ";".join(terms),
                        info["selection_reason"], info["source_file"])
    return (None, None, None, "", "", "")

# ── 2. Topic Safety Queue (20 rows) ──────────────────────

print("\nGenerating topic safety queue with evidence...")
safety_rows = []
seen_topics = set()
safety_ev_stats = {"FOUND": 0, "INSUFFICIENT": 0}

for row in topic_rows:
    tid = row["bertopic_id"]
    if tid in seen_topics:
        continue
    seen_topics.add(tid)

    ev_pn, ev_loc, ev_excerpt, ev_terms, ev_reason, ev_file = find_safety_evidence(tid)

    if ev_pn:
        ev_status = "FOUND"
        safety_ev_stats["FOUND"] += 1
    else:
        ev_status = "INSUFFICIENT"
        safety_ev_stats["INSUFFICIENT"] += 1

    safety_rows.append({
        "bertopic_id": tid,
        "bertopic_name": row["bertopic_name"],
        "proposed_safety": row.get("deepseek_safety_proposal", "").strip(),
        "safety_rationale": normalize_excerpt(row.get("rationale", "")),
        "supporting_patent_numbers": row.get("supporting_patent_numbers", ""),
        "evidence_patent_number": ev_pn or "",
        "evidence_location": ev_loc or "",
        "exact_evidence_excerpt": ev_excerpt or "",
        "safety_evidence_terms": ev_terms or "",
        "evidence_status": ev_status,
        "evidence_selection_reason": ev_reason or "",
        "evidence_source_file": ev_file or "",
        "human_safety_judgment": "",
        "reviewer_confidence": "",
        "reviewer_note": "",
    })

assert len(safety_rows) == 20

safety_fields = [
    "bertopic_id", "bertopic_name", "proposed_safety", "safety_rationale",
    "supporting_patent_numbers",
    "evidence_patent_number", "evidence_location", "exact_evidence_excerpt",
    "safety_evidence_terms", "evidence_status",
    "evidence_selection_reason", "evidence_source_file",
    "human_safety_judgment", "reviewer_confidence", "reviewer_note",
]
with open(os.path.join(OUT, "P1_topic_safety_review_queue.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=safety_fields, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(safety_rows)
print(f"  P1_topic_safety_review_queue.csv: {len(safety_rows)} rows")
print(f"  Evidence: {safety_ev_stats['FOUND']} FOUND, {safety_ev_stats['INSUFFICIENT']} INSUFFICIENT")

# ── 3. Topic×Subsystem Queue (121 rows, location-aware) ──

print("\nGenerating topic×subsystem queue with location-aware evidence...")
queue_rows = []
evidence_stats = {"FOUND": 0, "INSUFFICIENT": 0, "NO_DIRECT_EVIDENCE": 0}

for row in topic_rows:
    tid = row["bertopic_id"]
    tname = row["bertopic_name"]
    subsystems = parse_semicolon(row.get("deepseek_subsystem_proposal", ""))
    role_map = parse_role_map(row.get("role_proposal", ""))
    topic_patent_set = set(parse_semicolon(row.get("supporting_patent_numbers", "")))

    for subsys in subsystems:
        role = role_map.get(subsys, "")

        ev_pn, ev_loc, ev_excerpt = find_subsystem_evidence(tid, subsys, topic_patent_set)

        if ev_pn:
            evidence_status = "FOUND"
            evidence_stats["FOUND"] += 1
            # Ensure patent is in supporting list (should be by construction, but verify)
            assert ev_pn in topic_patent_set, f"BUG: {tid}/{subsys}: {ev_pn} not in supporting list"
        elif role in ("PRIMARY", "SECONDARY"):
            evidence_status = "INSUFFICIENT"
            evidence_stats["INSUFFICIENT"] += 1
        else:
            evidence_status = "NO_DIRECT_EVIDENCE"
            evidence_stats["NO_DIRECT_EVIDENCE"] += 1

        queue_rows.append({
            "bertopic_id": tid,
            "bertopic_name": tname,
            "proposed_safety": row.get("deepseek_safety_proposal", "").strip(),
            "subsystem_id": subsys,
            "proposed_role": role,
            "supporting_patent_numbers": ";".join(sorted(topic_patent_set)),
            "evidence_patent_number": ev_pn or "",
            "evidence_location": ev_loc or "",
            "exact_evidence_excerpt": ev_excerpt or "",
            "evidence_status": evidence_status,
            "human_subsystem_decision": "",
            "human_role_judgment": "",
            "reviewer_confidence": "",
            "reviewer_note": "",
        })

assert len(queue_rows) == 121

subsys_fields = [
    "bertopic_id", "bertopic_name", "proposed_safety", "subsystem_id",
    "proposed_role", "supporting_patent_numbers",
    "evidence_patent_number", "evidence_location", "exact_evidence_excerpt",
    "evidence_status",
    "human_subsystem_decision", "human_role_judgment",
    "reviewer_confidence", "reviewer_note",
]
with open(os.path.join(OUT, "P1_topic_review_queue.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=subsys_fields, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(queue_rows)
print(f"  P1_topic_review_queue.csv: {len(queue_rows)} rows")
print(f"  Evidence: {evidence_stats['FOUND']} FOUND, {evidence_stats['INSUFFICIENT']} INSUFFICIENT, {evidence_stats['NO_DIRECT_EVIDENCE']} NO_DIRECT_EVIDENCE")

# ── 4. DIRECT_FLOW Queue (1 row + CN201020717Y flag) ──────

print("\nGenerating DIRECT_FLOW queue...")
direct_rows = [r for r in interaction_rows if r.get("evidence_type_proposal", "").strip() == "DIRECT_FLOW"]

df_out = []
for r in direct_rows:
    pn = r.get("patent_number", "").strip()
    source_integrity = "ABSTRACT_CLAIM_MISMATCH" if pn == "CN201020717Y" else ""

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
    w = csv.DictWriter(f, fieldnames=df_fields, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(df_out)
print(f"  P1_direct_flow_review_queue.csv: {len(df_out)} rows")

# ── 5. CO_IMPLEMENTATION Queue (100 rows, location-aware) ─

print("\nGenerating CO_IMPLEMENTATION queue with location-aware evidence...")
co_rows = [r for r in interaction_rows if r.get("evidence_type_proposal", "").strip() == "CO_IMPLEMENTATION"]
print(f"  CO_IMPLEMENTATION: {len(co_rows)} rows")

co_evidence_stats = {"FOUND": 0, "INSUFFICIENT": 0}
co_with_priority = []

for r in co_rows:
    tid = r.get("bertopic_id", "")
    src = r.get("source_subsystem", "").strip()
    tgt = r.get("target_subsystem", "").strip()
    roles = topic_role_map.get(tid, {})

    def _priority(src, tgt, roles):
        if src in ("SAFETY_MONITORING", "EMERGENCY_FAILSAFE") or \
           tgt in ("SAFETY_MONITORING", "EMERGENCY_FAILSAFE"):
            return 1
        s_r, t_r = roles.get(src, ""), roles.get(tgt, "")
        if s_r == "PRIMARY" and t_r == "PRIMARY":
            return 2
        if "PRIMARY" in {s_r, t_r} and "SECONDARY" in {s_r, t_r}:
            return 3
        return 4

    pri = _priority(src, tgt, roles)

    # Search within the row's supporting_patent_numbers
    row_patents = set(parse_semicolon(r.get("supporting_patent_numbers", "")))
    # Also allow topic-level patents (will be added to supporting if used)
    topic_patent_set = set(topic_patents.get(tid, []))

    ev_pn, ev_loc, ev_excerpt, src_m, tgt_m = \
        find_coimplementation_evidence(tid, src, tgt, row_patents)

    # If not found in row-specific patents, try full topic list
    supplemental_pn = None
    if not ev_pn:
        ev_pn, ev_loc, ev_excerpt, src_m, tgt_m = \
            find_coimplementation_evidence(tid, src, tgt, set())
        if ev_pn and ev_pn not in row_patents:
            supplemental_pn = ev_pn

    if ev_pn:
        ev_status = "FOUND"
        co_evidence_stats["FOUND"] += 1
        # Build supporting list (add supplemental if needed)
        if supplemental_pn:
            row_patents.add(supplemental_pn)
        supp_list = ";".join(sorted(row_patents))
    else:
        ev_status = "INSUFFICIENT"
        co_evidence_stats["INSUFFICIENT"] += 1
        supp_list = r.get("supporting_patent_numbers", "")

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
        "source_mention": src_m,
        "target_mention": tgt_m,
        "exact_evidence_excerpt": ev_excerpt or "",
        "evidence_status": ev_status,
        "evidence_selection_reason": patent_index.get((tid, ev_pn), {}).get("selection_reason", "") if ev_pn else "",
        "evidence_source_file": patent_index.get((tid, ev_pn), {}).get("source_file", "") if ev_pn else "",
        "supporting_patent_numbers": supp_list,
        "standard_clauses": r.get("standard_clauses", ""),
        "rationale": r.get("rationale", ""),
        "human_coimplementation_decision": "",
        "reviewer_confidence": "",
        "reviewer_note": "",
    }))

co_with_priority.sort(key=lambda x: (x[0], int(x[1]["bertopic_id"])))

co_fields = [
    "review_priority", "bertopic_id", "bertopic_name",
    "source_subsystem", "target_subsystem",
    "evidence_type_proposal", "evidence_strength_proposal",
    "evidence_patent_number", "evidence_location",
    "source_mention", "target_mention",
    "exact_evidence_excerpt", "evidence_status",
    "evidence_selection_reason", "evidence_source_file",
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

pri_counts = Counter(r["review_priority"] for r in co_out)
for p in sorted(pri_counts):
    print(f"    Priority {p}: {pri_counts[p]} rows")

# ── 6. Content-level self-validation ──────────────────────

print("\n" + "=" * 60)
print("CONTENT-LEVEL SELF-VALIDATION")
print("=" * 60)
errors = []

# 6a. Topic×subsystem: FOUND rows must have excerpt containing subsystem
print("\nChecking topic×subsystem FOUND rows...")
ts_found = [r for r in queue_rows if r["evidence_status"] == "FOUND"]
ts_found_content_ok = 0
for i, r in enumerate(ts_found):
    pn = r["evidence_patent_number"]
    loc = r["evidence_location"]
    excerpt = r["exact_evidence_excerpt"]
    subsys = r["subsystem_id"]
    tid = r["bertopic_id"]

    # excerpt non-empty
    if not excerpt:
        errors.append(f"TS[{i}] {tid}/{subsys}: FOUND but excerpt empty")
        continue

    # evidence_patent_number in supporting list
    supp = set(parse_semicolon(r["supporting_patent_numbers"]))
    if pn not in supp:
        errors.append(f"TS[{i}] {tid}/{subsys}: {pn} NOT in supporting list {supp}")

    # subsystem must be detected in excerpt
    detected = _detect_subsystems_in_text(excerpt)
    if subsys not in detected:
        errors.append(f"TS[{i}] {tid}/{subsys}: {subsys} NOT detected in {loc} excerpt (pn={pn})")
        continue

    ts_found_content_ok += 1

print(f"  {ts_found_content_ok}/{len(ts_found)} FOUND rows pass content check")

# 6b. CO_IMPLEMENTATION: FOUND rows must have BOTH subsystems in same excerpt
print("\nChecking CO_IMPLEMENTATION FOUND rows...")
co_found = [r for r in co_out if r["evidence_status"] == "FOUND"]
co_found_content_ok = 0
for i, r in enumerate(co_found):
    pn = r["evidence_patent_number"]
    excerpt = r["exact_evidence_excerpt"]
    src = r["source_subsystem"]
    tgt = r["target_subsystem"]
    src_m = r["source_mention"]
    tgt_m = r["target_mention"]

    if not excerpt:
        errors.append(f"CO[{i}] {src}↔{tgt}: FOUND but excerpt empty")
        continue

    # Both subsystems in same excerpt
    detected = _detect_subsystems_in_text(excerpt)
    if src not in detected or tgt not in detected:
        errors.append(f"CO[{i}] {src}↔{tgt}: not both in excerpt (detected={detected}, pn={pn})")
        continue

    # Mentions must be actual text
    excerpt_lower = excerpt.lower()
    if src_m and src_m not in excerpt_lower:
        errors.append(f"CO[{i}] {src}↔{tgt}: source_mention '{src_m}' not in excerpt")
        continue
    if tgt_m and tgt_m not in excerpt_lower:
        errors.append(f"CO[{i}] {src}↔{tgt}: target_mention '{tgt_m}' not in excerpt")
        continue

    # evidence_patent_number in supporting list
    supp = set(parse_semicolon(r["supporting_patent_numbers"]))
    if pn not in supp:
        errors.append(f"CO[{i}] {src}↔{tgt}: {pn} NOT in supporting list")

    co_found_content_ok += 1

print(f"  {co_found_content_ok}/{len(co_found)} FOUND rows pass content check")

# 6c. Safety queue FOUND rows
print("\nChecking safety queue FOUND rows...")
safety_found = [r for r in safety_rows if r["evidence_status"] == "FOUND"]
safety_found_content_ok = 0
for i, r in enumerate(safety_found):
    pn = r["evidence_patent_number"]
    excerpt = r["exact_evidence_excerpt"]
    terms = r["safety_evidence_terms"]

    if not pn or not excerpt or not terms:
        errors.append(f"SAFETY[{i}] {r['bertopic_id']}: FOUND but missing pn/excerpt/terms")
        continue

    # Safety terms must be in excerpt
    excerpt_lower = excerpt.lower()
    for term in parse_semicolon(terms):
        if term not in excerpt_lower:
            errors.append(f"SAFETY[{i}] {r['bertopic_id']}: term '{term}' not in excerpt")
            break
    else:
        safety_found_content_ok += 1

print(f"  {safety_found_content_ok}/{len(safety_found)} FOUND rows pass content check")

# 6d. Patent binding: all FOUND evidence_pn in supporting list
print("\nChecking patent number binding...")
pn_binding_ok = 0
pn_binding_total = 0
for r in queue_rows:
    if r["evidence_status"] == "FOUND":
        pn_binding_total += 1
        supp = set(parse_semicolon(r["supporting_patent_numbers"]))
        if r["evidence_patent_number"] in supp:
            pn_binding_ok += 1
for r in co_out:
    if r["evidence_status"] == "FOUND":
        pn_binding_total += 1
        supp = set(parse_semicolon(r["supporting_patent_numbers"]))
        if r["evidence_patent_number"] in supp:
            pn_binding_ok += 1
print(f"  {pn_binding_ok}/{pn_binding_total} FOUND rows have evidence_pn in supporting list")

# 6e. Row count invariants
assert len(safety_rows) == 20, f"Safety: {len(safety_rows)}"
assert len(queue_rows) == 121, f"Topic×subsystem: {len(queue_rows)}"
assert len(df_out) == 1, f"DIRECT_FLOW: {len(df_out)}"
assert len(co_out) == 100, f"CO_IMPLEMENTATION: {len(co_out)}"
print("\nRow counts: 20+121+1+100 ✓")

# 6f. All human fields empty
for label, rows, fields in [
    ("safety", safety_rows, ["human_safety_judgment", "reviewer_confidence", "reviewer_note"]),
    ("subsys", queue_rows, ["human_subsystem_decision", "human_role_judgment", "reviewer_confidence", "reviewer_note"]),
    ("direct", df_out, ["human_interaction_decision", "human_strength_judgment", "reviewer_confidence", "reviewer_note"]),
    ("coimpl", co_out, ["human_coimplementation_decision", "reviewer_confidence", "reviewer_note"]),
]:
    for i, r in enumerate(rows):
        for f in fields:
            if r.get(f, "") != "":
                errors.append(f"{label}[{i}]: {f} not empty")
print("All human fields empty ✓")

# 6g. CN201020717Y
assert df_out[0]["patent_number"] == "CN201020717Y"
assert df_out[0]["source_integrity_flag"] == "ABSTRACT_CLAIM_MISMATCH"
print("CN201020717Y flag ✓")

# 6h. No confirmed/final files
for fname in os.listdir(OUT):
    lower = fname.lower()
    for fb in ["final", "confirmed", "validated"]:
        if fb in lower and not fname.startswith("_generate") and not fname.startswith("P1_human_review"):
            errors.append(f"Forbidden file: {fname}")
print("No confirmed/final files ✓")

# ── Summary ──
print("\n" + "=" * 60)
print("EVIDENCE COVERAGE SUMMARY")
print("=" * 60)

# Safety
print(f"\nSafety Queue: {len(safety_rows)} rows")
print(f"  FOUND:        {safety_ev_stats['FOUND']} ({100*safety_ev_stats['FOUND']/20:.0f}%)")
print(f"  INSUFFICIENT: {safety_ev_stats['INSUFFICIENT']} ({100*safety_ev_stats['INSUFFICIENT']/20:.0f}%)")

# Topic×Subsystem
total_ts = len(queue_rows)
found_ts = evidence_stats["FOUND"]
insuf_ts = evidence_stats["INSUFFICIENT"]
node_ts = evidence_stats["NO_DIRECT_EVIDENCE"]
print(f"\nTopic×Subsystem: {total_ts} rows")
print(f"  FOUND:              {found_ts} ({100*found_ts/total_ts:.1f}%)")
print(f"  INSUFFICIENT:       {insuf_ts} ({100*insuf_ts/total_ts:.1f}%)")
print(f"  NO_DIRECT_EVIDENCE: {node_ts} ({100*node_ts/total_ts:.1f}%)")
# Only FOUND rows should have content checked
if ts_found:
    pct = 100 * ts_found_content_ok / len(ts_found)
    print(f"  Content check pass: {ts_found_content_ok}/{len(ts_found)} ({pct:.0f}%)")

# CO_IMPLEMENTATION
total_co = len(co_out)
found_co = co_evidence_stats["FOUND"]
insuf_co = co_evidence_stats["INSUFFICIENT"]
print(f"\nCO_IMPLEMENTATION: {total_co} rows")
print(f"  FOUND:        {found_co} ({100*found_co/total_co:.1f}%)")
print(f"  INSUFFICIENT: {insuf_co} ({100*insuf_co/total_co:.1f}%)")
if co_found:
    pct = 100 * co_found_content_ok / len(co_found)
    print(f"  Content check pass: {co_found_content_ok}/{len(co_found)} ({pct:.0f}%)")

# Patent binding
if pn_binding_total:
    pct = 100 * pn_binding_ok / pn_binding_total
    print(f"\nPatent binding: {pn_binding_ok}/{pn_binding_total} ({pct:.0f}%)")

# Per-role evidence
print("\nPer-Role Evidence:")
for role in ["PRIMARY", "SECONDARY", "CONTEXT_ONLY"]:
    role_rows = [r for r in queue_rows if r["proposed_role"] == role]
    r_found = sum(1 for r in role_rows if r["evidence_status"] == "FOUND")
    r_insuf = sum(1 for r in role_rows if r["evidence_status"] == "INSUFFICIENT")
    r_node = sum(1 for r in role_rows if r["evidence_status"] == "NO_DIRECT_EVIDENCE")
    print(f"  {role}: {len(role_rows)} rows — {r_found} FOUND, {r_insuf} INSUFFICIENT, {r_node} NO_DIRECT_EVIDENCE")

# Final
if errors:
    print(f"\n❌ {len(errors)} CONTENT VALIDATION ERROR(S):")
    for e in errors[:20]:
        print(f"  - {e}")
    if len(errors) > 20:
        print(f"  ... and {len(errors)-20} more")
    sys.exit(1)
else:
    print(f"\n✅ All content-level validation checks passed.")

# Files list
print(f"\nFiles in {OUT}:")
for f in sorted(os.listdir(OUT)):
    fpath = os.path.join(OUT, f)
    if os.path.isfile(fpath):
        print(f"  {f} ({os.path.getsize(fpath):,} bytes)")
