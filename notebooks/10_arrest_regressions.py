"""
Analysis 10 - Do state arrest rates track changes in GDP, unemployment and crime?

Run after 06_geo_regressions.py (which writes state_year_panel.csv with outcomes and controls):
    python notebooks/10_arrest_regressions.py

Unit: state x year (2023, 2024, 2025; 2026 is a partial year and excluded). Old era = 2023-2024, new era = 2025.
Key regressor: ICE arrests (by apprehension state) per 100,000 residents, scaled per +10 (arr_rate10).
Same outcomes, controls, year fixed effects and state-clustered SEs as 06. Exploratory: Benjamini-Hochberg
adjusted q-values are reported across all arrest-rate coefficients.
Includes lagged change in youth share (ages 15-29) as an additional control from Census state age data.
"""
import os
import re
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

from geo_common import REPO, RESULTS, STATE_ABBR

warnings.filterwarnings("ignore")
pd.set_option("display.width", 220, "display.max_columns", 40)

a = pd.read_csv(os.path.join(REPO, "data", "arrests-latest 7-24-2026.csv"),
                usecols=["apprehension_date", "apprehension_state_filled_in", "apprehension_state_original",
                         "duplicate_drop_row"], low_memory=False, encoding="latin-1")
a = a[~a.duplicate_drop_row.fillna(False).astype(bool)]
a["year"] = pd.to_datetime(a.apprehension_date, errors="coerce").dt.year
name = a.apprehension_state_filled_in.fillna(a.apprehension_state_original).str.title().str.replace(" Of ", " of ")
a["state"] = name.map(STATE_ABBR | {"District of Columbia": "DC"})
print(f"arrests with unmapped state (dropped): {a.state.isna().sum():,}")
cnt = a[a.year.isin([2023, 2024, 2025])].dropna(subset=["state"]).groupby(["state", "year"]).size().rename("arrests")

panel = pd.read_csv(os.path.join(RESULTS, "state_year_panel.csv"))
panel = panel.merge(cnt.reset_index(), on=["state", "year"], how="left")
panel["arrests"] = panel.arrests.fillna(0)
panel["arr_rate"] = panel.arrests / panel["pop"] * 1e5
panel = panel.sort_values(["state", "year"])
panel["d_arr_rate"] = panel.groupby("state").arr_rate.diff()
panel["arr_rate10"] = panel.arr_rate / 10
panel["d_arr_rate10"] = panel.d_arr_rate / 10
panel["new"] = (panel.era == "New").astype(int)
panel.round(4)[["state", "year", "era", "region", "arrests", "arr_rate", "d_arr_rate"]].to_csv(
    os.path.join(RESULTS, "arrest_rate_panel.csv"), index=False)
print("panel", panel.shape, "| states:", panel.state.nunique())
print(panel.groupby("year")[["arr_rate", "d_gdp", "d_unemp", "d_violent", "d_property"]].mean().round(2))

OUT = {"d_gdp": "Real GDP growth (%)", "d_unemp": "Unemployment change (pp)",
       "d_violent": "Violent crime rate change (%)", "d_property": "Property (nonviolent) crime rate change (%)"}
OUT_FBI = {"d_violent_fbi": "Violent crime change, FBI (%)", "d_property_fbi": "Property crime change, FBI (%)"}
LAG = {"d_gdp": "lag_gdp_pc", "d_unemp": "lag_unemp", "d_violent": "lag_violent", "d_property": "lag_property"}
CONTROLS = "ln_pop + ln_density + pop_growth + ln_income + pct_bach + pct_hisp + med_age + gop24 + lag_d_youth15_29_pp"

# ---- correlations -----------------------------------------------------------
crow = []
for era in ["Old", "New"]:
    for gname, gd in [("All states", panel)] + [(f"Region: {r}", panel[panel.region == r])
                                                for r in sorted(panel.region.unique())]:
        sub = gd[gd.era == era]
        for yv, yl in {**OUT, **OUT_FBI}.items():
            if era == "New" and yv.endswith("_fbi"):
                continue
            for xv in ["arr_rate", "d_arr_rate"]:
                s = sub[sub.year == 2024] if (xv == "d_arr_rate" and era == "Old") else sub
                d = s[[xv, yv]].dropna()
                if len(d) < 8 or d[xv].nunique() < 3:
                    continue
                r, p = stats.pearsonr(d[xv], d[yv])
                rho, sp = stats.spearmanr(d[xv], d[yv])
                crow.append({"era": era, "group": gname, "outcome": yl, "arrest_measure": xv, "n": len(d),
                             "pearson_r": r, "pearson_p": p, "spearman_rho": rho, "spearman_p": sp})
corr = pd.DataFrame(crow)
corr["pearson_q_bh"] = multipletests(corr.pearson_p, method="fdr_bh")[1]
corr.round(4).to_csv(os.path.join(RESULTS, "arrest_correlations.csv"), index=False)

# ---- regressions ------------------------------------------------------------
def fit(formula, d):
    terms = [t for t in re.findall(r"[A-Za-z_][A-Za-z_0-9]*", formula) if t in d.columns]
    d = d.dropna(subset=terms)
    m = smf.ols(formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.state)[0]})
    return m, len(d)


rows = []


def collect(m, n, outcome, era, spec):
    for t in m.params.index:
        if t.startswith("C(year)") or t == "Intercept":
            continue
        rows.append({"outcome": {**OUT, **OUT_FBI}[outcome], "era": era, "spec": spec, "term": t,
                     "coef": m.params[t], "se": m.bse[t], "p": m.pvalues[t], "n": n, "r2": m.rsquared,
                     "adj_r2": m.rsquared_adj})


for yv in OUT:
    lag = LAG[yv]
    for era, sub in [("Old", panel[panel.era == "Old"]), ("New", panel[panel.era == "New"]), ("Pooled", panel)]:
        fe = " + C(year)" if sub.year.nunique() > 1 else ""
        for sp, f in {"M1 bivariate": f"{yv} ~ arr_rate10{fe}",
                      "M2 + controls": f"{yv} ~ arr_rate10 + {lag} + {CONTROLS}{fe}"}.items():
            collect(*fit(f, sub), yv, era, sp)
    for era, sub in [("Old", panel[panel.year == 2024]), ("New", panel[panel.year == 2025])]:
        collect(*fit(f"{yv} ~ d_arr_rate10 + {lag} + {CONTROLS}", sub), yv, era, "M5 first-difference")
    collect(*fit(f"{yv} ~ arr_rate10 + arr_rate10:new + new + {lag} + {CONTROLS}", panel), yv, "Pooled",
            "M6 era interaction")
    # detention exposure as an extra control: is arrest rate distinct from facility-located detention?
    collect(*fit(f"{yv} ~ arr_rate10 + det_rate10 + {lag} + {CONTROLS} + C(year)", panel), yv, "Pooled",
            "M7 + detention rate")

old = panel[panel.era == "Old"]
# panel has no FBI lagged level, so the FBI check omits the lagged-outcome control
for yv in ["d_violent_fbi", "d_property_fbi"]:
    for sp, f in {"M1 bivariate": f"{yv} ~ arr_rate10 + C(year)",
                  "M2 + controls": f"{yv} ~ arr_rate10 + {CONTROLS} + C(year)"}.items():
        collect(*fit(f, old), yv, "Old", sp)

reg = pd.DataFrame(rows)
key = reg.term.str.contains("arr_rate")
reg["q_bh"] = np.nan
reg.loc[key, "q_bh"] = multipletests(reg.loc[key, "p"], method="fdr_bh")[1]
reg.round(5).to_csv(os.path.join(RESULTS, "arrest_regressions.csv"), index=False)

print("\nKey arrest-rate coefficients (per +10 arrests per 100k):")
show = reg[key & reg.spec.isin(["M1 bivariate", "M2 + controls", "M5 first-difference", "M7 + detention rate"])]
print(show[["outcome", "era", "spec", "term", "coef", "se", "p", "q_bh", "n"]].round(3).to_string(index=False))
print(f"\nCorrelations tested: {len(corr)}; p<.05: {(corr.pearson_p < .05).sum()}; q<.10: {(corr.pearson_q_bh < .10).sum()}")
print(f"Regression arrest terms tested: {key.sum()}; p<.05: {(reg[key].p < .05).sum()}; q<.10: {(reg[key].q_bh < .10).sum()}")
print("\nAll-state correlations with p<.05:")
print(corr[(corr.pearson_p < .05) & (corr.group == "All states")].round(3).to_string(index=False))
