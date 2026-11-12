# Exploratory detention-stay survival analysis

`analysis/survival.py` estimates time from admission to recorded stay book-out,
not facility-stint length. The Deportation Data Project constructs stays across
facility transfers; a book-out is not necessarily a release into the community.
This analysis is separate from the published results and has not been run on
the raw data in this revision.

The incident cohort includes deduplicated stays beginning January 1, 2025
through March 11, 2026. Recorded book-outs before March 12 are events; missing
or later book-outs are administratively censored at the start of March 12.
Invalid starts, invalid or pre-admission ends, and missing person identifiers
are excluded and counted. Missing book-outs are assumed to remain under
observation until cutoff, not proved to be ongoing detentions; older starts are
excluded because of uncertainty in open records. This is a different estimand
and rule from the stint-level ADP analysis.

Kaplan–Meier estimates the probability of remaining in the recorded stay, with
Greenwood standard errors. The exploratory Cox model uses admission date
(per 30 days since January 1, 2025) as its sole covariate, Efron ties, and
person-clustered robust standard errors for repeat stays. The hazard ratio
describes the association with recorded book-out, not a causal effect. Both
methods require assumptions about informative censoring; the Cox model also
assumes proportional hazards. Admission date is tied to follow-up time, so
changes in data completeness and short follow-up can bias comparisons.
Check proportional hazards and censoring sensitivity before interpreting
coefficients; no such diagnostic or empirical claim is asserted here. KM
standard errors do not adjust for repeated people.

Hydrate the two July 24 stay files with Git LFS (they are not part of the four
checksum-verified published-pipeline inputs), or use the alternative parquet
source via `ICE_DATA_DIR`. The sources are different vintages and are not
interchangeable. Then run:

```bash
git lfs pull --include="data/detention_stays_2026-07-24_part*.csv" --exclude=""
unset ICE_DATA_DIR
python analysis/survival.py --output-dir /tmp/ice-survival
```

The output contains exclusion counts, the event-time KM curve and Cox estimates.
The existing published reproduction runner does not run or compare this analysis.
