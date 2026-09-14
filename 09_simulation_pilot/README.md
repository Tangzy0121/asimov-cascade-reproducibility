# Topic 22 Controlled Propagation Simulation — work/

本目录是预注册受控仿真的唯一工作区（见上级 spec.md / PREREGISTERED_PARAMETERS.md / plan.md / tasks.md / checklist.md）。

- `config/`：冻结预注册配置及 SHA-256
- `src/`：仿真与分析源代码（冻结后哈希进 manifest）
- `tests/`：pytest 测试（TDD，失败与通过证据在 `logs/tests.log`）
- `outputs/`：原始试验表、事件摘要、代表轨迹、统计结果、分类结果
- `figures/`：五张矢量 PDF 图（用户指示以 PDF 代替 plan.md 中的 PNG，偏差已登记）
- `logs/`：全部实际执行命令、退出码、异常
- 根级：AUDIT_REPORT.md、claim_impact_matrix.csv、page19_result_payload.md、final_manifest.json、tasks.md、checklist.md

复算：`src/analyze.py` 与 `src/make_figures.py` 只消费 `outputs/` 下冻结 CSV，无需重跑仿真。
