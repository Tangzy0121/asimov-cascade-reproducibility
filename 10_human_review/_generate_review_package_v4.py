"""
V4: Boundary-aware keyword detection + CN201020717Y abstract exclusion.

Key changes from V3:
1. Uses shared evidence_detector module (boundary-aware regex)
2. Excludes CN201020717Y ABSTRACT/TITLE from subsystem/safety evidence
3. Proper word boundaries on short words (STO, ROS, PID, SLAM, bus, trip)
4. High-precision EMERGENCY_FAILSAFE and SYSTEM_INTEGRATION patterns
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

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(PROJECT, "scripts"))
from evidence_detector import (
    SUBSYSTEM_IDS, detect_subsystems_in_text, detect_safety_keywords_in_text,
    extract_mention, is_location_excluded, get_exclusion_reason,
    EDGE_ENTITY_TERMS, REQUIRED_SUBSYSTEM_IDS,
)

# ── Helpers ──

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

# ── 1. Load data ──

print("Loading data...")

topic_rows = []
with open(TOPIC_REVIEW, "r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        topic_rows.append(row)
print(f"  topic_subsystem_review.csv: {len(topic_rows)} rows")

interaction_rows = []
with open(INTERACTION_REVIEW, "r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        interaction_rows.append(row)
print(f"  interaction_evidence_review.csv: {len(interaction_rows)} rows")

# Patent evidence index
patent_index = {}
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
            "title_mentions": detect_subsystems_in_text(title) if not is_location_excluded(pn, "TITLE") else set(),
            "title_excluded": is_location_excluded(pn, "TITLE"),
            "title_exclusion_reason": get_exclusion_reason(pn, "TITLE"),
            "abstract_excerpt": abstract,
            "abstract_mentions": detect_subsystems_in_text(abstract) if not is_location_excluded(pn, "ABSTRACT") else set(),
            "abstract_excluded": is_location_excluded(pn, "ABSTRACT"),
            "abstract_exclusion_reason": get_exclusion_reason(pn, "ABSTRACT"),
            "claim_excerpt": claim,
            "claim_mentions": detect_subsystems_in_text(claim),
            "selection_reason": row.get("selection_reason", ""),
            "source_file": row.get("source_file", ""),
            "app_year": row.get("app_year", ""),
        }
        topic_patents[tid].append(pn)
print(f"  topic_patent_evidence.csv: {len(patent_index)} entries across {len(topic_patents)} topics")

topic_role_map = {}
for row in topic_rows:
    tid = row["bertopic_id"]
    topic_role_map[tid] = parse_role_map(row.get("role_proposal", ""))

# Verify CN201020717Y exclusion
cn_key = None
for (tid, pn), info in patent_index.items():
    if pn == "CN201020717Y":
        cn_key = (tid, pn)
        break
if cn_key:
    info = patent_index[cn_key]
    assert info["abstract_excluded"], "CN201020717Y ABSTRACT must be excluded!"
    assert info["title_excluded"], "CN201020717Y TITLE must be excluded!"
    print("  CN201020717Y ABSTRACT/TITLE excluded ✓")

# ── Evidence lookup functions (boundary-aware) ──

def find_subsystem_evidence(topic_id, subsystem_id, allowed_patents):
    """Find patent whose CLAIM/ABSTRACT/TITLE contains target subsystem (boundary-aware).
    Respects location exclusions (e.g., CN201020717Y abstract)."""
    # CLAIM first
    for pn in topic_patents.get(topic_id, []):
        if allowed_patents and pn not in allowed_patents:
            continue
        info = patent_index.get((topic_id, pn))
        if not info:
            continue
        if subsystem_id in info["claim_mentions"] and info["claim_excerpt"]:
            return (pn, "CLAIM", info["claim_excerpt"])
    # ABSTRACT (respect exclusions)
    for pn in topic_patents.get(topic_id, []):
        if allowed_patents and pn not in allowed_patents:
            continue
        info = patent_index.get((topic_id, pn))
        if not info:
            continue
        if subsystem_id in info["abstract_mentions"] and info["abstract_excerpt"]:
            return (pn, "ABSTRACT", info["abstract_excerpt"])
    # TITLE (respect exclusions)
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
    """Find patent where CLAIM or ABSTRACT contains BOTH subsystems (same excerpt, boundary-aware)."""
    # CLAIM
    for pn in topic_patents.get(topic_id, []):
        if allowed_patents and pn not in allowed_patents:
            continue
        info = patent_index.get((topic_id, pn))
        if not info:
            continue
        if (src_subsys in info["claim_mentions"] and
            tgt_subsys in info["claim_mentions"] and
            info["claim_excerpt"]):
            src_m = extract_mention(info["claim_excerpt"], src_subsys)
            tgt_m = extract_mention(info["claim_excerpt"], tgt_subsys)
            if src_m and tgt_m:
                return (pn, "CLAIM", info["claim_excerpt"], src_m, tgt_m)
    # ABSTRACT (respect exclusions)
    for pn in topic_patents.get(topic_id, []):
        if allowed_patents and pn not in allowed_patents:
            continue
        info = patent_index.get((topic_id, pn))
        if not info:
            continue
        if (src_subsys in info["abstract_mentions"] and
            tgt_subsys in info["abstract_mentions"] and
            info["abstract_excerpt"]):
            src_m = extract_mention(info["abstract_excerpt"], src_subsys)
            tgt_m = extract_mention(info["abstract_excerpt"], tgt_subsys)
            if src_m and tgt_m:
                return (pn, "ABSTRACT", info["abstract_excerpt"], src_m, tgt_m)
    return (None, None, None, "", "")

def find_safety_evidence(topic_id):
    """Find patent whose claim/abstract contains boundary-aware safety keywords."""
    for pn in topic_patents.get(topic_id, []):
        info = patent_index.get((topic_id, pn))
        if not info:
            continue
        for location, excerpt in [
            ("CLAIM", info["claim_excerpt"]),
            ("ABSTRACT", info["abstract_excerpt"]),
        ]:
            if not excerpt:
                continue
            # Skip excluded locations
            if is_location_excluded(pn, location):
                continue
            terms = detect_safety_keywords_in_text(excerpt)
            if terms:
                return (pn, location, excerpt, ";".join(terms),
                        info["selection_reason"], info["source_file"])
    return (None, None, None, "", "", "")

# ── 2. Topic Safety Queue ──

print("\nGenerating topic safety queue...")
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
        "human_harm_link": "",
        "cascade_role": "",
        "plausible_cascade_path": "",
        "scope_limitation": "",
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
    "human_safety_judgment", "human_harm_link", "cascade_role",
    "plausible_cascade_path", "scope_limitation",
    "reviewer_confidence", "reviewer_note",
]
with open(os.path.join(OUT, "P1_topic_safety_review_queue.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=safety_fields, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(safety_rows)
print(f"  Safety: {len(safety_rows)} rows, {safety_ev_stats['FOUND']} FOUND, {safety_ev_stats['INSUFFICIENT']} INSUFFICIENT")

# ── 3. Topic×Subsystem Queue ──

print("\nGenerating topic×subsystem queue...")
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
            assert ev_pn in topic_patent_set, f"BUG: {tid}/{subsys}: {ev_pn} not in supporting"
        elif role in ("PRIMARY", "SECONDARY"):
            evidence_status = "INSUFFICIENT"
            evidence_stats["INSUFFICIENT"] += 1
        else:
            evidence_status = "NO_DIRECT_EVIDENCE"
            evidence_stats["NO_DIRECT_EVIDENCE"] += 1

        queue_rows.append({
            "bertopic_id": tid, "bertopic_name": tname,
            "proposed_safety": row.get("deepseek_safety_proposal", "").strip(),
            "subsystem_id": subsys, "proposed_role": role,
            "supporting_patent_numbers": ";".join(sorted(topic_patent_set)),
            "evidence_patent_number": ev_pn or "",
            "evidence_location": ev_loc or "",
            "exact_evidence_excerpt": ev_excerpt or "",
            "evidence_status": evidence_status,
            "human_subsystem_decision": "", "human_role_judgment": "",
            "reviewer_confidence": "", "reviewer_note": "",
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
print(f"  Topic×Subsystem: {len(queue_rows)} rows, {evidence_stats['FOUND']} FOUND, {evidence_stats['INSUFFICIENT']} INSUFFICIENT, {evidence_stats['NO_DIRECT_EVIDENCE']} NO_DIRECT_EVIDENCE")

# ── 4. DIRECT_FLOW Queue ──

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
        "human_interaction_decision": "", "human_strength_judgment": "",
        "reviewer_confidence": "", "reviewer_note": "",
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
print(f"  DIRECT_FLOW: {len(df_out)} rows")

# ── 5. CO_IMPLEMENTATION Queue ──

print("\nGenerating CO_IMPLEMENTATION queue...")
co_rows = [r for r in interaction_rows if r.get("evidence_type_proposal", "").strip() == "CO_IMPLEMENTATION"]
co_evidence_stats = {"FOUND": 0, "INSUFFICIENT": 0}
co_with_priority = []

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

for r in co_rows:
    tid = r.get("bertopic_id", "")
    src = r.get("source_subsystem", "").strip()
    tgt = r.get("target_subsystem", "").strip()
    roles = topic_role_map.get(tid, {})
    pri = _priority(src, tgt, roles)

    row_patents = set(parse_semicolon(r.get("supporting_patent_numbers", "")))

    ev_pn, ev_loc, ev_excerpt, src_m, tgt_m = \
        find_coimplementation_evidence(tid, src, tgt, row_patents)

    supplemental_pn = None
    if not ev_pn:
        ev_pn, ev_loc, ev_excerpt, src_m, tgt_m = \
            find_coimplementation_evidence(tid, src, tgt, set())
        if ev_pn and ev_pn not in row_patents:
            supplemental_pn = ev_pn

    if ev_pn:
        ev_status = "FOUND"
        co_evidence_stats["FOUND"] += 1
        if supplemental_pn:
            row_patents.add(supplemental_pn)
        supp_list = ";".join(sorted(row_patents))
    else:
        ev_status = "INSUFFICIENT"
        co_evidence_stats["INSUFFICIENT"] += 1
        supp_list = r.get("supporting_patent_numbers", "")

    co_with_priority.append((pri, {
        "review_priority": pri, "bertopic_id": tid,
        "bertopic_name": r.get("bertopic_name", ""),
        "source_subsystem": src, "target_subsystem": tgt,
        "evidence_type_proposal": "CO_IMPLEMENTATION",
        "evidence_strength_proposal": r.get("evidence_strength_proposal", ""),
        "evidence_patent_number": ev_pn or "",
        "evidence_location": ev_loc or "",
        "source_mention": src_m, "target_mention": tgt_m,
        "exact_evidence_excerpt": ev_excerpt or "",
        "evidence_status": ev_status,
        "evidence_selection_reason": patent_index.get((tid, ev_pn), {}).get("selection_reason", "") if ev_pn else "",
        "evidence_source_file": patent_index.get((tid, ev_pn), {}).get("source_file", "") if ev_pn else "",
        "supporting_patent_numbers": supp_list,
        "standard_clauses": r.get("standard_clauses", ""),
        "rationale": r.get("rationale", ""),
        "human_coimplementation_decision": "",
        "reviewer_confidence": "", "reviewer_note": "",
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
print(f"  CO_IMPLEMENTATION: {len(co_out)} rows, {co_evidence_stats['FOUND']} FOUND, {co_evidence_stats['INSUFFICIENT']} INSUFFICIENT")
pri_counts = Counter(r["review_priority"] for r in co_out)
for p in sorted(pri_counts):
    print(f"    Priority {p}: {pri_counts[p]} rows")

# ── 6. Content-level self-validation ──

print("\n" + "=" * 60)
print("CONTENT-LEVEL SELF-VALIDATION (V4 boundary-aware)")
print("=" * 60)
errors = []

# 6a. Topic×subsystem FOUND
print("\nChecking topic×subsystem FOUND rows...")
ts_found = [r for r in queue_rows if r["evidence_status"] == "FOUND"]
ts_found_ok = 0
for i, r in enumerate(ts_found):
    excerpt = r["exact_evidence_excerpt"]
    subsys = r["subsystem_id"]
    pn = r["evidence_patent_number"]
    if not excerpt:
        errors.append(f"TS[{i}] {r['bertopic_id']}/{subsys}: FOUND but excerpt empty")
        continue
    detected = detect_subsystems_in_text(excerpt)
    if subsys not in detected:
        errors.append(f"TS[{i}] {r['bertopic_id']}/{subsys}: NOT in {r['evidence_location']} excerpt (pn={pn})")
        continue
    supp = set(parse_semicolon(r["supporting_patent_numbers"]))
    if pn not in supp:
        errors.append(f"TS[{i}]: {pn} not in supporting")
    ts_found_ok += 1
print(f"  {ts_found_ok}/{len(ts_found)} pass")

# 6b. CO_IMPLEMENTATION FOUND
print("\nChecking CO_IMPLEMENTATION FOUND rows...")
co_found = [r for r in co_out if r["evidence_status"] == "FOUND"]
co_found_ok = 0
for i, r in enumerate(co_found):
    excerpt = r["exact_evidence_excerpt"]
    src, tgt = r["source_subsystem"], r["target_subsystem"]
    pn = r["evidence_patent_number"]
    if not excerpt:
        errors.append(f"CO[{i}] {src}<->{tgt}: FOUND but excerpt empty")
        continue
    detected = detect_subsystems_in_text(excerpt)
    if src not in detected or tgt not in detected:
        errors.append(f"CO[{i}] {src}<->{tgt}: not both in excerpt (detected={detected})")
        continue
    excerpt_lower = excerpt.lower()
    for mfield, mval in [("source_mention", r["source_mention"]), ("target_mention", r["target_mention"])]:
        if mval and mval.lower() not in excerpt_lower:
            errors.append(f"CO[{i}]: {mfield} '{mval}' not in excerpt")
            break
    else:
        supp = set(parse_semicolon(r["supporting_patent_numbers"]))
        if pn not in supp:
            errors.append(f"CO[{i}]: {pn} not in supporting")
        co_found_ok += 1
print(f"  {co_found_ok}/{len(co_found)} pass")

# 6c. Safety queue
print("\nChecking safety queue FOUND rows...")
safety_found = [r for r in safety_rows if r["evidence_status"] == "FOUND"]
safety_found_ok = 0
for i, r in enumerate(safety_found):
    excerpt = r["exact_evidence_excerpt"]
    if not r["evidence_patent_number"] or not excerpt or not r["safety_evidence_terms"]:
        errors.append(f"SAFETY[{i}] {r['bertopic_id']}: FOUND but missing fields")
        continue
    excerpt_lower = excerpt.lower()
    all_ok = True
    for term in parse_semicolon(r["safety_evidence_terms"]):
        if term.lower() not in excerpt_lower:
            errors.append(f"SAFETY[{i}] {r['bertopic_id']}: term '{term}' not in excerpt")
            all_ok = False
            break
    if all_ok:
        safety_found_ok += 1
print(f"  {safety_found_ok}/{len(safety_found)} pass")

# 6d. Patent binding
print("\nChecking patent number binding...")
pn_ok = pn_total = 0
for r in queue_rows:
    if r["evidence_status"] == "FOUND":
        pn_total += 1
        if r["evidence_patent_number"] in set(parse_semicolon(r["supporting_patent_numbers"])):
            pn_ok += 1
for r in co_out:
    if r["evidence_status"] == "FOUND":
        pn_total += 1
        if r["evidence_patent_number"] in set(parse_semicolon(r["supporting_patent_numbers"])):
            pn_ok += 1
print(f"  {pn_ok}/{pn_total} ({100*pn_ok/pn_total:.0f}%)" if pn_total else "  N/A")

# 6e. Anti-pattern: CN201020717Y abstract NOT used for anything
print("\nChecking CN201020717Y abstract not used as FOUND evidence...")
cn_found_abstract = []
for rows, label in [(queue_rows, "TS"), (safety_rows, "SAFETY"), (co_out, "CO")]:
    for i, r in enumerate(rows):
        if (r.get("evidence_status") == "FOUND" and
            r.get("evidence_patent_number") == "CN201020717Y" and
            r.get("evidence_location") == "ABSTRACT"):
            cn_found_abstract.append(f"{label}[{i}] {r.get('subsystem_id', r.get('bertopic_id',''))}")
if cn_found_abstract:
    errors.append(f"CN201020717Y ABSTRACT used as FOUND: {cn_found_abstract}")
else:
    print("  CN201020717Y ABSTRACT not used as FOUND ✓")

# 6f. Row counts
assert len(safety_rows) == 20
assert len(queue_rows) == 121
assert len(df_out) == 1
assert len(co_out) == 100
print("\nRow counts: 20+121+1+100 ✓")

# 6g. Human fields empty
for label, rows, fields in [
    ("safety", safety_rows, [
        "human_safety_judgment", "human_harm_link", "cascade_role",
        "plausible_cascade_path", "scope_limitation",
        "reviewer_confidence", "reviewer_note",
    ]),
    ("subsys", queue_rows, ["human_subsystem_decision", "human_role_judgment", "reviewer_confidence", "reviewer_note"]),
    ("direct", df_out, ["human_interaction_decision", "human_strength_judgment", "reviewer_confidence", "reviewer_note"]),
    ("coimpl", co_out, ["human_coimplementation_decision", "reviewer_confidence", "reviewer_note"]),
]:
    for i, r in enumerate(rows):
        for f in fields:
            if r.get(f, "") != "":
                errors.append(f"{label}[{i}]: {f} not empty")
print("Human fields empty ✓")

# 6h. CN201020717Y flag
assert df_out[0]["patent_number"] == "CN201020717Y"
assert df_out[0]["source_integrity_flag"] == "ABSTRACT_CLAIM_MISMATCH"
print("CN201020717Y flag ✓")

# 6i. No confirmed/final files
for fname in os.listdir(OUT):
    lower = fname.lower()
    for fb in ["final", "confirmed", "validated"]:
        if fb in lower and not fname.startswith("_generate") and not fname.startswith("P1_human_review"):
            errors.append(f"Forbidden: {fname}")
print("No confirmed/final files ✓")

# ── Summary ──
print("\n" + "=" * 60)
print("V4 EVIDENCE COVERAGE SUMMARY")
print("=" * 60)

print(f"\nSafety Queue: {len(safety_rows)} rows")
print(f"  FOUND:        {safety_ev_stats['FOUND']}")
print(f"  INSUFFICIENT: {safety_ev_stats['INSUFFICIENT']}")

print(f"\nTopic×Subsystem: {len(queue_rows)} rows")
print(f"  FOUND:              {evidence_stats['FOUND']}")
print(f"  INSUFFICIENT:       {evidence_stats['INSUFFICIENT']}")
print(f"  NO_DIRECT_EVIDENCE: {evidence_stats['NO_DIRECT_EVIDENCE']}")
if ts_found:
    print(f"  Content check: {ts_found_ok}/{len(ts_found)} ({100*ts_found_ok/max(1,len(ts_found)):.0f}%)")

print(f"\nCO_IMPLEMENTATION: {len(co_out)} rows")
print(f"  FOUND:        {co_evidence_stats['FOUND']}")
print(f"  INSUFFICIENT: {co_evidence_stats['INSUFFICIENT']}")
if co_found:
    print(f"  Content check: {co_found_ok}/{len(co_found)} ({100*co_found_ok/max(1,len(co_found)):.0f}%)")

print(f"\nPatent binding: {pn_ok}/{pn_total} ({100*pn_ok/max(1,pn_total):.0f}%)")

print("\nPer-Role Evidence:")
for role in ["PRIMARY", "SECONDARY", "CONTEXT_ONLY"]:
    role_rows = [r for r in queue_rows if r["proposed_role"] == role]
    r_found = sum(1 for r in role_rows if r["evidence_status"] == "FOUND")
    r_insuf = sum(1 for r in role_rows if r["evidence_status"] == "INSUFFICIENT")
    r_node = sum(1 for r in role_rows if r["evidence_status"] == "NO_DIRECT_EVIDENCE")
    print(f"  {role}: {len(role_rows)} rows — {r_found} FOUND, {r_insuf} INSUFFICIENT, {r_node} NO_DIRECT_EVIDENCE")

if errors:
    print(f"\n❌ {len(errors)} ERROR(S):")
    for e in errors[:20]:
        print(f"  - {e}")
    if len(errors) > 20:
        print(f"  ... and {len(errors)-20} more")
    sys.exit(1)
else:
    print(f"\n✅ All V4 validation checks passed.")

print(f"\nFiles in {OUT}:")
for f in sorted(os.listdir(OUT)):
    fpath = os.path.join(OUT, f)
    if os.path.isfile(fpath):
        print(f"  {f} ({os.path.getsize(fpath):,} bytes)")
