# Technical guide: cohorts, models and data provenance

The [Final Report](../Final%20Report.md) is the findings narrative. This guide defines its estimands and the generated artifacts; it is not a second report.

## Cohorts and denominators

| Analysis | Earlier window | Later window | Unit |
|---|---|---|---|
| Arrest descriptions | [2023-01-01, 2025-01-01): 731 days | [2025-01-01, 2026-03-11): 434 days | Deduplicated arrest record |
| Detention descriptions | [2023-01-01, 2025-01-01): 731 days | [2025-01-01, 2026-03-12): 435 days | Facility stint/overlapped bed-day |
| State regressions | Calendar 2023 and 2024 | Calendar 2025 only | State-year, 50 states |

The exports are dated July 24, 2026; that is not their event cutoff. Arrests on March 11 (one record) and September 17 (one stray record) are excluded. Detention includes March 11. The calendar split aligns complete outcome years; it does not isolate the January 20 inauguration. Annual models omit 2026 rather than treating its partial year as complete.

Arrest counts are not unique people, detention counts or completed removals. `arrest_criminality.csv` measures criminality **at arrest**. `overall.csv` measures criminality **at facility book-in**, counting transfers as additional stints: its convicted-category share is 30.9% → 32.6%, a different population and denominator from the arrest share of 43.0% → 33.1%. Neither describes a residence-level conviction rate.

`ice_lib.py` supplies interval rules to both detention scripts: facility book-out, then stay book-out, then censoring at March 12 for unknown ends on stints starting in 2025 or later. Older unknown ends (1,049 records) are excluded. This asymmetric censoring is an explicit measurement assumption and can bias period differences if older open records represent real ongoing detention. Missing starts and negative intervals are flagged and excluded. Windows are half-open; ADP is overlapped bed-days / actual days, and book-ins are annualized using 365.25 / actual days.

Median completed facility-stint duration is conditional on a known valid stint end. Transfers split a person's stay into multiple stints; right-censoring and the partial final period make comparisons selective. No release-rate comparison or change in release probability is reported.

Facility county → OMB CBSA and Census region. Known county without a CBSA is non-CBSA; unknown county is retained as unmapped. State/location and inferred operator tables retain unknown classifications for reconciliation. Per-capita ADP uses facility-location population, not detainee residence. Earlier-era population is the mean of 2023 and 2024; later-era and 2026 use 2025. This is not a population-time-weighted rate.

## Research design and uncertainty

The [labor-market literature appendix](LABOR_MARKET_LITERATURE.md) explains the economic motivation and competing mechanisms. GDP growth is exploratory, unemployment is closer to the labor-market question, and wages/fiscal outcomes are not observed. Crime regressions describe a separate association, without identifying whether enforcement changes crime or responds to it.

Primary association models (`M0`) include exposure per 10/100k, the lagged outcome and, for repeated years, year fixed effects. They are parsimonious descriptions, not causal estimates or state-fixed-effects models. `M1` is bivariate; `M2` adds log population, log density, population growth, log income, bachelor's share, Hispanic share, median age, 2024 Republican vote share and lagged change in ages-15–29 share. Controls describe scale, urbanization, socioeconomic context, demographic composition and political context; their choice was exploratory, not preregistered. Static ACS and 2024 vote measures cannot be interpreted as wholly pre-treatment controls for 2023.

Additional models use exposure changes, era interactions, operator/facility-location components or detention as an arrest-model control. The interaction specification uses an era indicator rather than year fixed effects and is especially vulnerable to omitted year shocks. Models of crime outcomes use lagged crime levels; GDP uses lagged log real GDP per capita, unemployment its lagged level. The arrest FBI check omits the unavailable lagged FBI level; the detention check reconstructs it.

OLS drops incomplete cases explicitly through the formula design. Single-observation-per-state samples use **HC3 robust SEs and residual-df t intervals**. Repeated-state samples use **state-clustered SEs and cluster-df t intervals** with finite-sample correction. CSVs include `n`, `n_states`, `n_parameters`, `df_resid`, `cov_type`, coefficient, SE, p-value and pointwise 95% bounds. Unidentified/saturated models fail explicitly.

The 2025 arrest reduced-control models use 44–50 observations; full-control models use 37–42, with 12 estimated parameters. Report intervals—not nonsignificance alone—define the observed uncertainty. Excluding Texas (highest 2025 arrest rate) is an influence sensitivity, not a license to remove inconvenient observations. The detention scatter labels Louisiana and shows correlations with and without it; its symlog x-axis changes display spacing, not the modeled exposure.

BH adjustment is applied separately to arrest and detention exposure-coefficient families across all reported specifications/eras/outcomes; controls are not in these families. Correlation Pearson and Spearman families are adjusted separately within each analysis. The 64 arrest coefficients include interaction terms, reduced-control models and the Texas exclusion check. Repeated specifications are dependent; nominal-significance counts must not be read as independent chance experiments. Pointwise intervals are not BH-adjusted confidence regions. Regional correlations pooling two years also have dependent state observations, so their ordinary correlation p-values are only exploratory.

## Sources and frozen retrieval

| Input | Publisher and coverage | Retrieval/processing |
|---|---|---|
| Arrest/stay/stint CSVs | Deportation Data Project, ICE FOIA; July 24, 2026 exports | Original LFS files in `data/`; documentation/license in [codebook](../data/codebook.txt); event dates filtered as above |
| Optional parquet sources | [DDP ICE data catalog](https://deportationdata.org/data/ice.html), official `deportationdata/ice` repository | `download_data.py` pins July 6, 2026 commit `bfc8b3fa7602fbf810fb811e6d07ef603e528b78`, SHA-256 and byte size per dataset; not claimed identical to local CSV exports |
| Facility location/attributes | [DDP facility data](https://github.com/deportationdata/ice-detention-facilities) | County FIPS and type; inferred operator rules in `geo_common.py`, no verified ownership history |
| County population | Census 2020–2025 estimates, hosted by [GreatTombProductions](https://github.com/GreatTombProductions/county-population) | 256 JSON shards; aggregate counties to state/region/CBSA |
| CBSA delineation | OMB July 2023, hosted by [Jennifer Peebles](https://github.com/jenniferpeebles/omb_msas_historical_delineation) | `list1_2023.xlsx` |
| Real GDP | BEA SAGDP1, chained 2017 dollars, hosted by [njl250](https://github.com/njl250/JoE-Spring-2026) | Year-over-year state growth; lagged real GDP per capita |
| Unemployment | BLS LAUS, hosted by [kmazurek95](https://github.com/kmazurek95/us-election-county-swing) and [dathere](https://github.com/dathere/bls-laus-stats) | Annual mean of available monthly state rates; source coverage/revisions can differ |
| Crime index | [AH Datalytics RTCI](https://github.com/AH-Datalytics/rtci), Jan 2017–Jun 2026 file | State agency sample, only 12-month years; sample-population rates, not statewide census coverage |
| FBI crime check | FBI rates 2010–2024, hosted by [CatalinaBedoya1](https://github.com/CatalinaBedoya1/PlotlyDashboard) | 2023–2024 changes; unavailable in 2025 |
| Demographic, land, election controls | Census ACS 2019–2023 and 2024 gazetteer; MIT Election Lab returns, hosted by [kmazurek95](https://github.com/kmazurek95/us-election-county-swing) | County population-weighted income/age, summed education/ethnicity counts, state land area and vote share |
| Youth population | [Census civilian state age/sex estimates 2020–2024](https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/asrh/sc-est2024-agesex-civ.csv) | Committed ordinary CSV; ages 15–29 / total, lagged annual share change in percentage points |

Secondary GitHub inputs use immutable revisions in `geo_common.REVISIONS` and exact URLs in `SOURCES`; no `main`/`HEAD` retrieval. The hosted copies are not guarantees of original-publisher accuracy, consistent revisions or comparable coverage. Cached files must come from those revisions; when changing sources use a fresh `GEO_CACHE`. The [DDP introductory paper](https://deportationdata.org/docs/ice/ice-data-preprint.pdf) describes the administrative records.

## Artifact map and execution order

Use the [README commands](../README.md#reproduce-the-full-analysis). `05` precedes `06` and `07`; `06` precedes `10`; `09` and `10` precede `08`. `eda.py` is optional descriptive exploration of all stays sheets and the same arrest cohort, not a report generator.

| Script | Generated tables |
|---|---|
| `05_geo_detention_analysis.py` | `overall`, `by_state`, `by_region`, `by_cbsa*`, `by_operator`, geography/operator cross-tabs, facility classification/counts and population denominators |
| `06_geo_regressions.py` | `state_year_panel`, `correlations`, `regressions` |
| `07_facility_changes.py` | `facility_changes` (observed codes/activity, not ownership) |
| `09_arrest_locations.py` | `arrests_by_state/aor/landmark`, `arrest_summary`, `arrest_criminality`, `monthly_arrests` |
| `10_arrest_regressions.py` | `arrest_rate_panel`, `arrest_correlations`, `arrest_regressions` |
| `08_figures.py` | Monthly arrest chart, geography/operator charts, labeled detention scatter, arrest coefficient intervals |

All tables live in `results/` as ordinary Git CSVs. `pytest` checks synthetic cohorts, boundary/censoring cases, covariance selection against statsmodels, confidence-interval arithmetic, download failure behavior, lightweight EDA/figure execution and aggregate reconciliation. CI never hydrates raw LFS or contacts data services.
