# Technical guide: cohorts, models and data provenance

The [Final Report](../final_report.md) is the findings narrative. This guide defines its estimands and the generated artifacts; it is not a second report.

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

The 2025 arrest reduced-control and full-control models both use 50 observations for GDP/unemployment, 45 for violent crime and 44 for property crime; full controls estimate 12 parameters. All nine controls are finite for every state in every panel year. Remaining crime gaps are outcome-source coverage: AK, DE, ME, SD and WV for violent crime, plus NM for property crime. Report intervals—not nonsignificance alone—define the observed uncertainty. Excluding Texas (highest 2025 arrest rate) is an influence sensitivity, not a license to remove inconvenient observations. The detention scatter labels Louisiana and shows correlations with and without it; its symlog x-axis changes display spacing, not the modeled exposure.

**Corrected election coverage:** the old source-wide `mode == "TOTAL"` filter removed ID, NC, RI, UT, WA, WI, WV and WY because their returns have missing mode (no voting-method breakdown). `republican_vote_share` now selects TOTAL rows within each state, falling back only to missing-mode rows where that state has no totals. Election shares cover all 51 jurisdictions, including DC, although the detention-derived analysis panel contains 50 states. The corrected full-control 2025 arrest sample sizes are 50/50/45/44, formerly 42/42/38/37. `require_control_coverage` runs before both regression scripts fit any models and fails with state/year/column details for any missing or nonfinite control. Synthetic mixed-mode tests and a committed-panel contract protect this invariant.

**Primary testing family:** four outcomes × the 2025 (`New`) lagged-outcome (`M0`) exposure coefficient, separately for arrests and detention. This revised analysis plan was defined after examining earlier results, not preregistered. Only those four rows per analysis receive `q_bh`; the other 60 arrest exposure terms, other eras, bivariate/full-control specifications, differences, interactions, Texas exclusion and FBI checks are sensitivity analyses with unadjusted p-values and blank q-values. `inference_family` distinguishes primary, sensitivity and control rows. No primary arrest q-value is below .10. Repeated specifications are dependent; nominal-significance counts must not be read as independent chance experiments. Pointwise intervals are not BH-adjusted confidence regions. Exploratory correlation Pearson and Spearman families remain adjusted separately within each analysis; regional correlations pooling two years have dependent state observations, so their ordinary correlation p-values are only exploratory.

**All-exposure BH sensitivity (`q_bh_all_exposure`):** because the primary family was defined post-hoc, each regression table also reports Benjamini–Hochberg applied across *every* exposure coefficient (64 arrest terms, 152 detention terms)—the broadest family, which cannot have been narrowed after inspecting results. For arrests none reach q < .10 (smallest .59), so the null primary conclusion is not an artifact of the family definition. For detention the four primary 2025 lagged-outcome tests likewise stay null (q ≈ .80–.96), but the broad family does flag four `Old`-era component and FBI-check terms (`det_corecivic10`/`det_micro10` in the operator and facility-location decompositions, and the `det_rate10` FBI bivariate); these are sensitivity decompositions of the pre-2025 period, not primary 2025 associations, and remain exploratory. This column supplements, and does not replace, `q_bh`.

**Detection limits:** `arrest_mde.csv` reports an approximate 80%-power minimum detectable association using nominal two-sided alpha .05: `(t(.975, residual df) + z(.80)) × HC3 SE`. Multiplying by the all-state 2025 arrest-rate IQR/10 (5.418754) gives 0.31 GDP-growth points, 0.14 unemployment-change points, 4.66% violent-crime change and 3.23% property-crime change. These retrospective, variance-conditional approximations describe design precision, not achieved power or a prospective power analysis. They do not account for BH selection, and multiplicity generally raises detection requirements. Only one post-period year and 44–50 states constrain detection of modest associations.

Same-year arrests can respond to local economic deterioration or crime changes; this specific reverse-causality mechanism is not eliminated by controlling for lagged outcomes.

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

Use the [README commands](../README.md#reproduce-the-full-analysis): run scripts `01`–`06` in order. `01` supplies inputs to `02` and `03`; `02` supplies the panel for `05`; `04` and `05` supply arrest tables for `06`. Each numbered script has a guarded `main()` entry point. `eda.py` is optional descriptive exploration of all stays sheets and the same arrest cohort, not a report generator.

| Script | Generated tables |
|---|---|
| `01_geo_detention_analysis.py` | `overall`, `by_state`, `by_region`, `by_cbsa*`, `by_operator`, geography/operator cross-tabs, facility classification/counts and population denominators |
| `02_geo_regressions.py` | `state_year_panel`, `correlations`, `regressions` |
| `03_facility_changes.py` | `facility_changes` (observed codes/activity, not ownership) |
| `04_arrest_locations.py` | `arrests_by_state/aor/landmark`, `arrest_summary`, `arrest_criminality`, `monthly_arrests` |
| `05_arrest_regressions.py` | `arrest_rate_panel`, `arrest_correlations`, `arrest_regressions`, `arrest_mde` |
| `06_figures.py` | Monthly arrest chart, geography/operator charts, labeled detention scatter, arrest coefficient intervals |

All tables live in `results/` as ordinary Git CSVs. `pytest` checks synthetic cohorts, boundary/censoring cases, covariance selection against statsmodels, confidence-interval arithmetic, download failure behavior, lightweight EDA/figure execution and aggregate reconciliation. CI never hydrates raw LFS or contacts data services.

## Portfolio examples

**SQL:** `04_arrest_locations.py --engine duckdb --output-dir /tmp/ice-sql-results` is an alternative implementation of the six arrest descriptive tables. [`sql/clean_arrests.sql`](sql/clean_arrests.sql) handles duplicate flags, date parsing, the half-open cohort window and location normalization; [`sql/arrest_locations.sql`](sql/arrest_locations.sql) uses conditional aggregation, a window denominator and zero-safe rate comparisons. The runner also aggregates criminality, era totals and a complete monthly calendar (including zero-record months). It reads the same original CSV or explicitly selected parquet, without sending records to an external service. Tests compare SQL to pandas on synthetic duplicate/date/location cases. Output ordering among tied locations may differ; counts, rates and shares must agree. No speed claim is made without a benchmark.

**Interactive view:** `streamlit run analysis/dashboard.py --browser.gatherUsageStats=false` from the repository root reads only committed state/AOR aggregates. Users select observation window, measure and top-location count, inspect the full table and download a CSV. Shares always use all records, not just displayed locations. Different window lengths, unknown locations and residence/record distinctions are explicit. Tests exercise both periods and both geographic levels without raw inputs.

**Forecasting:** `python analysis/forecast_arrests.py` compares last-month, seasonal-naive (12-month lag) and log-AR(1) predictions. The initial training period is January 2023–December 2024 (24 complete months). Each of the 14 targets from January 2025–February 2026 is predicted from an expanding history ending the previous month; there is no shuffled split, future normalization, tuning or fitting on test targets. Partial March 2026 is excluded even from fitting the final March full-month projection. `arrest_forecast_backtest.csv` records the origin, training size, actual, prediction and signed error for every model/target; `arrest_forecast_metrics.csv` reports MAE/RMSE; `arrest_forecast_projection.csv` holds the next-month projections.

| Model | Held-out months | MAE (records/month) | RMSE (records/month) |
|---|---:|---:|---:|
| Last month | 14 | 3,881.2 | 4,419.0 |
| Seasonal naive | 14 | 17,487.9 | 19,452.6 |
| Log-AR(1) | 14 | 4,472.8 | 5,015.3 |

The fitted log-AR(1) model does **not** beat the last-month baseline. It fits an intercept and lagged log count by OLS using past months only; inverse-log predictions represent conditional medians, bounded at zero to respect count support. The short evaluation period spans a policy/regime shift, so these 14 origins are not independent validation replicates or evidence of deployment readiness. The March full-month projections (29,661 last-month; 18,640 seasonal; 29,730 log-AR(1)) are illustrative, not observed totals. No calibrated forecast intervals or causal interpretation are claimed. Tests perturb future and partial-month counts to ensure earlier predictions do not change.
