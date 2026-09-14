# ASIMOV role-separated exploratory reanalysis

This analysis reuses frozen embeddings and model judgments; no LLM or network call was made. It is post hoc and exploratory because role separation was motivated after observing the inverse pooled sign.

## Reproduction gate

- Publication pooled exposure reproduces mapping files with maximum absolute differences: {'25': 9.71445146547012e-17, '50': 9.71445146547012e-17, '100': 9.71445146547012e-17}.
- Frozen DeepSeek and Kimi pooled coefficients reproduce within 1e-9 at k=25/50/100.

## Primary k=50 role coefficients (log odds per 1-SD exposure)

| Unit | Model | Role | beta | 95% CI | OR | p | q |
|---|---|---|---:|---:|---:|---:|---:|
| publication | DeepSeek | Barrier | -0.317 | [-0.482, -0.153] | 0.728 | 0.0001582 | 0.0009492 |
| publication | DeepSeek | Propagation | 0.104 | [-0.043, 0.251] | 1.110 | 0.166 | 0.4251 |
| publication | KimiMV | Barrier | -0.111 | [-0.316, 0.095] | 0.895 | 0.2913 | 0.2913 |
| publication | KimiMV | Propagation | 0.058 | [-0.136, 0.253] | 1.060 | 0.5555 | 0.6665 |
| family | DeepSeek | Barrier | -0.215 | [-0.381, -0.050] | 0.806 | 0.01079 | 0.02157 |
| family | DeepSeek | Propagation | -0.030 | [-0.197, 0.138] | 0.971 | 0.7303 | 0.7303 |
| family | KimiMV | Barrier | -0.079 | [-0.282, 0.123] | 0.924 | 0.442 | 0.5304 |
| family | KimiMV | Propagation | 0.047 | [-0.142, 0.236] | 1.048 | 0.6275 | 0.7303 |

## Robustness and limits

The DeepSeek barrier coefficient is negative and BH-retained for both corpus units at all three k values. The primary k=50 propagation coefficient is not distinguishable from zero in either corpus unit. No individual Kimi role coefficient survives BH correction. All scenarios have nonzero barrier and propagation exposure, and primary-model VIFs are below 1.13, so the null propagation result is not caused by exact zero exposure or severe collinearity.

Leave-one-role-topic-out analysis keeps the publication-level DeepSeek barrier sign negative for all 12 barrier-topic omissions (11 nominally significant). In the family pool, however, omitting Topic 22 reverses the barrier sign for both DeepSeek and Kimi. The family barrier result is therefore Topic-22-dependent. Propagation estimates are less stable and do not provide a robust positive cascade signal.

## Interpretation

Role separation does not convert the frozen ASIMOV stress test into positive validation. It localizes the pooled inverse association mainly to similarity with safety-barrier topics in DeepSeek, while exposure to propagation-node topics remains null or unstable. The result is useful as a construct diagnosis: the pooled exposure mixes protective and propagating mechanisms, but the current benchmark still does not validate the proposed technology-to-cascade link. See the CSV and JSON outputs for every declared variant and diagnostic.