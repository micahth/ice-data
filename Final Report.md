# ICE enforcement expanded; state-level outcome estimates remain uncertain

Micah Holmquist | Deportation Data Project CSV exports dated July 24, 2026

## Question and hypothesis

How did ICE enforcement change, and did states with more enforcement also experience better economic or crime trends?

Trump and administration officials have argued that unauthorized immigration depresses wages and burdens public resources; Secretary Kristi Noem explicitly linked departures to better job opportunities. The [primary-source appendix](notebooks/POLICY_SOURCES.md) documents these claims without endorsing them. A labor-competition hypothesis predicts better employment or wage outcomes following actual workforce removals, conditional on substitution and adjustment. This project tests only whether **arrest intensity is associated with annual state outcome changes**. It does not observe workers removed from employment; GDP growth is an indirect, exploratory outcome, not a necessary implication of wage or fiscal claims.

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

## Methods and limitations

Duplicate-drop flags are applied before counting. Arrest comparisons start January 1, 2023 and exclude a stray September 2026 record and the one-record March 11 partial day. January 1, 2025 is a calendar-year descriptive split, **not** the January 20 inauguration or a causal intervention date. Daily rates account for unequal windows; March 2026 remains a partial month. Regression models exclude partial-year 2026.

Detention ADP is overlapping bed-days divided by actual window days. Facility stints use half-open intervals; missing book-outs fall back to a recorded stay book-out. Otherwise, stints starting in 2025 or later are censored at March 12, 2026; 1,049 older open records are excluded. That date rule is an assumption about uncertain records, not evidence that older open records are artifacts. Completed-stint durations exclude ongoing stints and are neither full-stay durations nor comparable release hazards.

Repeated-state models use state-clustered t-based inference; 2025-only models use HC3, not nominal clustering with one observation per state. Nine demographic/economic/political controls plus a lagged outcome reduce samples to 37–42 in the full-control 2025 models. Some controls are contemporaneous or measured after the earlier outcomes, so they cannot establish causal adjustment. Small samples, influential states and model dependence limit what null results establish.

Enforcement may respond to local conditions; labor supply and demand may both change; apprehension state may differ from workplace or residence. Arrests are not completed removals, and employment status is unobserved. Annual averages can obscure delayed or sector-specific effects. Crime indices have incomplete state/agency coverage; state aggregates cannot establish individual effects.

**Conclusion:** the enforcement increase is well supported descriptively. This dataset does not establish a reliable state-level economic or crime association, and cannot confirm or refute the causal economic effects of deportation. [Methods, data provenance and reproducible outputs](notebooks/MASTER_RESULTS.md) provide the supporting detail.
