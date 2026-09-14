# Family-normalized held-out STM

- Input: 6,602 unique simple-family representatives.
- Design: K=12, 70/30 split, seed 12345, same prevalence/content formulas as the publication-level model.
- Held-out covariate tests: 120.
- Nominal p<0.05: 29.
- Benjamini-Hochberg q<=0.05: 18.
- Family HIGH topics with a nominal negative C2/C10 mirror: [22, 25].
- Reviewed humanoid HIGH topics passing both scope and BH multiplicity gates: [22, 25].

STM topic numbers are not compared one-to-one with the publication-level fit because independently fitted topic labels are permutation-invariant. The valid comparison is the number of held-out effects and the downstream BERTopic-to-STM document projection gate.
