# ICE Enforcement Data: From Administrative Records to Reproducible Analysis

I built an end-to-end analysis of arrest and detention records released by the [Deportation Data Project](https://deportationdata.org/). The analysis includes **656,919 deduplicated arrest records** (262,329 in 2023–2024 and 394,590 from January 2025 to March 10, 2026), plus detention stint records, joined with **nine external input groups** (the non-DDP-record rows of the [source inventory](notebooks/MASTER_RESULTS.md#sources-and-frozen-retrieval): DDP facility data, Census population, OMB CBSA delineations, BEA GDP, BLS unemployment, two crime sources, Census/election controls, and Census youth population). These are records, not unique people. The goal was to turn them into defensible measures and to report clearly what those measures can and cannot show.

> **Development note:** I used AI-assisted development tools to accelerate implementation,
> explore alternative approaches, and improve documentation and testing. I remained
> responsible for defining analytical requirements, evaluating methodological choices,
> validating outputs, and interpreting results.

## 1. The problem

How did ICE arrest and detention activity change over time and geographically, and were state-level arrest rates associated with economic or crime outcomes?

## 2. The data challenges

- Record-level administrative data from several extracts, with duplicate arrest records.
- Incomplete dates and open-ended detention stints (1,049 older open records excluded; qualifying newer ones censored at a stated date).
- Observation windows of different lengths (731 vs. 434 days), so counts had to become daily rates.
- Facility location and apprehension location measure different things, and neither is residence.
- External population, economic, demographic, and crime data had to be joined to state-year panels.

## 3. Worked example: turning open detention records into a measure

Detention records often lack an end date, and "no end date" can mean different things. I defined explicit rules (`notebooks/ice_lib.py`) and unit-tested each one. This illustration uses three made-up records, with the code's actual output, for the window January 1, 2025 to March 11, 2026 (435 days):

| Record | Book-in | Book-out | Rule applied | Bed-days counted |
|---|---|---|---|---:|
| A | 2025-03-01 | 2025-03-11 | Closed: use recorded end | 10 |
| B | 2025-06-01 | missing | Booked in on/after 2025-01-01: **censored** at the cutoff | 284 |
| C | 2023-05-01 | missing | Older open record: **excluded**, not assumed still detained | 0 |

The stint's own book-out is used first, then the stay's book-out, then censoring. Missing starts and negative intervals are flagged and excluded. Average daily population is overlapping bed-days divided by actual window days: (10 + 284) / 435 = 0.68 for these three records. Windows are half-open so a stay ending on the window's first day adds nothing. In the real data, 1,049 older open records are excluded.

The asymmetric treatment is a documented assumption: if old open records represent real ongoing detention, period comparisons could be biased. Choosing, testing, and disclosing that rule is the work, more than the pandas.

## 4. What I built

- Cleaning, validation, and detention-interval/average-daily-population calculations (`ice_lib.py`, `data_common.py`).
- Geographic classification (region, CBSA, state) and population-normalized measures.
- A state-year panel combining enforcement and external data.
- Descriptive comparisons and regressions with HC3 or clustered errors, 95% confidence intervals, and Benjamini–Hochberg adjustment.
- Declarative SQL reproductions of selected tables (`sql/`), cross-checked against the pandas pipelines.
- An interactive Streamlit dashboard over the committed result tables (`dashboard/`).
- Automated tests, committed result tables, and documented data provenance.

> **What I decided vs. what the source provided.** The Deportation Data Project supplied
> the raw record fields (dates, locations, criminality flags, duplicate markers). The
> analytical choices are mine: the open-record censoring rule and its asymmetric
> treatment, the January 1 era split, exposure-time denominators and per-capita
> normalization, the regression specifications and robust/clustered inference, and the
> Benjamini–Hochberg multiple-testing correction. Those judgment calls — and testing and
> disclosing them — are the contribution.

## 5. What I found

- Recorded arrests per day rose from about 359 to 909 (+153%) between windows.
- The convicted-criminal share of arrest records fell from 43.0% to 33.1%.
- Apprehensions shifted geographically (for example, Texas's share fell from 27.3% to 25.7% while Florida's rose from 7.4% to 10.1%); see the [Final Report](Final%20Report.md).
- None of 64 arrest-related state-level coefficients survived multiple-testing adjustment. I did not treat that as proof of no relationship.
- The results do not establish causality.

| Arrests over time | Geography of apprehensions |
|---|---|
| ![Monthly arrests](notebooks/figures/monthly_arrests.png) | ![Arrest geography](notebooks/figures/fig7_arrest_geography.png) |

| Detention geography | Regression estimates with confidence intervals |
|---|---|
| ![Facility ADP per 100k by region](notebooks/figures/fig1_region_per_capita.png) | ![Arrest-rate coefficients](notebooks/figures/fig6_arrest_coefficients.png) |

## 6. Quality assurance and limitations

- `pytest` covers interval boundaries and censoring, cohort definitions, covariance selection against statsmodels, confidence-interval arithmetic, download failure handling, aggregate reconciliation, and figure generation.
- Tests check that numbers in the report match the generated result tables, and that local links resolve.
- Source versions are documented: published results use July 24, 2026 CSV exports; the alternative pinned download is a different (July 6) revision and is not claimed to reproduce them. See [Reproduction status](README.md#reproduction-status).
- Limitations: arrests are not people or removals; locations are not residences; small samples and wide intervals limit inference.

## 7. Skills demonstrated

| Work | Skill | Where this appears in industry |
|---|---|---|
| Excluding duplicates and invalid intervals | Data quality and validation | Deduping events/orders; rejecting malformed records in a pipeline |
| Reconstructing detention intervals; handling open records | Record-level transformation, business rules | Active-subscription / still-employed cohorts (right-censoring) |
| Reconciling aggregates to source totals | Data integrity | Pipeline tie-outs; financial/reporting reconciliation |
| Joining external datasets | Data integration | Enriching facts with dimensions from multiple systems |
| Population-normalized rates | Metric construction | Per-user / per-capita KPIs instead of raw counts |
| Average daily population from bed-days | Exposure-adjusted measures | Average active users, utilization and occupancy rates |
| Declarative SQL matched to the pandas result | SQL / set-based thinking | Warehouse queries, dbt models, BI data sources |
| Multiple-testing correction (Benjamini–Hochberg) | Inferential discipline | Not declaring a winner across many A/B-test metrics |
| Interactive dashboard over result tables | Stakeholder communication | Self-serve BI dashboards for non-technical partners |
| Tests and CI | Quality assurance | Guarding analytics logic against regressions |
| Documenting source revisions and limits | Auditability | Reproducible, defensible reporting |
| Models with uncertainty | Analytical reasoning | Confidence intervals and honest effect-size reporting |

Tools: Python, pandas, NumPy, SciPy, statsmodels, matplotlib, SQL (DuckDB), Streamlit, pytest, Git/GitHub Actions, CSV/parquet.
