# 双人标注一致性报告(kappa report)

- 工作簿 topic 行数:77
- 一致性度量:Cohen's kappa(Rater A vs Rater B,逐字段);解释分档按 Landis & Koch (1977)。
- 总体指标:safety_judgment 二值化 —— candidate = {DIRECT, PARTIAL},其余(NOT_SAFETY / INCIDENTAL / UNCLEAR)为 not-candidate。

## 逐字段结果

| 字段 | 双人已填 n | 一致率 | Cohen's kappa | 分档 |
| ---- | ---------- | ------ | ------------- | ---- |
| safety_judgment | 0 | [—] | [—] | waiting for human fill-in |
| harm_link | 0 | [—] | [—] | waiting for human fill-in |
| cascade_role | 0 | [—] | [—] | waiting for human fill-in |
| scope_limitation | 0 | [—] | [—] | waiting for human fill-in |
| confidence | 0 | [—] | [—] | waiting for human fill-in |
| **binary candidate (DIRECT/PARTIAL vs 其余)** | 0 | [—] | [—] | waiting for human fill-in |

> 注:`scope_limitation` 为自由文本,kappa 按完全字符串一致计算,仅供完整性参考,论文中不报告。

## 可直接粘进论文的英文结果句(占位符在回填后自动替换)

```text
Two authors independently adjudicated all 77 non-noise topics using the label schema of Section IV-C. Inter-rater agreement was [substantial/almost perfect]: Cohen's kappa was [κ_safety] for the five-way safety judgment, [κ_harm] for the harm link, [κ_role] for the cascade role, and [κ_conf] for reviewer confidence. On the headline binary decision (candidate = DIRECT or PARTIAL, n = [N]), the two raters agreed on [agreement] of topics (kappa = [κ_binary]). Disagreements were resolved by discussion, with a third author arbitrating the remaining cases.
```

## 待办

- [ ] Rater A / B 完成独立标注并回填 workbook
- [ ] 重跑本脚本,确认所有字段 n = 77
- [ ] 将英文结果句中的占位符替换为实测值后粘入论文,并删除 "57 unadjudicated topics" 局限表述
