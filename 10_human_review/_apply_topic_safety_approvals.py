"""
Merge approved Topic Safety snapshots into the reviewed CSV.

Dry-run:
    python _apply_topic_safety_approvals.py

Apply:
    python _apply_topic_safety_approvals.py --apply

The original queue is read-only. Apply mode atomically replaces only
P1_topic_safety_reviewed.csv after all pre-write gates pass.
"""

import csv
import hashlib
import json
import os
import sys
import tempfile


BASE = os.path.dirname(os.path.abspath(__file__))
QUEUE_CSV = os.path.join(BASE, "P1_topic_safety_review_queue.csv")
REVIEWED_CSV = os.path.join(BASE, "P1_topic_safety_reviewed.csv")

SNAPSHOT_SHA256 = {
    os.path.join(BASE, "P1_topic_65_74_76_approved.json"):
        "9d02a4e094f6335e5fff68dc634f4c9f95c45525aaf901cc75c002a9f3987054",
    os.path.join(BASE, "P1_topic_remaining_17_approved.json"):
        "d7dc3ba0ac3bf9b0c7e8eaec010621fe1d34b9c16ba98a511f24eeb0a81931d3",
}

APPROVED_FIELD_NAMES = [
    "human_safety_judgment",
    "human_harm_link",
    "cascade_role",
    "plausible_cascade_path",
    "scope_limitation",
    "reviewer_confidence",
    "reviewer_note",
]

LONG_TEXT_FIELDS = [
    "plausible_cascade_path",
    "scope_limitation",
    "reviewer_note",
]

AUTOMATIC_FIELDS = [
    "bertopic_id",
    "bertopic_name",
    "proposed_safety",
    "safety_rationale",
    "supporting_patent_numbers",
    "evidence_patent_number",
    "evidence_location",
    "exact_evidence_excerpt",
    "safety_evidence_terms",
    "evidence_status",
    "evidence_selection_reason",
    "evidence_source_file",
]

ALLOWED_ENUMS = {
    "human_safety_judgment": {
        "DIRECT", "PARTIAL", "INCIDENTAL", "NOT_SAFETY", "UNCLEAR",
    },
    "human_harm_link": {"DIRECT", "INDIRECT", "NONE", "UNCLEAR"},
    "cascade_role": {
        "HAZARD_ENDPOINT", "PROPAGATION_NODE", "SAFETY_BARRIER",
        "CONTEXT_ONLY", "OUT_OF_SCOPE", "UNCLEAR",
    },
    "reviewer_confidence": {"HIGH", "MEDIUM", "LOW"},
}


def fail(message):
    print(f"FAIL: {message}")
    raise SystemExit(1)


def file_sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def verify_approval_snapshot(data):
    """Validate one approval snapshot without assuming a specific topic set."""
    if data.get("schema_version") != "p1_topic_safety_human_review_approval_v1":
        fail(f"schema_version invalid: {data.get('schema_version')}")
    if data.get("approval_status") != "APPROVED":
        fail("approval_status != APPROVED")
    if data.get("approved_field_order") != APPROVED_FIELD_NAMES:
        fail("approved_field_order mismatch")

    scope = data.get("scope", {})
    if scope.get("csv_mutation_authorized_by_this_snapshot") is not False:
        fail("csv_mutation_authorized_by_this_snapshot must be false")
    if scope.get("preserve_all_automatic_fields") is not True:
        fail("preserve_all_automatic_fields must be true")

    topics = data.get("topics", [])
    topic_ids = [topic.get("bertopic_id") for topic in topics]
    scope_ids = scope.get("approved_topic_ids", [])
    if not topics:
        fail("snapshot contains no topics")
    if len(topic_ids) != len(set(topic_ids)):
        fail(f"duplicate bertopic_id in snapshot: {topic_ids}")
    if set(topic_ids) != set(scope_ids) or len(scope_ids) != len(set(scope_ids)):
        fail("scope.approved_topic_ids does not match unique topics[].bertopic_id")

    integrity_checks = 0
    for topic in topics:
        topic_id = topic["bertopic_id"]
        approved = topic.get("approved_fields", {})
        if list(approved.keys()) != APPROVED_FIELD_NAMES:
            fail(f"T{topic_id}: approved fields or order mismatch")
        for field in APPROVED_FIELD_NAMES:
            value = approved.get(field, "")
            if not isinstance(value, str) or not value.strip():
                fail(f"T{topic_id}.{field}: empty")
        for field, allowed in ALLOWED_ENUMS.items():
            if approved[field] not in allowed:
                fail(f"T{topic_id}.{field}: invalid enum {approved[field]!r}")

        integrity = topic.get("integrity", {})
        for field in LONG_TEXT_FIELDS:
            text = approved[field]
            expected = integrity.get(field, {})
            actual_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if expected.get("character_length") != len(text):
                fail(f"T{topic_id}.{field}: character length mismatch")
            if expected.get("sha256_utf8") != actual_hash:
                fail(f"T{topic_id}.{field}: SHA-256 mismatch")
            integrity_checks += 1

    print(
        "Approval snapshot: PASS "
        f"({len(topics)} topics, {len(topics) * 7} fields, "
        f"{integrity_checks} integrity hashes)"
    )
    return topics


def load_verified_snapshots():
    """Load snapshots, pin file hashes, and reject overlapping topic IDs."""
    all_topics = []
    seen_ids = set()

    for path, expected_hash in SNAPSHOT_SHA256.items():
        if not os.path.exists(path):
            fail(f"approval snapshot not found: {path}")
        actual_hash = file_sha256(path)
        if actual_hash != expected_hash:
            fail(
                f"approval snapshot SHA-256 mismatch for {os.path.basename(path)}: "
                f"{actual_hash} != {expected_hash}"
            )
        print(
            f"Snapshot SHA-256: PASS "
            f"({os.path.basename(path)}: {actual_hash})"
        )
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        topics = verify_approval_snapshot(data)
        overlap = seen_ids.intersection(topic["bertopic_id"] for topic in topics)
        if overlap:
            fail(f"topic IDs overlap across snapshots: {sorted(overlap)}")
        seen_ids.update(topic["bertopic_id"] for topic in topics)
        all_topics.extend(topics)

    return all_topics


def apply_approvals(dry_run=True):
    """Validate and merge all approved Topic Safety decisions."""
    approved_topics = load_verified_snapshots()

    if not os.path.exists(QUEUE_CSV):
        fail(f"queue CSV not found: {QUEUE_CSV}")
    queue_hash_before = file_sha256(QUEUE_CSV)
    with open(QUEUE_CSV, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        queue_header = reader.fieldnames
        queue_rows = list(reader)

    if not queue_header:
        fail("queue CSV has no header")
    human_start = queue_header.index("human_safety_judgment")
    if queue_header[human_start:] != APPROVED_FIELD_NAMES:
        fail("queue human-review field order mismatch")
    if len(queue_rows) != 20:
        fail(f"queue has {len(queue_rows)} rows, expected 20")

    queue_ids = [int(row["bertopic_id"]) for row in queue_rows]
    if len(set(queue_ids)) != 20:
        fail("queue does not contain 20 unique topic IDs")

    approval_map = {}
    integrity_map = {}
    for topic in approved_topics:
        topic_id = topic["bertopic_id"]
        approval_map[topic_id] = topic["approved_fields"]
        integrity_map[topic_id] = topic["integrity"]

        queue_row = next(
            (row for row in queue_rows if int(row["bertopic_id"]) == topic_id),
            None,
        )
        if queue_row is None:
            fail(f"approved T{topic_id} is absent from queue")
        if topic.get("bertopic_name") != queue_row["bertopic_name"]:
            fail(f"T{topic_id}: bertopic_name mismatch")
        expected_auto = topic.get("automatic_fields_to_preserve", {})
        for field, expected_value in expected_auto.items():
            if queue_row.get(field, "") != expected_value:
                fail(f"T{topic_id}.{field}: automatic snapshot value mismatch")

    if set(approval_map) != set(queue_ids):
        missing = sorted(set(queue_ids) - set(approval_map))
        extra = sorted(set(approval_map) - set(queue_ids))
        fail(f"snapshot coverage mismatch; missing={missing}, extra={extra}")

    reviewed_rows = []
    diffs = []
    for row in queue_rows:
        topic_id = int(row["bertopic_id"])
        new_row = dict(row)
        for field in APPROVED_FIELD_NAMES:
            old_value = row.get(field, "")
            new_value = approval_map[topic_id][field]
            new_row[field] = new_value
            if old_value != new_value:
                diffs.append((topic_id, field, old_value, new_value))
        reviewed_rows.append(new_row)

    for index, (original, reviewed) in enumerate(zip(queue_rows, reviewed_rows)):
        for field in AUTOMATIC_FIELDS:
            if original.get(field, "") != reviewed.get(field, ""):
                fail(f"row {index}: automatic field {field} changed")

    if len(diffs) != 140:
        fail(f"field-level diff count is {len(diffs)}, expected 140")
    if any(
        not row.get(field, "").strip()
        for row in reviewed_rows
        for field in APPROVED_FIELD_NAMES
    ):
        fail("at least one reviewed human field is empty")

    print("Queue coverage: PASS (20 rows, 20 unique IDs, 20 approved topics)")
    print("Automatic fields byte-identical: PASS")
    print("Human fields: PASS (140/140 non-empty)")
    print("Field-level diff: PASS (140 changes)")

    if dry_run:
        if file_sha256(QUEUE_CSV) != queue_hash_before:
            fail("queue CSV changed during dry-run")
        print("Original queue unchanged: PASS")
        print(">>> DRY-RUN COMPLETE. No CSV written. <<<")
        return

    temp_fd, temp_path = tempfile.mkstemp(
        suffix=".csv",
        prefix="topic_safety_reviewed_",
        dir=BASE,
        text=True,
    )
    try:
        with os.fdopen(
            temp_fd, "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=queue_header,
                extrasaction="ignore",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(reviewed_rows)
        os.replace(temp_path, REVIEWED_CSV)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    with open(REVIEWED_CSV, "r", encoding="utf-8", newline="") as handle:
        written_rows = list(csv.DictReader(handle))
    if len(written_rows) != 20:
        fail(f"reviewed CSV has {len(written_rows)} rows, expected 20")

    written_map = {int(row["bertopic_id"]): row for row in written_rows}
    integrity_checks = 0
    for topic_id, approved in approval_map.items():
        row = written_map.get(topic_id)
        if row is None:
            fail(f"reviewed CSV missing T{topic_id}")
        for field in APPROVED_FIELD_NAMES:
            if row[field] != approved[field]:
                fail(f"reviewed CSV T{topic_id}.{field}: text mismatch")
        for field in LONG_TEXT_FIELDS:
            text = row[field]
            expected = integrity_map[topic_id][field]
            if expected["character_length"] != len(text):
                fail(f"reviewed CSV T{topic_id}.{field}: length mismatch")
            if expected["sha256_utf8"] != hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest():
                fail(f"reviewed CSV T{topic_id}.{field}: SHA-256 mismatch")
            integrity_checks += 1

    if file_sha256(QUEUE_CSV) != queue_hash_before:
        fail("original queue changed during apply")

    print(f"Post-write text verification: PASS (140/140 fields)")
    print(f"Post-write integrity: PASS ({integrity_checks}/60 hashes)")
    print("Original queue unchanged: PASS")
    print(f"Reviewed CSV SHA-256: {file_sha256(REVIEWED_CSV)}")
    print(f">>> APPLY COMPLETE: {REVIEWED_CSV} <<<")


if __name__ == "__main__":
    is_dry_run = "--apply" not in sys.argv
    print("=== DRY-RUN MODE ===" if is_dry_run else "=== APPLY MODE ===")
    apply_approvals(dry_run=is_dry_run)
