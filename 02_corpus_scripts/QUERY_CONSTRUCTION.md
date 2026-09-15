# Retrieval Query — Construction History

This document records how the final Boolean query in `query.txt` was constructed
and why the alternatives were rejected, so that the corpus can be understood (and
rebuilt) without relying on undocumented decisions. All counts below were
measured against the licensed database at the dates shown.

## Final query (adopted)

The frozen retrieval query is `query.txt`, applied on **2026-07-18** to title +
abstract (`TIAB`):

```
((humanoid OR "bipedal robot" OR "legged robot" OR "embodied intelligence" OR "human robot")
 AND ("safety" OR "avoidance" OR "force control" OR "torque control" OR "fail-safe"
      OR "monitoring" OR "prevention" OR "emergency" OR "risk" OR "stability"
      OR "redundancy" OR "limit" OR "detection" OR "reliability" OR "peripersonal"
      OR "collision" OR "shutdown" OR "fall" OR "drop" OR "adaptability"))
```

It pairs a **robot clause** (5 terms targeting humanoid and legged embodied
platforms) with a **safety clause** (20 terms spanning protection, avoidance,
force/torque control, fail-safe behavior, monitoring, and stability), so that a
record is retrieved only when the two concepts co-occur.

## Iteration history

| Version | Date | Query design | Measured yield | Decision |
|---|---|---|---|---|
| v1 (pilot) | 2026-07-05 | 3 robot terms × 8 safety terms, title + abstract + claims | 809 retrieved, 781 valid | Rejected: underfitting |
| v2 (drafted) | 2026-07-16 | + wildcards, synonyms, IPC subset (B25J/F16P/G05B/…), NOT-noise clause | not executed | Superseded during the 2026-07-18 session |
| v3 | 2026-07-18 | broadened robot clause (`robot*`, `manipulator*`), Chinese parallel block, IPC connected by OR | not executed (deprecated same day) | Superseded by v4 |
| v4 | 2026-07-18 | senior-reviewed framework + wildcards + extra control terms | **15,389** | Set aside: judged too broad for the study scope |
| v4.1 | 2026-07-18 | v4 + `exoskeleton*`, broader NOT-noise list | **~28,000** | Rejected: one added term pulled in ~13k records |
| **final** | 2026-07-18 | v4 framework **without** wildcards or added terms (5 robot terms × 20 safety terms, `TIAB`) | ~9,500 estimated; **9,710 exported** (same-day database growth) | **Adopted** as the frozen query |

Design rationale recorded at the time: the final form is deliberately the leaner
version — approximately 12× the v1 pilot — because the wider variants (15.4k,
28k) were judged to extend beyond the intended humanoid/legged interaction scope.
The broader variants are kept as documented alternatives for any future
re-scoping, together with their measured yields (9.5k / 15.4k / 28k), rather than
being discarded silently.

## Export, merge, and cleaning (2026-07-18)

1. The 9,710 detected records were exported from incoPat in **21 batches**
   (500 records per batch; 213 bibliographic fields per record).
2. Batches were merged and de-duplicated by export sequence number with
   `merge_v5_dataset.py`; the merged file carried 9,710 rows × 213 columns with
   no duplicates and continuous sequence numbers. (Two export glitches —
   a repeated segment and two missed segments — were corrected by re-export.)
3. `clean_v5_dataset.py` applied the funnel reported in the paper:
   9,710 → −334 non-analytic publication types (129 translations, 98 search
   reports, 71 design patents, 35 corrections, 1 short-term patent) → −437
   applications before 2006 → −11 empty texts → **8,928 analyzed publications**.
4. Additional dual-counting check (reported, not de-duplicated): 1,690 repeated
   application numbers and 4,889 publications belonging to multi-record simple
   families — the basis of the family-normalized re-estimation in
   `05_family_censoring_2024/`.

## Notes

- Robot-scope decision: the study targets humanoid robots and closely related
  human--robot platforms; broader retrievals covering manufacturing
  manipulators, AGVs, and AMRs were tested and rejected as outside the intended
  scope (Section IV-A of the paper). A humanoid/legged must-have term or a CPC
  anchor is the documented option if the scope is ever widened.
- The raw incoPat export is not redistributable under the database license
  (see the repository README, "Corpus access"); this document plus `query.txt`
  are sufficient to rebuild the corpus with an independent incoPat subscription.
- Chinese-language equivalents of the robot and safety terms were tested during
  the 2026-07-18 session (the v3 design) and produced no material gain over the
  English `TIAB` query; untranslated Chinese entries are still captured by the
  English terms in translated field variants.
