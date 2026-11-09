# ICE Enforcement & Detention, 2022–2026: Full Report Across Two Data Vintages

**Data:** Deportation Data Project ICE core data. *Old* = 7/24/2026 CSV extract (repo root). *New* = Sept 2026 parquet release (`data_updated/`, fetched with `notebooks/fetch_latest_data.py`).
**Code:** `analysis_05_release_outcomes.py` (run with and without `updated`) and `analysis_06_vintage_research.py`. All numbers below are from script output. Everything is descriptive; nothing here establishes cause.

Companion documents: `press_release_old_data.md`, `press_release_new_data.md`, `press_release_comparison_new_vs_old.md`, `findings_05_release_outcomes.md`, `findings_05_release_outcomes_updated.md`, `updated_data_and_future_projects.md`.

---

## 1. Highlights: the most interesting findings

1. **Detention became the default.** Share of arrests that led to a detention stay: **61.3% (Biden-era) → 90.0% (Trump 2nd)** in the old data; 61.4% → 89.1% in the new. Both vintages agree.
2. **The detained population roughly doubled and peaked mid-January 2026.** Reconstructed daily population: ~33.5k average (Oct 2022–Jan 2025), 39.8k in Jan 2025, **peak ≈72.0–72.3k on 2026-01-15** in both vintages, 65.6k in July 2026.
3. **Most "still detained" people in the old file are not anymore.** Linking stays across vintages, **75.5% (45,378 of 60,094)** of stays open in July now have a book-out date, after a median **91.2 days**. Among Jan 2025+ detained arrests through 2026-03-11, the share booked out went from **85.8% to 96.8%**. Recorded "release rates" are censoring-sensitive.
4. **Record arrest month is July 2026: 49,091** (old data could only see through Dec 2025's 39,829). Trump 2nd averages 28,624/month (Feb 2025–Feb 2026, old) and **30,932/month** (Feb 2025–Jul 2026, new) vs ~11,500 under Biden.
5. **Arrest method shifted toward at-large and 287(g) arrests.** At-large 41.1% → 48.3%; 287(g) 2.0% → 8.1%; custodial 46.7% → 41.9%; "Other" 10.1% → 1.7%.
6. **The arrested population changed.** Women 20.4% → 11.5%; under 18: 7.8% → 1.6%; median age 32 → 34; Mexico 31.2% → 40.4%, Guatemala 8.2% → 14.1%, Nicaragua 10.0% → 3.0%, Colombia 6.6% → 2.9%, Cuba 5.2% → 2.4%.
7. **Nearly 3 in 10 arrests involve someone who already had a final order** (28.1% vs 23.3% under Biden; 45.6% among convicted-criminal arrests).
8. **Counting never-detained arrests as 0 days flips the administration comparison.** Detained-only mean 49.5 (Biden) vs 39.1 (Trump 2nd), but per-arrest mean 30.4 vs 34.4, because many more arrests lead to detention.
9. **Release mix flipped** from parole/recognizance to removal: Removal 51.6% → 82.1% of book-outs (new data); parole 25.7% → 0.4%.
10. **Data-quality surprises:** (a) identifiers are re-anonymized every release (**0 shared IDs**), so vintages must be linked on a composite key (99.7% of old keys matched); (b) one arrest in the old file is dated 2026-09-17, after the extraction; (c) in the new file the bond "posted rate" is mechanically 100%; (d) the new detainer file drops 17,121 likely duplicates that the old file did not flag.
11. **Geography:** 46.4% of stays are in Texas and Louisiana; Miami AOR's arrest share rose 7.5% → 11.0%, while Houston, Dallas, Newark, and New York fell ~2 points each.

---

## 2. Data & coverage

| Item | Old (7/24/2026) | New (Sept 2026) |
|---|---|---|
| Arrests (excl. duplicate_drop_row) | 705,285 (after dropping 1 post-extraction record) | 886,369 |
| Arrest date range | 2022-10-01 – 2026-03-11 | 2022-10-01 – 2026-08-06 |
| Detention stays | 1,087,417 (two 1M-row sheets) | 1,264,756 (single file) |
| Stay book-in range ends | 2026-03-11 | 2026-08-06 |
| Stays with no book-out | 62,034 (5.7%) | 66,102 (5.2%) |
| Detainers | 609,769 | 723,480 after 17,121 duplicates dropped (740,601 raw) |

The old stays files stop about 134 days before their stated extraction date. The new release has no documented extraction date; we treat 2026-08-06 as its data end.

---

## 3. Funnel: arrest → detention → release (Analysis 5)

| Metric | Old Biden | Old Trump 2nd | New Biden | New Trump 2nd |
|---|---|---|---|---|
| Arrests | 315,461 | 389,824 | 314,830 | 571,539 |
| % detained | 61.3% | 90.0% | 61.4% | 89.1% |
| Never detained | 121,987 | 38,998 | 121,611 | 62,097 |
| % of arrests with recorded removal | 40.6% | 64.9% | 40.8% | 65.1% |
| % of detained with book-out | 99.6% | 85.8% | 99.8% | 88.7% |
| Mean days/arrest (never-detained = 0) | 29.7 | 32.8 | 30.4 | 34.4 |
| Mean days, detained only | 48.5 | 37.1 | 49.5 | 39.1 |

- Overall funnel, old: 705,285 → 544,300 detained (77.2%) → 493,776 booked out → 381,169 removed. New: 886,369 → 702,661 (79.3%) → 644,664 → 500,688.
- **Who is detained.** By criminality (new): 93.4% convicted, 92.9% pending charges, **59.1% other immigration violators** (54.1% old). By nationality (new): Honduras 90.5%, Guatemala 90.3%, Mexico 86.6%, … Cuba 51.9%, Peru 48.8%, Nicaragua 43.0%.
- **Average detention including never-detained arrests:** old 31.3 days (median 9.8) vs 41.5 (median 21.9) detained-only; new 32.9 (median 11.8) vs 42.2 (21.3).

## 4. Length of stay (released stays, 0–1,825 days)

| | Old | New |
|---|---|---|
| Released stays | 1,025,342 | 1,198,613 |
| Median / mean days | 26.7 / 45.9 | 25.8 / 46.3 |
| p90 | 106.6 | 108.8 |
| Median by book-in period: Biden / Trump 2nd | 29.1 / 21.2 | 29.2 / 21.0 |

- **By release reason (median, new):** relief/proceedings ended 110.9; order of supervision 86.1; bonded out 40.0; paroled 32.9; removed 23.3; voluntary departure 15.1; recognizance 9.1; transferred 4.7.
- **By nationality (median, new):** Nicaragua 48.1, Venezuela 41.1, Dominican Republic 36.7 … Guatemala 20.0, Mexico 10.0.
- **Criminality:** convicted criminals' median is 18.8 days vs 28.3 for other immigration violators.
- **Facilities (new, ≥500 released stays; 173 facilities):** longest medians: Dilley single female 85.1 days (n=531), Cibola County 75.0, FCI Berlin 69.9, California City 66.3. Shortest: hold rooms with ~0 days (Boston, Laredo, Austin, Harlingen). Busiest: Montgomery (43,677 stays, median 14.3), South Texas (36,949; 36.5), Port Isabel (35,798; 21.0), Stewart (34,633; 43.1).

## 5. Bond

- 7.3–7.4% of stays have a bond amount; median initial bond **$5,000** (IQR $3,000–$10,000).
- **Old:** 95.3% of stays with a bond amount show a posted bond; country range 91.3% (Venezuela) to 96.4% (El Salvador).
- **New:** every stay with a posted amount also has an initial amount (91,814 of 91,814), so the posted rate is **100% for all groups**. We read this as a recording artifact, inferred from the counts and not confirmed against the codebook. **The "do poorer countries post less?" question cannot be answered**; the old ~95% is also conditional on having a bond amount recorded.
- By criminality, median bond set rises from $5,000 (other immigration violators) to $6,500 (convicted), new data.

## 6. Release reasons

Old (book-in period, % of book-outs): Biden removal 55.0%, paroled 20.7%, recognizance 12.7%; Trump 2nd removal 83.8%, paroled 0.5%, recognizance 1.9%. New: Biden removal 51.6%, paroled 25.7%, recognizance 11.8%; Trump 2nd removal 82.1%, paroled 0.4%, recognizance 1.5%. New release reasons ("Paroled – Fear Found", "Court Ordered" with 12,946 releases) fill a new "Other" bucket (2.4% under Trump 2nd).

## 7. Arrests: method, geography, demographics (Analysis 6, new data)

| | Biden | Trump 2nd |
|---|---|---|
| At-large | 41.1% | 48.3% |
| Custodial | 46.7% | 41.9% |
| 287(g) | 2.0% | 8.1% |
| Other | 10.1% | 1.7% |
| Female | 20.4% | 11.5% |
| Median / mean age | 32 / 32.7 | 34 / 35.3 |
| Under 18 / 60+ | 7.8% / 1.5% | 1.6% / 2.3% |
| Existing final order at arrest | 23.3% | 28.1% |

- **AORs (share of arrests):** Miami 7.5% → 11.0%, Atlanta 4.8% → 7.1%, San Diego 0.9% → 3.1%; New York City 4.6% → 2.2%, Dallas 9.5% → 7.4%, Houston 8.7% → 6.6%, Newark 5.2% → 3.1%.
- **Age:** the new `age_at_apprehension_approximate` is non-missing for 100% of arrests and correlates 1.000 with age computed from birth year, so it adds no information beyond birth year.
- Old raw arrest-method values (top): Non-Custodial Arrest 38.8%, CAP Local Incarceration 22.7%, Custodial Arrest 14.7%, Located 6.1%.

## 8. Detainers (Analysis 6)

| | Old | New |
|---|---|---|
| Per month, Biden window | 11,648 | 11,508 |
| Per month, Trump 2nd (full months) | 18,909 | 21,119 |

Old numbers are not de-duplicated (no drop flag), so old-vs-new volumes are not strictly comparable. New-data composition, Biden → Trump 2nd: convicted-criminal detainers 35.3% → 19.7%, pending charges 61.5% → 67.5%, other immigration violators **3.2% → 12.8%**; "Detainer request" 78.3% → 83.1% of detainers. Facility-state share: California 23.4% → 17.3%, Texas 22.0% → 15.5%, Florida 6.1% → 12.0%, Georgia 3.4% → 5.6%, New York 2.2% → 5.3%.

## 9. Detention population & open stays

- Reconstructed from book-in/out dates (stays >5 years dropped, open stays held to the data end): mean ~33.6k (old) / 33.5k (new) in the Biden window; 39.9k in Jan 2025; 56.5–56.6k in Jun 2025; ~70.2–70.5k in Jan 2026; peak 72.3k (old) / 72.0k (new) on 2026-01-15; new Jul 2026 65.6k. This is a reconstruction from stay records, **not an official census**.
- Open stays: old 62,034 (median 59.5 days since book-in to data end); new 66,102 (median 41.6; 44,799 ≤ 90 days). By criminality (new): 42.2% other immigration violators, 30.4% pending, 27.4% convicted. Top countries: Mexico 17,020 (25.8%), Guatemala 7,077, Honduras 5,833, Venezuela 5,825, Cuba 4,359. Top facilities: Stewart 2,307, Adams County 1,987, Moshannon Valley 1,860, Diamondback 1,835, Adelanto 1,812.
- Geography of stays (new): TX 34.8%, LA 11.6%, AZ 9.3%, CA 7.4%, GA 5.6%, FL 5.4%.

## 10. Old vs new: what changed

- **Back-history barely moved.** Overlap Oct 2022–Feb 2026: 693,364 (new) vs 694,999 (old) arrests, −0.2%; largest monthly revision −171 (Jan 2026, −0.5%). Biden-window arrests/month 11,532 vs 11,509; mean population 33,598 vs 33,540.
- **Censoring corrections were large:** 75.5% of open stays closed (median 91.2 days; 2,695 already-closed stays had their book-out date changed; 14,716 remain open in both). The 3,345 old-only stays are not in the new file.
- **Not-yet-complete recent months:** arrests from 2026-03-12 to 2026-08-06 (181,461) are 87.1% detained and only 70.8% of those are booked out, so *those* numbers will also drift upward as stays close.
- **Median open-stay age fell** (59.5 → 41.6 days) because the new file includes 5 more months of recent book-ins.

---

## 11. Caveats

- **Right-censoring:** each vintage biases recent stay lengths downward and book-out rates downward; the cross-vintage comparison quantifies this for the old file. Expect the new file to show the same pattern for 2026 book-ins.
- **Linking stays across vintages** uses book-in minute + birth year + citizenship + gender, keeping only keys unique in both files (1,024,322 matches), so some stays are untested and ambiguous matches are excluded.
- **Bond fields:** ~7% populated; the new posted rate is a recording artifact; "lowest/earliest seen" values across stints.
- **Reconstructed population** is not an official count; hold rooms and short stays are included.
- **Release reasons** are keyword-grouped; new reasons appeared in the new release.
- **Plausibility filter:** released stays kept at 0–1,825 days (41 dropped in each vintage; no negatives). Pre-Biden stays (n ≈ 105–160) are unreliable and excluded from conclusions.
- **Administrations:** Biden = through 2025-01-19, Trump 2nd from 2025-01-20; the joined file only starts Oct 2022. The "Biden window" in this report is Oct 2022–Jan 2025.
- Groups with n < 50 are flagged in script output; none of the headline groups are small.
- All findings are descriptive; changes reflect policy, migration patterns, case mix, and recording practices together.

## 12. Figures (`notebooks/figures/`, `figures_updated/`, `figures_06/`)

| File | Description |
|---|---|
| `figures_06/arrests_monthly_old_vs_new.png` | Monthly arrests, both vintages |
| `figures_06/arrests_method_by_admin.png` | Arrest method by administration |
| `figures_06/detainers_monthly_old_vs_new.png` | Monthly detainers, both vintages |
| `figures_06/detention_population_old_vs_new.png` | Reconstructed daily detention population |
| `figures/release_*.png`, `figures_updated/release_*.png` | Analysis 5 figures for each vintage |

## 13. Suggested next steps

Survival analysis of time to removal; a deeper look at 287(g) growth by state; confirming the bond-field definition with the Deportation Data Project; rerunning on the next release to measure how much recent stays are revised (the censoring pattern found here predicts higher book-out rates for 2026).
