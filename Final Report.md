# Final Report

## Executive findings (centerpiece)

*Data snapshot: files dated 2026-07-24; arrest records run through 2026-03-10. Comparison periods: old = 2023-01-01 to 2024-12-31 (731 days); new = 2025-01-01 to 2026-03-10 (434 days). Regression panel: 2023–2025.*

The main result is a **large enforcement shift without a detectable state-level crime or economic signal**. Between the old and new periods, arrest pace rose sharply (~359 to ~909 arrests/day, peaking at 39,829 in Dec 2025) and the increase varied substantially by state and area of responsibility, while the share of arrestees with convictions fell and the share with pending charges rose. These are counts by recorded apprehension location, not where arrestees live. Multivariable regressions (with multiple-testing correction) still do not show reliable associations between arrest rates and changes in violent/property crime, GDP growth, or unemployment.

## 1) Arrest-location findings (`notebooks/09_arrest_locations.py`, PR 10)

Run on hydrated `arrests-latest 7-24-2026.csv` (705,286 rows after dropping `duplicate_drop_row`). Old = 2023–2024 (731 days); new = 2025-01-01 to 2026-03-10 (434 days). Outputs: `notebooks/results/arrests_by_{state,aor,landmark}.csv`.

- Daily arrests rose from ~359 to ~909 (+153%); monthly arrests peaked at 39,829 in Dec 2025.
- Texas holds 25.7% of new-era arrests (+138% per day). Fastest-growing states: Virginia +413%, Georgia +332%, Pennsylvania/Maryland +260%, Florida +245%. New York (+64%) and New Jersey (+61%) lagged.
- By AOR, San Diego grew +961% (2.4 → 25.4/day), Washington +422%, El Paso +364%. Miami is now the largest AOR.
- Share of arrestees with a criminal conviction fell from 43.0% to 33.1%, while pending-charge cases rose from 17.4% to 29.0%.
- Interpretation and data quality: locations are recorded apprehension locations, not arrestees' residences; landmark fields often use non-specific "general area" labels. One stray 2026-09-17 record and one partial-day 2026-03-11 record were excluded, so data effectively end 2026-03-10. The new window is shorter than the old window, March 2026 is partial, and all differences are descriptive rather than causal.

## 2) Arrest-rate regressions with youth-rate-change control (`notebooks/10_arrest_regressions.py`, PR 11)

State × year panel (2023–2025, 50 states), arrests per 100k by apprehension state against changes in real GDP, unemployment and violent/property crime (RTCI, FBI check). Controls include population/density/income/education/demographics/politics, lagged outcomes, and **lagged change in youth share (ages 15–29)** from Census `sc-est2024-agesex-civ.csv`. Year fixed effects and state-clustered SEs; Benjamini–Hochberg q-values.

- Mean state arrest rate: 37.5 (2023), 26.7 (2024), 73.1 (2025) per 100k.
- 6 of 48 arrest-rate coefficients and 7 of 100 correlations are nominally significant (p<.05), near chance-level screening rates.
- **No arrest-rate coefficient survives multiple-testing correction** (q<.10). One exploratory correlation survives: old-era arrest rate versus GDP growth in the South (r = 0.57, n = 32, q = 0.061); it is not adjusted for covariates.
- Old-era controlled models still show opposite-signed nominal crime coefficients (violent +1.1, p = 0.03; property −1.1, p = 0.06, per +10 arrests/100k), but these do not replicate in 2025 or the FBI check.
- Bottom line: this is evidence of **no robust detectable association in this dataset**, not proof of zero effect.

## 3) Detention-rate regressions rerun with the same youth control (`notebooks/06_geo_regressions.py`)

The detention regressions were rerun after adding the same lagged youth-share-change control. Substantive interpretation is unchanged: most associations are weak/unstable and should be treated as exploratory, not causal.

## Interesting findings reported by the analysis

- The reported national average daily population rises from about 33.6k in 2023–24 to 55.1k in 2025–March 2026; the reported rate rises from about 9.9 to 16.1 per 100,000 residents.
- Rural/non-CBSA facilities are reported at 78.4 detainees per 100,000 residents, compared with 10.9 in metropolitan counties. These are facility locations divided by local population, not a measure of how many local residents are detained.
- Louisiana is reported at 163.1 per 100,000, and the Midwest has the largest reported regional increase (+318%). Small local populations and large facilities can make these per-resident facility rates extreme.
- Local/state facilities are reported to have grown from 2.2k to 7.8k ADP; the documents estimate that GEO and CoreCivic together hold 56% of the newer-period ADP. Operator labels are inferred, not provided by ICE.
- The correlation and regression documents characterize associations with economic and crime outcomes as weak or unstable, and explicitly caution against causal interpretation and over-reading multiple comparisons.
- The facility-change analysis identifies 111 facility codes first appearing after January 20, 2025, and 13 that stopped booking. It correctly distinguishes observed activity changes from unverified ownership/operator claims.

## Findings and changes made

1. **Duration was mislabeled as full detention-stay length.** `05_geo_detention_analysis.py` calculates duration as the difference between each stint's facility book-in and book-out. It excludes stints without a book-out date. A person transferred between facilities can therefore contribute several shorter stints, rather than one full stay. Updated the relevant summary and press-release labels to say “completed facility stint,” clarified the selection caveat, and renamed the generated summary fields to `mean_stint_days` and `median_stint_days`.
2. **The EDA workflow targeted an absent notebook.** The workflow referenced `notebooks/01_eda.ipynb`, which is not tracked, although the available analysis entry point is `notebooks/eda.py`. It also watched the nonexistent notebook path and attempted notebook/HTML conversion. Updated and renamed the workflow to run the available script, trigger on its script and data inputs, and upload the generated figures.
3. **The administration comparison is not reproducible from this repository.** `findings_04_administrations.md` names `notebooks/analysis_04_administrations.py`, which is absent, and retains the placeholder `[your name]`. Its administration-level counts and comparisons could not be checked against an analysis script here.
4. **The data extraction date and analysis cutoff need to be explained together.** Source filenames say `7-24-2026`, while the geographic analysis explicitly sets its event cutoff to March 11, 2026. These may represent the extraction date and last included event date respectively, but that distinction should be stated and the actual maximum source dates verified after LFS files are hydrated.
5. **Some claims need stronger publication framing.** The correlations script screens up to 500 outcome × detention measure × group × era combinations before filtering unusable samples, while the original press release said about 40 comparisons. The 2025 state-level regressions also have small samples. Updated the correlation document to state the screening scale and exploratory status; any portfolio-facing p-values should be adjusted for multiple testing or clearly labeled exploratory. Tier B facility ownership/operator events are explicitly unverified and should remain unpublished as factual claims until sourced.
6. **Unequal windows made a raw count sound like a decline.** The old period is 24 months and the new period is 15 months. The original “unique people fell” statement compared 539k with 455k without accounting for those unequal windows. Updated the press releases to label these as period totals and avoid calling them a decline.
7. **Facility rates could be mistaken for resident detention rates.** A state's facility ADP divided by state population measures detention at facilities in that state, including people from elsewhere. Updated the PR 1–3 headlines/notes and master finding to make this facility-location interpretation explicit.
8. **Portfolio orientation is missing.** There is no top-level README describing the research question, data provenance, setup, entry points, generated artifacts, or limitations. The copied `codebook.txt` identifies its source and CC-0 license, but project-specific citation and provenance for the additional data inputs are spread across code rather than summarized for readers.

## Validation performed

- Hydrated the required LFS inputs (`arrests-latest` and `detention-stints` sheets), reran `05_geo_detention_analysis.py`, `06_geo_regressions.py`, and `10_arrest_regressions.py`, and updated output CSVs.
- Added Census state age data (`sc-est2024-agesex-civ.csv`) to `notebooks/data/` and verified youth-share controls are present in `state_year_panel.csv`. The Census source is the [2024 state civilian population estimates by age and sex](https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/asrh/sc-est2024-agesex-civ.csv).
- The repository contains no automated test suite. Recommended data-dependent checks are listed below.

## Recommended tests before publication

- Hydrate the LFS data, rerun the analysis scripts in documented order, and compare regenerated tables and figures with the claims in all press releases and `MASTER_RESULTS.md`.
- Add tests for interval overlap and boundary dates, duplicate-stint exclusion, negative/invalid durations, missing book-outs, and the cutoff applied to open recent stints.
- Check that facility ADP aggregates reconcile to national ADP, state totals reconcile to region totals, and operator/area classifications do not silently drop facilities. Include unmapped geography and unclassified operators in the reconciliation.
- Verify the population denominators and the handling of the partial 2026 period; test that the annualization uses the actual number of days in each window.
- For the regressions, assert expected sample sizes and missingness by outcome, independently verify state-clustered standard errors, and report a multiple-comparison adjustment or explicitly designate p-values as exploratory.
- Add a reproducibility check that every documented script, input, result, and figure path exists, including the administration comparison.

## Suggestions to prepare the repository for a data-science portfolio

- Add a concise README with a project overview, research questions, data provenance/citations, environment setup, one-command reproduction instructions, figures, and a plain-language limitations section.
- Restore and document the missing administration-analysis code, remove the author placeholder, and make its period definitions and filters explicit.
- Add a source manifest with dataset URLs, release/extraction dates, event-date coverage, licenses, checksums, and retrieval instructions. Explain why the July 2026-named extracts are analyzed only through March 11.
- Keep large raw inputs in LFS or an external data store, but provide a small, clearly labeled fixture for CI so tests run without downloading multi-gigabyte data. Ensure the fixture contains no unnecessary person-level identifiers.
- Add focused automated tests and a reproducible environment lock file; make CI run syntax, data-contract, and small-fixture checks in addition to the EDA workflow.
- Separate source data, derived results, and presentation assets clearly; describe which outputs are generated and avoid making stale generated CSVs appear authoritative.
- Add citations beside sensitive or news-based facility claims, and provide a methods note on the inferred operator labels, small-area denominators, censoring/selection, and limits of causal inference.
- Keep reports concise and consolidated: use `MASTER_RESULTS.md` as the technical index and link the press releases from it; identify the codebook as third-party documentation rather than project-authored analysis.

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
