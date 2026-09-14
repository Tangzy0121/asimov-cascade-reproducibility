# Pre-Frozen Analysis Plan

## Analysis Set

- Full content set: the 49 normalized patent families of Topic 22 and the 38 normalized patent families of Topic 25.
- `UNCLEAR` is not treated as `NO` by default; for every metric we report the denominator, the number of `UNCLEAR` cases, and the complete-case proportion.

## Primary Descriptive Endpoints

1. Direct safety purity: the proportion with `safety_relevance = DIRECT`.
2. Contact safety mechanisms: the proportion whose `contact_context` is one of PHYSICAL_HRI / COLLISION_CONTACT / PROXIMITY_SEPARATION.
3. Force/proximity sensing proportion: `sensing_type` is one of FORCE_TORQUE / PROXIMITY / BOTH.
4. Complete mechanism chain proportion: sensor, decision, and response all coded YES.
5. Explicit humanoid proportion: `humanoid_scope = EXPLICIT_HUMANOID`.
6. Explicit propagation evidence proportion: `propagation_evidence = EXPLICIT_CROSS_SUBSYSTEM`.
7. Off-topic proportion: `topic_scope = OFF_TOPIC`; MIXED is also reported separately.

Each proportion is reported per Topic with the count, denominator, proportion, and Wilson 95% CI.

## Comparative Analysis

- Binary differences between Topic 22 and Topic 25 are tested with Fisher's exact test, reporting the odds ratio, exact p-value, and the difference between the two proportions.
- The comparisons are exploratory; p<0.05 is not used as the sole criterion for whether a topic is "genuine" or "spurious."
- Benjamini–Hochberg q-values are reported alongside the seven primary comparisons.

## Intra-Rater Agreement

- The 18 delayed re-reviews are paired with the first-round coding.
- Raw agreement rates are reported for categorical fields.
- Cohen's kappa is reported for binary derived endpoints; when category degeneracy makes kappa undefined, it is honestly marked as NA.
- This result is called `intra-rater agreement` and must not be called `inter-rater agreement`.

## Missingness and Bias

- Incomplete fields block the formal analysis; no imputation is performed.
- Single-author review carries observer bias; topic blinding and delayed re-review can mitigate but not eliminate it.
- Publication No, titles, and applicants may let an author familiar with the data guess the topic; the procedure is therefore "blinded to the Topic label," not fully blinded.

## Claim Escalation Rules

- If Topic 22 shows high direct safety purity and a high complete mechanism chain proportion, it may be described as "a model-generated text cluster enriched for force-aware HRI safety mechanisms."
- Even if the explicit propagation evidence proportion is high, it may only be called "cross-subsystem propagation disclosure in patent texts"; it cannot be used to claim that a real-robot cascade has been validated.
- If OFF_TOPIC/MIXED cases are numerous, the strength of the Topic 22 label should be downgraded, and the topic admixture should be reported openly.
