"""Fill Round 2 (same-session repeat coding) rows 2-19, T001-T018 + validation.
Only touches columns I-AA of 02_round2_delayed_retest.xlsx."""

import datetime
import sys
from collections import Counter

import openpyxl

PATH = "02_round2_delayed_retest.xlsx"
TODAY = datetime.date.today().isoformat()

# Columns I-AA of 01_REVIEW: status, safety relevance, harm path, safety topic,
# sensing modality, sensor / decision / response flags, action type, robot type,
# barrier, cross-subsystem flag, scope label, evidence source, claim excerpt,
# coding rationale, confidence, coder id, coding date.
# Claim excerpts are verbatim from the incoPat export (original language kept).
# Chinese rationale strings are part of the reproducible data payload and are kept
# verbatim; each carries an English gloss in the comment directly above it.
ROWS = {
   2: [
      "COMPLETE",
      "NOT_SAFETY",
      "NONE",
      "OBJECT_ENVIRONMENT",
      "NONE",
      "NO",
      "NO",
      "NO",
      "NONE",
      "GENERAL_ROBOT",
      "NO",
      "ABSENT",
      "OFF_TOPIC",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "配备了具有手腕和上述手腕上搭载的缠绕装置的机器人， 上述缠绕装置包括由电动机驱动的可绕轴旋转的缠绕轴",
      # Rationale gloss: reel unwinding/handling unit (robot-mounted winding device
      # for loading/unloading reels) for material handling; no safety mechanism,
      # sensing, decision, or protective element.
      "卷轴开卷/处理单元（机器人搭载缠绕装置装卸卷轴），面向物料处理，无安全机制、传感、判断或保护环节。",
      "HIGH",
      3,
      TODAY,
   ],
   3: [
      "COMPLETE",
      "DIRECT",
      "DIRECT",
      "PHYSICAL_HRI",
      "FORCE_TORQUE",
      "YES",
      "YES",
      "YES",
      "MULTIPLE",
      "GENERAL_ROBOT",
      "YES",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      "when a detected value of said force sensor exceeds a predetermined value, stopping said robot or controlling operation of said robot so that a detected value of said force sensor becomes smaller…a limiter which limits a work area of said human so as to prevent contact by said human with said first robot portion",
      # Rationale gloss: shared human-robot workspace: when the force sensor reading
      # exceeds the limit, stop the robot or control it to reduce force
      # (STOP+LIMIT_FORCE); a separate limiter restricts the human's work area to
      # prevent contact with the robot's far-side part (ISOLATE), hence
      # action=MULTIPLE. Prevention of bodily contact is explicit, harm=DIRECT.
      "人机共享区域：力传感器检测值超限→停止或控制使力减小（STOP+LIMIT_FORCE），另设限制器限制人的工作区域防止与机器人远侧部分接触（ISOLATE），action=MULTIPLE。明确防止人体接触，harm=DIRECT。",
      "HIGH",
      4,
      TODAY,
   ],
   4: [
      "COMPLETE",
      "DIRECT",
      "INDIRECT",
      "NONE",
      "NONE",
      "NO",
      "YES",
      "NO",
      "NONE",
      "NON_ROBOT",
      "YES",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "用于确定用于与系统协作的人-机器人的安全限值，并且被配置为基于……第一和第二参数(V，M，A，K)与预定值……之间的机械固定关系……第二参数输出的极限值(V111，V124，V224)，特别是用于显示",
      # Rationale gloss: portable handheld device for determining HRC system safety
      # limits: computes and outputs/displays limit values from fixed relationships
      # among parameters (DIRECT). A computation/display tool without sensing
      # (sensor=NO); limit derivation counts as threshold determination
      # (decision=YES); it performs no protective action itself (response=NO). The
      # primary subject is not a robot system, NON_ROBOT.
      "确定 HRC 系统安全限值的便携式手持装置：基于参数间固定关系计算并输出/显示极限值（DIRECT）。计算/显示工具无传感检测（sensor=NO），限值推导属阈值确定（decision=YES），本身不执行保护动作（response=NO）。主对象非机器人系统，NON_ROBOT。",
      "MEDIUM",
      4,
      TODAY,
   ],
   5: [
      "COMPLETE",
      "NOT_SAFETY",
      "NONE",
      "NONE",
      "NONE",
      "NO",
      "YES",
      "NO",
      "NONE",
      "GENERAL_ROBOT",
      "NO",
      "ABSENT",
      "OFF_TOPIC",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "执行被配置为对与资源和任务相关联的信息进行编码的图网络；以及执行递归解码器……在考虑由所述图网络建立的一个或多个时空约束的同时确定调度",
      # Rationale gloss: human-robot team task scheduling learned with a graph
      # network plus recurrent decoder; a scheduling/AI topic (listed as OFF_TOPIC
      # in the codebook) with no safety mechanism. Schedule determination counts as
      # a decision, decision=YES.
      "图网络+递归解码器的人-机器人团队任务调度学习，属调度/AI 类（手册列 OFF_TOPIC），无安全机制。调度确定属判断，decision=YES。",
      "HIGH",
      3,
      TODAY,
   ],
   6: [
      "COMPLETE",
      "DIRECT",
      "INDIRECT",
      "NONE",
      "NONE",
      "NO",
      "YES",
      "NO",
      "NONE",
      "NON_ROBOT",
      "YES",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "用于确定用于与所述系统协作的人-机器人的安全限值，并且被配置为基于……第一和第二参数(V，M，A，K)与预定值……之间的固定关系……输出第二参数，特别是显示",
      # Rationale gloss: portable handheld device for determining HRC system safety
      # limits (same family as T003, outputs the second parameter): computes and
      # outputs/displays limit values from fixed parameter relationships (DIRECT).
      # No sensing (sensor=NO); limit derivation counts as threshold determination
      # (decision=YES); NON_ROBOT.
      "确定 HRC 系统安全限值的便携式手持装置（与 T003 同族，输出第二参数）：基于参数固定关系计算并输出/显示极限值（DIRECT）。无传感检测（sensor=NO），限值推导属阈值确定（decision=YES），NON_ROBOT。",
      "MEDIUM",
      3,
      TODAY,
   ],
   7: [
      "COMPLETE",
      "DIRECT",
      "DIRECT",
      "PROXIMITY_SEPARATION",
      "PROXIMITY",
      "YES",
      "YES",
      "YES",
      "STOP",
      "GENERAL_ROBOT",
      "YES",
      "EXPLICIT_CROSS_SUBSYSTEM",
      "IN_SCOPE",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "具有检测人类接近机器人信息的接近信息检测部, 将上述接近信息发送给其他机器人的发送部, 以及基于上述接近信息设定动作或停止动作模式的动作模式设定部的第1机器人……根据上述接近信息设定停止或动作的动作模式的动作模式设定部的第2机器人",
      # Rationale gloss: multi-robot system: robot 1 detects human approach,
      # broadcasts the proximity information, and each robot sets its stop/motion
      # mode accordingly (STOP). The abstract explicitly states "ensuring human
      # safety", harm=DIRECT. The text explicitly states that one robot's sensing
      # output changes other robots' motion conditions and triggers a stop
      # response; coded EXPLICIT_CROSS_SUBSYSTEM under the codebook's literal
      # criterion (same criterion as Round 1, for consistent handling in the
      # analysis).
      '机器人群系统：第1机器人检测人接近→广播接近信息→各机器人据此设定停止/动作模式（STOP）。摘要明确"确保人的安全"，harm=DIRECT。文本明确一个机器人的检测输出改变其他机器人的动作条件并产生停止响应，按手册字面判 EXPLICIT_CROSS_SUBSYSTEM（与第一轮同口径，供分析时统一处理）。',
      "MEDIUM",
      4,
      TODAY,
   ],
   8: [
      "COMPLETE",
      "DIRECT",
      "INDIRECT",
      "PROXIMITY_SEPARATION",
      "PROXIMITY",
      "YES",
      "YES",
      "NO",
      "NONE",
      "GENERAL_ROBOT",
      "UNCLEAR",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "在该支承台的上表面载置所述机器人， 在所述支承台设置所述传感器， 所述传感器检测人侵入机器人的作业范围",
      # Rationale gloss: mobile support platform carrying the robot; the sensor that
      # detects human intrusion into the robot's working range is the
      # distinguishing feature (DIRECT). The provided text ends at detection, with
      # no protective-action wording (response=NO); any barrier effect from
      # detection alone is not stated (barrier=UNCLEAR).
      "可移动支撑台载机器人，传感器检测人侵入机器人作业范围为区别特征（DIRECT）；所提供的文本止于检测环节，无保护动作文字（response=NO），仅靠检测的阻断作用未明言（barrier=UNCLEAR）。",
      "MEDIUM",
      3,
      TODAY,
   ],
   9: [
      "COMPLETE",
      "DIRECT",
      "DIRECT",
      "COLLISION_CONTACT",
      "FORCE_TORQUE",
      "YES",
      "NO",
      "NO",
      "NONE",
      "GENERAL_ROBOT",
      "YES",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (mixed original/machine
      # translation, kept as exported).
      "具有弹性突起(12)和用于防止事故的机器人传感器系统；Title/Abstract: A robot sensor for human-robot collision…promote safety of a worker",
      # Rationale gloss: human-robot collision sensor: contact sensing structure of
      # an elastic conductor, a groove, and elastic protrusions; explicitly
      # "prevents accidents" and improves worker safety (harm=DIRECT). The claim
      # describes only the sensor's mechanical structure, with no decision or
      # protective-response element (decision=NO, response=NO). The sensing purpose
      # is explicitly accident prevention, barrier=YES.
      '人-机器人碰撞传感器：弹性导体+凹槽+弹性突起接触式传感结构，明确"防止事故"、提升工人安全（harm=DIRECT）。权利要求仅描述传感器机械结构，无判断与保护响应环节（decision=NO、response=NO）。检测目的明确为事故防护，barrier=YES。',
      "MEDIUM",
      4,
      TODAY,
   ],
   10: [
      "COMPLETE",
      "DIRECT",
      "INDIRECT",
      "PROXIMITY_SEPARATION",
      "NONE",
      "NO",
      "NO",
      "YES",
      "WARNING",
      "GENERAL_ROBOT",
      "YES",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      "said safety system setting for using from the track for the position and timing information for signal transmission to the human-robot cooperation environment, and wherein, said safe system so as to comprise of vision and/or hearing of single delivery information for the device",
      # Rationale gloss: safety system used with a robot: conveys the planned
      # trajectory's position/timing information to the HRC environment as visual
      # or auditory signals (WARNING-type protection, response=YES). The
      # information comes from the controller's planned trajectory, not from
      # sensing (sensor=NO, decision=NO). The claim translation is poor,
      # confidence MEDIUM.
      "与机器人配合使用的安全系统：将规划轨迹的位置/时序信息以视觉/听觉信号传递给 HRC 环境（WARNING 型保护，response=YES）。信息来自控制器规划轨迹而非传感检测（sensor=NO、decision=NO）。claim 译文差，信心 MEDIUM。",
      "MEDIUM",
      4,
      TODAY,
   ],
   11: [
      "COMPLETE",
      "DIRECT",
      "INDIRECT",
      "OBJECT_ENVIRONMENT",
      "FORCE_TORQUE",
      "YES",
      "YES",
      "YES",
      "ISOLATE_OR_FALLBACK",
      "NON_ROBOT",
      "YES",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "如果所监测的操作参数偏离所需状态，则通过自给的第二辅助真空源(20, 26)在抽吸夹持器(12)中产生辅助负压",
      # Rationale gloss: human-robot collaborative vacuum handling device: monitors
      # state variables during handling (vacuum-pressure type,
      # sensing=FORCE_TORQUE); on deviation from the desired state a self-contained
      # auxiliary vacuum source holds the workpiece (failure fallback holding,
      # ISOLATE_OR_FALLBACK). The drop-prevention failure response is the main
      # safety function (DIRECT). The workpiece-drop injury path is plausible but
      # not stated, harm=INDIRECT. The subject is a vacuum handling device, not a
      # robot system, NON_ROBOT.
      "人机协作真空搬运装置：搬运中监测状态变量（真空压力类，sensing=FORCE_TORQUE）→偏离所需状态时自给辅助真空源保持工件（故障应急保持，ISOLATE_OR_FALLBACK），防掉件故障响应是主要安全功能（DIRECT）。掉件伤人路径合理但未明言，harm=INDIRECT。主体为真空搬运装置而非机器人系统，NON_ROBOT。",
      "MEDIUM",
      4,
      TODAY,
   ],
   12: [
      "COMPLETE",
      "PARTIAL",
      "INDIRECT",
      "OBJECT_ENVIRONMENT",
      "PROXIMITY",
      "YES",
      "YES",
      "NO",
      "NONE",
      "GENERAL_ROBOT",
      "UNCLEAR",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "其中， 工作装置与工业机器人A(3)相关的检测器(7)用于检测未预料到的工件的运动(5)",
      # Rationale gloss: HRC tactile industrial robot with a movable workpiece: a
      # detector senses unexpected workpiece motion. The protective purpose
      # (preventing injury from workpiece slippage) is not stated in the text, so
      # safety relevance is PARTIAL and harm=INDIRECT; the claim ends at detection
      # (response=NO), barrier=UNCLEAR. The translation is fragmentary, confidence
      # MEDIUM.
      "HRC 触觉工业机器人+可动工件：检测装置检测工件的意外运动。防护用途（防工件滑脱伤人）文本未明言，安全相关性 PARTIAL、harm=INDIRECT；claim 止于检测（response=NO），barrier=UNCLEAR。译文残缺，信心 MEDIUM。",
      "MEDIUM",
      4,
      TODAY,
   ],
   13: [
      "COMPLETE",
      "DIRECT",
      "DIRECT",
      "COLLISION_CONTACT",
      "PROXIMITY",
      "YES",
      "YES",
      "NO",
      "NONE",
      "GENERAL_ROBOT",
      "YES",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "其中在评估模块(38)中，关于人的损伤的经验确定的数据被存储在具有特定边界几何形状的固体与人的特定身体部分发生的碰撞中……从评估模块(38)输出速度，该速度被接受为机械手(10)的参考点的允许处理速度(V_ZUL)",
      # Rationale gloss: HRC (MRK) planning method: records the layout, MRK zones,
      # limiting geometry and masses, and the motion plan; the evaluation module
      # determines the permissible handling speed from "empirical data on injuries
      # to specific human body parts in collisions with solids of specific
      # boundary geometry" and assigns collision-risk body parts to MRK zones.
      # Collision-injury data is explicit (harm=DIRECT). The method ends at speed
      # planning, with no run-time protective action (response=NO).
      'MRK 规划方法：记录布局/MRK 区域/极限几何与质量/运动计划→评估模块基于"固体与人身体部位碰撞致人损伤的经验数据"确定允许处理速度，并将碰撞风险身体部位分配给 MRK 区域。碰撞致伤数据明确（harm=DIRECT）。方法止于速度规划，无运行期保护动作（response=NO）。',
      "MEDIUM",
      5,
      TODAY,
   ],
   14: [
      "COMPLETE",
      "NOT_SAFETY",
      "NONE",
      "OBJECT_ENVIRONMENT",
      "NONE",
      "NO",
      "NO",
      "NO",
      "NONE",
      "GENERAL_ROBOT",
      "NO",
      "ABSENT",
      "OFF_TOPIC",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "输送装置形成为重力输送机和向下倾斜输送机，其上安装有工业机器人，被设置成可通过其自身的重量移动",
      # Rationale gloss: an industrial robot mounted on a gravity conveyor track
      # and moving by its own weight; a purely mechanical/logistics arrangement
      # with no safety mechanism, sensing, or decision element.
      "工业机器人安装在重力输送轨道上靠自重移动，纯机械/物流布置，无任何安全机制、传感或判断环节。",
      "HIGH",
      3,
      TODAY,
   ],
   15: [
      "COMPLETE",
      "PARTIAL",
      "INDIRECT",
      "PROXIMITY_SEPARATION",
      "PROXIMITY",
      "YES",
      "YES",
      "YES",
      "SLOW",
      "GENERAL_ROBOT",
      "YES",
      "ABSENT",
      "MIXED",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "从感测数据生成人类安全区(504)并维持与机器人臂工作空间相关联的机器人安全区(502)，确定人类安全区(504)和机器人安全区(502)之间的空间重叠(508)的程度，并基于所确定的空间重叠来调节机器人臂运动轨迹的执行速度",
      # Rationale gloss: imaging senses hand position/proximity; human and robot
      # safety zones are maintained and execution speed is adjusted by the degree
      # of spatial overlap (SLOW), so the safety mechanism is explicit. But the
      # claim's co-equal core is a neural network ranking trajectories by a
      # "collaboration productivity score" (not a primary safety function), hence
      # PARTIAL+MIXED. The bodily-injury path is plausible but not stated,
      # harm=INDIRECT.
      '成像感知人手位置/接近度→人/机安全区→按空间重叠程度调节执行速度（SLOW），安全机制明确；但权利要求同等核心是神经网络按"协作生产率得分"排序轨迹（非安全主功能），故 PARTIAL+MIXED。人体伤害路径合理但未明言，harm=INDIRECT。',
      "HIGH",
      5,
      TODAY,
   ],
   16: [
      "COMPLETE",
      "DIRECT",
      "DIRECT",
      "PHYSICAL_HRI",
      "UNCLEAR",
      "UNCLEAR",
      "UNCLEAR",
      "YES",
      "ISOLATE_OR_FALLBACK",
      "GENERAL_ROBOT",
      "YES",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated,
      # including the "(original text truncated)" marker).
      "用于人-机器人协作的生产站，包括……可在打开和关闭位置之间移动的门……通过其访问至一工作空间……关闭；-第一，在工作腔中排列机器人，其在与物体，特别是人接触时(22…（原文截断）",
      # Rationale gloss: HRC (MRK) production station: perimeter guarding plus an
      # openable access door (ISOLATE); the robot in the work chamber acts "when
      # in contact with an object, in particular a human..." - the claim text is
      # truncated at the critical mechanism, so how contact is detected and
      # decided cannot be confirmed (sensor/decision=UNCLEAR), but the isolation
      # guarding is explicit (response=YES, barrier=YES). Relies mainly on
      # incomplete text, confidence LOW.
      'MRK 生产站：周围保护装置+可开闭访问门（ISOLATE），工作腔内机器人"在与物体特别是人接触时…"——claim 原文在关键机制处截断，接触如何检测与判定无法确认（sensor/decision=UNCLEAR），但隔离防护明确（response=YES，barrier=YES）。主要依赖不完整文字，信心 LOW。',
      "LOW",
      4,
      TODAY,
   ],
   17: [
      "COMPLETE",
      "DIRECT",
      "INDIRECT",
      "PROXIMITY_SEPARATION",
      "PROXIMITY",
      "YES",
      "YES",
      "YES",
      "OTHER",
      "GENERAL_ROBOT",
      "YES",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      "reading the maximum range diameter of history execution instruction set, and generating operation warning range; …comparing the working range with the operation warning range, obtaining the execution value A, the execution value A comprises 1 or 0; the execution module is used for judging the work based on the execution value A",
      # Rationale gloss: safety-interactive HRC robot: identifies the robot's
      # spatial position, generates an "operation warning range" from the maximum
      # envelope of the historical instruction set, compares the commanded working
      # range with the warning range to obtain execution value A (0/1), and the
      # execution module gates work based on A (command gating, coded OTHER).
      # Safety-range gating is the main function (DIRECT); the bodily-injury path
      # is plausible but not stated, harm=INDIRECT.
      '安全交互人-机器人协作机器人：识别机器人空间位置、按历史指令集最大包络生成"操作警戒范围"→将指令工作范围与警戒范围比较得执行值 A(0/1)→执行模块按 A 判定是否作业（指令门控，记 OTHER）。安全范围门控为主要功能（DIRECT），人体伤害路径合理但未明言，harm=INDIRECT。',
      "MEDIUM",
      4,
      TODAY,
   ],
   18: [
      "COMPLETE",
      "NOT_SAFETY",
      "NONE",
      "NONE",
      "OTHER",
      "YES",
      "YES",
      "NO",
      "NONE",
      "GENERAL_ROBOT",
      "NO",
      "ABSENT",
      "OFF_TOPIC",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "确定所述任务步骤列表中的每个任务步骤对应于由所述传感器捕获的所述场景中的人类的行为的概率；基于所述概率确定预测的下一意图步骤",
      # Rationale gloss: intent tracking: vision captures the scene, detects
      # objects, predicts the human's next intended step, and executes the
      # corresponding action. The codebook explicitly lists intent tracking as
      # OFF_TOPIC; no safety language (NOT_SAFETY). Detecting human behavior gives
      # sensor=YES (vision, hence sensing=OTHER); intent/probability estimation
      # gives decision=YES; no protective response.
      "意图跟踪：视觉捕获场景、检测对象、预测人类下一意图步骤并执行对应操作。手册明确将意图跟踪列为 OFF_TOPIC；无安全用语（NOT_SAFETY）。检测人的行为 sensor=YES（视觉故 sensing=OTHER），意图/概率判断 decision=YES，无保护响应。",
      "HIGH",
      3,
      TODAY,
   ],
   19: [
      "COMPLETE",
      "PARTIAL",
      "INDIRECT",
      "PROXIMITY_SEPARATION",
      "PROXIMITY",
      "YES",
      "YES",
      "NO",
      "NONE",
      "GENERAL_ROBOT",
      "YES",
      "ABSENT",
      "IN_SCOPE",
      "FIRST_CLAIM",
      # Verbatim claim excerpt from the incoPat export (kept untranslated).
      "获得场景中的被占用空间的体素化表示……使用拓扑映射在场景中的感兴趣点周围形成未被占用空间的分层凸多胞形(HCP)区域；以及确定机器人从所述HCP区域内的所述兴趣点到终点的路径",
      # Rationale gloss: in HRC, a depth camera voxelizes occupied space,
      # unoccupied hierarchical convex polytope (HCP) free space is built, and a
      # collision-free path is planned. The main function is motion planning;
      # collision avoidance is a safety component (PARTIAL). The claim ends at
      # path determination, with no run-time protective action (response=NO);
      # collision-free planning itself limits hazard development, barrier=YES.
      "HRC 中基于深度相机体素化占用空间→构建无占用分层凸多胞形自由空间→规划无碰撞路径。主功能为运动规划，无碰撞属安全组成（PARTIAL）；claim 止于路径确定，无运行期保护动作（response=NO）；无碰撞规划本身限制危险发展，barrier=YES。",
      "MEDIUM",
      4,
      TODAY,
   ],
}

LEGAL = {
   9: {"COMPLETE", "NEEDS_FULL_TEXT", "EXCLUDE_DATA_ERROR"},
   10: {"DIRECT", "PARTIAL", "INCIDENTAL", "NOT_SAFETY", "UNCLEAR"},
   11: {"DIRECT", "INDIRECT", "NONE", "UNCLEAR"},
   12: {
      "PHYSICAL_HRI",
      "COLLISION_CONTACT",
      "PROXIMITY_SEPARATION",
      "OBJECT_ENVIRONMENT",
      "NONE",
      "UNCLEAR",
   },
   13: {"FORCE_TORQUE", "PROXIMITY", "BOTH", "OTHER", "NONE", "UNCLEAR"},
   14: {"YES", "NO", "UNCLEAR"},
   15: {"YES", "NO", "UNCLEAR"},
   16: {"YES", "NO", "UNCLEAR"},
   17: {
      "STOP",
      "RETREAT",
      "SLOW",
      "LIMIT_FORCE",
      "WARNING",
      "ISOLATE_OR_FALLBACK",
      "MULTIPLE",
      "OTHER",
      "NONE",
      "UNCLEAR",
   },
   18: {"EXPLICIT_HUMANOID", "GENERAL_ROBOT", "NON_ROBOT", "UNCLEAR"},
   19: {"YES", "NO", "UNCLEAR"},
   20: {"EXPLICIT_CROSS_SUBSYSTEM", "PLAUSIBLE_ONLY", "ABSENT", "UNCLEAR"},
   21: {"IN_SCOPE", "MIXED", "OFF_TOPIC", "UNCLEAR"},
   22: {"FIRST_CLAIM", "ABSTRACT", "TITLE", "FULL_TEXT", "MULTIPLE", "UNCLEAR"},
   25: {"HIGH", "MEDIUM", "LOW"},
}

wb = openpyxl.load_workbook(PATH)
ws = wb["01_REVIEW"]
for r, vals in ROWS.items():
   for i, v in enumerate(vals):
      ws.cell(row=r, column=9 + i, value=v)
try:
   wb.save(PATH)
except PermissionError:
   print("LOCKED: file still open in Excel, nothing saved")
   sys.exit(2)
print("SAVED rows 2-19")

# ---- validation ----
wb = openpyxl.load_workbook(PATH)
ws = wb["01_REVIEW"]
bk = openpyxl.load_workbook("02_round2_retest.backup.xlsx")["01_REVIEW"]
diff = sum(
   1
   for r in range(1, 20)
   for c in range(1, 9)
   if ws.cell(r, c).value != bk.cell(r, c).value
)
print("A-H diffs vs backup:", diff)
problems = []
for r in range(2, 20):
   for c in range(9, 28):
      v = ws.cell(r, c).value
      if v in (None, ""):
         problems.append((r, c, "EMPTY"))
      elif c in LEGAL and v not in LEGAL[c]:
         problems.append((r, c, "ILLEGAL:" + str(v)))
print("field problems:", problems if problems else "NONE")
print("status:", dict(Counter(ws.cell(r, 9).value for r in range(2, 20))))
print("safety:", dict(Counter(ws.cell(r, 10).value for r in range(2, 20))))
print("scope:", dict(Counter(ws.cell(r, 21).value for r in range(2, 20))))
print("conf:", dict(Counter(ws.cell(r, 25).value for r in range(2, 20))))
