# ICE enforcement expanded; state-level outcome estimates remain uncertain

Micah Holmquist | Deportation Data Project CSV exports dated July 24, 2026

## Question and motivation

How did ICE arrest and detention activity change, and did states with higher arrest rates also experience different economic or crime trends?

The labor-market effects of enforcement are an empirical question, not a one-direction prediction. East et al. find that Secure Communities reduced employment among likely undocumented immigrants and U.S.-born workers, illustrating how labor-market responses can differ from a simple competition story ([Journal of Labor Economics, 2023](https://doi.org/10.1086/721152)). This project asks a narrower descriptive question: whether **state arrest intensity is associated with annual state outcome changes**. Arrests do not identify workers removed from employment.

## Main findings

| Measure | 2023–2024 | Jan 2025–Mar 10, 2026 |
|---|---:|---:|
| Included arrest records | 262,329 | 394,590 |
| Window length | 731 days | 434 days |
| Arrests per day | 358.9 | 909.2 |
| Convicted-criminal share of arrest records | 43.0% | 33.1% |
| Pending-charge share of arrest records | 17.4% | 29.0% |

Daily arrest pace increased **153%**; monthly arrests peaked at **39,829 in December 2025**. Texas accounted for 25.7% of newer-period arrests. Differences describe recorded apprehension locations, not arrestees' residences. Criminality categories describe arrest records, not unique detainees or proven effects on crime.

National detention average daily population (ADP) increased from **33.6k to 55.1k**, using a detention window ending March **11**, 2026 (435 newer-period days). Facility ADP per resident rose in every region; rural facilities held about 78.4 detainees per 100,000 local residents versus 10.9 in metropolitan counties. These measure where facilities hold people, **not local residents' likelihood of detention**. Operator classifications are inferred, not verified ownership records.

## Where apprehensions occurred

![Share of arrest records by state and ICE Area of Responsibility](notebooks/figures/fig7_arrest_geography.png)

Recorded apprehensions are concentrated but became somewhat less concentrated in Texas. By state, Texas's share fell from 27.3% to 25.7% while Florida rose from 7.4% to 10.1% and Georgia from 2.2% to 3.7%; the ten largest states account for 65.8% of newer-period records. By ICE Area of Responsibility, Miami (10.2%), New Orleans (7.9%) and Dallas (7.6%) lead, with Atlanta and Washington gaining the most share. Landmark-level records are far more dispersed (6,393 distinct labels; top ten = 22.3%), and many are generic "general area" entries, so they reflect reporting convention as much as place. Full tables: `arrests_by_state.csv`, `arrests_by_aor.csv` and `arrests_by_landmark.csv` in `notebooks/results/`.

This uses apprehension location rather than detention-facility location, which reflects bed capacity and transfers. Neither measures where people live or work.

## State-level associations and uncertainty

The panel covers 50 states in 2023–2025; complete-case sample sizes vary by outcome and controls. The primary descriptive specification uses the arrest rate and a lagged outcome, with year effects when multiple years are included. The full-control specification is a sensitivity check, not a preferred high-dimensional model for a small cross-section.

2025 estimates below use HC3 heteroskedasticity-robust standard errors and t-based, **pointwise 95% confidence intervals**. Coefficients are outcome change per additional 10 arrests per 100,000 residents:

| Outcome | Lagged outcome only: estimate [95% CI], n | Full controls: estimate [95% CI], n |
|---|---|---|
| Real GDP growth (percentage points) | 0.021 [−0.019, 0.061], 50 | −0.016 [−0.137, 0.106], 42 |
| Unemployment change (percentage points) | 0.000 [−0.018, 0.018], 50 | 0.011 [−0.047, 0.070], 42 |
| Violent crime rate change (%) | −0.444 [−1.051, 0.164], 45 | 0.218 [−1.091, 1.526], 38 |
| Property crime rate change (%) | −0.151 [−0.573, 0.270], 44 | 0.109 [−0.949, 1.168], 37 |

Across 64 arrest-related coefficients, **none passes Benjamini–Hochberg q < .10**. Removing Texas, the highest arrest-rate state in 2025, does not resolve uncertainty in the reduced-control models. The [coefficient chart](notebooks/figures/fig6_arrest_coefficients.png) shows both specifications and that sensitivity check. These intervals allow positive and negative associations; they are not equivalence tests or multiplicity-adjusted intervals.

For scale, the interquartile range of 2025 state arrest rates is about **54 per 100,000**, or 5.4 units of the model's +10-per-100,000 scale. Across that range, the lagged-outcome intervals translate to about **−0.10 to +0.10 percentage points** for unemployment change, **−0.10 to +0.33 points** for GDP growth, and **−5.7% to +0.9%** for violent-crime change. Under this specification, the confidence intervals are comparatively narrow for unemployment change, providing evidence against very large state-level associations. They do not establish that the true association is zero, and the intervals are pointwise rather than multiplicity-adjusted. The violent-crime interval still allows a meaningful reduction.

## Methods and limitations

Arrest counts are deduplicated records, not unique people or completed removals; apprehension location need not be residence or workplace. The January 1, 2025 split is a calendar-year comparison, not an intervention-date design. March 2026 is partial, and regression models omit partial-year 2026.

Detention ADP is overlapping bed-days divided by actual window days. Facility-stint comparisons use recorded book-outs where available and censor qualifying open stints at March 12, 2026; 1,049 older open records are excluded. No release-rate comparison is reported because censoring makes it unreliable.

The primary models are parsimonious; full-control models are a sensitivity check. Single-year models use HC3 intervals, and repeated-state models use state-clustered inference. Intervals are pointwise, not multiplicity-adjusted. Small samples, confounding, model dependence, incomplete crime coverage, and unobserved employment limit interpretation; the [technical guide](notebooks/MASTER_RESULTS.md) documents specifications and data handling.

**Conclusion:** the enforcement increase is well supported descriptively. This dataset does not establish a reliable state-level economic or crime association, and cannot confirm or refute the causal economic effects of deportation.
