# PRESS RELEASE — What Changed Between the July and September 2026 ICE Data Releases

**FOR IMMEDIATE RELEASE**

## New ICE data confirm the old picture, add five months of surging arrests, and show most "still detained" people in the July file have since been released

*Comparison of the Deportation Data Project's 7/24/2026 extract and its September 2026 release*

**Headline comparisons**

| Measure | July extract (old) | Sept release (new) |
|---|---|---|
| Last arrest / book-in date | 2026-03-11 (stays) | 2026-08-06 |
| Arrests in file (after duplicate drops) | 705,285 | 886,369 |
| Arrests per month, Biden-era window | 11,532 | 11,509 |
| Arrests per month, Trump 2nd (full months) | 28,624 (Feb 2025–Feb 2026, 13 months) | 30,932 (18 months) |
| Record month | Dec 2025: 39,829 | Jul 2026: 49,091 |
| % of arrests detained (Biden / Trump 2nd) | 61.3% / 90.0% | 61.4% / 89.1% |
| Per-arrest mean detention days (never-detained = 0) | 31.3 | 32.9 |
| Released-stay median (days) | 26.7 | 25.8 |
| Stays with no book-out | 62,034 (5.7%) | 66,102 (5.2%) |
| Median days open stays have been in custody | 59.5 | 41.6 |
| Peak reconstructed detention population | 72,292 (Jan 15, 2026) | 72,012 (Jan 15, 2026) |
| Mean daily population, Biden-era window | 33,598 | 33,540 |

**Findings**

- **History is stable.** For Oct 2022 – Feb 2026, the new file contains 693,364 arrests versus 694,999 in the old one (−0.2%). The Biden-era detained share is 61.3% vs 61.4%, and its mean population is within 0.2%.
- **Most open stays closed.** Of 60,094 stays open in the July file that we could link to the new file, **45,378 (75.5%) now have a book-out date**; they lasted a median of **91.2 days** (mean 126.8). This shows how much right-censoring biased the July file: among Jan 2025+ detained arrests through Mar 11, 2026, the share with a book-out rose from **85.8% to 96.8%**.
- **Recent arrests: new months are slightly less detained.** Arrests made between Mar 12 and Aug 6, 2026 (181,461) show 87.1% detained so far, with only 70.8% of those yet booked out.
- **Data changes.** The new release adds age, arrest-method, and final-order-before-arrest variables, and detainer duplicates are now flagged (17,121 dropped). Identifiers were re-anonymized, so **no unique_identifier values are shared between the two files**. Bond posted rates became uninformative (100%).
- **The detained-share story is robust.** Detention rose from about 61% to about 90% in both vintages.

*Report: `notebooks/big_report_old_vs_new.md`; code: `notebooks/analysis_06_vintage_research.py`.*
