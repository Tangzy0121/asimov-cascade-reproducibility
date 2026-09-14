# 编码手册 v1.0（编码开始后冻结）

## 总原则

只根据当前行提供的专利文字判断，不根据 Topic 名称、模型排名或既有论文结论推断。优先级为 First Claim > Abstract > Title。若文本不足，选择 `UNCLEAR`。

## 字段定义

### safety_relevance

- `DIRECT`：人身保护、危险降低、安全控制、故障响应、碰撞/接触保护是主要技术功能。
- `PARTIAL`：安全是重要组成，但同时混有明显的非安全主功能。
- `INCIDENTAL`：只顺带出现安全用语，主要服务于性能、便利或一般控制。
- `NOT_SAFETY`：文本不支持安全机制解释。
- `UNCLEAR`：证据不足或互相矛盾。

### human_harm_link

- `DIRECT`：文字明确涉及人受伤、碰撞、挤压、危险接触等。
- `INDIRECT`：存在合理下游伤害路径，但专利没有明确陈述。
- `NONE`：没有可追溯的人体伤害联系。
- `UNCLEAR`：无法判断。

### contact_context

- `PHYSICAL_HRI`：人与机器人直接或近距离物理交互。
- `COLLISION_CONTACT`：明确碰撞、接触或冲击。
- `PROXIMITY_SEPARATION`：以距离、接近或隔离为主要机制。
- `OBJECT_ENVIRONMENT`：主要面对物体或环境，而非人。
- `NONE`：没有接触/接近语境。
- `UNCLEAR`：无法判断。

### sensing_type

- `FORCE_TORQUE`：力、力矩、压力、接触负载等。
- `PROXIMITY`：距离、接近、分离监测等。
- `BOTH`：两类均有明确证据。
- `OTHER`：视觉、声音等其他感知，但无上述两类。
- `NONE`：无感知证据。
- `UNCLEAR`：无法判断。

### sensor_evidence / decision_evidence / response_evidence

- `YES`：文字明确支持该环节。
- `NO`：文字明确不含或与该环节无关。
- `UNCLEAR`：提供的文字不足以确认。

其中：

- sensor：检测人、接触、力、距离、危险状态或相关输入；
- decision：阈值比较、分类、意图判断、状态判断、风险判断或控制条件；
- response：减速、后退、停止、限力、告警、隔离、降级或其他保护动作。

分析中的“完整机制链”仅在三项均为 `YES` 时成立。

### protective_action

`STOP`、`RETREAT`、`SLOW`、`LIMIT_FORCE`、`WARNING`、`ISOLATE_OR_FALLBACK`、`MULTIPLE`、`OTHER`、`NONE`、`UNCLEAR`。若存在两个及以上明确动作，选 `MULTIPLE` 并在理由中列出。

### humanoid_scope

- `EXPLICIT_HUMANOID`：明确写 humanoid、仿人或具有人形身体结构的机器人。
- `GENERAL_ROBOT`：一般机器人、机械臂、协作机器人等，未限定 humanoid。
- `NON_ROBOT`：主要对象不是机器人系统。
- `UNCLEAR`：无法判断。

### barrier_evidence

- `YES`：该机制明确阻断、缓解或限制危险发展。
- `NO`：没有此作用。
- `UNCLEAR`：无法判断。

这只是文本中的 barrier mechanism，不等于已验证的 cascade barrier。

### propagation_evidence

- `EXPLICIT_CROSS_SUBSYSTEM`：文本明确说明一个子系统的输出、状态或错误改变另一个子系统的输入/条件，并产生后续响应。
- `PLAUSIBLE_ONLY`：根据机制可以提出传播假设，但专利文字没有明确给出传播链。
- `ABSENT`：提供的文字没有传播证据。
- `UNCLEAR`：无法判断。

禁止把多个部件同时出现自动编码为明确传播。

### topic_scope

- `IN_SCOPE`：主要技术内容与力感知/HRI安全或安全控制机制一致。
- `MIXED`：既包含上述机制，也有显著的非相关主功能。
- `OFF_TOPIC`：主要是搬运、AR、调度、纠错、意图跟踪或其他不构成相关安全机制的内容。
- `UNCLEAR`：无法判断。

### reviewer_confidence

- `HIGH`：关键判定有明确 claim/abstract 原文。
- `MEDIUM`：总体可判断，但部分环节需要解释。
- `LOW`：主要依赖间接线索；通常应同时使用一个或多个 `UNCLEAR`。

## 边界示例

- “检测外力超过阈值并停止关节”：sensor=YES，decision=YES，response=YES，完整机制链成立。
- “检测外力用于提高轨迹精度”：sensor=YES，但安全相关性可能是 INCIDENTAL，保护响应不能自动记为 YES。
- “人接近后机械臂减速”：若文本明确检测与减速条件，三环节可均为 YES。
- “多个控制模块共同工作”：只说明共存，不足以标记 `EXPLICIT_CROSS_SUBSYSTEM`。
- “没有发现传播文字”：记录 `ABSENT`，结论只能是“该专利文本未提供传播证据”，不能写“传播不存在”。
