# AUDIT REPORT — Topic 22 Controlled Propagation Simulation

日期：2026-09-02　执行环境：`<python>/envs/<env>/python.exe`（Python 3.12.13，Windows 11）

## 1. 最终结果分类

**PILOT_SUPPORT**（`outputs/outcome_classification.json`，由冻结规则机械判定，非人工挑选）

判定证据：
- C0 基线有效：正式 150/150 无突破、局部契约全过；校准（种子 1000–1009）30/30 通过；
- 支持速度档：0.30 m/s（50/75/100 ms 三个相邻延迟均 BH q<0.05 且 RD 95% CI 下界=1.00>0）与 0.45 m/s（25/50/75/100 ms 相邻延迟同样满足）；0.15 m/s 仅 150 ms 单点显著，不满足相邻条件；
- 全部 518 次 PROPAGATED 试验局部契约通过（100%）且 100% 满足严格事件顺序（≥90% 要求）。

## 2. 试验与数据完整性

- 正式试验恰好 3300：C0=150、C1=900、C2=600、C3=150、C4=1500；66 个单元格 × 50 种子，种子 2000–2049 跨条件复用（common random numbers：同种子同初始间距、同噪声流、同指令抖动）。
- 试验表在首次仿真前生成并保存：`outputs/trial_table.csv`（SHA-256 `526dc9b8…130d4`），执行顺序用行政种子 9001 随机化。
- 逐行增量写入 `outputs/raw_results.jsonl`（可断点续跑）；标签第二遍用冻结的 `classify.decide_label` 统一计算。
- 无任何删除种子、选择性重跑或隐藏结果；相位 3/4 的确定性重放（66 代表 + 14 固定子集）全部与原结果逐位一致。

## 3. 与预注册的偏差（全部登记）

1. **trial_duration_s 4.0 → 8.0**（校准规则明确允许项）。原因：0.15 m/s 档 2/10 校准试验在 4.0 s 内未观察到完整接近段。书面理由见 `outputs/calibration/calibration_decision.md`；变更后重新生成配置哈希（`99e784f7…` → `0bf3f035…`）并从头重启校准。除此之外未改任何参数；d_safe、网格、契约、事件顺序、突破时长、分类规则均未动。
2. **图片输出为矢量 PDF 而非 PNG**（用户本轮明确指示"画图要做出矢量图，你需要给出PDF而不是PNG"）。五张图以 PDF 交付，无 PNG 产物（`logs/fig_preview/` 内的 PNG 仅为质检预览，非交付物）。图的科学内容要求（尺寸、单位、字号、色盲友好、面板编号、图注、不夸大因果）不变。
3. 运行期缺陷修复（不改变任何已产生结果或定义）：`trial_id` 索引列 bug（首次运行在执行任何试验前崩溃，无数据产生）；`pd.read_json`/`read_csv` 浮点解析精度（`precise_float=True`/`round_trip`），修复后由原始 jsonl 精确重算 raw CSV，标签分布不变；F3 图 yerr 非负截断与图例位置（纯展示）。

## 4. 操作性定义（设计决定，已在代码与图注中固化记录）

- 名义指令起始时刻 0.10 s（叠加冻结的 ±0.02 s 抖动）；C3 +0.08 m 偏置在真实间距首次 ≤0.35 m 时注入、持续 0.25 s。
- 无到达样本时（t < 延迟）监控器不评估、不触发（不虚构新数据）。
- 突破判定：margin<0 持续 ≥10 ms 且穿越时刻接近速度 ≥0.05 m/s。
- 停止延迟 = 实际触发时刻 − 匹配 C0 同速度同种子触发时刻。
- 代表轨迹：每单元格最小安全裕度下中位（平局按种子）；F2 三元组：传播计数中位的 C1 单元格 → 其内下中位裕度试验 → 同速度同种子 C0/C1/C4。选中结果为（0.45 m/s, 200 ms, seed 2029），该试验标签为 BREACH_UNORDERED（大延迟下突破先于延迟触发），F2 图注已如实声明。
- 行政种子（非实验因子）：执行顺序 9001、bootstrap 9101。

## 5. 主要结果（全部可由冻结 `outputs/raw_trials.csv` 重算，字节一致）

| 条件 | n | PROPAGATED | CONTAINED | BREACH_UNORDERED | ORDINARY_FAILURE |
|---|---:|---:|---:|---:|---:|
| C0 | 150 | 0 | 150 | 0 | 0 |
| C1 | 900 | 369 (41.0%, Wilson 95% CI 37.8–44.2%) | 287 | 244 | 0 |
| C2 | 600 | 149 (24.8%, 21.5–28.4%) | 300 | 151 | 0 |
| C3 | 150 | 0 | 0 | 0 | 150 |
| C4 | 1500 | 0 (CI 上界 0.26%) | 1500 | 0 | 0 |

- C1 18 个配对精确 McNemar + BH、C2 12 个独立族 + BH、配对风险差 + 种子级 bootstrap CI：见 `outputs/inferential_results.csv`；Fisher 精确检验仅作非配对敏感性（同表 `fisher_p_sensitivity` 列）。
- 延迟-响应趋势（Cochran–Armitage）：0.15 m/s Z=+6.71 (p=1.9×10⁻¹¹)；0.30 m/s Z=−1.34 (p=0.18)；0.45 m/s Z=−4.68 (p=2.8×10⁻⁶)。**非单调**：传播集中于中间延迟区间；大延迟下突破先于延迟触发，违反严格顺序而计为 BREACH_UNORDERED。趋势本身不作因果证明。
- 合成接触力：全部 3300 次试验为 0 N（最小间距 0.1175 m > 0，未发生表面穿透）。该变量仅为仿真量，不作任何伤害解释。
- 修复效果：凡父条件发生传播的单元格，C4 配对修复后传播全部消除（RD=父条件率，CI 下界>0）；C4 总体 0/1500。

## 6. 合规确认

- 一切写入限于 `work/`；PatSense、现有论文与 PPT 未触碰。
- 校准仅用 C0 + 种子 1000–1009；校准与正式种子不相交；冻结哈希后才开始正式试验与查看 C1/C2。
- 未安装 PyBullet/MuJoCo；主实验为计划规定的轻量状态空间模型。
- TDD 证据（先失败后通过）完整保存于 `logs/tests.log`；最终干净进程全套件 33/33 通过。
- `src/verify_package.py` 干净进程 20/20 通过：3300 唯一试验、单元格完整、种子无缺失/重复、哈希正确、统计可由冻结原始 CSV 字节一致重算、五图存在、分类符合冻结规则。
- 禁止措辞清单已在 `page19_result_payload.md` §8 明确列出。

## 7. 关键哈希

- 冻结配置 `config/preregistered.yaml`：`0bf3f0351d8e1622160b94b835b555fc6ffc44b79a077c2a4b6276e96c8d55e9`
- 试验表 `outputs/trial_table.csv`：`526dc9b8a3e654b3c4bfe0facb562696c9a7cfad2d83a610623f657c76e130d4`
- 原始结果 `outputs/raw_trials.csv`：`39a733141082f6a8b7e677d2b74d18159001431157cb56a292c15a884dd70897`
- 全部产物哈希：`final_manifest.json`

## 8. 结论措辞

允许且仅有数据支持的表述：
> "In a controlled simulation, a bounded interface mismatch produced ordered and repeatable safety-margin erosion while the modeled local contracts remained satisfied."

本实验不构成对真实人形机器人、事故预测或伤害风险的任何证据。
