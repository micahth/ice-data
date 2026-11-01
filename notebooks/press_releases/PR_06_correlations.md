# PRESS RELEASE 6 — Detention rates track economic and crime outcomes only weakly, and the sign flips between eras

State-year panel (states plus DC, 2023–2025). Old = 2023–24, New = 2025. Outcomes are year-over-year changes: real GDP growth (BEA), unemployment (BLS LAUS, pp), violent and property ("nonviolent") crime rate (Real-Time Crime Index for 2025 and the Old era; FBI as an Old-era check). Full tables: `results/correlations.csv`.

Selected significant (p<.05) all-state Pearson correlations:

| Era | Outcome | r | n |
|---|---|---:|---:|
| Old | GDP growth | +0.24 | 100 |
| Old | Violent-crime change | +0.26 | 90 |
| Old | Change in detention vs violent-crime change | +0.42 | 45 |
| Old | Property-crime change vs CoreCivic ADP | −0.23 | 88 |
| New | GDP growth vs local/state-run ADP | −0.31 | 50 |

- **Unemployment:** no significant correlation in either era.
- **Crime in 2025:** no significant correlation with overall detention; the only flag is micropolitan-facility detention vs violent-crime change (r = −0.29, p = 0.05).
- Spearman (rank) correlations are mostly insignificant, so many results are driven by a few high-rate states (LA, NM, MS).
- The script screens up to 500 outcome × detention measure × group × era combinations before filtering unusable samples. Treat nominal p-values as exploratory unless the comparisons are corrected for multiple testing.

**Caveat:** correlation only. 2025 crime comes from a sample-based index covering 45 states + DC (not FBI).
