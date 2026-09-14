# -*- coding: utf-8 -*-
# clean_v5_dataset.py
# Clean the merged export (9,710 rows): drop non-analytic publication
# types, keep application years >= 2006, and require at least ten
# characters of combined text. Writes the clean set, a removed-records
# archive, and the cleaning-funnel report.
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.data import _is_english  # noqa: E402
from engine.v5_columns import DATA, load_v5_mapped  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "output" / "time_analysis" / "02_eda" / "v5"
CLEAN_PATH = DATA / "humanoid_safety_patents_v5_clean.xlsx"
REMOVED_PATH = DATA / "humanoid_safety_patents_v5_removed.xlsx"

MIN_YEAR = 2006
MIN_TEXT_LENGTH = 10
# incoPat publication-type labels, matched verbatim against the raw export
DROP_PUB_TYPES = ["译文", "检索报告", "修正或者更正专利", "短期专利"]
# incoPat patent-type labels ("外观设计" = design patents), matched verbatim
DROP_PATENT_TYPES = ["外观设计"]


def _safe_inventory(df):
    """Field inventory: coverage/dtype/min-max (min/max degrade safely for
    mixed-type columns)."""
    rows = []
    for c in df.columns:
        s = df[c]
        non_null = int(s.notna().sum())
        try:
            cmin, cmax = s.min(), s.max()
        except TypeError:
            cmin = cmax = None
        rows.append({
            "column": c, "dtype": str(s.dtype), "non_null": non_null,
            "coverage_pct": round(100 * non_null / len(df), 1),
            "min": cmin, "max": cmax,
        })
    return pd.DataFrame(rows)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # funnel holds (step, remaining, dropped, note); the step labels and notes
    # are Chinese strings written verbatim into cleaning_funnel.md so that the
    # regenerated report stays consistent with the archived one. An English
    # gloss is given after each append.
    funnel = []

    df = load_v5_mapped()
    funnel.append(("原始合并集", len(df), 0, "21 批合并,序号去重后"))
    # gloss: raw merged set — 21 batches merged, after sequence-number dedup

    # --- Step A: drop miscellaneous publication types (dropped rows archived separately) ---
    # "公开类型" / "专利类型" are incoPat export column names, matched verbatim
    mask_junk = (
        df["公开类型"].astype(str).isin(DROP_PUB_TYPES)
        | df["专利类型"].astype(str).isin(DROP_PATENT_TYPES)
    )
    removed = df[mask_junk].copy()
    df = df[~mask_junk].copy()
    removed.to_excel(REMOVED_PATH, index=False)
    detail = removed["公开类型"].value_counts().to_dict()
    funnel.append(("剔杂项公开类型", len(df), len(removed),
                   f"剔除 {detail} → 存档 {REMOVED_PATH.name}"))
    # gloss: drop miscellaneous publication types — dropped {detail} -> archived as ...

    # --- Step B: application-year filter (app_year >= 2006) ---
    app_dates = pd.to_datetime(df["Application Date"], errors="coerce", utc=True)
    df["app_year"] = app_dates.dt.year
    mask_year = df["app_year"] >= MIN_YEAR
    n_drop = int((~mask_year).sum())
    df = df[mask_year].copy()
    funnel.append((f"年份过滤 (>={MIN_YEAR})", len(df), n_drop,
                   "与 v1 pipeline 口径一致"))
    # gloss: year filter — consistent with the v1 pipeline criteria

    # --- Step C: English first-claim detection (no rows dropped; non-English claims blanked) ---
    df["clean_abstract"] = df["Abstract (English)"].astype(str).str.strip()
    raw_claims = df["First Claim(English)"].astype(str).str.strip()
    raw_claims = raw_claims.where(df["First Claim(English)"].notna(), other="")
    eng_mask = raw_claims.apply(_is_english)
    df["clean_claim"] = raw_claims.where(eng_mask, other="")
    funnel.append(("英文首权检测", len(df), 0,
                   f"{int(eng_mask.sum())}/{len(df)} 首权为英文,其余置空(不删行)"))
    # gloss: English first-claim detection — X/Y first claims are English, the rest blanked (rows kept)

    # --- Step D: minimum text length ---
    df["combined_text"] = (df["clean_abstract"] + " " + df["clean_claim"]).str.strip()
    short_mask = df["combined_text"].str.len() < 50
    df.loc[short_mask, "combined_text"] = df.loc[short_mask, "clean_abstract"]
    mask_text = df["combined_text"].str.len() >= MIN_TEXT_LENGTH
    n_drop = int((~mask_text).sum())
    df = df[mask_text].copy()
    funnel.append((f"最小文本长度 (>={MIN_TEXT_LENGTH} 字符)", len(df), n_drop, ""))
    # gloss: minimum text length (>= MIN_TEXT_LENGTH characters)

    # --- duplicate counts under both criteria (report only, no dedup) ---
    # "申请号" / "简单同族个数" are incoPat export column names, matched verbatim
    n_appno_dup = int(df["申请号"].duplicated().sum())
    fam = pd.to_numeric(df["简单同族个数"], errors="coerce")
    n_family_multi = int((fam > 1).sum())

    # --- write the main set ---
    df.to_excel(CLEAN_PATH, index=False)

    # --- field inventory ---
    inv = _safe_inventory(df)
    inv.to_csv(OUT_DIR / "field_inventory.csv", index=False, encoding="utf-8-sig")

    # --- funnel report ---
    # The report template below is emitted verbatim to cleaning_funnel.md in
    # Chinese, to stay consistent with the archived report. Gloss:
    #   "# v5 清洗漏斗报告" = v5 cleaning-funnel report
    #   输入 / 输出 = input / output
    #   步骤 | 剩余 | 本步剔除 | 备注 = step | remaining | dropped in this step | note
    #   漏斗守恒校验 = funnel conservation check
    #   重复口径(按拍板:全保留,只报告) = duplicate criteria (per decision: keep all, report only)
    #   申请号重复(同案申请+授权双公开) = application-number duplicates (application and
    #     grant publications of the same case)
    #   简单同族成员数 >1 = records whose simple-family member count is > 1
    #   剔除存档 = removed-records archive; 字段盘点 = field inventory
    total_in = funnel[0][1]
    total_out = funnel[-1][1]
    total_removed_steps = sum(f[2] for f in funnel)
    lines = [
        "# v5 清洗漏斗报告 (2026-07-18)",
        "",
        f"输入: `data/humanoid_safety_patents_v5_20260718.xlsx` ({total_in} 行)",
        f"输出: `data/humanoid_safety_patents_v5_clean.xlsx` ({total_out} 行)",
        "",
        "| 步骤 | 剩余 | 本步剔除 | 备注 |",
        "|------|------|---------|------|",
    ]
    for step, remain, dropped, note in funnel:
        lines.append(f"| {step} | {remain} | {dropped} | {note} |")
    lines += [
        "",
        f"**漏斗守恒校验**: {total_in} == {total_out} + {total_removed_steps} "
        f"→ {'✓' if total_in == total_out + total_removed_steps else '✗'}",
        "",
        "## 重复口径(按拍板:全保留,只报告)",
        "",
        f"- 申请号重复(同案申请+授权双公开): {n_appno_dup} 条",
        f"- 简单同族成员数 >1: {n_family_multi} 条",
        "",
        f"剔除存档: `data/humanoid_safety_patents_v5_removed.xlsx` ({len(removed)} 行)",
        f"字段盘点: `output/time_analysis/02_eda/v5/field_inventory.csv` ({len(inv)} 列)",
    ]
    (OUT_DIR / "cleaning_funnel.md").write_text("\n".join(lines), encoding="utf-8")

    for f in funnel:
        print(f"  {f[0]:<24} remain {f[1]:>6}  dropped {f[2]:>5}  {f[3]}")
    print(f"OK: clean={total_out}, removed={len(removed)}, "
          f"conservation={total_in == total_out + total_removed_steps}")
    print(f"duplicate criteria: application-number duplicates {n_appno_dup}, "
          f"simple-family members >1 {n_family_multi}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
