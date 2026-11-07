# ICE Enforcement Data Analysis

By Micah Holmquist

Reproducible analysis of U.S. Immigration and Customs Enforcement (ICE) arrest, detainer and detention records, linked to state-level crime, economic and demographic data.

**Start here:** [Final Report](Final%20Report.md) · [Master results](notebooks/MASTER_RESULTS.md) · [Codebook](codebook.txt)

## Abstract

This project examines how ICE enforcement changed between 2023–2024 and 2025 to March 2026, using person-level arrest, detainer and detention records released by the Deportation Data Project (snapshot dated 2026-07-24). Daily arrests rose from about 359 to 909 (+153%), with large differences by state and Area of Responsibility, while the share of arrestees with a criminal conviction fell from 43.0% to 33.1% and pending-charge cases rose from 17.4% to 29.0%. State-by-year regressions (2023–2025, 50 states) with demographic, political and lagged-outcome controls, year fixed effects, state-clustered standard errors and Benjamini–Hochberg correction found no robust association between arrest rates and changes in violent or property crime, GDP growth or unemployment. Findings are descriptive, not causal; the new window is shorter than the old one and the final month is partial.

## Inventory

| Path | Contents |
|---|---|
| `Final Report.md` | Executive findings and detailed results |
| `codebook.txt` | Data documentation (Deportation Data Project) |
| `*.csv` (root) | Arrests, detainers, detention stays/stints, joined arrests–stays (dated 2026-07-24) |
| `notebooks/eda.py` | Exploratory data analysis |
| `notebooks/05_geo_detention_analysis.py` | Detention rates by region, area type and operator |
| `notebooks/06_geo_regressions.py` | Detention-rate regressions |
| `notebooks/07_facility_changes.py` | Facility changes over time |
| `notebooks/08_figures.py` | Publication figures |
| `notebooks/09_arrest_locations.py` | Arrests by state, AOR and landmark |
| `notebooks/10_arrest_regressions.py` | Arrest-rate panel regressions |
| `notebooks/geo_common.py`, `ice_lib.py` | Shared helpers |
| `notebooks/results/` | Output tables (CSV) |
| `notebooks/figures/` | Charts (PNG) |
| `notebooks/data/` | Census population estimates by age and sex |
| `notebooks/*.md` | Supporting findings write-ups |
| `tests/` | Unit tests |
| `.github/workflows/run-eda.yml` | GitHub Actions workflow |

## Suggested citation (APA 7)

Holmquist, M. (2026). *ICE enforcement data analysis* [Data analysis project; Computer software]. GitHub. https://github.com/micahth/ice-data

Source data: Deportation Data Project. (2026). *ICE arrests, detainers and detention data* [Data set; snapshot dated July 24, 2026]. https://deportationdata.org

## Skills demonstrated

- Data cleaning, deduplication and joining of large administrative datasets
- Exploratory and descriptive analysis; period-over-period comparisons
- Panel regression with fixed effects and clustered standard errors
- Multiple-testing correction (Benjamini–Hochberg) and robustness checks
- Per-capita normalization using Census data; geographic aggregation (state, region, CBSA, AOR)
- Data visualization and written communication of limitations and causal caveats
- Reproducible workflows: scripted notebooks, pinned requirements, unit tests, CI
- Git/GitHub collaboration through pull requests

## Languages and tools

- **Language:** Python
- **Libraries:** pandas, NumPy, SciPy, statsmodels, matplotlib, seaborn, PyArrow, openpyxl, xlrd
- **Environment:** Jupyter / nbconvert
- **Platform:** Git, GitHub, GitHub Actions
- **Formats:** CSV, Markdown

Install dependencies with `pip install -r notebooks/requirements.txt`.
