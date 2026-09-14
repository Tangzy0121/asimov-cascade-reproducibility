# Topic 22/25 单人结构化内容审计：范围说明

## 目标

对修正后的 Topic 22（49 个规范化专利族）和 Topic 25（38 个规范化专利族）进行完整、盲化到 Topic 身份的单人内容审计，回答两个问题：

1. Topic 22 是否富集了可追溯的力/接近感知、人机接触安全与保护性响应机制？
2. Topic 22 与 Topic 25 在机制构成、主题纯度和明确传播证据上有何描述性差异？

## 证据边界

- 本研究是 `single-reviewer structured content audit`，不是双人盲审，也不是外部独立验证。
- 专利文本反映技术披露，不证明实际部署、事故频率、伤害后果或真实 cascade。
- Topic 身份在人工编码期间隐藏；审查完成后才解盲。
- Topic 22 和 Topic 25 全量纳入，不再抽取“代表性 10 件”作为最终人工证据。

## 输入

- 修正代表集：`<project>/HelpCC\kimi_family_id_audit\work\corrected\family_representatives.csv`
- 原始文本：`<project>/PatSense\Cascade\data\humanoid_safety_patents_v5_clean.xlsx`
- 固定随机种子：`20260902`

## 输出

- 第一轮盲化审查工作簿（87 条）
- 延迟复审工作簿（18 条，约 20.7%）
- 解盲密钥（审查期间不得打开）
- 编码手册、执行说明、预先冻结的分析计划与结论措辞边界
- 审查完成后由分析脚本生成结果工作簿和 Markdown 报告

## 不在范围内

- 不修改 BERTopic、HMM、STM 或 cascade score。
- 不把 Topic 25当作机器人动力学实验的“无风险对照”。
- 不进行真实机器人实验或世界模型仿真。
- 不计算审查者间一致性；仅可计算延迟复审的审查者内一致性。
