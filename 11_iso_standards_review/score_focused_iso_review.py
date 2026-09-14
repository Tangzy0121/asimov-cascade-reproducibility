"""Score the focused ISO blind-review package after both reviewers return files."""

from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
from sklearn.metrics import cohen_kappa_score


ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "output" / "standards_validation" / "focused_iso_blind_review"
VALID = {"DIRECT", "PARTIAL", "NONE", "INSUFFICIENT"}


def load_reviewer(label: str) -> pd.DataFrame:
    path = PKG / f"focused_iso_review_reviewer_{label}.csv"
    frame = pd.read_csv(path, dtype=str).fillna("")
    frame["mapping_judgment"] = frame["mapping_judgment"].str.strip().str.upper()
    bad = sorted(set(frame["mapping_judgment"]) - VALID)
    if bad or (frame["mapping_judgment"] == "").any():
        raise SystemExit(f"Reviewer {label} is incomplete or has invalid judgments: {bad}")
    if frame["pair_id"].duplicated().any():
        raise SystemExit(f"Reviewer {label} contains duplicate pair_id values")
    return frame[["pair_id", "mapping_judgment"]].rename(columns={"mapping_judgment": label})


def main() -> None:
    key = pd.read_csv(PKG / "_admin_prespecified_key_DO_NOT_SHARE.csv", dtype=str)
    scored = key.merge(load_reviewer("A"), on="pair_id", validate="one_to_one")
    scored = scored.merge(load_reviewer("B"), on="pair_id", validate="one_to_one")
    if len(scored) != len(key):
        raise SystemExit("Reviewer files do not cover the frozen pair set")

    complete = scored[(scored.A != "INSUFFICIENT") & (scored.B != "INSUFFICIENT")].copy()
    complete["A_binary"] = complete.A.isin(["DIRECT", "PARTIAL"])
    complete["B_binary"] = complete.B.isin(["DIRECT", "PARTIAL"])
    complete["consensus_match"] = complete.A_binary & complete.B_binary

    applicable = complete[complete.prespecified_key.eq("applicable")]
    decoys = complete[complete.prespecified_key.eq("decoy")]
    group_cov = (
        applicable.groupby(["bertopic_id", "standard"])["consensus_match"]
        .any().rename("has_consensus_mapping").reset_index()
    )

    result = {
        "n_frozen_pairs": int(len(scored)),
        "n_complete_pairs": int(len(complete)),
        "raw_agreement_four_class": float((complete.A == complete.B).mean()),
        "cohen_kappa_four_class": float(cohen_kappa_score(complete.A, complete.B)),
        "raw_agreement_binary": float((complete.A_binary == complete.B_binary).mean()),
        "cohen_kappa_binary": float(cohen_kappa_score(complete.A_binary, complete.B_binary)),
        "applicable_pair_coverage_consensus": float(applicable.consensus_match.mean()),
        "mechanism_standard_coverage_consensus": float(group_cov.has_consensus_mapping.mean()),
        "decoy_false_mapping_rate_reviewer_A": float(decoys.A_binary.mean()),
        "decoy_false_mapping_rate_reviewer_B": float(decoys.B_binary.mean()),
        "decoy_false_mapping_rate_consensus": float(decoys.consensus_match.mean()),
    }
    (PKG / "scored_pairs.csv").write_text(scored.to_csv(index=False), encoding="utf-8-sig")
    (PKG / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    group_cov.to_csv(PKG / "coverage_by_mechanism_standard.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
