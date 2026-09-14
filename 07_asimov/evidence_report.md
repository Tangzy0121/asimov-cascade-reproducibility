# Pillar 1 Evidence Report

## Scenario-level logistic regression (error ~ E_decay + controls)

| model | n | E coef | odds ratio | p |
|---|---|---|---|---|
| v2 DeepSeek k=25 | 1276 | -3.753 | 0.02 | 0.0013 |
| v2 DeepSeek k=50 | 1276 | -3.818 | 0.02 | 0.0007 |
| v2 DeepSeek k=100 | 1276 | -3.835 | 0.02 | 0.0036 |
| v2 DeepSeek strict(all-4) k=50 | 319 | -3.815 | 0.02 | 0.0171 |
| v2 KimiMV k=25 | 1232 | -2.114 | 0.12 | 0.1600 |
| v2 KimiMV k=50 | 1232 | -2.263 | 0.10 | 0.1005 |
| v2 KimiMV k=100 | 1232 | -2.223 | 0.11 | 0.1815 |
| v2 KimiMV strict(all-4) k=50 | 308 | -1.923 | 0.15 | 0.2224 |
| v2 BothWrong k=25 | 1276 | -3.314 | 0.04 | 0.0065 |
| v2 BothWrong k=50 | 1276 | -3.340 | 0.04 | 0.0041 |
| v2 BothWrong k=100 | 1276 | -3.309 | 0.04 | 0.0245 |
| v2 BothWrong strict(all-4) k=50 | 319 | -3.310 | 0.04 | 0.0460 |

| topic-level v2 DeepSeek | n_topics=17 | rho=-0.231 | p_asym=0.3726 | p_perm=0.3669 |
| v1 DeepSeek k=25 | 304 | -0.392 | 0.68 | 0.8045 |
| v1 DeepSeek k=50 | 304 | -0.064 | 0.94 | 0.9705 |
| v1 DeepSeek k=100 | 304 | -0.032 | 0.97 | 0.9862 |
| v1 KimiMV k=25 | 304 | 0.884 | 2.42 | 0.5894 |
| v1 KimiMV k=50 | 304 | 1.192 | 3.29 | 0.5014 |
| v1 KimiMV k=100 | 304 | 1.807 | 6.09 | 0.3100 |
| v1 BothWrong k=25 | 304 | 0.713 | 2.04 | 0.5678 |
| v1 BothWrong k=50 | 304 | 1.128 | 3.09 | 0.4034 |
| v1 BothWrong k=100 | 304 | 1.408 | 4.09 | 0.3169 |

| topic-level v1 DeepSeek | n_topics=20 | rho=0.159 | p_asym=0.5038 | p_perm=0.5031 |

## Topic-level (secondary matrix view)


## Caveats
- Kimi v2 landed 2026-07-31 (3 seeds, common=308/319, mean agreement 95.6%): KimiMV coefficients negative at all k but NS (p=.10-.18, T=1.0 locked for kimi-for-coding); BothWrong negative and significant (p=.004-.046). Direction consistent with DeepSeek.
- v1 scenarios sit far from patent language (nn sim ~0.1-0.2); treat v1 as weak replication.
- GPT-5/Gemini comparisons are aggregate-level only (no per-scenario labels published).