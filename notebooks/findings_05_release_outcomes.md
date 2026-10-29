# Analysis #5 — "Who Gets Out?" Release & Bond Equity
## ICE Detention Data, extracted 7/24/2026

---

## What We Measured

| Metric | Description |
|---|---|
| Detained share | % of arrests (joined arrests/stays file) with a detention stay vs. released without book-in |
| Funnel stages | Arrested → detained → booked out → removed, by administration |
| Stay length | Days from book-in to book-out for released stays (median, mean, p90), filtered to 0–1,825 days |
| Bond posted rate | % of stays with an initial bond amount that also have a bond-posted amount/date |
| Release reason mix | Share of book-outs by grouped `stay_release_reason`, by month and administration |
| Mean days per arrest | Mean stay length over closed stays plus never-detained arrests counted as 0 days (open stays excluded) |
| Still-detained cohort | Stays with no book-out date: count, time in, criminality, country, facility |

Administration periods: Biden = 2021-01-20 to 2025-01-19; Trump 2nd = 2025-01-20 onward.
Group sizes (n) are printed in the script output; groups with n < 50 are flagged `SMALL N`.

---

## Summary Table

| Metric | Biden | Trump 2nd |
|---|---|---|
| Arrests (joined file, Oct 2022–Mar 2026) | 315,461 | 389,824 |
| % of arrests detained | 61.3% | 90.0% |
| % of arrests ending in a recorded removal | 40.6% | 64.9% |
| % of detained with a book-out date | 99.6% | 85.8% |
| Mean days per arrest, never-detained = 0 | 29.7 | 32.8 |
| Mean days, detained only (closed stays, by arrest date) | 48.5 | 37.1 |
| Median stay, released (days, by book-in period) | 29.1 | 21.2 |
| % of releases that are "Removed" | 55.0% | 83.8% |
| % of releases that are Order of Recognizance / Paroled | 12.7% / 20.7% | 1.9% / 0.5% |

Overall: **705,285 arrests → 544,300 detained (77.2%) → 493,776 booked out (90.7% of detained) → 381,169 removed (77.2% of booked out)**.

---

## Key Findings

### 1. Being arrested no longer means being released: detained share rose from 61% to 90%
**61.3% of Biden-era arrests resulted in a detention stay vs. 90.0% under Trump 2nd.**
The "arrested but never booked in" group fell from 121,987 people to 38,998.
By apprehension criminality, 93.1% of convicted-criminal and 92.6% of pending-charge
arrests were detained, but only **54.1% of "Other Immigration Violators"**.

### 2. Who is detained varies enormously by nationality
Among the 10 largest arrest nationalities, the detained share ranges from **90.0%
(Honduras) and 89.7% (Guatemala) down to 47.2% (Cuba), 45.1% (Peru) and 37.8% (Nicaragua)**.
Mexico is 86.8% on 251,945 arrests. The low-detention nationalities are largely those
with fewer removal options, so this likely reflects the removability of the person
rather than ICE choice alone (descriptive only).

### 3. Stay length differs most by how someone leaves, and by nationality
Released stays (n = 1,025,342) have a **median of 26.7 days (mean 45.9, p90 106.6)**.
Medians by release reason: relief/proceedings ended **109.9 days**, order of supervision
**85.2**, bonded out **39.7**, removed **24.8**, order of recognizance **9.9**.
By nationality (top 10): **Nicaragua 51.7 days, Venezuela 41.7** vs. **Guatemala 20.8, Mexico 8.2**.
Convicted criminals have a *shorter* median (19.0) than other groups (29.1), consistent with
faster removal of people with prior removals/convictions. Bond-posters are held longer
(median 37.8 vs. 25.8 days), as bond follows a hearing.

### 4. Bond: nearly everyone with a bond amount posts it, with little country variation
Only **7.4%** of stays (80,997) have an initial bond amount. Median initial bond is **$5,000**
(IQR $3,000–$10,000; 90th pct $12,500). **95.3%** of those stays show a posted bond; by country
the posted rate ranges narrowly from **91.3% (Venezuela) to 96.4% (El Salvador)** and median bonds
from $3,000 (Peru) to $6,000 (El Salvador). Using a rough hand-entered GDP-per-capita
ordering, rank correlations are weak (GDP vs. posted rate −0.29; vs. median bond −0.60, n = 10).
In this data we do **not** see poorer countries posting less often. But see the selection caveat below.

### 5. Release mix flipped from parole/recognizance to removal
Among stays booked in under Biden, **55.0%** ended in removal, 20.7% in parole and 12.7% in
orders of recognizance. For Trump 2nd book-ins removal is **83.8%**, with parole at 0.5%
and recognizance at 1.9%. Bonded-out shares are similar (5.3% vs. 5.5%). The Trump 2nd
figures are right-censored (see caveats), which inflates the share of quick outcomes like removal.

### 6. 62,034 stays have no book-out date, mostly from 2025–2026
**5.7% of stays** are open (26,023 booked in during 2025, 33,730 in 2026). Measured to the last
book-in in the data (2026-03-11), the **median open stay is 59.5 days** (194 days measured to the
extraction date). By criminality: 43.4% Other Immigration Violator, 29.2% pending charges, 27.5% convicted. Top countries: Mexico 12,315 (19.9%), Guatemala 6,086,
Honduras 5,238, Venezuela 4,979, Cuba 4,493. Largest facilities: Stewart (2,084), Florida
Soft-Sided South (2,054), Moshannon Valley (1,839), Adelanto (1,613).

### 7. Counting never-detained arrests as 0 days: mean falls to 31.3 days, and the administrations flip
Across all 705,285 arrests, the mean is **31.3 days (median 9.8)** versus **41.5 days (median 21.9)** among
detained people only. By arrest date: Biden **29.7 days** (detained-only 48.5) vs. Trump 2nd **32.8 days**
(detained-only 37.1). People are held for shorter stays under Trump 2nd, but far more arrests lead to
detention (90.0% vs. 61.3%), so the average per arrest is slightly *higher*. Medians differ much more
(0.3 vs. 16.8 days) because under Biden over 38% of arrests had no detention at all. Method: closed stays of 0-1,825 days
plus never-detained arrests at 0; 50,524 detained arrests with no book-out (49,810 Trump 2nd) are excluded,
so the Trump 2nd figure is biased downward (those open cases would raise it). Figure: `release_avg_days_per_arrest.png`.
An update on the newer Sept 2026 data (arrests through 2026-08-06) gives a similar picture: 32.9 days overall; Biden 30.4; Trump 2nd 34.4
(detained-only 42.2 / 49.5 / 39.1), with 57,997 open stays excluded.

---

## Caveats

### Sheet 1 vs. sheet 2 of detention stays
Sheet 1 holds exactly **1,000,000 stays** (book-ins 2004-12-05 to 2025-12-23, 2.7% with no book-out);
sheet 2 holds **87,417** (book-ins 2025-12-23 to 2026-03-11, 40.3% with no book-out). The split is
chronological (a row-limit overflow), not by AOR; stay IDs do not overlap, so we combine them.
Sheet 2 is therefore heavily censored.

### Data coverage / right-censoring
- Detention stays end at book-in **2026-03-11**, about 134 days before the 7/24/2026 extraction. "Still
  detained" is therefore a snapshot as of ~March 2026, not July. Measuring to the extraction date makes
  every open stay at least 135 days old, which is an artifact; we report both.
- Stays still open are excluded from stay-length statistics, so Trump 2nd stay lengths (median 21.2
  vs. 29.1 days) are biased downward, and its release mix is biased toward quick outcomes. The
  14.2% of detained Trump 2nd arrests lacking a book-out is the censored share.
- The joined arrests file begins Oct 2022 (705,285 arrests) while the stays files go back to 2004,
  so the funnel covers Biden's final ~2.25 years only. One arrest dated after the stays cutoff was dropped.
- Pre-Biden stays (n ≈ 160 released) show median ~1,100 days: old open-ended records, not real stays.
  We exclude it from conclusions.

### Plausibility filter
Released stays are kept if 0 ≤ stay_days ≤ 1,825 (5 years): 0 negative durations and 41 stays over 1,825 days were dropped.

### Missingness and bond definitions
- Bond fields are sparse (7.4% of stays have an initial bond; codebook notes substantial missingness
  of bond/sentence fields). Bond fields are "lowest/earliest seen" across stints.
- **Selection bias:** the posted rate is computed only among stays that have a bond amount recorded.
  Many people with a bond set who never posted may have no recorded bond amount, so the 95% posted rate
  is likely overstated and cannot be read as the share of all bond-eligible people who post.
- A max initial bond of $246,924,998 is clearly a data-entry error; medians are used for this reason.
- GDP per capita values are hand-entered rough approximations used only to order countries; n = 10.

### Release-reason ambiguity
Free-text reasons are grouped by keyword (e.g., "Bonded Out - IJ" and "- Field Office" → Bonded out;
"U.S. Marshals or other agency" and "Transferred" → Transferred). "Removed" does not distinguish
removal from voluntary departure outcomes beyond the separate "Voluntary" categories.

### Causation
All findings are descriptive. Differences reflect policy, nationality-specific removal feasibility,
case mix, and record-keeping. Nothing here establishes cause.

---

## Figures Produced

| File | Description |
|---|---|
| `release_funnel_detained_share.png` | Detained vs. never-detained % by administration, criminality, top-10 country |
| `release_funnel_stages.png` | Arrested → detained → booked out → removed, Biden vs. Trump 2nd |
| `release_stay_length_distribution.png` | Stay length histogram (linear and log) |
| `release_los_heatmap.png` | Median days by criminality × release reason |
| `release_los_by_country.png` | Median stay by top-10 citizenship |
| `release_bond_distribution.png` | Initial and posted bond amount distributions |
| `release_bond_equity_country.png` | Median bond vs. posted rate by country |
| `release_bond_by_criminality.png` | Bond-posted rate by criminality |
| `release_reason_mix_over_time.png` | Monthly 100% stacked area of release reasons with administration lines |
| `release_avg_days_per_arrest.png` | Mean days: detained only vs. per arrest incl. never-detained |
| `release_still_detained.png` | Open-stay cohort: time in, criminality, country |

---

## Suggested Headlines

- *"Nine in ten ICE arrests now end in detention, up from six in ten under Biden"*
- *"Where you're from shapes whether you're detained: 90% of Hondurans vs. 38% of Nicaraguans"*
- *"Parole and recognizance releases nearly vanish as removals reach 84% of ICE releases"*

---

*Data source: Deportation Data Project ICE core data, extracted 7/24/2026.
Code: `notebooks/analysis_05_release_outcomes.py`*
