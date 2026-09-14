# 预先冻结的分析计划

## 分析集

- 全量内容集：Topic 22 的49个规范化专利族与 Topic 25 的38个规范化专利族。
- `UNCLEAR` 不默认当作 `NO`；每个指标同时报告分母、UNCLEAR数量和完整案例比例。

## 主要描述性终点

1. 直接安全纯度：`safety_relevance = DIRECT` 的比例。
2. 接触安全机制：`contact_context` 属于 PHYSICAL_HRI / COLLISION_CONTACT / PROXIMITY_SEPARATION 的比例。
3. 力/接近感知比例：`sensing_type` 属于 FORCE_TORQUE / PROXIMITY / BOTH。
4. 完整机制链比例：sensor、decision、response 三项均为 YES。
5. 明确 humanoid 比例：`humanoid_scope = EXPLICIT_HUMANOID`。
6. 明确传播证据比例：`propagation_evidence = EXPLICIT_CROSS_SUBSYSTEM`。
7. 主题偏离比例：`topic_scope = OFF_TOPIC`；另报告 MIXED。

每个比例按 Topic 报告计数、分母、比例和 Wilson 95% CI。

## 比较分析

- Topic 22 与 Topic 25 的二分类差异使用 Fisher exact test，报告 odds ratio、精确 p 值和两组比例差。
- 比较是探索性的；不以 p<0.05 作为“主题真实/虚假”的唯一标准。
- 对7个主要比较同时报告 Benjamini–Hochberg q 值。

## 审查者内一致性

- 18条延迟复审与第一轮配对。
- 对分类字段报告原始一致率。
- 对二分类派生终点报告 Cohen's kappa；类别退化导致 kappa 不可定义时如实标记 NA。
- 该结果称为 `intra-rater agreement`，不得称为 `inter-rater agreement`。

## 缺失和偏差

- 未完成字段会阻止正式分析，不进行插补。
- 单一作者审查存在观察者偏差；Topic盲化和延迟复审只能缓解，不能消除。
- Publication No、标题、申请人可能让熟悉数据的作者猜到主题；因此是“盲化到Topic标签”，不是完全盲法。

## 结论升级规则

- 若 Topic 22 的直接安全纯度和完整机制链比例较高，可称其为“富集 force-aware HRI safety mechanisms 的模型生成文本簇”。
- 即使明确传播证据比例较高，也只能称为“专利文本中的跨子系统传播披露”，不能据此宣称真实机器人 cascade 已验证。
- 若 OFF_TOPIC/MIXED 较多，应下调 Topic 22 标签强度，并公开报告主题混杂。
