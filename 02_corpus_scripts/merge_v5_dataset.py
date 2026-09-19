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
OUT_PATH = Path("<project>/Cascade/data/humanoid_safety_patents_v5_20260718.xlsx")
EXPECTED_ROWS = 9710
# incoPat export column names, matched verbatim against the raw export
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

# Key-field coverage check (field list taken from the v1 214-column inventory;
# order-of-magnitude sanity check only). Column names below match the raw
# incoPat export verbatim and are kept in Chinese for that reason.
COVERAGE_FIELDS = [
    "标题 (英文)", "摘要 (英文)", "首权翻译", "申请日", "公开（公告）日",
    "最早优先权日", "授权公告日", "实质审查生效日", "预估到期日", "首次公开日",
    "IPC主分类-小组", "申请人国家/地区", "合享价值度", "被引证次数",
    "家族引证次数", "工商成立日期", "发明(设计)人数量", "权利要求数量",
    "首权字数", "文献页数",
]


def main() -> int:
    files = sorted(glob.glob(SRC_GLOB))
    print(f"[1/5] batch files: {len(files)}")
    if not files:
        print("ERROR: no batch files found"); return 1

    frames = []
    for f in files:
        df = pd.read_excel(f)
        df["__src"] = Path(f).name
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    print(f"      raw total rows: {len(raw)}")

    # [2] dedup by sequence number (for the duplicated 5501-6000 range, keep
    # the batch in which it appears first)
    raw[SEQ_COL] = pd.to_numeric(raw[SEQ_COL], errors="coerce")
    before = len(raw)
    merged = raw.drop_duplicates(subset=SEQ_COL, keep="first").copy()
    print(f"[2/5] sequence-number dedup: {before} -> {len(merged)} "
          f"({before - len(merged)} duplicate rows removed)")

    # [3] assertions
    n = len(merged)
    n_id = merged[ID_COL].astype(str).nunique()
    seqs = set(merged[SEQ_COL].astype(int))
    missing_seq = sorted(set(range(1, EXPECTED_ROWS + 1)) - seqs)
    print(f"[3/5] assertions: rows={n} (expected {EXPECTED_ROWS}), "
          f"unique publication numbers={n_id}, missing sequence numbers={len(missing_seq)}")
    assert n == EXPECTED_ROWS, f"row count {n} != {EXPECTED_ROWS}"
    assert n_id == EXPECTED_ROWS, f"duplicate publication numbers: {n_id} unique values"
    assert not missing_seq, f"missing sequence numbers: {missing_seq[:10]}..."
    dup_src = merged["__src"].value_counts()
    assert (dup_src <= 500).all(), "a single batch contributes more than 500 rows; anomalous"

    # [4] sort and write
    merged = merged.sort_values(SEQ_COL).drop(columns="__src")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_excel(OUT_PATH, index=False)
    print(f"[4/5] written: {OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB, "
          f"{len(merged.columns)} columns)")

    # [5] sanity report
    print("[5/5] sanity report")
    print(f"      retrieval query: {QUERY_V5[:60]}...")
    # "申请人国家/地区" (applicant country/region) is an incoPat export column
    # name and "中国" a raw cell value; both are matched verbatim
    country = merged["申请人国家/地区"].astype(str)
    cn_share = (country.str.contains("CN") | country.str.contains("中国")).mean()
    print(f"      CN applicant share: {cn_share:.1%} (v1: 78%)")
    years = pd.to_datetime(merged["申请日"], errors="coerce").dt.year
    print(f"      application-year range: {int(years.min())} - {int(years.max())}")
    print("      key-field coverage:")
    for c in COVERAGE_FIELDS:
        if c in merged.columns:
            cov = merged[c].notna().mean()
            print(f"        {c:<14} {cov:.1%}")
        else:
            print(f"        {c:<14} **column missing**")
    print("OK — all assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
