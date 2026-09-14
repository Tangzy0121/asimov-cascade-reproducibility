# -*- coding: utf-8 -*-
"""Merge the 21 batched incoPat exports (2026-07-18) into a single
deduplicated dataset of 9,710 rows. Deduplication keys on the export
sequence number, with the publication number as a cross-check. The v1
dataset and the source batches are left untouched.
"""
import glob
import sys
from pathlib import Path

import pandas as pd

SRC_GLOB = "<exports>/2026-07-18*.xlsx"
OUT_PATH = Path("<project>/PatSense/Cascade/data/humanoid_safety_patents_v5_20260718.xlsx")
EXPECTED_ROWS = 9710
ID_COL = "公开（公告）号"
SEQ_COL = "序号"

# Frozen retrieval query, archived verbatim for the audit trail
QUERY_V5 = (
    '((humanoid OR "bipedal robot" OR "legged robot" OR "embodied intelligence" '
    'OR "human robot") AND ("safety" OR "avoidance" OR "force control" OR '
    '"torque control" OR "fail-safe" OR "monitoring" OR "prevention" OR '
    '"emergency" OR "risk" OR "stability" OR "redundancy" OR "limit" OR '
    '"detection" OR "reliability" OR "peripersonal" OR "collision" OR '
    '"shutdown" OR "fall" OR "drop" OR "adaptability"))'
)

# 关键字段覆盖率对照(口径来自 v1 214列盘点, 仅作量级 sanity check)
COVERAGE_FIELDS = [
    "标题 (英文)", "摘要 (英文)", "首权翻译", "申请日", "公开（公告）日",
    "最早优先权日", "授权公告日", "实质审查生效日", "预估到期日", "首次公开日",
    "IPC主分类-小组", "申请人国家/地区", "合享价值度", "被引证次数",
    "家族引证次数", "工商成立日期", "发明(设计)人数量", "权利要求数量",
    "首权字数", "文献页数",
]


def main() -> int:
    files = sorted(glob.glob(SRC_GLOB))
    print(f"[1/5] 批次文件: {len(files)} 个")
    if not files:
        print("ERROR: 未找到批次文件"); return 1

    frames = []
    for f in files:
        df = pd.read_excel(f)
        df["__src"] = Path(f).name
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    print(f"      原始总行数: {len(raw)}")

    # [2] 按序号去重(重复段 5501-6000 只留先出现的批次)
    raw[SEQ_COL] = pd.to_numeric(raw[SEQ_COL], errors="coerce")
    before = len(raw)
    merged = raw.drop_duplicates(subset=SEQ_COL, keep="first").copy()
    print(f"[2/5] 序号去重: {before} -> {len(merged)} (去掉 {before - len(merged)} 行重复)")

    # [3] 断言
    n = len(merged)
    n_id = merged[ID_COL].astype(str).nunique()
    seqs = set(merged[SEQ_COL].astype(int))
    missing_seq = sorted(set(range(1, EXPECTED_ROWS + 1)) - seqs)
    print(f"[3/5] 断言: 行数={n} (期望 {EXPECTED_ROWS}), 唯一公开号={n_id}, "
          f"缺号={len(missing_seq)}")
    assert n == EXPECTED_ROWS, f"行数 {n} != {EXPECTED_ROWS}"
    assert n_id == EXPECTED_ROWS, f"公开号有重复: 唯一值 {n_id}"
    assert not missing_seq, f"序号缺号: {missing_seq[:10]}..."
    dup_src = merged["__src"].value_counts()
    assert (dup_src <= 500).all(), "某批次贡献超过 500 行,异常"

    # [4] 排序输出
    merged = merged.sort_values(SEQ_COL).drop(columns="__src")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_excel(OUT_PATH, index=False)
    print(f"[4/5] 已写出: {OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB, "
          f"{len(merged.columns)} 列)")

    # [5] sanity 报告
    print("[5/5] Sanity 报告")
    print(f"      检索式: {QUERY_V5[:60]}...")
    country = merged["申请人国家/地区"].astype(str)
    cn_share = (country.str.contains("CN") | country.str.contains("中国")).mean()
    print(f"      CN 申请人占比: {cn_share:.1%} (v1 为 78%)")
    years = pd.to_datetime(merged["申请日"], errors="coerce").dt.year
    print(f"      申请年范围: {int(years.min())} - {int(years.max())}")
    print("      关键字段覆盖率:")
    for c in COVERAGE_FIELDS:
        if c in merged.columns:
            cov = merged[c].notna().mean()
            print(f"        {c:<14} {cov:.1%}")
        else:
            print(f"        {c:<14} **列缺失**")
    print("OK — 全部断言通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
