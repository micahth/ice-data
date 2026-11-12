# Plan: monthly ICE detention population (ADP) forecast

Status: **complete (Stages 1–7 executed)**. This is the historical plan; results and decisions are in
[`ADP_DATA_AUDIT.md`](ADP_DATA_AUDIT.md) and [`MASTER_RESULTS.md`](MASTER_RESULTS.md#portfolio-examples).
The optional Diebold-Mariano tests and the `log_ar1_arrests` link beyond the records series were not done.

## Design decisions

| Decision | Choice | Reason |
|---|---|---|
| Relationship to existing work | New, separate component; `forecast_arrests.py` and its outputs stay unchanged | Arrests are a flow and ADP is a stock. They answer different questions. |
| Primary target | **Monthly average daily population (ADP):** person-days in ICE detention during calendar month *m* ÷ days in *m* | Describes the typical daily detained population. It matches the half-open interval method in `ice_lib.adp()`. |
| Not the target | Monthly book-ins and unique people | Book-ins are a flow that transfers inflate. ADP is not a unique-person count. |
| Data series | (A) **Record-level ADP** from DDP detention stints, 2023 to Feb 2026. (B) **Published ADP** from ICE detention-management statistics, as parsed by DDP, from FY2019 (Oct 2018). | (B) provides about 7 years of history, compared with about 3 for (A). |
| Combining A and B | **Compare and reconcile; never silently splice.** Each row keeps a `source` column. A spliced series, if any, is only a labeled sensitivity analysis. | The two series use different definitions, facility scopes and vintages. |
| Forecast horizon | One month ahead, complete months only | Matches the arrest forecast and avoids partial-month leakage |
| Evaluation | Expanding-window, rolling-origin backtest that uses past data only, with last-month and seasonal-naive baselines | Consistent with `forecast_arrests.py` |

### Risks found while reading the code

1. **Transfer double counting.** `ice_lib.build_intervals()` sets
   `end = book_out_date_time.fillna(stay_book_out_date_time)`. When a non-final stint in a
   multi-stint stay has no stint book-out, its end becomes the stay book-out. The interval
   then overlaps every later stint in that stay, and those person-days are counted twice.
   The existing period-level ADP (`overall.csv`) may already be inflated by this; Stage 1
   must measure how much.
2. **Older open stints are dropped.** Stints with an unknown end that were booked in before
   `OPEN_STINT_START` (2025-01-01) are excluded. This may understate ADP in later months.
3. **Left truncation.** People booked in before the extract's first record are missing.
   Early months may therefore be undercounted until long stays "burn in."
4. **Right censoring and the partial final month.** The cutoff is 2026-03-11. March 2026
   is partial, and recent months depend on censored open stints.
5. **Published-series vintages.** The ICE spreadsheets are issued about twice a month, each
   with a `file_date` and `pull_date`, and values can be revised. Some tables are
   **fiscal-year-to-date** averages rather than monthly values.

### Proposed artifacts

| Path | Purpose |
|---|---|
| `analysis/ice_lib.py` | New pure helpers: `transfer_safe_intervals()` and `monthly_adp()` |
| `analysis/07_monthly_adp.py` | Builds record-level monthly ADP from raw stints. Requires LFS data or `ICE_DATA_DIR`. |
| `analysis/download_official_adp.py` | Pinned, checksum-verified fetch of DDP detention-management data, reduced to a small CSV |
| `analysis/data/ice_published_adp_monthly.csv` | Small committed published series with vintage columns |
| `analysis/results/monthly_adp_records.csv` | Series A with diagnostic columns |
| `analysis/results/adp_series_reconciliation.csv` | Month-by-month comparison of A and B |
| `analysis/forecast_adp.py` | Baselines, models, backtest, intervals and projection |
| `analysis/results/adp_forecast_{backtest,metrics,projection}.csv` | Forecast outputs |
| `analysis/figures/monthly_adp_forecast.png` | Series, backtest forecasts and intervals |
| `tests/test_adp.py` | Synthetic, network-free tests |

---

## Shared context (prepend to every prompt)

```text
Repository: micahth/ice-data (Python 3.11, pandas, numpy, statsmodels, pytest; pinned in
requirements.txt). Conventions:
- Interval rules live in analysis/ice_lib.py: half-open windows [w0, w1); ADP =
  overlapped person-days / actual window days. Tests are in tests/test_intervals.py.
- Raw inputs are under Git LFS in data/ and are read through analysis/data_common.read_source().
  Set ICE_DATA_DIR to use parquet files instead. Tests and CI must NOT need LFS data or
  network access. They use synthetic fixtures and small committed CSVs in analysis/results
  or analysis/data.
- The existing arrest forecast is analysis/forecast_arrests.py (last_month, seasonal_naive,
  log_ar1; expanding window; partial final month excluded), tested in tests/test_portfolio.py.
  Do not change its behavior or its outputs.
- Numbers quoted in README.md, final_report.md, CASE_STUDY.md and analysis/*.md are
  asserted against generated CSVs by tests/test_documentation.py. Update prose and CSVs
  together, and add assertions for any new headline number.
- Facility and booking language is descriptive. ADP is not a unique-person count, and
  nothing here is causal.
- Keep changes surgical. Comment only non-obvious logic. Run `python -m pytest -q`.
Target: monthly average daily population (ADP) = person-days in detention in calendar
month m / number of days in m. Forecasts are one month ahead and use complete months only.
```

---

## Stage 1: Audit detention records and interval calculations

**Goal:** Quantify how stint records and `build_intervals()` behave before any monthly
series is built.

**Checks:**
- `duplicate_drop_row` handling
- Stints per stay
- Overlapping stints within a stay, caused by missing stint ends or by data overlap
- Concurrent stays for the same `unique_identifier`
- Interval-status counts by book-in month
- Left-truncation burn-in
- The person-days added by the stay-end fallback

**Acceptance:**
- A diagnostic CSV and a short Markdown note.
- The estimated percentage of double-counted person-days, by month and overall.
- A recommended first trustworthy month for Series A.

```text
[Shared context]
Task (Stage 1 – audit only; do not change published results):
1. Read analysis/ice_lib.py, analysis/01_geo_detention_analysis.py and the stint/stay
   sections of data/codebook.txt.
2. Add a pure function `interval_diagnostics(stints)` to analysis/ice_lib.py. It takes
   deduplicated stints with stay_ID, unique_identifier, book_in_date_time,
   book_out_date_time and stay_book_out_date_time, plus the output of build_intervals().
   Return per-record flags:
   - `stay_end_fallback`: the stint end came from stay_book_out_date_time.
   - `overlaps_next_stint`: the interval end is after the next stint's book-in in the same
     stay, ordering by book_in_date_time with stable ties.
   - `overlap_days`: the overlapping duration.
   - `concurrent_stay`: the person has another stay whose interval overlaps this one.
3. Add synthetic unit tests to tests/test_intervals.py:
   - A 3-stint transfer stay with a missing middle book-out must flag the middle stint
     and report the exact overlap days.
   - A clean transfer stay must have zero overlap.
   - Two overlapping stays for one person must be flagged.
4. Add analysis/audit_detention_intervals.py. It reads stints through read_source(), with
   the same columns and deduplication as script 01. It writes
   analysis/results/detention_interval_audit.csv with one row per calendar month from the
   first to the last observed month. Columns: month, book_ins, stints_closed,
   stints_open_censored, stints_open_excluded, invalid_negative, missing_book_in,
   stay_end_fallback, overlapping_stints, overlap_person_days, adp_current_method, and
   adp_overlap_removed (overlaps clipped as in Stage 3), using monthly windows.
   Also add a burn-in diagnostic: for each month, the ADP share from stints booked in more
   than 90 and more than 365 days before the month start.
5. Do not modify ice_lib.build_intervals() or any existing result CSV in this stage.
6. Summarize the findings in analysis/ADP_DATA_AUDIT.md: the size of the transfer
   double count, the impact of the open-stint policy, the recommended first trustworthy
   month (justify it with the burn-in curve), and open questions. Use only numbers from the
   generated CSV.
Stop when tests pass and the audit note is written. If raw data are unavailable, say so,
deliver the code and tests, and leave the CSV and numbers as TODO.
```

## Stage 2: Obtain and validate the published monthly ADP series

**Goal:** Build a reproducible, vintage-aware monthly ADP series from DDP's parsed ICE
detention-management statistics, starting in FY2019.

**Acceptance:**
- A pinned downloader with a SHA-256 checksum.
- A small committed CSV: `month, adp, source_table, fiscal_year, file_date, pull_date,
  is_fytd_derived, vintage_rank`.
- Validation tests that run offline.

```text
[Shared context]
Task (Stage 2 – published series):
1. Find the Deportation Data Project's processed ICE detention-management datasets on
   https://deportationdata.org/data/processed/ice.html (bundled Excel/Parquet). Raw
   spreadsheets are also on its government-reports page. Identify the table(s) that
   contain average daily population and record exactly what each measures:
   - Monthly ADP or fiscal-year-to-date ADP
   - Total population or a breakdown by arresting agency (ICE vs. CBP),
     criminality, or facility type
   - Units, and whether family or ORR populations are included
   Record the URLs and revision identifiers. If the site or files cannot be reached, stop
   and report that; do not invent values.
2. Add analysis/download_official_adp.py. Follow analysis/download_data.py: fetch a pinned
   revision, verify a SHA-256 stored in a JSON checksum file, and cache files under
   analysis/.cache/. Reduce the data to analysis/data/ice_published_adp_monthly.csv.
3. Normalize to calendar months:
   - If the tables give monthly ADP, use those values directly.
   - If they give only fiscal-year-to-date ADP from snapshots, derive monthly values
     only where consecutive snapshots fall at month ends:
     ADP_m = (YTD_m * D_m - YTD_{m-1} * D_{m-1}) / days(m),
     where D_m is the number of days in the fiscal year to date. Set
     is_fytd_derived=True. Leave months that cannot be derived exactly as missing; never
     interpolate.
   - Keep every vintage (file_date and pull_date). Use the latest vintage per month as
     the default value, and also store the first-published vintage (vintage_rank=1) for a
     real-time sensitivity check.
4. Add validation as pure functions with synthetic tests in tests/test_adp.py:
   - Months are unique and contiguous, except for documented gaps.
   - Values are finite and greater than 0.
   - FY boundaries are correct: October starts the fiscal year.
   - The FYTD-to-monthly derivation is exact on a synthetic example.
   - Revisions between vintages are reported but do not raise errors.
   - A sanity check verifies that the recomputed FYTD average from monthly values matches
     the published FYTD figure within a stated tolerance.
5. Write analysis/results/published_adp_revisions.csv with each month's first and latest
   value and the percentage revision.
Tests must read only the committed CSV or synthetic data, never the network.
```

## Stage 3: Construct a consistent monthly target without double-counting transfers

**Goal:** Build Series A with a transfer-safe interval rule. Then reconcile Series A with
Series B and choose the modeling target explicitly.

**Transfer-safe rule:** Within a stay, order stints by book-in. Set each stint's effective
end to `min(own end, next stint's book_in)`. Compute the stay-end fallback only for the
**last** stint. Merge any remaining overlap at the person level, so that one person
contributes at most one person-day per day.

**Acceptance:**
- In synthetic tests, the summed stint person-days equal the person-days from the stay
  union.
- `monthly_adp_records.csv` and `adp_series_reconciliation.csv` are written.
- The documented target choice is either "Series B primary, Series A validation" or the
  reverse, with reasons.

```text
[Shared context]
Task (Stage 3 – target construction and reconciliation):
1. In analysis/ice_lib.py add `transfer_safe_intervals(df)`. It runs after build_intervals()
   and returns start/end values in which:
   (a) For non-final stints, the end is clipped to the next stint's book-in in the same
       stay_ID.
   (b) The stay_book_out fallback applies only to the final stint of a stay.
   (c) Overlapping intervals for the same unique_identifier are merged, so concurrent
       records cannot add a second person-day.
   (d) Gaps between stints stay gaps.
   Keep build_intervals() unchanged so that existing results still reproduce.
2. Add `monthly_adp(intervals, first_month, last_month, cutoff)`. It applies ice_lib.adp()
   to each calendar-month window [month start, next month start) and returns:
   month, adp, days_in_month, days_observed and partial_month. A month is partial when
   the cutoff falls inside it, and its ADP uses only the observed days.
3. Tests in tests/test_adp.py:
   - A 3-stint transfer with a missing middle book-out gives the same person-days as the
     stay-level interval.
   - A transfer across a month boundary splits correctly.
   - February and leap-year day counts are correct.
   - Two concurrent stays for one person count once.
   - The partial final month uses observed days only.
   - The sum over months of ADP*days equals the total person-days.
4. Add analysis/07_monthly_adp.py, which reads stints like script 01 does. Write
   analysis/results/monthly_adp_records.csv with these columns: month, adp (transfer-safe,
   primary), adp_current_method (build_intervals only), adp_censor_all, adp_exclude_all,
   days_observed, partial_month, and burn_in_ok (from the Stage 1 recommendation).
5. Write analysis/results/adp_series_reconciliation.csv for overlapping months. Columns:
   month, adp_records, adp_published_latest, adp_published_first, difference,
   pct_difference, and ratio. Report the mean, median and range of the differences, the
   correlation of month-over-month changes, and whether the gap trends over time.
   List the definitional reasons for any gaps:
   - Hold rooms and short stays
   - Facility scope
   - Snapshot timing
   - The open-stint policy
   - Revisions
6. Decide and document the modeling target in analysis/ADP_DATA_AUDIT.md:
   - Default: Series B (published, latest vintage) is the primary target because it
     covers more history.
   - Series A is the validation and secondary target over 2023 to Feb 2026.
   - A spliced or level-adjusted series may only be a labeled sensitivity check, with
     a `source` column on every row.
   - If the reconciliation shows that the series are not comparable, say so and model
     them separately.
Do not modify existing result CSVs or report numbers.
```

## Stage 4: Establish last-month and seasonal-naive baselines

**Goal:** Define the baselines that any model must beat, using the same complete-month
rules as the arrest forecast.

**Acceptance:**
- `forecast_adp.py` exposes `complete_months()`, `predict_baselines()` and `backtest()`.
- The arrest forecast's outputs remain byte-identical.

```text
[Shared context]
Task (Stage 4 – baselines):
1. Create analysis/forecast_adp.py, modeled on analysis/forecast_arrests.py.
   - Input columns: month, adp, partial_month, and source.
   - Validation: unique, ordered and contiguous months; only the final month may be
     partial; ADP values are finite and greater than 0; there is exactly one source per
     run.
   If it reduces duplication, generalize forecast_arrests.complete_months() with a
   `value` column parameter. In that case, rerun forecast_arrests.py and confirm that
   arrest_forecast_*.csv are byte-identical.
2. Baselines:
   - last_month: y_{t-1}
   - seasonal_naive: y_{t-12}
   - seasonal_naive_drift (optional): y_{t-12} * (y_{t-1} / y_{t-13}), clearly marked
     as an extra baseline
3. backtest(series, min_train) runs an expanding window with one forecast per origin and
   records month, train_end, n_train, model, actual, forecast and error
   (forecast - actual). Defaults:
   - Series B: min_train = 36 months, so October 2018 to September 2021 is the first
     training window.
   - Series A: min_train = 24 months, from the first burn_in_ok month.
4. Tests in tests/test_adp.py with synthetic series:
   - train_end < month for every row.
   - Perturbing future months or the partial month does not change earlier forecasts.
   - The last-month and seasonal-naive forecasts equal the shifted actuals.
   - Gaps, duplicates, non-positive values, an early partial month and too-short input
     all raise ValueError.
```

## Stage 5: One-month-ahead models with expanding-window backtesting

**Goal:** Fit a small, pre-declared set of models using only information available at
each origin.

**Candidate models (fixed before seeing test errors):**
- `log_ar1`: AR(1) on log ADP, with the same form as the arrest model
- `log_ar1_seasonal`: log-AR(1) with month-of-year dummies, used only when n_train ≥ 36
- `ets_damped`: additive damped-trend ETS on log ADP (statsmodels)
- Optional `log_ar1_arrests`: log-AR(1) plus last month's log arrests from
  `monthly_arrests.csv`. Series A only, because arrests start in 2023. This is the
  "connected" link to the arrest component, and it uses only lagged arrests.

**Acceptance:**
- Models are fitted on the past only.
- A failed fit is recorded and does not stop the backtest.
- Results come from the regime split as well as the full sample.

```text
[Shared context]
Task (Stage 5 – models):
1. In analysis/forecast_adp.py, extend predict(history, exog=None) with the following
   models. Fit each one on the supplied history only:
   - log_ar1: OLS intercept plus lagged log ADP, with an inverse-log median forecast.
   - log_ar1_seasonal: log_ar1 plus month-of-year dummies. Use it only when
     len(history) >= 36; otherwise return NaN.
   - ets_damped: statsmodels ExponentialSmoothing on log ADP with trend="add",
     damped_trend=True and no seasonality. Fix the settings; do not search them
     per origin.
   - log_ar1_arrests (Series A only): add log arrests at t-1 from
     analysis/results/monthly_arrests.csv using complete months only. Arrests for month t
     are never used to forecast month t.
   If a model fails to converge, return NaN for that origin and record it in
   `fit_status`. Do not drop the row silently.
2. Do not tune hyperparameters on backtest targets. The model list is final before the
   backtest runs. Put the list in a module-level MODELS tuple.
3. main() runs the backtest for Series B (primary) and Series A (validation), with the
   source recorded on every row. It writes:
   - analysis/results/adp_forecast_backtest.csv
   - analysis/results/adp_forecast_projection.csv: the next complete month for each
     model and source, with the training window stated
4. Tests:
   - Each model's forecast at origin k is unchanged when data after k are perturbed.
   - The log_ar1_arrests model never reads arrests at or after the target month.
   - The seasonal model returns NaN below 36 training months.
```

## Stage 6: Evaluate errors, bias and prediction intervals

**Goal:** Give an honest comparison against the baselines, with calibrated uncertainty.

**Metrics for each model, source and period:**
- MAE, RMSE and MAPE
- MASE relative to `last_month`
- Mean signed error (bias) and the share of over-forecasts
- 80% and 95% interval coverage, mean width, and the interval (Winkler) score

**Periods:**
- Full sample
- Before 2020-03
- 2020-03 to 2021-12 (COVID-era collapse)
- 2022–2024
- 2025 onward (policy regime)

**Intervals:** empirical quantiles of each model's past one-step log errors, using only
errors from earlier origins. This is split-conformal style, with a minimum of 12 prior
errors; intervals are left blank before that.

**Acceptance:**
- `adp_forecast_metrics.csv` is written.
- Coverage is reported honestly, even when it is poor.
- No claim of deployment readiness is made.

```text
[Shared context]
Task (Stage 6 – evaluation):
1. In analysis/forecast_adp.py add `prediction_intervals(predictions, levels=(0.8, 0.95),
   min_errors=12)`. For each model and origin, take the log errors log(actual/forecast)
   from strictly earlier origins of the same model and source. Use their empirical
   quantiles to set lower and upper bounds. Leave the bounds missing when fewer than
   min_errors errors exist.
2. Add `evaluate(predictions)`. It returns one row per model, source and period, using
   the period labels full, pre_covid (<2020-03), covid (2020-03..2021-12), 2022_2024 and
   2025_on. Columns: n_forecasts, mae, rmse, mape, mase_vs_last_month, mean_error,
   pct_over, cover80, cover95, width80, width95, interval_score95.
   Write the result to analysis/results/adp_forecast_metrics.csv.
3. Optionally add Diebold-Mariano tests against last_month, reported as descriptive only
   with an explicit note that the origins are serially dependent and few.
4. Tests with synthetic data:
   - Intervals use only earlier errors, so perturbing a later actual leaves earlier
     bounds unchanged.
   - Coverage is about 0.8 and 0.95 on a long i.i.d. lognormal-noise synthetic series
     (loose tolerance).
   - The metric formulas match hand-computed values.
   - The bounds are missing before min_errors.
5. Print a short summary that states whether any model beats last_month on MAE in each
   period. Do not cherry-pick a period.
```

## Stage 7: Integrate the model, tests, charts and documentation

**Goal:** Ship the component in the same way as the arrest forecast, with docs bound to
the CSVs by tests.

**Acceptance:**
- `python -m pytest -q` passes with no LFS data and no network.
- `06_figures.py` produces the new figure.
- The docs quote only tested numbers.

```text
[Shared context]
Task (Stage 7 – integration):
1. Figure: add `plot_monthly_adp_forecast(series, predictions, path)` to
   analysis/figure_common.py, using the existing style and colors. It plots:
   - Series B and Series A, each with its own label
   - Last-month and best-model backtest forecasts
   - 80% intervals
   - Shading for the COVID and 2025+ periods
   - The partial final month marked
   - A source footnote
   Call it from analysis/06_figures.py using only committed CSVs, write
   analysis/figures/monthly_adp_forecast.png, and update the figure count in
   tests/test_scripts.py.
2. Result contracts in tests/test_result_contracts.py:
   - The ADP backtest rows have train_end < month.
   - The metrics recompute from the backtest CSV.
   - The projection month equals the last complete month + 1.
   - The reconciliation months fall within both series.
   - Every row has a valid source.
3. Docs:
   - analysis/MASTER_RESULTS.md, "Portfolio examples": describe the target definition,
     the transfer-safe rule, the two sources and their reconciliation, the baselines,
     the models, the backtest design, the intervals and the limitations.
   - README.md "SQL, interactive view and forecasting": add one paragraph and the
     command `python analysis/forecast_adp.py`. Explain how to refresh the published
     series.
   - final_report.md: add a brief subsection only if the results warrant it.
   - Wording: "average daily detained population", not "people detained".
   - State whether models beat last_month.
   - Explain why the record-level ADP differs from the published ADP.
   - Note that the existing period ADP in overall.csv uses the original interval rule,
     and quantify the difference from the Stage 1 audit. Do not silently change
     published period numbers. If the team decides to adopt the transfer-safe rule
     everywhere, make that a separate, explicit change.
4. Add assertions to tests/test_documentation.py for every new number quoted in the
   docs, such as the MAE values, coverage and the reconciliation gap.
5. Update .github/workflows/tests.yml only if new paths need to trigger CI. Run
   `python -m pytest -q` and `python -m compileall -q analysis tests`.
6. Remove analysis/ADP_FORECAST_PLAN.md, or mark it complete, once the work is done.
```

## Out of scope

- Facility-level or AOR-level ADP forecasts
- Forecasts more than one month ahead
- Causal claims about policy effects
- Replacing the arrest forecast
- Combining sources without a `source` label
