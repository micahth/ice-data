"""
Analysis 05 - Do state arrest rates track changes in GDP, unemployment and crime?

Run after 02_geo_regressions.py (which writes state_year_panel.csv with outcomes and controls):
    python analysis/05_arrest_regressions.py

Unit: state x year (2023, 2024, 2025; 2026 is a partial year and excluded). Old era = 2023-2024, new era = 2025.
Key regressor: ICE arrests (by apprehension state) per 100,000 residents, scaled per +10 (arr_rate10).
Same outcomes and controls as 02. Parsimonious lagged-outcome models are primary; full controls and
exclusion of the highest-rate state are sensitivity checks. Repeated-state models use clustered SEs;
single-year models use HC3. BH q-values (`q_bh`) cover only the four 2025 lagged-outcome exposure tests;
`q_bh_all_exposure` adds a sensitivity BH across all arrest exposure coefficients (none reach q<.10).
Includes lagged change in youth share (ages 15-29) as an additional control from Census state age data.
"""
import os

import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from geo_common import RESULTS, STATE_ABBR
from arrest_common import clean_arrests, load_arrests
from regression_common import CONTROLS, coefficient, fit, primary_bh, require_control_coverage


def main():
    pd.set_option("display.width", 220, "display.max_columns", 40)

    arrests = clean_arrests(load_arrests(["apprehension_date", "apprehension_state_filled_in",
                                   "apprehension_state_original", "duplicate_drop_row"]))
    arrests["year"] = arrests.date.dt.year
    state_names = arrests.apprehension_state_filled_in.fillna(arrests.apprehension_state_original).str.title().str.replace(" Of ", " of ")
    arrests["state"] = state_names.map(STATE_ABBR | {"District of Columbia": "DC"})
    print(f"arrests with unmapped state (dropped): {arrests.state.isna().sum():,}")
    arrest_counts = arrests[arrests.year.isin([2023, 2024, 2025])].dropna(subset=["state"]).groupby(["state", "year"]).size().rename("arrests")

    panel = pd.read_csv(os.path.join(RESULTS, "state_year_panel.csv"))
    require_control_coverage(panel, set(STATE_ABBR.values()) - {"DC"})
    panel = panel.merge(arrest_counts.reset_index(), on=["state", "year"], how="left")
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

    # ---- correlations -----------------------------------------------------------
    correlation_rows = []
    for era in ["Old", "New"]:
        for group_name, group_data in [("All states", panel)] + [
                (f"Region: {region}", panel[panel.region == region])
                for region in sorted(panel.region.unique())]:
            subset = group_data[group_data.era == era]
            for outcome_key, outcome_label in {**OUT, **OUT_FBI}.items():
                if era == "New" and outcome_key.endswith("_fbi"):
                    continue
                for exposure_key in ["arr_rate", "d_arr_rate"]:
                    sample = subset[subset.year == 2024] if (exposure_key == "d_arr_rate" and era == "Old") else subset
                    complete_cases = sample[[exposure_key, outcome_key]].dropna()
                    if len(complete_cases) < 8 or complete_cases[exposure_key].nunique() < 3:
                        continue
                    pearson_r, pearson_p = stats.pearsonr(complete_cases[exposure_key], complete_cases[outcome_key])
                    spearman_rho, spearman_p = stats.spearmanr(complete_cases[exposure_key], complete_cases[outcome_key])
                    correlation_rows.append({"era": era, "group": group_name, "outcome": outcome_label, "arrest_measure": exposure_key, "n": len(complete_cases),
                                 "pearson_r": pearson_r, "pearson_p": pearson_p,
                                 "spearman_rho": spearman_rho, "spearman_p": spearman_p})
    correlations = pd.DataFrame(correlation_rows)
    correlations["pearson_q_bh"] = multipletests(correlations.pearson_p, method="fdr_bh")[1]
    correlations["spearman_q_bh"] = multipletests(correlations.spearman_p, method="fdr_bh")[1]
    correlations.round(4).to_csv(os.path.join(RESULTS, "arrest_correlations.csv"), index=False)

    # ---- regressions ------------------------------------------------------------
    rows = []


    def collect(model, n_observations, outcome, era, specification):
        for term in model.params.index:
            if term.startswith("C(year)") or term == "Intercept":
                continue
            rows.append({"outcome": {**OUT, **OUT_FBI}[outcome], "era": era, "spec": specification, "term": term,
                         "n": n_observations, **coefficient(model, term)})


    for outcome_key in OUT:
        lagged_outcome = LAG[outcome_key]
        for era, subset in [("Old", panel[panel.era == "Old"]), ("New", panel[panel.era == "New"]), ("Pooled", panel)]:
            year_effects = " + C(year)" if subset.year.nunique() > 1 else ""
            for specification, formula in {"M0 + lagged outcome": f"{outcome_key} ~ arr_rate10 + {lagged_outcome}{year_effects}",
                          "M1 bivariate": f"{outcome_key} ~ arr_rate10{year_effects}",
                          "M2 + controls": f"{outcome_key} ~ arr_rate10 + {lagged_outcome} + {CONTROLS}{year_effects}"}.items():
                collect(*fit(formula, subset), outcome_key, era, specification)
        new = panel[panel.year == 2025]
        highest = new.loc[new.arr_rate.idxmax(), "state"]
        collect(*fit(f"{outcome_key} ~ arr_rate10 + {lagged_outcome}", new[new.state != highest]), outcome_key, "New",
                f"M0 excluding highest-rate state ({highest})")
        for era, subset in [("Old", panel[panel.year == 2024]), ("New", panel[panel.year == 2025])]:
            collect(*fit(f"{outcome_key} ~ d_arr_rate10 + {lagged_outcome} + {CONTROLS}", subset), outcome_key, era, "M5 first-difference")
        collect(*fit(f"{outcome_key} ~ arr_rate10 + arr_rate10:new + new + {lagged_outcome} + {CONTROLS}", panel), outcome_key, "Pooled",
                "M6 era interaction")
        # detention exposure as an extra control: is arrest rate distinct from facility-located detention?
        collect(*fit(f"{outcome_key} ~ arr_rate10 + det_rate10 + {lagged_outcome} + {CONTROLS} + C(year)", panel), outcome_key, "Pooled",
                "M7 + detention rate")

    old = panel[panel.era == "Old"]
    # panel has no FBI lagged level, so the FBI check omits the lagged-outcome control
    for outcome_key in ["d_violent_fbi", "d_property_fbi"]:
        for specification, formula in {"M1 bivariate": f"{outcome_key} ~ arr_rate10 + C(year)",
                      "M2 + controls": f"{outcome_key} ~ arr_rate10 + {CONTROLS} + C(year)"}.items():
            collect(*fit(formula, old), outcome_key, "Old", specification)

    regressions = pd.DataFrame(rows)
    arrest_terms = regressions.term.str.contains("arr_rate")
    regressions = primary_bh(regressions, "arr_rate10")
    regressions.round(5).to_csv(os.path.join(RESULTS, "arrest_regressions.csv"), index=False)
    primary = regressions.loc[regressions.inference_family == "primary"].copy()
    iqr_units = (panel.loc[panel.year == 2025, "arr_rate"].quantile(0.75)
                 - panel.loc[panel.year == 2025, "arr_rate"].quantile(0.25)) / 10
    primary["alpha"] = 0.05
    primary["power"] = 0.80
    primary["mde_per_10"] = (stats.t.ppf(0.975, primary.df_resid) + stats.norm.ppf(0.80)) * primary.se
    primary["arrest_iqr_per_10"] = iqr_units
    primary["mde_across_iqr"] = primary.mde_per_10 * iqr_units
    primary[["outcome", "n", "alpha", "power", "se", "df_resid", "mde_per_10",
             "arrest_iqr_per_10", "mde_across_iqr"]].round(6).to_csv(
        os.path.join(RESULTS, "arrest_mde.csv"), index=False)

    print("\nKey arrest-rate coefficients (per +10 arrests per 100k):")
    show = regressions[arrest_terms & regressions.spec.isin(["M0 + lagged outcome", "M2 + controls"])]
    print(show[["outcome", "era", "spec", "coef", "ci_low", "ci_high", "cov_type", "q_bh", "n"]].round(3).to_string(index=False))
    print(f"\nCorrelations tested: {len(correlations)}; p<.05: {(correlations.pearson_p < .05).sum()}; q<.10: {(correlations.pearson_q_bh < .10).sum()}")
    print(f"Primary family: {len(primary)} tests; q<.10: {(primary.q_bh < .10).sum()}; "
          f"{arrest_terms.sum() - len(primary)} sensitivity terms have unadjusted p-values only")
    print("\nAll-state correlations with p<.05:")
    print(correlations[(correlations.pearson_p < .05) & (correlations.group == "All states")].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
