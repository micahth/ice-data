# PRESS RELEASE 11 — Even after adding youth-population change, state arrest rates show no reliable link to crime or economic shifts

**Old = 2023–2024 · New = 2025.** Unit: state × year (50 states). Regressor: ICE arrests (by apprehension state) per 100,000 residents, per +10. Script: `notebooks/10_arrest_regressions.py` (OLS, year fixed effects, state-clustered SEs, controls for population, density, income, education, Hispanic share, median age, 2024 GOP vote share, lagged outcome, and **lagged change in youth share ages 15–29** from Census `sc-est2024-agesex-civ.csv`). Outputs: `results/arrest_regressions.csv`, `results/arrest_correlations.csv`, `results/arrest_rate_panel.csv`.

- **Arrest rates tripled in 2025:** the mean state rate was 37.5 (2023), 26.7 (2024) and 73.1 (2025) arrests per 100k.
- **No arrest-rate regression coefficient survives multiple-testing correction.** Of 48 coefficients, 6 had p<.05; none had a Benjamini–Hochberg q<.10. Of 100 correlations, 7 had p<.05 and one had q<.10: the old-era South-region correlation between arrest rate and GDP growth (r = 0.57, n = 32, q = 0.061). This exploratory correlation is unadjusted for covariates and does not establish causation.
- **Crime — the nominal signals still point in opposite directions:** with controls, old-era arrest rates were associated with *higher* violent-crime change (+1.1 pts per +10, p = 0.03) and with *lower* property-crime change (−1.1, p = 0.06). Neither appears in the 2025 sample (violent +0.2, p = 0.66; property +0.1, p = 0.77) or in FBI-based checks (violent −0.37, p = 0.25; property −0.33, p = 0.23), and neither is robust to correction.
- **Economy:** GDP growth and unemployment change show no association with arrest rates in the controlled models (all p>0.36). Adding the facility-located detention rate leaves the conclusions unchanged.
- **Context:** Crime fell nearly everywhere in 2025 (mean violent −9%, property −13% in the sample), so a flat relationship with arrests is unsurprising.

**Caveats:** Exploratory and descriptive, ≤150 state-years (37–50 in the new era, one year only). Arrest location is not residence. Arrests are heavily concentrated in Texas, Florida and California. Crime data are the Real-Time Crime Index sample, with FBI data as a check. Youth controls are lagged because the Census file ends at 2024. No causal claim is supported.

## References

AH Datalytics. (n.d.). *Real-Time Crime Index: Reported crime trends, January 2017–June 2026* [Data set]. GitHub. https://github.com/AH-Datalytics/rtci/blob/main/data/Crime_Index_Reported_Crime_Trends_Jan17_Jun26.csv

Blair, G., Hausman, D., & Neff, P. (2025). *Immigration and Customs Enforcement individual-level data: An introduction* [Preprint]. https://deportationdata.org/docs/ice/ice-data-preprint.pdf

Deportation Data Project. (n.d.-a). *ICE administrative arrests* [Data set; government data obtained from U.S. Immigration and Customs Enforcement through a Freedom of Information Act request]. https://deportationdata.org/data/ice.html

Deportation Data Project. (n.d.-b). *ICE detention facilities: Facility locations and attributes* [Data sets]. https://github.com/deportationdata/ice-detention-facilities

Deportation Data Project. (n.d.-c). *ICE detention stints* [Data set; government data obtained from U.S. Immigration and Customs Enforcement through a Freedom of Information Act request]. https://deportationdata.org/data/ice.html

GreatTombProductions. (n.d.). *County population trends: 2020–2025 Census population estimates* [Data set]. GitHub. https://github.com/GreatTombProductions/county-population

MIT Election Data and Science Lab. (n.d.). *County presidential election returns* [Data set; file hosted by kmazurek95]. GitHub. https://github.com/kmazurek95/us-election-county-swing/blob/main/data/raw/countypres_2000-2024.csv

Office of Management and Budget. (2023). *2023 delineation of metropolitan and micropolitan statistical areas* [Data set; file hosted by Jennifer Peebles]. https://github.com/jenniferpeebles/omb_msas_historical_delineation/blob/HEAD/data/raw/list1_2023.xlsx

U.S. Bureau of Economic Analysis. (n.d.). *SAGDP1: Real GDP by state* [Data set; file hosted by njl250]. GitHub. https://github.com/njl250/JoE-Spring-2026/blob/main/SAGDP1_ALL_AREAS_1997_2025.csv

U.S. Bureau of Labor Statistics. (n.d.). *Local Area Unemployment Statistics: State unemployment rates* [Data sets; files hosted by kmazurek95 and dathere]. GitHub. https://github.com/kmazurek95/us-election-county-swing/blob/main/data/raw/bls_laus_states.json ; https://github.com/dathere/bls-laus-stats/blob/HEAD/output/stateUnemployment.csv

U.S. Census Bureau. (n.d.-a). *2024 county gazetteer* [Data set; file hosted by kmazurek95]. GitHub. https://github.com/kmazurek95/us-election-county-swing/blob/main/data/raw/gazetteer_counties.txt

U.S. Census Bureau. (n.d.-b). *American Community Survey, 2019–2023 five-year estimates: County demographics* [Data set; file hosted by kmazurek95]. GitHub. https://github.com/kmazurek95/us-election-county-swing/blob/main/data/raw/acs_demographics.csv

U.S. Census Bureau. (n.d.-c). *Annual estimates of the civilian population by single year of age and sex for states: 2020–2024* [Data set]. https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/asrh/sc-est2024-agesex-civ.csv

U.S. Federal Bureau of Investigation. (n.d.). *State crime rates* [Data set; file hosted by CatalinaBedoya1]. GitHub. https://github.com/CatalinaBedoya1/PlotlyDashboard/blob/main/FinalProject/data/fbi_state_crime-2010-2024.csv
