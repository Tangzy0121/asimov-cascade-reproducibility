# Codebook v1.0 (frozen once coding began)

## General Principles

Judge only from the patent text provided in the current row; do not infer from topic names, model rankings, or conclusions of prior papers. The priority order is First Claim > Abstract > Title. If the text is insufficient, choose `UNCLEAR`.

## Field Definitions

### safety_relevance

- `DIRECT`: Human protection, hazard reduction, safety control, fault response, or collision/contact protection is the primary technical function.
- `PARTIAL`: Safety is an important component, but it is mixed with a clearly non-safety primary function.
- `INCIDENTAL`: Safety language appears only in passing, mainly serving performance, convenience, or general control.
- `NOT_SAFETY`: The text does not support a safety-mechanism interpretation.
- `UNCLEAR`: Evidence is insufficient or contradictory.

### human_harm_link

- `DIRECT`: The text explicitly mentions human injury, collision, crushing, hazardous contact, or similar.
- `INDIRECT`: A plausible downstream harm pathway exists, but the patent does not state it explicitly.
- `NONE`: No traceable link to human harm.
- `UNCLEAR`: Cannot be determined.

### contact_context

- `PHYSICAL_HRI`: Direct or close-range physical interaction between a human and a robot.
- `COLLISION_CONTACT`: Explicit collision, contact, or impact.
- `PROXIMITY_SEPARATION`: Distance, approach, or separation is the primary mechanism.
- `OBJECT_ENVIRONMENT`: Primarily oriented toward objects or the environment rather than humans.
- `NONE`: No contact/proximity context.
- `UNCLEAR`: Cannot be determined.

### sensing_type

- `FORCE_TORQUE`: Force, torque, pressure, contact load, or similar.
- `PROXIMITY`: Distance, approach, separation monitoring, or similar.
- `BOTH`: Clear evidence for both types.
- `OTHER`: Other sensing such as vision or sound, but neither of the two types above.
- `NONE`: No sensing evidence.
- `UNCLEAR`: Cannot be determined.

### sensor_evidence / decision_evidence / response_evidence

- `YES`: The text explicitly supports this stage.
- `NO`: The text explicitly does not contain this stage or is unrelated to it.
- `UNCLEAR`: The provided text is insufficient to confirm.

Specifically:

- sensor: detecting a human, contact, force, distance, hazardous state, or related input;
- decision: threshold comparison, classification, intent judgment, state judgment, risk assessment, or a control condition;
- response: slowing down, retreating, stopping, force limiting, warning, isolation, fallback, or another protective action.

A "complete mechanism chain" in the analysis holds only when all three stages are `YES`.

### protective_action

`STOP`, `RETREAT`, `SLOW`, `LIMIT_FORCE`, `WARNING`, `ISOLATE_OR_FALLBACK`, `MULTIPLE`, `OTHER`, `NONE`, `UNCLEAR`. If two or more explicit actions are present, choose `MULTIPLE` and list them in the rationale.

### humanoid_scope

- `EXPLICIT_HUMANOID`: Explicitly states humanoid, human-like, or a robot with a human-shaped body structure.
- `GENERAL_ROBOT`: General robots, robotic arms, collaborative robots, etc., not restricted to humanoids.
- `NON_ROBOT`: The primary subject is not a robot system.
- `UNCLEAR`: Cannot be determined.

### barrier_evidence

- `YES`: The mechanism explicitly blocks, mitigates, or limits the development of a hazard.
- `NO`: No such effect.
- `UNCLEAR`: Cannot be determined.

This is only a barrier mechanism in the text and does not amount to a validated cascade barrier.

### propagation_evidence

- `EXPLICIT_CROSS_SUBSYSTEM`: The text explicitly states that the output, state, or error of one subsystem changes the input/conditions of another subsystem and produces a subsequent response.
- `PLAUSIBLE_ONLY`: A propagation hypothesis can be proposed from the mechanism, but the patent text does not explicitly give a propagation chain.
- `ABSENT`: The provided text contains no propagation evidence.
- `UNCLEAR`: Cannot be determined.

Do not automatically code the co-occurrence of multiple components as explicit propagation.

### topic_scope

- `IN_SCOPE`: The main technical content is consistent with force sensing / HRI safety or safety control mechanisms.
- `MIXED`: Contains both the above mechanisms and a significant unrelated primary function.
- `OFF_TOPIC`: Mainly material handling, AR, scheduling, error correction, intent tracking, or other content that does not constitute a relevant safety mechanism.
- `UNCLEAR`: Cannot be determined.

### reviewer_confidence

- `HIGH`: Key judgments are supported by explicit claim/abstract text.
- `MEDIUM`: Overall judgment is possible, but some stages require interpretation.
- `LOW`: Relies mainly on indirect cues; one or more `UNCLEAR` codes should usually be used alongside.

## Boundary Examples

- "Detects an external force exceeding a threshold and stops the joint": sensor=YES, decision=YES, response=YES; the complete mechanism chain holds.
- "Detects external force to improve trajectory accuracy": sensor=YES, but safety relevance may be INCIDENTAL, and the protective response cannot automatically be coded YES.
- "The robotic arm slows down when a human approaches": if the text explicitly gives the detection and the slowing condition, all three stages can be YES.
- "Multiple control modules work together": this only indicates co-existence and is insufficient to mark `EXPLICIT_CROSS_SUBSYSTEM`.
- "No propagation text found": record `ABSENT`; the conclusion can only be "this patent text provides no propagation evidence", not "propagation does not exist".
