# 任务表

- [x] 冻结研究问题与证据边界
- [x] 确认修正后 Topic 22=49、Topic 25=38
- [x] 生成第一轮盲化工作簿
- [x] 生成18条延迟复审工作簿
- [x] 生成并隔离解盲密钥
- [x] 生成编码手册与执行说明
- [x] 生成结果分析脚本
- [x] 验证工作簿字段、随机化、数据验证和盲化
- [x] 用模拟填写副本测试分析脚本
- [x] 完成最终质量复核

## Round 1 done (2026-09-02)
- [x] Batch 1-8: rows 2-88 all COMPLETE (87/87)
- [x] Final validation: A-H zero diffs, 0 empty, 0 illegal enums
- [ ] User calibration pending: EXPLICIT_CROSS_SUBSYSTEM on R051, R083 (2 cells)

## Round 2 done (2026-09-02, same-session)
- [x] 02_round2 18/18 COMPLETE; backup: 02_round2_retest.backup.xlsx; fill script: scripts/fill_round2.py
- [x] 命名变更:第二轮为 same-session repeat coding(同日重复编码),非 7-14 天延迟复审
- [x] 一致率/Cohen κ 仅作探索性结果(同日记忆或使一致性偏高)
- [ ] 用户决定后统一处理 propagation 口径(R051/R083 EXPLICIT_CROSS_SUBSYSTEM)
- [ ] 待用户确认后可运行 scripts/analyze_completed_audit.py 解盲
