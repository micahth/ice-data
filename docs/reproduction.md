# Methods and reproduction

## Setup

Requires Python 3.11 or 3.12. Direct dependencies are pinned, but transitive
dependencies are not locked.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python analysis/06_figures.py
```

Tests and figures use synthetic fixtures and committed result tables; neither
requires raw LFS data. See the [technical guide](../analysis/MASTER_RESULTS.md)
for sources, model specifications, tables, and limitations.

## Reproduce published results

The published analysis uses the four `2026-07-24` CSVs listed with hashes,
sizes and an immutable source revision in the
[input manifest](../analysis/published_inputs.json). The download is 2.56 GB.
Use at least 8 GB RAM and 8 GB free disk; secondary inputs also require network
access.

```bash
python analysis/download_data.py
unset ICE_DATA_DIR
python analysis/reproduce.py --work-dir /tmp/ice-reproduction
```

The workspace must not already exist. The runner verifies checksums, uses a
fresh secondary-input cache, runs scripts 01–05 and the arrest forecast, and
compares all 30 published result tables to Git HEAD. It ignores row order and
uses absolute numeric tolerance 1e-6. Logs and regenerated tables stay in the
workspace; tracked results are not overwritten.

Alternatively, hydrate and verify the same LFS objects:

```bash
git lfs install
git lfs pull --include="data/arrests_2026-07-24.csv,data/detention_stints*.csv" --exclude=""
python analysis/download_data.py --verify-only
```

For manual regeneration, which overwrites working-tree outputs:

```bash
unset ICE_DATA_DIR
python analysis/01_geo_detention_analysis.py
python analysis/02_geo_regressions.py
python analysis/03_facility_changes.py
python analysis/04_arrest_locations.py
python analysis/05_arrest_regressions.py
python analysis/06_figures.py
```

Arrests are observed through March 10, 2026; detention is observed through
March 11. March 11 has one arrest and is excluded as a partial day; a stray
September 2026 arrest is also excluded.

The alternative `python analysis/download_data.py --source alternative` fetches
a pinned July 6 parquet revision, not the published CSVs. Set
`ICE_DATA_DIR="$PWD/data/raw"` to use it; it cannot reproduce published numbers.
The DuckDB alternative is
`python analysis/04_arrest_locations.py --engine duckdb --output-dir /tmp/ice-sql-results`.
Forecasts are run with `python analysis/forecast_arrests.py` and
`python analysis/forecast_adp.py`; their backtests and limitations are in the
[technical guide](../analysis/MASTER_RESULTS.md#portfolio-examples).

## Dashboard

```bash
streamlit run analysis/dashboard.py --browser.gatherUsageStats=false
```

The dashboard uses committed aggregate tables, not individual records. It can
be deployed on Streamlit Community Cloud using this repository, the desired
published branch, and `analysis/dashboard.py` as the entry point. No hosted
deployment has been verified.

## Detention survival analysis

See [survival analysis](survival.md) for the cohort, censoring rule, model,
diagnostics, and command. This is separate from the published results.

## Design rationale

The single-year state regressions use HC3 because heteroskedasticity and
high-leverage states can distort ordinary OLS standard errors in a small sample.
Repeated-state specifications cluster by state to allow within-state correlation;
neither method removes confounding. The primary ADP rule censors unknown ends
only for stints booked in from 2025 onward, because older open records may be
incomplete; `censor_all` and `exclude_all` are reported as sensitivity bounds,
not proof that either assumption is correct. The survival cohort and censoring
rule differ; see its documentation.

## AI use

Copilot assisted with code, tests, and documentation. While AI did make 
recommendations that were considered, the final responsibility for any decisions 
or errors belongs to Micah Holmquist.


The project’s original code is licensed under the [MIT License](../LICENSE).
This does not grant rights to source data. The [Deportation Data Project’s ICE
documentation](https://deportationdata.org/docs/ice.html) does not specify reuse
or redistribution terms for these files, so those terms are unclear; check with
the source before redistributing the data.
