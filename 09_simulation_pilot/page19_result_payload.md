# Page 19 Result Payload — Topic 22 Controlled Propagation Simulation

## 1. 建议标题

**"Controlled propagation pilot: bounded interface mismatch erodes safety margin while local contracts hold (1-D simulation)"**

中文备选："受控传播仿真试验：局部契约全过下的有界接口失配侵蚀全局安全裕度"

## 2. 状态标签

**PILOT RESULTS**

（依据 `outputs/outcome_classification.json`：outcome = `PILOT_SUPPORT`，冻结规则触发：C0 基线有效；0.30 与 0.45 m/s 两档各存在 ≥2 个相邻非零延迟满足 BH 校正后精确 McNemar q<0.05 且配对风险差 95% CI 下界>0；全部 518 次传播试验局部契约通过、100% 满足严格事件顺序。）

## 3. 三个可放进 PPT 的核心数字

| # | 数字 | 含义 |
|---|------|------|
| 1 | **41.0%（369/900，Wilson 95% CI 37.8–44.2%）** | C1 时间戳延迟条件下满足严格事件顺序的传播率；峰值单元格 0.30 m/s × 75 ms 达 50/50（RD=1.00 [1.00, 1.00]，BH q=6.4×10⁻¹⁵） |
| 2 | **24.8%（149/600，Wilson 95% CI 21.5–28.4%）** | C2 阈值偏移条件下传播率；峰值单元格 0.45 m/s × −0.03 m 达 50/50（RD=1.00 [1.00, 1.00]，BH q=1.1×10⁻¹⁴） |
| 3 | **0/1500（Wilson 95% CI 上界 0.26%）** | C4 匹配修复（25 ms 时间戳年龄门 + 共享阈值契约检查）后传播次数；所有发生传播的单元格，修复后配对风险差 = 父条件率且 CI 下界 > 0 |

护栏数字（如需）：C0 基线 150/150 全部安全（最小裕度 +0.0075 m）；C3 部件故障 150/150 全部判为普通组件故障，0 次计入传播；全部 3300 次试验合成接触力为 0 N（突破 d_safe 但未发生表面接触）。

## 4. 数字出处（结果表与单元格）

- 数字 1：由 `outputs/raw_trials.csv`（condition=C1, label=PROPAGATED）聚合；单元格级见 `outputs/descriptive_results.csv`（condition=C1 各行 `n_propagated`/`n`/`wilson_lo`/`wilson_hi`）；峰值单元格检验见 `outputs/inferential_results.csv` 行 `family=C1, kind=c1_vs_c0, speed_mps=0.30, delay_ms=75.0`（b=50, mcnemar_p=1.78×10⁻¹⁵, bh_q=6.39×10⁻¹⁵, risk_diff=1.00, rd_ci=[1.00,1.00]）。
- 数字 2：`outputs/inferential_results.csv` 行 `family=C2, kind=c2_vs_c0, speed_mps=0.45, offset_m=-0.03`（b=50, bh_q=1.07×10⁻¹⁴, risk_diff=1.00 [1.00,1.00]）；聚合率由 `descriptive_results.csv`（condition=C2）汇总。
- 数字 3：`outputs/raw_trials.csv`（condition=C4）计数；修复配对效果见 `outputs/inferential_results.csv` `family=C4`（如 `rescue_c1, speed 0.45, delay 75 ms`：b=50, c=0, RD=1.00 [1.00,1.00]）。

## 5. 一句主要结论

"In a controlled simulation, a bounded interface mismatch produced ordered and repeatable safety-margin erosion while the modeled local contracts remained satisfied."

（允许措辞，数据支持：传播集中在中间延迟区间——0.30 m/s 的 50–100 ms、0.45 m/s 的 25–150 ms 各相邻单元格均通过冻结显著性标准。）

## 6. 一句限制说明

This is a preregistered 1-D state-space simulation pilot of an interface mechanism only: the delay–response is non-monotone (at the largest delays the margin breach begins before the delayed trigger, so those breaches fail the strict event-order rule and are reported as unordered breaches, not propagation), the synthetic contact force is a simulation variable with no injury interpretation, and nothing here is evidence about real humanoid robots.

## 7. 推荐插入 PPT 的图片面板

- 首选：`figures/F1_propagation_heatmap.pdf`（速度×延迟传播热图，含每格计数，直观呈现"中间延迟区间传播、大延迟转为无序突破"的结构）
- 次选：`figures/F3_condition_rates.pdf`（五条件发生率 + Wilson CI，含 C3 普通故障排除说明）
- 备用：`figures/F4_contract_and_rescue.pdf`（局部契约通过率 + 修复效果配对森林图）
- 若空间允许：`figures/F2_aligned_traces.pdf`（匹配三元组轨迹，注意其失配面板按冻结中位规则选中的是 BREACH_UNORDERED 试验，图注已如实说明）
- `figures/code_excerpt.pdf` 仅作可追溯性附录，不作证据。

## 8. 不能使用的表述（禁止）

- "Topic 22 proves an Asimov Cascade in real humanoid robots."
- "The patent trend predicts accidents."
- "The simulation validates injury risk."
- "No propagation was observed, therefore cascades do not exist."（本结果也不适用此句——观察到了受控传播，但同样禁止反推现实事故）
- "已经完成了真实机器人实验。"
- "已经证明现实中会发生人员伤害。"
- 任何把合成接触力换算为人体伤害概率的说法；任何把 Topic 25 当作同场景物理对照的说法；任何超出 "controlled simulation pilot / mechanistic propagation test" 的定性。
