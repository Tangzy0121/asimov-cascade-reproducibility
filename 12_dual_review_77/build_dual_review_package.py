#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: scripts/build_dual_review_package.py
# Purpose : Build the 77-topic dual human review workbook for the ICRA 2027
#           revision (reviewer asked for full human adjudication of all
#           non-noise topics + human Cohen's kappa, replacing the
#           "57 unadjudicated topics" limitation). One row per topic with
#           label / top keywords / up to 3 representative patent excerpts,
#           followed by two independent EMPTY rater blocks (Rater A / B).
# Inputs  : output/time_analysis/04_bertopic_time/topic_summary.csv
#           output/time_analysis/10_cascade/llm_safety_labels.csv  (set check only)
#           ../data/humanoid_safety_patents_v5_clean.xlsx          (patent numbers)
# Outputs : output/dual_review/dual_review_workbook.xlsx
#           output/dual_review/label_definitions.md
# Integrity: NO LLM label and NO human judgment is written into the rater
#            columns — the LLM labels file is only used to assert that the
#            topic set matches the frozen screening set (77 non-noise topics).
#            Label schema mirrors the P1 pilot file
#            output/subsystem_validation/human_review/P1_topic_safety_reviewed.csv
# Usage   : <python>/envs/<env>/python.exe -X utf8 scripts/build_dual_review_package.py
from __future__ import annotations

import ast
import csv
import re
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOPIC_SUMMARY = (
    PROJECT_ROOT / "output" / "time_analysis" / "04_bertopic_time" / "topic_summary.csv"
)
LLM_LABELS = (
    PROJECT_ROOT / "output" / "time_analysis" / "10_cascade" / "llm_safety_labels.csv"
)
PATENTS_XLSX = (
    PROJECT_ROOT.parent / "data" / "humanoid_safety_patents_v5_clean.xlsx"
)
OUT_DIR = PROJECT_ROOT / "output" / "dual_review"
OUT_XLSX = OUT_DIR / "dual_review_workbook.xlsx"
OUT_LABEL_DEFS = OUT_DIR / "label_definitions.md"

EXCERPT_CHARS = 400          # representative abstract truncation length
MAX_REP_DOCS = 3
TOP_N_KEYWORDS = 10

# Label schema — value sets confirmed against
# output/subsystem_validation/human_review/P1_topic_safety_reviewed.csv
SAFETY_JUDGMENT = ["DIRECT", "PARTIAL", "INCIDENTAL", "NOT_SAFETY", "UNCLEAR"]
HARM_LINK = ["DIRECT", "INDIRECT", "UNCLEAR"]
CASCADE_ROLE = ["SAFETY_BARRIER", "PROPAGATION_NODE", "CONTEXT_ONLY",
                "OUT_OF_SCOPE", "UNCLEAR"]
CONFIDENCE = ["HIGH", "MEDIUM", "LOW"]

# Workbook columns: topic info + representative evidence + rater blocks
INFO_COLS = ["topic_id", "topic_label", "doc_count", "top_keywords"]
REP_COLS = [f"rep{i}_{part}" for i in (1, 2, 3) for part in ("patent", "excerpt")]
RATER_FIELDS = ["safety_judgment", "harm_link", "cascade_role",
                "scope_limitation", "confidence", "note"]
HEADERS = (INFO_COLS + REP_COLS
           + [f"A_{f}" for f in RATER_FIELDS]
           + [f"B_{f}" for f in RATER_FIELDS])

# enum field -> allowed values (None = free text, no dropdown)
ENUMS = {
    "safety_judgment": SAFETY_JUDGMENT,
    "harm_link": HARM_LINK,
    "cascade_role": CASCADE_ROLE,
    "scope_limitation": None,
    "confidence": CONFIDENCE,
    "note": None,
}


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def norm_text(s: object) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def build_abstract_index() -> dict[str, str]:
    """normalized clean_abstract -> Publication No."""
    df = pd.read_excel(PATENTS_XLSX, usecols=["Publication No", "clean_abstract"])
    idx = {}
    for _, r in df.iterrows():
        key = norm_text(r["clean_abstract"])
        if key and key != "nan":
            idx[key] = str(r["Publication No"]).strip()
    return idx


def truncate(text: str, limit: int = EXCERPT_CHARS) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " …"


def collect_topics() -> list[dict]:
    """One record per non-noise topic, with up to 3 representative patents."""
    summary = load_csv(TOPIC_SUMMARY)
    llm = load_csv(LLM_LABELS)
    topics = [r for r in summary if r["Topic"] != "-1"]
    llm_ids = {int(r["bertopic_id"]) for r in llm}
    topic_ids = {int(r["Topic"]) for r in topics}
    assert topic_ids == llm_ids, (
        f"topic set mismatch: summary {len(topic_ids)} vs llm_labels {len(llm_ids)}; "
        f"diff={topic_ids ^ llm_ids}"
    )
    abs2pn = build_abstract_index()

    records = []
    for r in sorted(topics, key=lambda x: int(x["Topic"])):
        docs = ast.literal_eval(r["Representative_Docs"])[:MAX_REP_DOCS]
        reps = []
        for d in docs:
            key = norm_text(d)
            pn = abs2pn.get(key, "")
            if not pn:  # prefix fallback (truncation differences)
                pn = next((v for k, v in abs2pn.items()
                           if k[:150] == key[:150]), "")
            reps.append((pn, truncate(d)))
        while len(reps) < MAX_REP_DOCS:
            reps.append(("", ""))
        words = ast.literal_eval(r["Representation"])[:TOP_N_KEYWORDS]
        records.append({
            "topic_id": int(r["Topic"]),
            "topic_label": r["Name"],
            "doc_count": int(r["Count"]),
            "top_keywords": ", ".join(words),
            "reps": reps,
        })
    return records


def write_workbook(records: list[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "dual_review"

    header_fill = PatternFill("solid", start_color="FFD9E1F2")   # info: blue
    rep_fill = PatternFill("solid", start_color="FFE2EFDA")      # evidence: green
    a_fill = PatternFill("solid", start_color="FFFFF2CC")        # rater A: yellow
    b_fill = PatternFill("solid", start_color="FFFCE4D6")        # rater B: orange
    n_info, n_rep = len(INFO_COLS), len(REP_COLS)

    for c, name in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.font = Font(bold=True)
        if c <= n_info:
            cell.fill = header_fill
        elif c <= n_info + n_rep:
            cell.fill = rep_fill
        elif c <= n_info + n_rep + len(RATER_FIELDS):
            cell.fill = a_fill
        else:
            cell.fill = b_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)

    for i, rec in enumerate(records, start=2):
        row = ([rec["topic_id"], rec["topic_label"], rec["doc_count"],
                rec["top_keywords"]]
               + [v for rep in rec["reps"] for v in rep]
               + [""] * (2 * len(RATER_FIELDS)))
        for c, v in enumerate(row, start=1):
            cell = ws.cell(row=i, column=c, value=v)
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    # dropdown validations for enum rater fields, applied to all data rows
    last_row = len(records) + 1
    for prefix in ("A", "B"):
        for field in RATER_FIELDS:
            allowed = ENUMS[field]
            if not allowed:
                continue
            col = HEADERS.index(f"{prefix}_{field}") + 1
            letter = get_column_letter(col)
            dv = DataValidation(
                type="list", formula1='"' + ",".join(allowed) + '"',
                allow_blank=True, showErrorMessage=True,
                errorTitle="invalid label",
                error=f"choose one of: {', '.join(allowed)}",
            )
            ws.add_data_validation(dv)
            dv.add(f"{letter}2:{letter}{last_row}")

    # column widths
    widths = {"topic_id": 9, "topic_label": 34, "doc_count": 9,
              "top_keywords": 46}
    for i in (1, 2, 3):
        widths[f"rep{i}_patent"] = 16
        widths[f"rep{i}_excerpt"] = 60
    for prefix in ("A", "B"):
        widths[f"{prefix}_safety_judgment"] = 16
        widths[f"{prefix}_harm_link"] = 12
        widths[f"{prefix}_cascade_role"] = 20
        widths[f"{prefix}_scope_limitation"] = 34
        widths[f"{prefix}_confidence"] = 12
        widths[f"{prefix}_note"] = 30
    for c, name in enumerate(HEADERS, start=1):
        ws.column_dimensions[get_column_letter(c)].width = widths.get(name, 14)

    ws.freeze_panes = "E2"   # first row + id/label/count/keywords stay visible
    ws.row_dimensions[1].height = 30
    wb.save(OUT_XLSX)


LABEL_DEFS_MD = """# 双人标注标签定义(label schema)

本文件定义 `dual_review_workbook.xlsx` 中 Rater A / Rater B 两套标注列的取值含义。
取值集合与 P1 试点标注(`output/subsystem_validation/human_review/P1_topic_safety_reviewed.csv`)
完全一致,对应论文 Section IV-C 的安全级联判读框架。标注前请先通读本文件;遇到拿不准的
topic,按协议记录在 `*_note` 列,不要留空。

## 1. safety_judgment(主题安全相关性判定)

| 取值 | 定义 |
| ---- | ---- |
| `DIRECT` | 主题内专利**明示**以保护人员/防止人体伤害为目的,或直接描述人形机器人对人员的安全风险及对应机制。 |
| `PARTIAL` | 主题包含明确的安全机制(如平衡恢复、安全制动、碰撞监测),但安全并非主题内多数专利的主要贡献,或主题明显混杂安全与非安全内容。 |
| `INCIDENTAL` | 安全内容仅作为附属条件或间接出现(如为完成测绘/作业任务而避障),发明目标不是人员保护。 |
| `NOT_SAFETY` | 证据文本中没有实质安全机制;"安全"关键词只是背景或风格性措辞(如 human-like 指驾驶风格)。 |
| `UNCLEAR` | 证据不足、或主题严重混杂(如夹持器/电极/测量混在一个 topic),无法给出可靠判定。 |

## 2. harm_link(与人体伤害的关联)

| 取值 | 定义 |
| ---- | ---- |
| `DIRECT` | 专利原文直接描述人员伤害、人体接触风险或人员保护对象(如夹伤手指、共享空间接触)。 |
| `INDIRECT` | 人员伤害是从证据**跨场景推断**的(如四足/轮腿平台的跌倒可能波及附近人员),原文未直接报告人员受伤。 |
| `UNCLEAR` | 无法确定伤害关联。 |

## 3. cascade_role(主题在 Asimov Cascade 中的角色)

| 取值 | 定义 |
| ---- | ---- |
| `SAFETY_BARRIER` | 主题是阻断或缓解级联失效的屏障(急停、安全制动、碰撞检测后停机、平衡恢复等)。 |
| `PROPAGATION_NODE` | 主题描述感知→规划→控制→执行之间的信息/控制传递链,接口不一致可能沿链传播为失稳、碰撞等后果。 |
| `CONTEXT_ONLY` | 安全仅是完成其他任务的背景条件,只能作为背景链条而非核心安全证据。 |
| `OUT_OF_SCOPE` | 主题主体不属于人形机器人研究范围(如自动驾驶换道、烟草仓储设备),应从主分析中排除。 |
| `UNCLEAR` | 角色无法判定。 |

## 4. scope_limitation(范围限制,自由文本)

记录该主题证据的适用范围限制,无下拉、自由填写。常见写法(参照 P1 实际用法):

- 证据平台非人形:"证据均为轮腿/四足机器人,不是人形机器人;人员伤害仅为间接推断。"
- 主题混杂:"主题混合 X、Y 与少量人形机器人专利。"
- 证据性质:"专利描述的是风险预防方法,并非真实事故记录。"

无范围问题时填 `无` 或留简短说明,**不要留空**。

## 5. confidence(标注置信度)

| 取值 | 定义 |
| ---- | ---- |
| `HIGH` | 证据直接、判定依据明确(如原文明示人员接触与停机机制)。 |
| `MEDIUM` | 判定依据成立但需跨场景推断,或主题有一定混杂。 |
| `LOW` | 证据稀薄或主题严重混杂,判定仅供裁决参考。 |

## 6. note(标注备注,自由文本)

记录判定理由、可疑点、建议(如"建议拆分该主题")。可与 scope_limitation 互补:
scope_limitation 写"证据能外推到什么范围",note 写"我为什么这么判"。
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = collect_topics()
    write_workbook(records)
    OUT_LABEL_DEFS.write_text(LABEL_DEFS_MD, encoding="utf-8")
    print(f"topics written : {len(records)}")
    print(f"workbook       : {OUT_XLSX}")
    print(f"label defs     : {OUT_LABEL_DEFS}")


if __name__ == "__main__":
    main()
