# ICE Enforcement Data Analysis

By Micah Holmquist

**[Start here: Final Report](Final%20Report.md)**

## Abstract

This project cleans person-level ICE administrative records and links enforcement measures to state economic and crime data. Between 2023–2024 and January 2025–March 10, 2026, daily arrests increased from **359 to 909 (+153%)**, while the share of arrest records classified as convicted criminal fell from **43.0% to 33.1%**. The 2023–2025 state panel does not establish a reliable enforcement–outcome association after multiple-testing adjustment. Confidence intervals, reduced-control models and outlier checks show the uncertainty rather than treating a nonsignificant result as proof of no effect. Arrests are not deportations, employment records or residence locations.

![Deduplicated monthly ICE arrests, with partial March 2026 marked separately](notebooks/figures/monthly_arrests.png)

The economic question is motivated by documented administration claims that unauthorized immigration harms workers and public resources, and that departures improve job opportunities. These claims motivate an exploratory association test, not an assumption that deportation must increase GDP. See the [policy sources and hypothesis](notebooks/POLICY_SOURCES.md).

## Read and inspect

The **Final Report is the sole findings narrative**. The [technical guide](notebooks/MASTER_RESULTS.md) documents cohorts, model choices, sources and output tables; the [source codebook](codebook.txt) is third-party Deportation Data Project documentation. [Facility activity definitions](notebooks/FACILITY_CHANGES.md) explain what new or inactive facility codes do and do not establish.

The strongest reusable component is [`ice_lib.py`](notebooks/ice_lib.py): tested half-open interval overlap, censoring, ADP and annualization, used by both detention analyses.

## Setup and lightweight reproduction

Python 3.11 or 3.12; direct dependencies are version-pinned (not a transitive environment lock).

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r notebooks/requirements.txt
python -m pytest -q
python notebooks/08_figures.py
```

Tests and figure generation use small ordinary-Git result tables and synthetic fixtures, **not raw LFS downloads or live data services**. CI runs these tests on pushes and pull requests. No notebook server is required: `notebooks/` contains Python scripts; historical numbers 05–10 are analysis identifiers, not missing prerequisites.

## Full analysis

For the exact July 24, 2026 CSV exports used in the report, hydrate only the needed inputs:

```bash
git lfs install
git lfs pull --include="arrests-latest 7-24-2026.csv,detention-stints*.csv" --exclude=""
python notebooks/05_geo_detention_analysis.py
python notebooks/06_geo_regressions.py
python notebooks/07_facility_changes.py
python notebooks/09_arrest_locations.py
python notebooks/10_arrest_regressions.py
python notebooks/08_figures.py
```

An alternative avoids this repository's LFS bandwidth by downloading checksum-verified parquet files **directly from the Deportation Data Project's public repository**:

```bash
python notebooks/download_data.py
export ICE_DATA_DIR="$PWD/data/raw"
```

Then run the same analysis sequence. This is a pinned upstream July 6, 2026 revision, **not a byte-identical copy of the July 24 CSV exports**; equivalence must be checked before reusing the report's numbers. Downloads are ignored by Git. `--datasets arrests detention-stints detention-stays` includes stays for the optional `eda.py` script. Raw CSV mode EDA requires both stays sheets as well as arrests.

Secondary inputs are fetched at immutable revisions and cached in `notebooks/.cache/`. Changing raw inputs requires deleting the specific cached `stints_clean.pkl` (CSV mode) or `stints_downloaded.pkl` (parquet mode) before rerunning. `GEO_CACHE` can select a fresh cache. See the technical guide for provenance and limitations.

## Outputs and scope

| Path | Purpose |
|---|---|
| `05_geo_detention_analysis.py` | Facility geography/operator tables and ADP |
| `06_geo_regressions.py` | State panel, detention correlations and models |
| `07_facility_changes.py` | Recorded facility activity changes |
| `09_arrest_locations.py` | Arrest cohorts, location, criminality and monthly counts |
| `10_arrest_regressions.py` | Arrest-rate models, intervals and sensitivity checks |
| `08_figures.py` | Report charts from committed tables |
| `notebooks/results/`, `notebooks/figures/` | Derived CSV tables and PNG charts |
| `tests/` | Interval, cohort, inference, download, script and reconciliation checks |

The project demonstrates administrative-data cleaning, joining, geographic normalization and cautious statistical communication. It does **not** identify the causal effect of deportation or validate inferred facility ownership.

## Citation

Holmquist, M. (2026). *ICE enforcement data analysis* [Data analysis project; software]. https://github.com/micahth/ice-data

Source: Deportation Data Project, *ICE administrative data*, exports dated July 24, 2026. https://deportationdata.org/data/ice.html
