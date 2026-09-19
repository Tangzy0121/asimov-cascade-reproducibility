# Dual-Review Label Definitions (label schema)

This file defines the allowed values for the Rater A / Rater B annotation columns in
`dual_review_workbook.xlsx`. The value set is identical to the P1 pilot annotations
(`output/subsystem_validation/human_review/P1_topic_safety_reviewed.csv`) and corresponds
to the safety-cascade interpretation framework in Section IV-C of the paper. Please read
this file in full before annotating; for any topic you are unsure about, record your
concern in the `*_note` column per the protocol — do not leave it blank.

## 1. safety_judgment (safety relevance of the topic)

| Value | Definition |
| ---- | ---- |
| `DIRECT` | Patents within the topic **explicitly** state the protection of people / prevention of bodily harm as their purpose, or directly describe safety risks posed by humanoid robots to people and the corresponding mechanisms. |
| `PARTIAL` | The topic contains explicit safety mechanisms (e.g., balance recovery, safe braking, collision monitoring), but safety is not the main contribution of most patents in the topic, or the topic clearly mixes safety and non-safety content. |
| `INCIDENTAL` | Safety content appears only as an ancillary condition or indirectly (e.g., obstacle avoidance carried out to complete a surveying/inspection task); the invention goal is not the protection of people. |
| `NOT_SAFETY` | There is no substantive safety mechanism in the evidence text; "safety" keywords are merely background or stylistic wording (e.g., human-like referring to a driving style). |
| `UNCLEAR` | Evidence is insufficient, or the topic is severely mixed (e.g., grippers, electrodes, and measurement combined in one topic), so no reliable judgment can be made. |

## 2. harm_link (link to bodily harm)

| Value | Definition |
| ---- | ---- |
| `DIRECT` | The patent text directly describes injuries to people, risks of contact with the human body, or the protection of people as an object (e.g., pinched fingers, contact in shared spaces). |
| `INDIRECT` | Harm to people is **inferred across scenarios** from the evidence (e.g., a fall of a quadruped/wheeled-legged platform could endanger nearby people); the text does not directly report injuries to people. |
| `UNCLEAR` | The link to harm cannot be determined. |

## 3. cascade_role (role of the topic in the Asimov Cascade)

| Value | Definition |
| ---- | ---- |
| `SAFETY_BARRIER` | The topic is a barrier that interrupts or mitigates cascading failure (emergency stop, safe braking, shutdown after collision detection, balance recovery, etc.). |
| `PROPAGATION_NODE` | The topic describes the information/control transfer chain across perception → planning → control → actuation; interface mismatches may propagate along the chain into consequences such as instability or collision. |
| `CONTEXT_ONLY` | Safety is merely a background condition for accomplishing other tasks, and can serve only as a contextual chain rather than core safety evidence. |
| `OUT_OF_SCOPE` | The bulk of the topic does not belong to humanoid robot research (e.g., lane changing for autonomous driving, tobacco warehousing equipment) and should be excluded from the main analysis. |
| `UNCLEAR` | The role cannot be determined. |

## 4. scope_limitation (scope limitation, free text)

Record the applicability limits of the topic's evidence; there is no dropdown — fill in
freely. Common phrasings (following actual P1 usage):

- Evidence platform is not humanoid: "The evidence all comes from wheeled-legged/quadruped robots, not humanoid robots; harm to people is only indirectly inferred."
- Mixed topic: "The topic mixes X and Y with a small number of humanoid robot patents."
- Nature of the evidence: "The patent describes a risk-prevention method, not a record of an actual accident."

If there is no scope issue, write `none` or a brief note — **do not leave it blank**.

## 5. confidence (annotation confidence)

| Value | Definition |
| ---- | ---- |
| `HIGH` | The evidence is direct and the basis for the judgment is explicit (e.g., the text explicitly states human contact and a shutdown mechanism). |
| `MEDIUM` | The basis for the judgment holds but requires cross-scenario inference, or the topic is somewhat mixed. |
| `LOW` | The evidence is thin or the topic is severely mixed; the judgment is provided only as a reference for adjudication. |

## 6. note (annotation remarks, free text)

Record the reasoning behind the judgment, suspicious points, and suggestions (e.g.,
"recommend splitting this topic"). This can complement scope_limitation:
scope_limitation states "how far the evidence can be extrapolated"; note states "why I
judged it this way".
