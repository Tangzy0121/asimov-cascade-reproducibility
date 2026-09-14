# 77 Topic 双人人工筛查标注协议(ICRA 2027 revision)

## 0. 目的

回应审稿意见:语料经冻结筛选后仅含 77 个非噪声 BERTopic topic,全部由两名作者
独立人工判读并报告 Cohen's kappa,取代原文 "57 unadjudicated topics" 的局限表述。
标注标签体系沿用 P1 试点(`output/subsystem_validation/human_review/P1_topic_safety_reviewed.csv`)
与论文 Section IV-C 的框架,取值定义见同目录 `label_definitions.md`。

## 1. 材料

| 文件 | 说明 |
| ---- | ---- |
| `dual_review_workbook.xlsx` | 标注工作簿,77 行(每 topic 一行),含 topic id、label、top keywords、3 篇代表专利节选(摘要前 ~400 字符),后接 Rater A / B 两套空列。 |
| `label_definitions.md` | 五个标注字段的取值定义,**标注前必读**。 |
| `PROTOCOL.md` | 本文件。 |

每位评审填写 6 列:`*_safety_judgment`、`*_harm_link`、`*_cascade_role`、
`*_scope_limitation`、`*_confidence`、`*_note`。前四个枚举字段已配置下拉
(枚举值与 P1 schema 一致);`scope_limitation` 与 `note` 为自由文本。

## 2. 盲法要求(强制)

- 工作簿中**不含** DeepSeek 冻结标签(`llm_safety_labels.csv`),评审全程不得查阅该文件,
  也不得查阅 P1 已审 20 题的作者标签。
- Rater A 与 Rater B **各自保存一份工作簿副本独立标注**,标注完成前不得交流、
  不得互相查看对方的列。汇合前建议各自把副本重命名为
  `dual_review_workbook_raterA.xlsx` / `dual_review_workbook_raterB.xlsx` 存档。
- 判读依据仅为:topic label、top keywords、3 篇代表专利节选;如需更多上下文,
  可按 `rep*_patent` 的公开号检索原文,但两人须遵循相同的查阅规则
  (建议:先看节选,不足时再查原文,并在 note 中注明"查了原文")。

## 3. 标注流程

1. **独立标注**(Rater A、B 并行,互不可见):
   - 通读 `label_definitions.md`;
   - 逐行判读 77 个 topic,六个字段全部填写,**不留空**(无范围限制时
     `scope_limitation` 填"无";拿不准用 `UNCLEAR` 并在 note 写明原因);
   - 每行给出 `confidence`(HIGH/MEDIUM/LOW)。
2. **汇合比对**:两人把各自的列回填进同一份工作簿(A 列块 / B 列块),
   运行 `scripts/compute_dual_review_kappa.py` 得到逐字段 kappa 与
   二值化(candidate = DIRECT/PARTIAL)总体 kappa。
3. **分歧裁决**:
   - 先由两位评审逐条讨论分歧 topic,参考代表专利原文,能达成一致的直接
     记录为最终标签(共识优先);
   - 讨论后仍不一致的,由第三位作者仲裁,仲裁结果为最终标签;
   - 任何一方原为 `UNCLEAR` 的分歧,裁决时**必须**给出非 UNCLEAR 的最终标签
     (除非三位评审一致认为证据确实不足,此时保留 UNCLEAR 并在 note 说明);
   - 裁决结果写入最终数据集(另存 adjudicated 列或单独 CSV),不得覆盖
     工作簿中 A/B 的原始独立标注。

## 4. 预计工时

77 题 × 每题约 3–4 分钟 ≈ 每人 4–5 小时;汇合与裁决约 1 小时。
两人一下午(各自独立)+ 一次短会即可完成,与审稿意见中的估计一致。

## 5. 回填与论文更新步骤

1. 两位评审完成标注 → 回填进 `dual_review_workbook.xlsx` 的 A/B 列块。
2. 运行:
   ```
   <python>/envs/<env>/python.exe -X utf8 scripts/compute_dual_review_kappa.py
   ```
   生成 `output/dual_review/kappa_report.md`,确认所有字段 n = 77。
3. 将报告中英文结果句模板(占位符已替换为实测值)粘入论文实验/验证章节,
   并删除原稿中 "57 unadjudicated topics" 的局限表述,替换为
   "all 77 non-noise topics were independently adjudicated by two authors
   (Cohen's κ = …)"。
4. 最终裁决标签存档到 `output/dual_review/`(如 `adjudicated_labels.csv`),
   供正文数字与附录引用。
