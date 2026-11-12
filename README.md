# ICE arrests and detention, 2023–2026

**Arrests classified as involving convicted criminals nearly doubled per day**, from
154 to 301, even as their share fell from 43.0% to 33.1%. These are arrest
records, not unique people or completed removals; the comparison adjusts for
window length, not seasonality.

![Daily arrest pace by calendar month and year](analysis/figures/monthly_arrests_by_calendar_month.png)

- Overall arrests rose from 359 to 909 per day (+153%).
- Facility average daily population per local resident rose in every region; this measures where people are held, not where they live.
- None of four primary 2025 arrest-rate tests survived BH adjustment at q < .10; associations are exploratory, not causal.

**Stack:** Python, pandas, DuckDB, statsmodels, Matplotlib, Streamlit, pytest, GitHub Actions.

**Explore:** [Dashboard (local setup)](docs/reproduction.md#dashboard) · [Case study](CASE_STUDY.md) · [Report](final_report.md) · [Methods and reproduction](docs/reproduction.md) · [Data source](https://deportationdata.org/data/ice.html) · [AI use](docs/reproduction.md#ai-use)
