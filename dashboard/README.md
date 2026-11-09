# Interactive dashboards

Both interfaces read **committed aggregate tables**, not raw LFS records.

## Streamlit

```bash
python -m pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

The five views are:

1. **Enforcement over time:** comparison KPIs including detention ADP, with a period
   filter for the monthly chart and partial March identified. KPIs always compare
   both windows; they do not silently change meaning when the chart is filtered.
2. **Geography:** year and region filters, annual arrests per 100k on a fixed color
   scale, and a state selector (or map selection) for AOR/landmark drill-downs.
   The annual panel contains 50 states, not DC/territories. Drill-downs use
   `arrests_state_locations.csv`, **joint state/year/location counts**, not
   relationships inferred from separate marginal totals.
3. **Detention geography:** region, CBSA class or inferred operator; raw ADP versus
   population-normalized ADP; and period filtering. Operator per-capita figures use
   **national** denominators, not local operator catchment populations.
4. **Model uncertainty:** outcome/specification controls and an M0 excluding-Texas
   sensitivity toggle. Different outcomes have separate axes and unit labels.
   These are precomputed 2025 national state-level models, not region-filtered fits.
5. **SQL:** DuckDB runs the query against a clearly labeled synthetic fixture.
   Query errors and input failures are surfaced separately.

The methods sidebar stays visible. Each chart exposes its table and a filtered CSV
download. The exact AI-development disclosure appears in README and the case study;
the dashboard carries a short responsibility note.

`panels.py` separates chart logic from Streamlit. Tests cover filters, source
reconciliation, all SQL result columns, and real Streamlit widget interactions.

## Standalone browser companion / GitHub Pages

```bash
python dashboard/build_site.py --output site
python -m http.server 8000 --directory site
```

Open `http://localhost:8000`. This is a separate, static implementation of the same
five views, using the same committed data, with a bundled Plotly library and no
Python server in production. It includes a full-size figure viewer and downloadable
Tableau package. The SQL result is **precomputed at build time**, not executed in
the browser. The Plotly library and licensed US topology are bundled locally, so
charts do not require a runtime CDN request. Run Streamlit from the repository root
so `.streamlit/config.toml` enables serving the same local basemap.

CI uploads `dashboard-preview` as a downloadable site artifact. Serve the extracted
directory over HTTP; double-clicking `index.html` may block JSON requests.

**Public deployment is blocked pending repository configuration.** The current
credential received HTTP 403 when enabling Pages. A repository administrator must
choose **Settings > Pages > Source: GitHub Actions**. Once merged,
`.github/workflows/pages.yml` publishes on changes to the site/data and supports a
manual run. It declares its actual deployment URL in the workflow environment.
No live URL is claimed before a successful deployment.

Streamlit Community Cloud hosting is an alternative, not currently provisioned:
sign in, select this public repository and `dashboard/app.py`, and deploy. Its
adjacent `requirements.txt` pins runtime dependencies. No credentials belong in
this repository.

## Provenance and reproduction

`arrests_state_locations.csv` was generated from the exact July 24, 2026 CSV with
`python notebooks/09_arrest_locations.py`. Its AOR, landmark, and state marginals
reconcile to the existing published tables. Unknown locations are retained.
The year 2026 contains only January 1-March 10 and is not offered as an annual map.
The alternate July 6 parquet is not claimed to reproduce the published tables.

The [Tableau companion](../bi/README.md) is a real packaged workbook, not just
instructions, but native Tableau rendering and Tableau Public publication still
require an external application/account.
