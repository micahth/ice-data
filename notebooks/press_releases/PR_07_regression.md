# PRESS RELEASE 7 — Multivariable regressions: no robust effect of detention on unemployment or crime

OLS, state-clustered SEs, year fixed effects. Regressor: ADP per 100k **+10**. M2 adds controls: lagged outcome, ln population, ln density, population growth, ln income, % bachelor's, % Hispanic, median age, 2024 GOP vote share. M5 is a first-difference model. Full output: `results/regressions.csv`.

Coefficient on +10 detention ADP per 100k (p-value):

| Outcome | Old M2 | New M2 | Pooled M2 | Old M5 (Δ) | New M5 (Δ) |
|---|---:|---:|---:|---:|---:|
| Real GDP growth (pp) | +0.155 (<.001) | −0.031 (.10) | +0.061 (.015) | +0.428 (.002) | −0.356 (.026) |
| Unemployment change (pp) | −0.008 (.72) | +0.008 (.64) | −0.004 (.73) | −0.052 (.60) | −0.078 (.49) |
| Violent-crime change (%) | +0.70 (.15) | +0.75 (.17) | +0.63 (.047) | +3.4 (.55) | +8.9 (.020) |
| Property-crime change (%) | −0.67 (.28) | −0.00 (.99) | −0.34 (.29) | −1.8 (.68) | +1.4 (.43) |

Interpretation:
- **Unemployment and property crime:** null in every spec.
- **GDP:** positive in 2023–24 but negative (borderline) in 2025; it reversed sign, suggesting confounding by regional growth, not a stable effect.
- **Violent crime:** positive in the pooled and 2025 first-difference models only. With 38–45 observations this is suggestive, not conclusive.
- Adjusted R² for most models is ≤0.3.

**Caveats:** state-level only (~50 per year), no causal identification, multiple testing, mixed crime data sources (FBI vs RTCI) between eras.
