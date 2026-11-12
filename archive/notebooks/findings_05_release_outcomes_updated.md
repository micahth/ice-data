# Analysis #5 (updated data) — "Who Gets Out?" Release & Bond Equity
## ICE detention data, Sept 2026 release (arrests/stays through 2026-08-06)

Same analysis as `findings_05_release_outcomes.md` (7/24/2026 extract), rerun on the newer Deportation Data Project
parquet files in `data_updated/` (downloaded with `notebooks/fetch_latest_data.py`).
Code: `python notebooks/analysis_05_release_outcomes.py updated`. Figures: `notebooks/figures_updated/`.

---

## What We Measured

| Metric | Description |
|---|---|
| Detained share | % of arrests (joined file) with a detention stay vs. released without book-in |
| Funnel stages | Arrested → detained → booked out → removed, by administration |
| Stay length | Days book-in to book-out for released stays, filtered to 0–1,825 days |
| Mean days per arrest | Mean over closed stays plus never-detained arrests counted as 0 days (open stays excluded) |
| Bond posted rate | % of stays with an initial bond amount that also have a posted amount |
| Release reason mix | Share of book-outs by grouped `stay_release_reason` |
| Still-detained cohort | Stays with no book-out: count, time in, criminality, country, facility |

Administration periods: Biden = 2021-01-20 to 2025-01-19; Trump 2nd = 2025-01-20 onward. Groups with n < 50 are flagged in the script output.

---

## Summary Table (old extract in parentheses)

| Metric | Biden | Trump 2nd |
|---|---|---|
| Arrests (joined file, Oct 2022–Aug 2026) | 314,830 (315,461) | 571,539 (389,824) |
| % of arrests detained | 61.4% (61.3%) | 89.1% (90.0%) |
| % of arrests ending in a recorded removal | 40.8% (40.6%) | 65.1% (64.9%) |
| % of detained with a book-out date | 99.8% (99.6%) | 88.7% (85.8%) |
| Mean days per arrest, never-detained = 0 | 30.4 (29.7) | 34.4 (32.8) |
| Mean days, detained only (closed stays) | 49.5 (48.5) | 39.1 (37.1) |
| Median stay, released (by book-in period) | 29.2 (29.1) | 21.0 (21.2) |
| % of releases "Removed" | 51.6% (55.0%) | 82.1% (83.8%) |
| % Order of Recognizance / Paroled | 11.8% / 25.7% (12.7% / 20.7%) | 1.5% / 0.4% (1.9% / 0.5%) |

Overall: **886,369 arrests → 702,661 detained (79.3%) → 644,664 booked out (91.7% of detained) → 500,688 removed (77.7% of booked out)**.

---

## Key Findings

### 1. Detained share rose from 61% to 89% — unchanged by the update
**61.4% of Biden-era arrests led to a detention stay vs. 89.1% under Trump 2nd** (never detained: 121,611 vs. 62,097).
By criminality: 93.4% convicted and 92.9% pending-charge arrests were detained vs. **59.1% of Other Immigration Violators**
(54.1% in the old extract; the added months pull this up).

### 2. Nationality still drives who is detained
Top-10 nationalities: **Honduras 90.5%, Guatemala 90.3%**, Mexico 86.6% (n = 328,809) down to **Cuba 51.9%, Peru 48.8%, Nicaragua 43.0%**.
Descriptive only; likely reflects removability and enforcement context.

### 3. Stay length: same ordering of release reasons and countries
Released stays (n = 1,198,613): **median 25.8 days, mean 46.3, p90 108.8**. By release reason: relief/proceedings ended **110.9**,
order of supervision **86.1**, bonded out **40.0**, removed **23.3**, order of recognizance **9.1**. Top-10 countries:
**Nicaragua 48.1, Venezuela 41.1** vs. **Guatemala 20.0, Mexico 10.0**. Convicted criminals' median is 18.8 vs. 28.3 for
Other Immigration Violators. Stays with a posted bond are longer (median 38.0 vs. 24.7).

### 4. Average detention per arrest including never-detained: 32.9 days
Counting never-detained arrests as 0 days, the mean over all closed outcomes is **32.9 days (median 11.8)**, vs. **42.2 days
(median 21.3)** among detained people only. Biden **30.4** (detained-only 49.5; median 0.3) vs. Trump 2nd **34.4**
(detained-only 39.1; median 16.1). Shorter stays under Trump 2nd are offset by far fewer people released without detention.
57,997 open stays (57,585 Trump 2nd) are excluded, so Trump 2nd is biased downward.

### 5. Release mix: removals dominate Trump 2nd releases
Removal is **51.6%** of Biden book-in releases (paroled 25.7%, recognizance 11.8%) and **82.1%** under Trump 2nd
(paroled 0.4%, recognizance 1.5%). Bonded out: 4.9% vs. 5.4%. A new "Other" bucket (2.4% under Trump 2nd) is mostly the new
"Court Ordered" reason (12,946 releases).

### 6. 66,102 open stays (5.2%), now a true recent snapshot
Stays now run to 2026-08-06, so open stays are current: **median 41.5 days in custody, 44,799 open ≤ 90 days**
(old extract: median 194 days, none ≤ 90). 55,762 booked in during 2026 and 9,123 in 2025. By criminality:
42.2% Other Immigration Violator, 30.4% pending charges, 27.4% convicted. Top countries: Mexico 17,020 (25.8%),
Guatemala 7,077, Honduras 5,833, Venezuela 5,825, Cuba 4,359. Top facilities: Stewart 2,307, Adams County 1,987,
Moshannon Valley 1,860, Diamondback 1,835, Adelanto 1,812.

---

## Caveats

### Bond analysis is not comparable in the new data
In the new files **every stay with a posted bond amount also has an initial bond amount (91,814 of 91,814), so the posted rate is 100%
for every country and criminality group**. This is a field-definition artifact (initial bond appears only for bonds that were
posted), not evidence that everyone posts. The old extract's ~95% rate was likewise computed only among stays with a bond amount.
The "do poorer countries post less often?" question therefore **cannot be answered**; only bond amounts can be described:
7.3% of stays have a bond amount, median **$5,000** (IQR $3,000–$10,000, p90 $15,000), median by country from $3,000 (Peru) to $7,000 (El Salvador).
A maximum of $246,924,998 is a data-entry error. GDP-per-capita values are rough hand-entered figures.

### Data coverage / censoring
- The new stays file is one parquet (1,264,756 stays), not two 1M-row sheets; the old sheet 1/2 split no longer applies.
- "Extract date" is taken as the latest recorded date in the data (2026-08-06) since no extraction date is documented for the new release.
- Open stays are excluded from stay-length statistics (5.2% of stays; 11.3% of detained Trump 2nd arrests), biasing Trump 2nd lengths downward.
- The joined arrests file begins Oct 2022; Biden covers only his final ~2.25 years.
- Pre-Biden stays (n = 105 released) show median ~1,065 days: old open-ended records. Filter: 0 ≤ stay_days ≤ 1,825 (41 dropped, 0 negative).
- Roughly 7% of stays have bond fields; other fields have missingness per the codebook.

### Release-reason ambiguity
Reasons are keyword-grouped. The new release adds reasons such as "Paroled - Fear Found" and "Court Ordered".

### Causation
All findings are descriptive; nothing here establishes cause.

---

## Figures Produced (`notebooks/figures_updated/`)

| File | Description |
|---|---|
| `release_funnel_detained_share.png` | Detained vs. never-detained by administration, criminality, country |
| `release_funnel_stages.png` | Arrested → detained → booked out → removed |
| `release_avg_days_per_arrest.png` | Mean days: detained only vs. per arrest incl. never-detained |
| `release_stay_length_distribution.png` | Stay length histogram |
| `release_los_heatmap.png` | Median days by criminality × release reason |
| `release_los_by_country.png` | Median stay by top-10 country |
| `release_bond_distribution.png` | Bond amount distributions |
| `release_bond_equity_country.png` | Median bond vs. posted rate (posted rate uninformative, see caveats) |
| `release_bond_by_criminality.png` | Bond-posted rate by criminality (uninformative) |
| `release_reason_mix_over_time.png` | Monthly release-reason mix |
| `release_still_detained.png` | Open-stay cohort |

---

## Suggested Headlines

- *"Nearly nine in ten ICE arrests now end in detention, up from six in ten"*
- *"Average ICE arrest means 33 days in detention once those never booked in are counted"*
- *"Over 44,000 people have been in ICE custody under 90 days, as of August 2026"*

---

*Data source: Deportation Data Project ICE core data, Sept 2026 release. Code: `notebooks/analysis_05_release_outcomes.py updated`*
