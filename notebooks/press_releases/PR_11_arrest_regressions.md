# PRESS RELEASE 11 — State arrest rates show no reliable link to changes in crime, GDP or unemployment

**Old = 2023–2024 · New = 2025.** Unit: state × year (50 states). Regressor: ICE arrests (by apprehension state) per 100,000 residents, per +10. Script: `notebooks/10_arrest_regressions.py` (OLS, year fixed effects, state-clustered SEs, controls for population, density, income, education, Hispanic share, median age, 2024 GOP vote share and the lagged outcome). Outputs: `results/arrest_regressions.csv`, `results/arrest_correlations.csv`, `results/arrest_rate_panel.csv`.

- **Arrest rates tripled in 2025:** the mean state rate was 37.5 (2023), 26.7 (2024) and 73.1 (2025) arrests per 100k.
- **Nothing survives multiple-testing correction.** Of 48 arrest-rate regression coefficients, 7 had p<.05 (about 2–3 expected by chance); none had a Benjamini–Hochberg q<.10. Of 100 correlations, 7 had p<.05 and only 1 had q<.10, and that one was a weak positive link between arrest rate and GDP growth in the old era (r = 0.27) that vanishes with controls (coef 0.06, p = 0.48).
- **Crime — the nominal signals point in opposite directions:** with controls, old-era arrest rates were associated with *higher* violent-crime change (+1.1 pts per +10, p = 0.03) and with *lower* property-crime change (−1.0, p = 0.05). Neither appears in the 2025 sample (violent +0.3, p = 0.53; property +0.1, p = 0.79) or in FBI-based checks (violent −0.37, p = 0.25; property −0.34, p = 0.24), and neither is robust to correction.
- **Economy:** GDP growth and unemployment change show no association with arrest rates in the controlled models (all p>0.47). Adding the facility-located detention rate leaves the conclusions unchanged.
- **Context:** Crime fell nearly everywhere in 2025 (mean violent −9%, property −13% in the sample), so a flat relationship with arrests is unsurprising.

**Caveats:** Exploratory and descriptive, ≤150 state-years (37–50 in the new era, one year only). Arrest location is not residence. Arrests are heavily concentrated in Texas, Florida and California. Crime data are the Real-Time Crime Index sample, with FBI data as a check. No causal claim is supported.
