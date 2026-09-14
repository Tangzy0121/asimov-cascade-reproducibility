#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: scripts/compute_dual_review_kappa.py
# Purpose : After both raters have filled dual_review_workbook.xlsx, compute
#           per-field Cohen's kappa (Rater A vs Rater B) for the five schema
#           fields, plus the headline binary kappa used in the paper:
#           candidate (safety_judgment in {DIRECT, PARTIAL}) vs not-candidate.
#           Writes a markdown report with a results table and English result
#           sentences that can be pasted into the paper (placeholders remain
#           until the workbook is filled).
# Inputs  : output/dual_review/dual_review_workbook.xlsx  (filled by raters)
# Outputs : output/dual_review/kappa_report.md
# Integrity: this script only READS the workbook; it never writes back to it.
# Behavior : fields where fewer than 2 rows are filled by BOTH raters are
#            reported as "waiting for human fill-in" instead of failing.
#            scope_limitation is free text; its kappa is exact-string-match
#            agreement and is reported for completeness only.
# Usage   :
#   <python>/envs/<env>/python.exe -X utf8 scripts/compute_dual_review_kappa.py
#   <python>/envs/<env>/python.exe -X utf8 scripts/compute_dual_review_kappa.py --workbook PATH --out PATH
from __future__ import annotations

import argparse
import math
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_XLSX = PROJECT_ROOT / "output" / "dual_review" / "dual_review_workbook.xlsx"
DEFAULT_OUT = PROJECT_ROOT / "output" / "dual_review" / "kappa_report.md"

FIELDS = ["safety_judgment", "harm_link", "cascade_role",
          "scope_limitation", "confidence"]
CANDIDATE_LABELS = {"DIRECT", "PARTIAL"}


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    """Cohen's kappa for two aligned label vectors (pure stdlib)."""
    n = len(labels_a)
    po = sum(1 for x, y in zip(labels_a, labels_b) if x == y) / n
    ca, cb = Counter(labels_a), Counter(labels_b)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    return float("nan") if pe == 1.0 else (po - pe) / (1.0 - pe)


def kappa_band(k: float) -> str:
    # Landis & Koch (1977) interpretation bands
    if k != k:  # NaN
        return "undefined (one rater used a single label)"
    for lo, name in [(0.81, "almost perfect"), (0.61, "substantial"),
                     (0.41, "moderate"), (0.21, "fair"), (0.0, "slight")]:
        if k >= lo:
            return name
    return "poor"


def read_rows(path: Path) -> list[dict]:
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(h) for h in rows[0]]
    out = []
    for r in rows[1:]:
        if r[0] is None:
            continue
        rec = {h: ("" if v is None else str(v).strip()) for h, v in zip(headers, r)}
        out.append(rec)
    wb.close()
    return out


def paired(rows: list[dict], field: str) -> tuple[list[str], list[str]]:
    """Aligned A/B labels for rows where BOTH raters filled the field."""
    a, b = [], []
    for r in rows:
        va, vb = r.get(f"A_{field}", ""), r.get(f"B_{field}", "")
        if va and vb:
            a.append(va.upper())
            b.append(vb.upper())
    return a, b


def field_stats(rows: list[dict], field: str) -> dict:
    a, b = paired(rows, field)
    n = len(a)
    if n < 2:
        return {"field": field, "n": n, "agree": None, "kappa": None,
                "band": "waiting for human fill-in"}
    agree = sum(1 for x, y in zip(a, b) if x == y) / n
    k = cohens_kappa(a, b)
    return {"field": field, "n": n, "agree": agree, "kappa": k,
            "band": kappa_band(k)}


def binary_stats(rows: list[dict]) -> dict:
    a, b = paired(rows, "safety_judgment")
    n = len(a)
    if n < 2:
        return {"n": n, "agree": None, "kappa": None,
                "band": "waiting for human fill-in"}
    ba = ["candidate" if x in CANDIDATE_LABELS else "not-candidate" for x in a]
    bb = ["candidate" if x in CANDIDATE_LABELS else "not-candidate" for x in b]
    agree = sum(1 for x, y in zip(ba, bb) if x == y) / n
    k = cohens_kappa(ba, bb)
    return {"n": n, "agree": agree, "kappa": k, "band": kappa_band(k)}


def fmt(v: float | None, digits: int = 3, placeholder: str = "[—]") -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return placeholder
    return f"{v:.{digits}f}"


def build_report(rows: list[dict]) -> str:
    stats = [field_stats(rows, f) for f in FIELDS]
    binary = binary_stats(rows)
    n_total = len(rows)

    lines = []
    lines.append("# 双人标注一致性报告(kappa report)\n")
    lines.append(f"- 工作簿 topic 行数:{n_total}")
    lines.append("- 一致性度量:Cohen's kappa(Rater A vs Rater B,逐字段);"
                 "解释分档按 Landis & Koch (1977)。")
    lines.append("- 总体指标:safety_judgment 二值化 —— candidate = {DIRECT, PARTIAL},"
                 "其余(NOT_SAFETY / INCIDENTAL / UNCLEAR)为 not-candidate。\n")

    lines.append("## 逐字段结果\n")
    lines.append("| 字段 | 双人已填 n | 一致率 | Cohen's kappa | 分档 |")
    lines.append("| ---- | ---------- | ------ | ------------- | ---- |")
    for s in stats:
        lines.append(f"| {s['field']} | {s['n']} | "
                     f"{fmt(s['agree'])} | {fmt(s['kappa'])} | {s['band']} |")
    lines.append(f"| **binary candidate (DIRECT/PARTIAL vs 其余)** | {binary['n']} | "
                 f"{fmt(binary['agree'])} | {fmt(binary['kappa'])} | {binary['band']} |")
    lines.append("")
    lines.append("> 注:`scope_limitation` 为自由文本,kappa 按完全字符串一致计算,"
                 "仅供完整性参考,论文中不报告。")
    lines.append("")

    # English result sentences — placeholders until the workbook is filled
    k_safety = fmt(field_stats(rows, 'safety_judgment')['kappa'],
                   placeholder="[κ_safety]")
    k_harm = fmt(field_stats(rows, 'harm_link')['kappa'],
                 placeholder="[κ_harm]")
    k_role = fmt(field_stats(rows, 'cascade_role')['kappa'],
                 placeholder="[κ_role]")
    k_conf = fmt(field_stats(rows, 'confidence')['kappa'],
                 placeholder="[κ_conf]")
    k_bin = fmt(binary['kappa'], placeholder="[κ_binary]")
    n_bin = binary['n'] if binary['n'] else "[N]"
    agr_bin = fmt(binary['agree'], digits=3, placeholder="[agreement]")

    lines.append("## 可直接粘进论文的英文结果句(占位符在回填后自动替换)\n")
    lines.append("```text")
    lines.append(
        f"Two authors independently adjudicated all {n_total} non-noise topics "
        f"using the label schema of Section IV-C. Inter-rater agreement was "
        f"[substantial/almost perfect]: Cohen's kappa was {k_safety} for the "
        f"five-way safety judgment, {k_harm} for the harm link, {k_role} for "
        f"the cascade role, and {k_conf} for reviewer confidence. On the "
        f"headline binary decision (candidate = DIRECT or PARTIAL, n = {n_bin}), "
        f"the two raters agreed on {agr_bin} of topics (kappa = {k_bin}). "
        f"Disagreements were resolved by discussion, with a third author "
        f"arbitrating the remaining cases."
    )
    lines.append("```")
    lines.append("")
    lines.append("## 待办\n")
    lines.append("- [ ] Rater A / B 完成独立标注并回填 workbook")
    lines.append("- [ ] 重跑本脚本,确认所有字段 n = 77")
    lines.append("- [ ] 将英文结果句中的占位符替换为实测值后粘入论文,"
                 "并删除 \"57 unadjudicated topics\" 局限表述")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workbook", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = read_rows(args.workbook)
    report = build_report(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    n_filled = len(paired(rows, "safety_judgment")[0])
    print(f"topics read    : {len(rows)}")
    print(f"both filled    : {n_filled} (safety_judgment)")
    print(f"report written : {args.out}")


if __name__ == "__main__":
    main()
