# Updated Data & Future Project Ideas

## Is there newer data? Yes.
The upstream repo (`deportationdata/ice`) was refreshed in Sept 2026 ("New variables sep2026", commit `dcfd2c0`,
2026-09-22). The files here are the 7/24/2026 extract. `notebooks/fetch_latest_data.py` downloads the
new parquet files (the sandbox could reach `media.githubusercontent.com`, so I verified they download as real data).

| File | Rows (new) | Notes |
|---|---|---|
| arrests | 896,393 | apprehensions through 2026-08-06 (current CSV: 713,464) |
| detainers | 740,601 | new simplified `request_type`, duplicate flags |
| detention-stays | 1,264,756 | book-ins through 2026-08-06; 5.2% without book-out (current files: stays end 2026-03-11, sheets cap at 1M rows) |
| detention-stints | 3,202,317 | new variables |
| joined arrests/stays | 886,369 | |

Why it matters: Analysis #5's biggest caveat was that stays stopped at 2026-03-11, ~134 days before extraction,
so Trump-2nd stay lengths and the still-detained snapshot were censored. The new data covers ~5 more months and
the parquet format has no 1M-row sheet split. New columns include `age_at_apprehension_approximate`,
`apprehension_method_simple`, `final_order_before_apprehension`, duplicate-flag fields, cleaned city, and
`final_program_group`.

Not yet done: the committed CSVs and analysis #5 outputs were not regenerated on the new data. Next step is
to point `analysis_05` at `data_updated/` (switch `read_csv` to `pyarrow` parquet reads) and rerun.

## Future project ideas
1. **Refresh #5 on the new data** – recompute funnel, release mix and the still-detained snapshot with far less censoring; compare to the 7/24 numbers (a vintage diff).
2. **Detention population time series** – daily census from stints (book-in/out) by facility and state; capacity vs. growth, new facilities.
3. **Transfers and distance** – stint sequences: how many transfers per person, distance from arrest city to final facility, links to length of stay.
4. **Detainer pipeline** – detainers → arrests → detention; which jurisdictions' detainers convert, how long after prep date; use new `request_type` and duplicate flags.
5. **Arrest method shifts** – `apprehension_method_simple` by administration, state and criminality (at-large vs. jail transfer vs. border).
6. **Age and vulnerability** – using `age_at_apprehension_approximate`: detention rates, bond and stay length for minors, seniors, women.
7. **Final order before arrest** – share arrested with an existing final order, time to removal, by country.
8. **Geography/hotspots** – map arrests per capita by city/county using cleaned city; surges by month.
9. **Time-to-removal survival analysis** – Kaplan–Meier / hazard curves for stays by nationality, criminality and administration, handling censoring properly.
10. **Data-quality tracker** – duplicates, missingness and anomalies across vintages.
