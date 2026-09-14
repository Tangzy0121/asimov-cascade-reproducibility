# ASIMOV -> Safety Topic kNN Soft-Exposure Report

- Embedding model: `AAUBS/PatentSBERTa_V2` (same as BERTopic v5)
- Method: patent-level kNN soft exposure over 2395 safety patents (20 topics)
- E_s = sum(sim * decay) / sum(sim) over k nearest patents; primary k=50, sensitivity k=[25, 100]

- **Why not hard assignment**: centroid top-1 was degenerate (316/319 v2 scenarios -> one topic; top-1 margins are noise). Plurality vote below is a spot-check display aid ONLY; all statistics use the soft exposure / weight shares.

## v2-Injury (n=319)
- E_decay_k50 quantiles (10/25/50/75/90%): 0.043, 0.059, 0.085, 0.144, 0.215
- nearest-neighbor median sim quantiles: 0.418, 0.450, 0.487
- plurality-vote topic counts (display only):
  - 47_fault_health_state_data: 272
  - 1_humanoid robot_humanoid_joint_robot: 33
  - 22_force_external force_human robot_robot: 13
  - 25_industrial robot_industrial_tool_work: 1

## v1-Injury (n=304)
- E_decay_k50 quantiles (10/25/50/75/90%): 0.060, 0.094, 0.137, 0.211, 0.353
- nearest-neighbor median sim quantiles: 0.095, 0.177, 0.234
- plurality-vote topic counts (display only):
  - 0_leg_end_wheel_connected: 157
  - 1_humanoid robot_humanoid_joint_robot: 66
  - 37_foot_sole_heel_arch: 31
  - 7_vehicle_lane_driving_lane changing: 19
  - 29_module_intelligent_service_display: 17
  - 47_fault_health_state_data: 9
  - 28_tobacco_robotic_operation_shelf: 3
  - 12_bearing_shaft_motor_output: 1
  - 22_force_external force_human robot_robot: 1
