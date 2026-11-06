# PRESS RELEASE 7 — Multivariable regressions: no robust effect of detention on unemployment or crime

**Historical results:** This table predates the addition of the youth-share-change control and does not reflect the rerun in `results/regressions.csv`. Use the latter for current coefficients.

OLS, state-clustered SEs, year fixed effects. Regressor: ADP per 100k **+10**. M2 adds controls: lagged outcome, ln population, ln density, population growth, ln income, % bachelor's, % Hispanic, median age, 2024 GOP vote share. M5 is a first-difference model. Full output: `results/regressions.csv`.

Coefficient on +10 detention ADP per 100k (p-value):

| Outcome | Old M2 | New M2 | Pooled M2 | Old M5 (Δ) | New M5 (Δ) |
|---|---:|---:|---:|---:|---:|
| Real GDP growth (pp) | +0.155 (<.001) | −0.031 (.10) | +0.061 (.015) | +0.428 (.002) | −0.356 (.026) |
| Unemployment change (pp) | −0.008 (.72) | +0.008 (.64) | −0.004 (.73) | −0.052 (.60) | −0.078 (.49) |
| Violent-crime change (%) | +0.70 (.15) | +0.75 (.17) | +0.63 (.047) | +3.4 (.55) | +8.9 (.020) |
| Property-crime change (%) | −0.67 (.28) | −0.00 (.99) | −0.34 (.29) | −1.8 (.68) | +1.4 (.43) |

Interpretation:
- **Unemployment and property crime:** null in every spec.
- **GDP:** positive in 2023–24 but negative (borderline) in 2025; it reversed sign, suggesting confounding by regional growth, not a stable effect.
- **Violent crime:** positive in the pooled and 2025 first-difference models only. With 38–45 observations this is suggestive, not conclusive.
- Adjusted R² for most models is ≤0.3.

**Caveats:** state-level only (~50 per year), no causal identification, multiple testing, mixed crime data sources (FBI vs RTCI) between eras.

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

U.S. Census Bureau. (n.d.-c). *Annual estimates of the civilian population by single year of age and sex for states: 2020–2024* [Data set]. https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/asrh/sc-est2024-agesex-civ.csv

U.S. Federal Bureau of Investigation. (n.d.). *State crime rates* [Data set; file hosted by CatalinaBedoya1]. GitHub. https://github.com/CatalinaBedoya1/PlotlyDashboard/blob/main/FinalProject/data/fbi_state_crime-2010-2024.csv
