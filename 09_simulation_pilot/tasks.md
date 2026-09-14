# Execution Tasks — completed ledger (work/ copy)

- [x] Freeze environment and preregistered configuration — `environment.json`、`config/preregistered.yaml` + SHA-256、README、source_manifest（2026-09-02T03:18Z）
- [x] Implement/test dynamics — TDD 失败→通过证据在 `logs/tests.log`（6 项）
- [x] Implement/test perception, planning, safety, and control modules — TDD（8 项）
- [x] Implement/test local contracts and event classifier — TDD（6+7 项）
- [x] Run C0-only calibration with disjoint seeds — 种子 1000–1009，30 试验
- [x] Freeze config hash after calibration — duration 4.0→8.0（允许项，书面理由+新哈希 `0bf3f035…`+重启校准通过）
- [x] Build randomized main trial table — 3300 行，先于首次仿真保存并哈希
- [x] Run all C0–C4 trials without selective deletion — 3300/3300，无删改
- [x] Verify reproducibility and completeness — 66 代表重放 + 14 固定子集逐位一致；verify_package 20/20
- [x] Generate descriptive and inferential results — `descriptive_results.csv`、`inferential_results.csv`
- [x] Apply frozen outcome classification — `outcome_classification.json`：PILOT_SUPPORT
- [x] Generate four figures and code excerpt — 五张矢量 PDF（用户指示 PDF 替代 PNG，已登记偏差）
- [x] Generate Page 19 result payload — `page19_result_payload.md`
- [x] Write audit report and claim impact matrix — `AUDIT_REPORT.md`、`claim_impact_matrix.csv`
- [x] Freeze final hash manifest — `final_manifest.json`
