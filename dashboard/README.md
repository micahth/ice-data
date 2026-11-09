# Interactive dashboard

A [Streamlit](https://streamlit.io/) app that lets a reviewer explore the analysis
without reading code. It reads only the committed result tables in
`notebooks/results/`, so it runs with no raw LFS data and deploys on
[Streamlit Community Cloud](https://streamlit.io/cloud) for free.

## Run locally

```bash
python -m pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

## Pages

1. **Enforcement over time** — headline KPIs (arrests/day +153%, convicted-criminal
   share 43%→33%) and the monthly arrest trend with the partial month flagged.
2. **Geography** — arrests per 100k by apprehension state (year slider) plus the top
   ICE Areas of Responsibility by era.
3. **Detention geography** — facility average daily population per 100k local residents
   by region, CBSA class, or operator.
4. **Model uncertainty** — a coefficient-and-CI forest plot; none of the 64 arrest-rate
   coefficients survives Benjamini–Hochberg adjustment.
5. **SQL** — the declarative `sql/arrests_by_state.sql` query, run live against the
   synthetic fixture via DuckDB.

Every page carries the project's caveats (records, not people; location is not
residence), keeps a "Methods & limitations" sidebar visible, and offers a
"Data behind this chart" expander linking each view to its source table.

## Design and testing

Chart and table construction lives in `panels.py`, which has **no Streamlit import**, so
the figures are unit-tested directly in `tests/test_dashboard.py`; `app.py` is a thin UI
layer over those builders.

## Publishing a BI mirror (optional)

For roles that require Tableau or Power BI, the same committed tables
(`notebooks/results/arrests_by_state.csv`, `arrest_rate_panel.csv`, `by_region.csv`,
`arrest_regressions.csv`) load directly as CSV data sources; the Geography page maps
cleanly to a Tableau Public filled-map view.
