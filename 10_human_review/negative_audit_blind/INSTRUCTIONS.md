# Negative Audit 双人盲审 — 审核说明(P0-5 / 安全筛查召回率估计)

## 1. 这个包是什么

自动安全筛查把 77 个非噪声主题分成 20 个阳性(已审)和 57 个阴性(从未人工核查)。
为估计筛查的 recall / specificity / F1,从 57 个阴性里分层抽了 18 个
(抽样方案:`../negative_audit_sampling_plan.md`,seed=20260728)。

**本包把这 18 个阴性样本和 20 个已审阳性混在一起**(共 38 个主题),洗乱后交给
两位审核员独立重判——你拿到的文件里**没有任何列能区分阴性与阳性**,
也看不到机器分数和 LLM 理由。对照关系只存在于 `admin_keys.csv`
(仅管理员持有,审核结束前不要打开)。

## 2. 文件清单

- `blind_review_reviewerA.csv` / `blind_review_reviewerB.csv` — 两份审核表,各 38 行。
  内容相同,仅行序不同(A 种子 20260808,B 种子 20260809)。
  **Reviewer A 只填 A 文件,Reviewer B 只填 B 文件,审核期间互不交流、互不看对方文件。**
- `admin_keys.csv` — 管理员键(topic_id, is_negative_sample, safety_score, stratum,
  ht_weight, original_judgment)。审核员勿开。
- 本文件。

## 3. 填写规范(每行)

判断标准与 P1 主题安全审核完全一致
(`../human_review/P1_human_review_protocol.md` §3.1–3.1d),只看表内给出的
主题标签 + 代表专利号/标题/摘要摘录,不凭主题名猜。

| 列 | 取值 | 说明 |
|----|------|------|
| `human_safety_judgment` | DIRECT / PARTIAL / INCIDENTAL / NOT_SAFETY / UNCLEAR | 该主题是否真涉机器人安全(必填) |
| `human_harm_link` | DIRECT / INDIRECT / NONE / UNCLEAR | 机制与人身伤害的可追溯链路(必填) |
| `cascade_role` | HAZARD_ENDPOINT / PROPAGATION_NODE / SAFETY_BARRIER / CONTEXT_ONLY / OUT_OF_SCOPE / UNCLEAR | 在 Cascade 传播链中的位置(必填) |
| `plausible_cascade_path` | 自由文本 | 可检验的传播假设;非因果断言,格式见 protocol §3.1c |
| `scope_limitation` | 自由文本 | 证据边界(非人形、间接推断、主题混杂等) |
| `reviewer_confidence` | HIGH / MEDIUM / LOW | 必填 |
| `reviewer_note` | 自由文本 | 疑难行留痕 |

**红线**:不要修改 `item_no / topic_id / topic_label / rep_*` 等已有列;不要增删行;
不要与他人核对答案;拿不准填 UNCLEAR,优于硬猜。

## 4. 回收后计算(管理员)

两位审核员把填好的文件放回本目录(文件名不变)。计算内容:

1. **A/B 一致性**:Cohen's κ(先把 DIRECT/PARTIAL 并为 S+、INCIDENTAL/NOT_SAFETY
   并为 S−,UNCLEAR 在仲裁后定);分歧讨论仲裁后锁定标签。
2. **复测一致性**:38 题中 20 题与首次批准结果
   (`../human_review/P1_topic_safety_reviewed.csv`)对照,报告一致率。
3. **假阴率与指标**:按抽样方案 §6,HT 加权 p̂_FN → recall / specificity / F1,
   区间由分层 bootstrap 给出。

(计算脚本待 W4 编写,见 `HelpCC/validation-sprint/tasks.md`。)

## 5. 复现本包(如需)

```bash
cd <project>/PatSense/Cascade/BERT_Python
<python>/python.exe -X utf8 scripts/build_negative_blind_review.py
```

只读取 `negative_audit_package.csv` 与 `P1_topic_safety_reviewed.csv`,绝不修改输入。
