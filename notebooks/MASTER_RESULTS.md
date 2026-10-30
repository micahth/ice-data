# MASTER RESULTS — Geography, operator, per-capita and outcome analysis of ICE detention

Data: `detention-stints` (ICE book-in/out records, Oct 2022 → **2026-03-11**, the actual cutoff).
**Old = CY2023–2024; New = 2025-01-01 → 2026-03-11.** (My assumption; change `PERIODS` in `notebooks/geo_common.py` to redefine.)

## Contents

| # | Result | Press release |
|---|---|---|
| 1 | Region | [PR_01](press_releases/PR_01_region.md) |
| 2 | State | [PR_02](press_releases/PR_02_state.md) |
| 3 | Metropolitan / micropolitan / rural | [PR_03](press_releases/PR_03_metro_micro.md) |
| 4 | Operator (ICE / CoreCivic / GEO / other) | [PR_04](press_releases/PR_04_operator.md) |
| 5 | National per-capita rate | [PR_05](press_releases/PR_05_per_capita.md) |
| 6 | Correlations with GDP, unemployment, crime | [PR_06](press_releases/PR_06_correlations.md) |
| 7 | Multivariable regressions | [PR_07](press_releases/PR_07_regression.md) |
| 8 | Interesting findings | [PR_08](press_releases/PR_08_interesting_findings.md) |
| 9 | Ownership/operating changes since 2025-01-20 | [PR_09](press_releases/PR_09_facility_changes.md), full list [FACILITY_CHANGES.md](FACILITY_CHANGES.md) |

## Headline numbers

| | Old | New |
|---|---:|---:|
| National ADP | 33.6k | 55.1k |
| ADP per 100k | ≈9.9 | ≈16.1 |
| South / West / Northeast / Midwest per 100k | 17.3 / 9.5 / 4.1 / 1.2 | 25.9 / 15.1 / 8.0 / 5.1 |
| Metro / micro / rural per 100k | 6.2 / 20.0 / 54.9 | 10.9 / 30.6 / 78.4 |
| GEO / CoreCivic / other private / local-state / ICE / federal ADP | 12.3k / 9.1k / 6.6k / 2.2k / 3.4k / 22 | 18.4k / 12.2k / 9.4k / 7.8k / 6.3k / 971 |
| Median stay (days) | 6.9 | 1.8 (censored) |

## Key findings

1. Per-capita detention rose in every region, state-group and area type. The Midwest grew fastest (+318%), the South remains highest.
2. Rural and micropolitan facilities carry 3–7× the per-resident rate of metros.
3. GEO and CoreCivic hold 56% of ADP; local/state sites grew fastest (3.5×).
4. Detention is not robustly associated with unemployment or property crime. GDP and violent-crime associations are unstable and change sign between eras.
5. 111 facility codes were first used after 1/20/2025; 13 stopped booking.

## Methods

- **ADP:** overlapped bed-days ÷ window days from stints (duplicates dropped). Open stints are censored at the cutoff if booked since 2025 or at `stay_book_out` when present; 1,049 older open stints are excluded.
- **Geography:** facility county FIPS (`deportationdata/ice-detention-facilities`) → Census region and OMB July 2023 CBSA delineation. No CBSA match = rural; no county = unmapped (negligible ADP).
- **Population:** county estimates 2020–2025; 2026 uses 2025.
- **Operator:** name/code rules in `geo_common.py` (ICE publishes none).
- **Outcomes** (state-year, 2023–25): BEA real GDP; BLS LAUS unemployment; Real-Time Crime Index (2025; violent and property, 45 states + DC); FBI state crime (2023–24 check); ACS and 2024 election controls.
- **Models:** correlations (Pearson, Spearman) and OLS with year fixed effects and state-clustered SEs (M1 bivariate, M2 controls, M3 operator, M4 area type, M5 first-difference, M6 era interaction).

## Limitations

- Operator labels are approximations; ownership changes in FACILITY_CHANGES.md Tier B are unverified (web search was unavailable).
- Outcomes exist only at state level, so metro/micro analysis maps detention in those facilities onto state residents.
- Crime for 2025 uses a sample-based index, not FBI data; 2026 crime unavailable.
- About 50 states per year; correlational only; many comparisons tested.
- The 2026 window is partial; median stay is biased short.
- Facility rate reflects detainees from elsewhere, not local residents.

## Reproduce

```
pip install -r notebooks/requirements.txt
python notebooks/05_geo_detention_analysis.py   # division tables
python notebooks/06_geo_regressions.py          # correlations, regressions
python notebooks/07_facility_changes.py         # facility change list
```
External data are downloaded to `notebooks/.cache` (override with `GEO_CACHE`). Outputs are in `notebooks/results/`.
