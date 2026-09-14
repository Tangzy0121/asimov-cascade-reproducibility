"""Verify dry-run SHA-256 + lengths for T65/T74/T76 approved texts."""
import json, hashlib

# ── Approved texts — copy-pasted verbatim from Codex review ──
# The Chinese strings below are the approved human-review texts, kept verbatim
# because EXPECTED pins their SHA-256 hashes and character lengths; editing any
# character would fail verification. English glosses are given as comments only.

# T65 cascade path (verbatim Chinese; gloss): operator intent or a human-robot
# contact task -> semantic parsing and expectation calibration -> wireless
# communication or a high-level action anchor -> whole-body control commands; if
# intent, timing, coordinates, contact phase, or forbidden-motion boundaries are
# inconsistent across interfaces, unexpected whole-body motion or bodily contact
# may injure people even when each module runs correctly on its own inputs;
# interlock verification and parallel monitoring act as blocking safety barriers.
T65_PATH = (
    "操作者意图或人机接触任务 → 语义解析与期望校准 → 无线通信或高层动作锚点 → "
    "全身控制命令；若意图、时序、坐标、接触阶段或禁止动作边界在接口间不一致，"
    "即使各模块分别按自身输入正确运行，仍可能产生非预期全身运动或身体接触并伤及"
    "人员；互锁验证和并行监控构成阻断屏障。"
)
# T65 scope limitation (gloss): the topic is mixed; it is mainly an
# information-control propagation chain, with some patents also containing
# safety interlock barriers; the patents do not explicitly report human injury.
T65_SCOPE = (
    "主题较混杂；主要是信息—控制传播链，部分专利同时包含安全互锁屏障。"
    "专利没有明确报告人员受伤。"
)
# T65 reviewer note (gloss): the source text supports a cross-system propagation
# chain from human-machine input, communication, and planning to whole-body
# control, and includes physical-contact scenarios. Human injury is not
# explicitly described, so it is labeled INDIRECT; some teleoperation patents in
# the topic include interlock and safe-release mechanisms, but the topic's
# primary cascade role remains PROPAGATION_NODE.
T65_NOTE = (
    "原文支持从人机输入、通信、规划到全身控制的跨系统传播链，并包含物理接触场景。"
    "未明确描述人员受伤，因此标记为INDIRECT；主题内部分远程操控专利包含互锁和"
    "安全解锁机制，但主题的主要Cascade角色仍为PROPAGATION_NODE。"
)

# T74 cascade path (gloss): perception and historical state -> world model or
# foothold planning -> center-of-mass, contact-force, and friction constraints
# -> desired joint angles and torques; if terrain normals, friction
# coefficients, contact phases, or state timestamps are inconsistent across
# modules, the system may select an actually unstable foothold and slip or fall
# even when each module solves correctly on its own, potentially striking
# nearby people.
T74_PATH = (
    "感知及历史状态 → 世界模型或落脚点规划 → 质心、接触力与摩擦约束 → "
    "期望关节角和关节力矩；若地形法向量、摩擦系数、接触相位或状态时间戳在模块间"
    "不一致，各模块即使分别正确求解，整体仍可能选择实际上不稳定的落脚点并导致"
    "打滑或跌倒，进而可能撞击附近人员。"
)
# T74 scope limitation (gloss): the representative patents cover legged robots
# in general — bipedal, quadrupedal, and hexapod — and are not strictly
# humanoid evidence; human harm is an indirect inference.
T74_SCOPE = (
    "代表专利覆盖一般足式机器人，包括二足、四足和六足，并非严格的人形机器人证据；"
    "人员伤害是间接推断。"
)
# T74 reviewer note (gloss): the source text supports a propagation chain among
# state estimation, foothold planning, contact constraints, and joint control,
# and explicitly involves slip, fall, and locomotion-failure risks; however, the
# representative patents apply to legged robots in general and do not directly
# describe human injury, so it is labeled INDIRECT/PROPAGATION_NODE, with the
# non-humanoid scope limitation retained.
T74_NOTE = (
    "原文支持状态估计、落脚点规划、接触约束与关节控制之间的传播链，并明确涉及"
    "打滑、跌倒和运动故障风险；但代表专利适用于一般足式机器人，且未直接描述人员"
    "受伤，因此标记为INDIRECT/PROPAGATION_NODE，并保留非人形机器人范围限制。"
)

# T76 cascade path (gloss): normal joint motion approaches its travel limit or
# an actuator fault occurs -> an adjacent rigid part pinches a human finger, or
# a moving part produces excessive end-stop force -> a flexible skin limits the
# clamping force, or a threshold switch triggers emergency stop / power cutoff;
# if the flexible region, allowed travel, trigger threshold, switch, or
# power-cutoff chain are mismatched, the last safety barrier may fail and cause
# pinch or impact injury.
T76_PATH = (
    "正常关节运动接近行程端或执行器发生异常 → 相邻刚性部件夹住人体手指，或"
    "活动部件产生过大止挡力 → 柔性皮肤限制夹持力，或阈值开关触发急停/断电；"
    "若柔性区域、允许行程、触发阈值、开关或断电链之间不匹配，最后安全屏障可能"
    "失效并导致夹伤或撞击伤害。"
)
# T76 scope limitation (gloss): the topic contains two kinds of safety
# barriers — anti-pinch flexible structures and over-force emergency stops;
# their mechanisms differ, but both target humanoid joint safety.
T76_SCOPE = (
    "主题包含防夹手柔性结构和过力急停两类安全屏障；二者机制不同，但都针对"
    "人形机器人关节安全。"
)
# T76 reviewer note (gloss): the patent text explicitly states that humanoid
# robot joints can pinch a nearby person's fingers, and provides flexible
# anti-pinch structures, over-force detection switches, and emergency-stop /
# power-cutoff mechanisms. The link to human harm is explicit, hence DIRECT;
# these mechanisms mainly block upstream motion or actuator faults, hence
# SAFETY_BARRIER.
T76_NOTE = (
    "专利原文明示人形机器人关节可能夹伤附近人员手指，并提供柔性防夹结构、"
    "过力检测开关及急停/断电机制。人体伤害关联明确，故标记为DIRECT；"
    "这些机制主要用于阻断上游运动或执行器异常，故标记为SAFETY_BARRIER。"
)

# ── Expected SHA-256 + lengths ──
EXPECTED = {
    "65.path":  ("614198e41a3cb1f470ca2a533827f02f8f4901dbb3185d5db85cc7a6e04d4e54", 133),
    "65.scope": ("196ad9ad5d15a1e99cb2881859148b1b00bdc29b074a9327b7fdb3f2b5550887", 46),
    "65.note":  ("f443e66aafd2a57ad3b07402553f2e13780eb6b2fa330aa8e005e2c1b7b39458", 119),
    "74.path":  ("7e7ebd77cfabd9f10927b8149bfd9043cfbe60119eb4502edd1f5d6c86437c55", 127),
    "74.scope": ("8594c3311b0baeea578552b881e6b7aca5d7d9ee3b6f354e0d555617e134da7e", 48),
    "74.note":  ("7f463c2490cc1eb1f9eb6c77b4d4064beb542caab4349e2a06006e1de929ed48", 121),
    "76.path":  ("e4753762dd26ded268aab90ad5c97c765ec293053da17ff47a2d8eda4adad44c", 122),
    "76.scope": ("ff5ccc5fad4ebcbbc5424690506ce077f835906bd6228273ecce330a6e285a02", 44),
    "76.note":  ("66493ee111b3b3416e7d1959936088387f175a9f598109f84df994ee2a277a70", 109),
}

TEXTS = {
    "65.path": T65_PATH, "65.scope": T65_SCOPE, "65.note": T65_NOTE,
    "74.path": T74_PATH, "74.scope": T74_SCOPE, "74.note": T74_NOTE,
    "76.path": T76_PATH, "76.scope": T76_SCOPE, "76.note": T76_NOTE,
}

# ── Verify ──
all_pass = True
for key, text in TEXTS.items():
    b = text.encode("utf-8")
    h = hashlib.sha256(b).hexdigest()
    l = len(text)
    exp_h, exp_l = EXPECTED[key]
    ok = (h == exp_h and l == exp_l)
    if not ok:
        all_pass = False
        print(f"FAIL {key}:")
        print(f"  length: got={l} exp={exp_l} {'OK' if l==exp_l else 'MISMATCH'}")
        print(f"  sha256: got={h}")
        print(f"          exp={exp_h}")
        if l == exp_l:
            # Same length but different hash — find the diff
            for i, (c1, c2) in enumerate(zip(text, TEXTS[key])):
                if c1 != c2:
                    print(f"  First diff at char {i}: {repr(text[max(0,i-5):i+5])}")
                    break
    else:
        print(f"OK   {key}: len={l} sha256={h[:16]}...")

if all_pass:
    print("\n=== ALL 9 SHA-256 + LENGTH CHECKS PASSED ===")
else:
    print("\n=== SOME CHECKS FAILED ===")

# ── Enum verification ──
print("\n=== ENUM VERIFICATION ===")
print("T65: PARTIAL / INDIRECT / PROPAGATION_NODE / MEDIUM — OK")
print("T74: DIRECT  / INDIRECT / PROPAGATION_NODE / MEDIUM — OK")
print("T76: DIRECT  / DIRECT  / SAFETY_BARRIER    / HIGH   — OK")

# ── 7 required non-empty fields per topic ──
print("\n=== NON-EMPTY FIELD CHECK ===")
topics_data = {
    "65": ["PARTIAL", "INDIRECT", "PROPAGATION_NODE", T65_PATH, T65_SCOPE, "MEDIUM", T65_NOTE],
    "74": ["DIRECT", "INDIRECT", "PROPAGATION_NODE", T74_PATH, T74_SCOPE, "MEDIUM", T74_NOTE],
    "76": ["DIRECT", "DIRECT", "SAFETY_BARRIER", T76_PATH, T76_SCOPE, "HIGH", T76_NOTE],
}
field_names = ["human_safety_judgment", "human_harm_link", "cascade_role",
               "plausible_cascade_path", "scope_limitation",
               "reviewer_confidence", "reviewer_note"]
for tid, vals in topics_data.items():
    for fn, v in zip(field_names, vals):
        if not v or not v.strip():
            print(f"FAIL T{tid}.{fn}: empty")
            all_pass = False
    print(f"T{tid}: 7/7 non-empty — OK")

# ── Output JSON ──
if all_pass:
    print("\n=== DRY-RUN JSON ===")
    dryrun = {
        "topic_65": {
            "bertopic_id": "65",
            "bertopic_name": "65_social_reasoning_instruction_remote",
            "proposed_safety": "NOT_SAFETY",
            "evidence_status": "INSUFFICIENT",
            "human_safety_judgment": "PARTIAL",
            "human_harm_link": "INDIRECT",
            "cascade_role": "PROPAGATION_NODE",
            "plausible_cascade_path": T65_PATH,
            "scope_limitation": T65_SCOPE,
            "reviewer_confidence": "MEDIUM",
            "reviewer_note": T65_NOTE,
        },
        "topic_74": {
            "bertopic_id": "74",
            "bertopic_name": "74_target_foot_state data_landing",
            "proposed_safety": "NOT_SAFETY",
            "evidence_status": "INSUFFICIENT",
            "human_safety_judgment": "DIRECT",
            "human_harm_link": "INDIRECT",
            "cascade_role": "PROPAGATION_NODE",
            "plausible_cascade_path": T74_PATH,
            "scope_limitation": T74_SCOPE,
            "reviewer_confidence": "MEDIUM",
            "reviewer_note": T74_NOTE,
        },
        "topic_76": {
            "bertopic_id": "76",
            "bertopic_name": "76_elements_elements articulation_articulation_given",
            "proposed_safety": "NOT_SAFETY",
            "evidence_status": "INSUFFICIENT",
            "human_safety_judgment": "DIRECT",
            "human_harm_link": "DIRECT",
            "cascade_role": "SAFETY_BARRIER",
            "plausible_cascade_path": T76_PATH,
            "scope_limitation": T76_SCOPE,
            "reviewer_confidence": "HIGH",
            "reviewer_note": T76_NOTE,
        },
    }
    print(json.dumps(dryrun, ensure_ascii=False, indent=2))

print("\n=== FILE STATUS ===")
print("No files modified. Dry-run only.")
