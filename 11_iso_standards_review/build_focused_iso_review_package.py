"""Build a blinded, clause-level ISO validation package for the robust HIGH mechanisms.

The package contains only two candidate mechanisms that remain HIGH after the
family-normalized primary re-estimation (T22 and T25).  Applicable clauses and
within-standard decoys are fixed here before human scoring.  Reviewer files do
not expose the intended/decoy key or any machine-proposed judgment.
"""

from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "standards_validation" / "focused_iso_blind_review"
HUMAN = ROOT / "output" / "subsystem_validation" / "human_review" / "P1_topic_safety_reviewed.csv"
CLAUSES = ROOT / "data" / "standards" / "clause_toc.csv"

SEED_A = 22025
SEED_B = 25025


MECHANISMS = {
    22: {
        "mechanism_label": "Contact-force detection and protective response",
        "mechanism_summary": (
            "Physical human-robot contact is sensed as external/operator force; the controller "
            "distinguishes intended guidance from abnormal contact and reduces force or stops."
        ),
    },
    25: {
        "mechanism_label": "Shared-workspace state-dependent motion control",
        "mechanism_summary": (
            "Human presence and workspace/tactile state are used to assign a hazard state and "
            "select robot speed, force, or operating behavior near a person."
        ),
    },
}

# Exactly two prespecified applicable clauses and one negative-control clause
# per mechanism per standard.  Titles are verified against clause_toc.csv.
PAIR_SPEC = {
    22: {
        "ISO 10218-1:2025": [("5.10.4", "applicable"), ("5.4.3", "applicable"), ("5.1.6", "decoy")],
        "ISO 10218-2:2025": [("5.14.6", "applicable"), ("6.3.3", "applicable"), ("5.12.3", "decoy")],
        "ISO 13482:2014": [("5.13", "applicable"), ("6.7", "applicable"), ("5.2", "decoy")],
    },
    25: {
        "ISO 10218-1:2025": [("5.10.3", "applicable"), ("5.5.3", "applicable"), ("5.9", "decoy")],
        "ISO 10218-2:2025": [("5.14.2", "applicable"), ("5.14.5", "applicable"), ("5.10.2", "decoy")],
        "ISO 13482:2014": [("5.10", "applicable"), ("6.4", "applicable"), ("5.5", "decoy")],
    },
}


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    human = pd.read_csv(HUMAN)
    toc = pd.read_csv(CLAUSES, dtype={"clause_id": str})
    toc["clause_id"] = toc["clause_id"].astype(str)

    rows: list[dict] = []
    for topic_id, mechanism in MECHANISMS.items():
        h = human.loc[human["bertopic_id"].eq(topic_id)]
        if len(h) != 1:
            raise RuntimeError(f"Expected one human-reviewed row for T{topic_id}; got {len(h)}")
        hrow = h.iloc[0]
        for standard, clause_pairs in PAIR_SPEC[topic_id].items():
            for clause_id, key in clause_pairs:
                hit = toc.loc[toc["standard"].eq(standard) & toc["clause_id"].eq(clause_id)]
                if len(hit) != 1:
                    raise RuntimeError(f"Clause lookup failed: {standard} {clause_id}")
                clause = hit.iloc[0]
                rows.append(
                    {
                        "pair_id": f"T{topic_id}_{standard.split(':')[0].replace(' ', '_')}_{clause_id}",
                        "bertopic_id": topic_id,
                        "mechanism_label": mechanism["mechanism_label"],
                        "mechanism_summary": mechanism["mechanism_summary"],
                        "representative_evidence": str(hrow["exact_evidence_excerpt"])[:700],
                        "scope_limitation": hrow["scope_limitation"],
                        "standard": standard,
                        "clause_id": clause_id,
                        "clause_title": clause["clause_title"],
                        "clause_level": int(clause["level"]),
                        "prespecified_key": key,
                    }
                )

    admin = pd.DataFrame(rows)
    admin.to_csv(OUT / "_admin_prespecified_key_DO_NOT_SHARE.csv", index=False, encoding="utf-8-sig")

    reviewer_cols = [
        "item_no", "pair_id", "bertopic_id", "mechanism_label", "mechanism_summary",
        "representative_evidence", "scope_limitation", "standard", "clause_id",
        "clause_title", "clause_level", "normative_text_checked", "requirement_type",
        "mapping_judgment", "confidence", "reviewer_comment",
    ]
    for reviewer, seed in (("A", SEED_A), ("B", SEED_B)):
        visible = admin.drop(columns=["prespecified_key"]).sample(frac=1, random_state=seed).reset_index(drop=True)
        visible.insert(0, "item_no", np.arange(1, len(visible) + 1))
        for col in ["normative_text_checked", "requirement_type", "mapping_judgment", "confidence", "reviewer_comment"]:
            visible[col] = ""
        visible[reviewer_cols].to_csv(
            OUT / f"focused_iso_review_reviewer_{reviewer}.csv", index=False, encoding="utf-8-sig"
        )

    protocol = """# Focused independent standards validation — blinded review protocol

## Fixed scope

This round was frozen before human scoring. It evaluates two mechanisms that remain HIGH after family-normalized primary re-estimation (T22 and T25), against ISO 10218-1:2025, ISO 10218-2:2025, and ISO 13482:2014. For each mechanism-standard combination, the package contains two prespecified applicable clauses and one within-standard negative-control clause (18 pairs total; 12 applicable and 6 decoys).

## Blinding and independence

Reviewer A completes only `focused_iso_review_reviewer_A.csv`; Reviewer B completes only the B file. Work independently and do not compare answers before both files are frozen. Do not open `_admin_prespecified_key_DO_NOT_SHARE.csv`. Rows are independently shuffled, and the reviewer files do not reveal applicable/decoy status or any model-generated mapping.

## Mandatory source check

Clause titles are navigation aids, not normative text. For every row, consult a licensed or otherwise authorized copy of the cited standard and clause. Enter `Y` in `normative_text_checked` only after reading the applicable normative text. If access is unavailable, enter `N` and use `INSUFFICIENT` rather than inferring a requirement from the title.

## Coding

- `requirement_type`: `HAZARD`, `SAFEGUARD`, `INTERFACE`, or `NONE`.
- `mapping_judgment`: `DIRECT`, `PARTIAL`, `NONE`, or `INSUFFICIENT`.
- `confidence`: `HIGH`, `MEDIUM`, or `LOW`.
- `reviewer_comment`: required for `PARTIAL` and `INSUFFICIENT`; briefly identify the missing or mismatched element.

`DIRECT` means the mechanism instantiates the clause's normative hazard, safeguard, or interface requirement without adding a material unstated element. `PARTIAL` means there is a real but incomplete correspondence. `NONE` means no defensible normative correspondence. `INSUFFICIENT` means the reviewer cannot judge from authorized source material.

## Scoring after both files are returned

Run `<python>/python.exe -X utf8 scripts/score_focused_iso_review.py`. It reports raw agreement and Cohen's kappa (four-class and binary), applicable-pair coverage, mechanism-by-standard coverage, and decoy false-mapping rates. No standards-validation result should be inserted into the manuscript before this scoring step succeeds.
"""
    (OUT / "README_REVIEW_PROTOCOL.md").write_text(protocol, encoding="utf-8")

    manifest = {
        "topics": sorted(MECHANISMS),
        "standards": ["ISO 10218-1:2025", "ISO 10218-2:2025", "ISO 13482:2014"],
        "n_pairs": len(admin),
        "n_prespecified_applicable": int(admin["prespecified_key"].eq("applicable").sum()),
        "n_decoys": int(admin["prespecified_key"].eq("decoy").sum()),
        "reviewer_shuffle_seeds": {"A": SEED_A, "B": SEED_B},
        "status": "awaiting_two_independent_human_reviews",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    build()
