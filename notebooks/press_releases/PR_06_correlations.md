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

## References

AH Datalytics. (n.d.). *Real-Time Crime Index: Reported crime trends, January 2017–June 2026* [Data set]. GitHub. https://github.com/AH-Datalytics/rtci/blob/main/data/Crime_Index_Reported_Crime_Trends_Jan17_Jun26.csv

Deportation Data Project. (n.d.-a). *ICE detention facilities: Facility locations and attributes* [Data sets]. https://github.com/deportationdata/ice-detention-facilities

Deportation Data Project. (n.d.-b). *ICE detention stints* [Data set; government data obtained from U.S. Immigration and Customs Enforcement through a Freedom of Information Act request]. https://deportationdata.org/data/ice.html

GreatTombProductions. (n.d.). *County population trends: 2020–2025 Census population estimates* [Data set]. GitHub. https://github.com/GreatTombProductions/county-population

MIT Election Data and Science Lab. (n.d.). *County presidential election returns* [Data set; file hosted by kmazurek95]. GitHub. https://github.com/kmazurek95/us-election-county-swing/blob/main/data/raw/countypres_2000-2024.csv

Office of Management and Budget. (2023). *2023 delineation of metropolitan and micropolitan statistical areas* [Data set; file hosted by Jennifer Peebles]. https://github.com/jenniferpeebles/omb_msas_historical_delineation/blob/HEAD/data/raw/list1_2023.xlsx

U.S. Bureau of Economic Analysis. (n.d.). *SAGDP1: Real GDP by state* [Data set; file hosted by njl250]. GitHub. https://github.com/njl250/JoE-Spring-2026/blob/main/SAGDP1_ALL_AREAS_1997_2025.csv

U.S. Bureau of Labor Statistics. (n.d.). *Local Area Unemployment Statistics: State unemployment rates* [Data sets; files hosted by kmazurek95 and dathere]. GitHub. https://github.com/kmazurek95/us-election-county-swing/blob/main/data/raw/bls_laus_states.json ; https://github.com/dathere/bls-laus-stats/blob/HEAD/output/stateUnemployment.csv

U.S. Census Bureau. (n.d.-a). *2024 county gazetteer* [Data set; file hosted by kmazurek95]. GitHub. https://github.com/kmazurek95/us-election-county-swing/blob/main/data/raw/gazetteer_counties.txt

U.S. Census Bureau. (n.d.-b). *American Community Survey, 2019–2023 five-year estimates: County demographics* [Data set; file hosted by kmazurek95]. GitHub. https://github.com/kmazurek95/us-election-county-swing/blob/main/data/raw/acs_demographics.csv

U.S. Federal Bureau of Investigation. (n.d.). *State crime rates* [Data set; file hosted by CatalinaBedoya1]. GitHub. https://github.com/CatalinaBedoya1/PlotlyDashboard/blob/main/FinalProject/data/fbi_state_crime-2010-2024.csv
