from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from build_audit_package import CODING_COLUMNS, ENUMS, ROOT


ROUND1 = ROOT / "01_round1_blinded_review.xlsx"
ROUND2 = ROOT / "02_round2_delayed_retest.xlsx"
KEY = ROOT / "99_DO_NOT_OPEN_topic_key.xlsx"
OUT_XLSX = ROOT / "audit_results.xlsx"
OUT_MD = ROOT / "audit_results.md"


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total == 0:
        return math.nan, math.nan
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return centre - half, centre + half


def bh_adjust(p_values: list[float]) -> list[float]:
    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [math.nan] * n
    running = 1.0
    for rank_from_end, idx in enumerate(reversed(order), start=1):
        rank = n - rank_from_end + 1
        running = min(running, p_values[idx] * n / rank)
        adjusted[idx] = min(1.0, running)
    return adjusted


def fisher_exact(table: list[list[int]]) -> tuple[float, float]:
    """Two-sided Fisher exact test using fixed margins (SciPy-compatible definition)."""
    a, b = table[0]
    c, d = table[1]
    row1, row2 = a + b, c + d
    col1 = a + c
    total = row1 + row2
    low = max(0, col1 - row2)
    high = min(row1, col1)

    def probability(x: int) -> float:
        return math.comb(col1, x) * math.comb(total - col1, row1 - x) / math.comb(total, row1)

    observed = probability(a)
    p_value = sum(probability(x) for x in range(low, high + 1) if probability(x) <= observed + 1e-15)
    if b * c == 0:
        odds_ratio = math.inf if a * d > 0 else math.nan
    else:
        odds_ratio = (a * d) / (b * c)
    return odds_ratio, min(1.0, p_value)


def cohen_kappa(a: pd.Series, b: pd.Series) -> float:
    pairs = pd.DataFrame({"a": a, "b": b}).dropna()
    if pairs.empty:
        return math.nan
    observed = (pairs.a == pairs.b).mean()
    cats = sorted(set(pairs.a) | set(pairs.b))
    expected = sum((pairs.a == c).mean() * (pairs.b == c).mean() for c in cats)
    if math.isclose(expected, 1.0):
        return math.nan
    return (observed - expected) / (1 - expected)


def read_review(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name="01_REVIEW", dtype=str).fillna("")


def validate(df: pd.DataFrame, expected_n: int, id_col: str) -> None:
    if len(df) != expected_n:
        raise ValueError(f"{id_col}: expected {expected_n} rows, found {len(df)}")
    if df[id_col].nunique() != expected_n:
        raise ValueError(f"{id_col}: IDs are not unique")
    for col, allowed in ENUMS.items():
        bad = sorted(set(df[col]) - set(allowed))
        if bad:
            raise ValueError(f"{id_col}: illegal values in {col}: {bad}")
    if not (df["review_status"] == "COMPLETE").all():
        pending = df.loc[df["review_status"] != "COMPLETE", id_col].tolist()
        raise ValueError(f"{id_col}: incomplete rows: {pending}")
    required = list(ENUMS.keys()) + ["exact_evidence_quote", "decision_reason"]
    missing = df[required].eq("").any(axis=1)
    if missing.any():
        raise ValueError(f"{id_col}: completed rows with missing fields: {df.loc[missing, id_col].tolist()}")


def derive(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["direct_safety"] = out["safety_relevance"].map(
        {"DIRECT": 1, "PARTIAL": 0, "INCIDENTAL": 0, "NOT_SAFETY": 0}
    )
    out["contact_safety_context"] = out["contact_context"].map(
        {
            "PHYSICAL_HRI": 1, "COLLISION_CONTACT": 1, "PROXIMITY_SEPARATION": 1,
            "OBJECT_ENVIRONMENT": 0, "NONE": 0,
        }
    )
    out["force_or_proximity"] = out["sensing_type"].map(
        {"FORCE_TORQUE": 1, "PROXIMITY": 1, "BOTH": 1, "OTHER": 0, "NONE": 0}
    )
    def chain(row):
        vals = [row.sensor_evidence, row.decision_evidence, row.response_evidence]
        if all(x == "YES" for x in vals):
            return 1
        if "NO" in vals:
            return 0
        return math.nan
    out["complete_mechanism_chain"] = out.apply(chain, axis=1)
    out["explicit_humanoid"] = out["humanoid_scope"].map(
        {"EXPLICIT_HUMANOID": 1, "GENERAL_ROBOT": 0, "NON_ROBOT": 0}
    )
    out["explicit_propagation"] = out["propagation_evidence"].map(
        {"EXPLICIT_CROSS_SUBSYSTEM": 1, "PLAUSIBLE_ONLY": 0, "ABSENT": 0}
    )
    out["off_topic"] = out["topic_scope"].map(
        {"OFF_TOPIC": 1, "MIXED": 0, "IN_SCOPE": 0}
    )
    return out


METRICS = [
    "direct_safety", "contact_safety_context", "force_or_proximity",
    "complete_mechanism_chain", "explicit_humanoid", "explicit_propagation", "off_topic",
]


def outcome_table(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    tests = []
    for metric in METRICS:
        for topic in [22, 25]:
            vals = data.loc[data.topic == topic, metric].dropna().astype(int)
            yes, total = int(vals.sum()), len(vals)
            lo, hi = wilson(yes, total)
            rows.append(
                {
                    "metric": metric, "topic": topic, "yes": yes, "denominator": total,
                    "unclear_excluded": int((data.topic == topic).sum() - total),
                    "proportion": yes / total if total else math.nan,
                    "wilson_95_low": lo, "wilson_95_high": hi,
                }
            )
        a = data.loc[data.topic == 22, metric].dropna().astype(int)
        b = data.loc[data.topic == 25, metric].dropna().astype(int)
        table = [[int(a.sum()), int((1-a).sum())], [int(b.sum()), int((1-b).sum())]]
        odds_ratio, p = fisher_exact(table)
        tests.append(
            {
                "metric": metric, "topic22_yes": table[0][0], "topic22_no": table[0][1],
                "topic25_yes": table[1][0], "topic25_no": table[1][1],
                "risk_difference_22_minus_25": a.mean() - b.mean(),
                "odds_ratio": odds_ratio, "fisher_p": p,
            }
        )
    desc = pd.DataFrame(rows)
    comp = pd.DataFrame(tests)
    comp["bh_q"] = bh_adjust(comp["fisher_p"].tolist())
    return desc, comp


def intra_rater(round1: pd.DataFrame, round2: pd.DataFrame, key: pd.DataFrame) -> pd.DataFrame:
    paired = key.dropna(subset=["retest_id"])[["review_id", "retest_id"]].merge(
        round1, left_on="review_id", right_on="record_id", validate="one_to_one"
    ).merge(
        round2, left_on="retest_id", right_on="record_id", suffixes=("_r1", "_r2"), validate="one_to_one"
    )
    rows = []
    fields = [c for c in ENUMS if c != "review_status"]
    for field in fields:
        a, b = paired[f"{field}_r1"], paired[f"{field}_r2"]
        rows.append(
            {
                "field": field, "n": len(paired), "raw_agreement": (a == b).mean(),
                "cohen_kappa": cohen_kappa(a, b),
            }
        )
    return pd.DataFrame(rows)


def style_workbook(path: Path) -> None:
    wb = load_workbook(path)
    for ws in wb.worksheets:
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]:
            cell.font = Font(name="Arial", bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="17365D")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.font = Font(name="Arial", size=10)
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        for col in ws.columns:
            letter = col[0].column_letter
            width = min(42, max(11, max(len(str(c.value or "")) for c in col) + 2))
            ws.column_dimensions[letter].width = width
    wb.save(path)


def main() -> None:
    r1 = read_review(ROUND1)
    r2 = read_review(ROUND2)
    validate(r1, 87, "record_id")
    validate(r2, 18, "record_id")

    key = pd.read_excel(KEY, sheet_name="DO_NOT_OPEN", dtype=str)
    if key["review_id"].nunique() != 87 or key["family_id_norm"].nunique() != 87:
        raise ValueError("Unblinding key failed uniqueness checks")
    data = r1.merge(key, left_on="record_id", right_on="review_id", validate="one_to_one")
    data["topic"] = data["topic"].astype(int)
    data = derive(data)
    desc, comp = outcome_table(data)
    agreement = intra_rater(r1, r2, key)

    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        desc.to_excel(writer, sheet_name="01_Descriptive", index=False)
        comp.to_excel(writer, sheet_name="02_Topic_Comparison", index=False)
        agreement.to_excel(writer, sheet_name="03_Repeat_Agreement", index=False)
        data.to_excel(writer, sheet_name="04_Unblinded_Data", index=False)
    style_workbook(OUT_XLSX)

    lines = [
        "# Topic 22/25 structured single-reviewer audit results", "",
        "> This is a single-reviewer content audit with same-session repeat coding of 18 blinded records; it is not a delayed retest, inter-rater assessment, or independent validation.", "",
        "## Descriptive outcomes", "",
        "| Metric | Topic | Yes / denominator | Proportion | Wilson 95% CI | Unclear excluded |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in desc.itertuples(index=False):
        lines.append(
            f"| {row.metric} | {row.topic} | {row.yes}/{row.denominator} | {row.proportion:.1%} | "
            f"{row.wilson_95_low:.1%}–{row.wilson_95_high:.1%} | {row.unclear_excluded} |"
        )
    lines += ["", "## Exploratory Topic 22 vs 25 comparisons", "",
              "| Metric | Risk difference | Odds ratio | Fisher p | BH q |", "|---|---:|---:|---:|---:|"]
    for row in comp.itertuples(index=False):
        lines.append(
            f"| {row.metric} | {row.risk_difference_22_minus_25:.3f} | {row.odds_ratio:.3g} | "
            f"{row.fisher_p:.3g} | {row.bh_q:.3g} |"
        )
    lines += ["", "## Same-session repeat agreement (exploratory)", "",
              "| Field | n | Raw agreement | Cohen's kappa |", "|---|---:|---:|---:|"]
    for row in agreement.itertuples(index=False):
        kappa = "NA" if pd.isna(row.cohen_kappa) else f"{row.cohen_kappa:.3f}"
        lines.append(f"| {row.field} | {row.n} | {row.raw_agreement:.1%} | {kappa} |")
    lines += ["", "## Interpretation boundary", "",
              "These results characterize disclosed patent mechanisms and cluster composition. They do not establish deployment, accident frequency, injury consequences, or real-world cascade causation."]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_XLSX}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
