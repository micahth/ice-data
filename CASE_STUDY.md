# ICE Enforcement Data: From Administrative Records to Reproducible Analysis

**The rate of arrest records classified as convicted-criminal nearly doubled,
from 154.2 to 301.4 per day, even as their share fell from 43.0% to 33.1%.**
The two windows differ in length and are not seasonally adjusted.

I built an end-to-end analysis of arrest and detention records released by the [Deportation Data Project](https://deportationdata.org/) (DDP), for this project. The analysis includes 656,919 deduplicated arrest records (262,329 in 2023–2024 and 394,590 from January 2025 to March 10, 2026), plus detention stint records, joined with nine external input groups (the non-DDP-record rows of the [source inventory](analysis/MASTER_RESULTS.md#sources-and-frozen-retrieval): DDP facility data, Census population, OMB CBSA delineations, BEA GDP, BLS unemployment, two crime sources, Census/election controls, and Census youth population). These are records, not unique people. The goal was to turn them into defensible measures and to report clearly what those measures can and cannot show.

## 1. The problem

How did ICE arrest and detention activity change over time and geographically, and were state-level arrest rates associated with economic or crime outcomes?

## 2. The data challenges

- Record-level administrative data from several extracts, with duplicate arrest records.
- Incomplete dates and open-ended detention stints (1,049 older open records excluded; qualifying newer ones censored at a stated date).
- Observation windows of different lengths (731 vs. 434 days), so daily averages had to be used.
- Facility location and apprehension location measure different things, and neither is residence.
- External population, economic, demographic, and crime data had to be joined to state-year panels.

## 3. Worked example: turning open detention records into a measure

Detention records often lack an end date, and "no end date" can mean different things. I defined explicit rules (`analysis/ice_lib.py`) and unit-tested each one. This illustration uses three made-up records, with the code's actual output, for the window January 1, 2025 to March 11, 2026 (435 days):

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
- DuckDB SQL for the same arrest cohort and aggregates, with a window-function share calculation and parity checks against pandas.
- An aggregate-only Streamlit view of state/AOR shares and daily rates, with CSV download.
- Descriptive comparisons and regressions with HC3 or clustered errors, 95% confidence intervals, and Benjamini–Hochberg adjustment.
- Monthly forecasts with expanding-window backtesting against last-month and seasonal-naive baselines.
- Automated tests, committed result tables, and documented data provenance.

## 5. What I found

- Recorded arrests per day rose from about 359 to 909 (+153%) between windows.
- The convicted-criminal share of arrest records fell from 43.0% to 33.1%.
- Apprehensions shifted geographically (for example, Texas's share fell from 27.3% to 25.7% while Florida's rose from 7.4% to 10.1%); see the [Final Report](final_report.md).
- None of the four primary 2025 lagged-outcome arrest-rate tests survived BH adjustment; the other 60 exposure terms are unadjusted sensitivity analyses. Detection limits, not nonsignificance alone, frame the uncertainty.
- The log-AR(1) forecaster did not beat the last-month baseline on 14 held-out months. I report that comparison rather than presenting a fitted model as an improvement.
- The results do not establish causality.

| Arrests over time | Geography of apprehensions |
|---|---|
| ![Monthly arrests](analysis/figures/monthly_arrests.png) | ![Arrest geography](analysis/figures/fig7_arrest_geography.png) |

The 153% daily-rate comparison normalizes window length but not seasonality. This calendar-month view shows the historical pattern alongside 2025–2026; March 2026 is partial and uses its 10 observed days.

![Monthly arrest pace by calendar month and year](analysis/figures/monthly_arrests_by_calendar_month.png)

| Detention geography | Regression estimates with confidence intervals |
|---|---|
| ![Facility ADP per 100k by region](analysis/figures/fig1_region_per_capita.png) | ![Arrest-rate coefficients](analysis/figures/fig6_arrest_coefficients.png) |

## 6. Quality assurance and limitations

- `pytest` covers interval boundaries and censoring, cohort definitions, covariance selection against statsmodels, confidence-interval arithmetic, download failure handling, aggregate reconciliation, and figure generation.
- Tests check that numbers in the report match the generated result tables, and that local links resolve.
- A source-wide election-mode filter silently lost eight states. Selecting TOTAL rows per state and retaining unsplit rows where totals are absent restored the full-control economic samples from 42 to 50. Both regression scripts now reject missing controls across every state-year; crime coverage gaps remain explicit.
- Published results use four checksum-identified July 24, 2026 CSVs, available through the default downloader or Git LFS. The isolated reproduction check regenerated and matched all 30 committed result tables. The explicitly selected July 6 parquet alternative is not a reproduction source. See [Reproduce published results](docs/reproduction.md#reproduce-published-results).
- Limitations: arrests are not people or removals; locations are not residences; small samples and wide intervals limit inference.
- Annual economic outcomes are calendar-year measures: the 2025 arrest period begins January 1, not January 20, and is not an inauguration-date comparison.

## 7. Skills demonstrated

| Work | Skill |
|---|---|
| Excluding duplicates and invalid intervals | Data quality and validation |
| Reconstructing detention intervals; handling open records | Record-level transformation, business rules |
| Reconciling aggregates to source totals | Data integrity |
| Joining external datasets | Data integration |
| Conditional aggregation and window shares in DuckDB | SQL |
| State/AOR dashboard and aggregate CSV downloads | Stakeholder communication |
| Time-ordered backtesting against naive forecasts | Predictive modeling and leakage prevention |
| Population-normalized rates | Metric construction |
| Tests and CI | Quality assurance |
| Documenting source revisions and limits | Auditability |
| Models with uncertainty | Analytical reasoning |

Tools: Python, SQL, DuckDB, Streamlit, pandas, NumPy, SciPy, statsmodels, matplotlib, pytest, Git/GitHub Actions, CSV/parquet.
