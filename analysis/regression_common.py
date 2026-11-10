"""OLS inference for repeated-state panels and single-year cross-sections."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

CONTROL_COLUMNS = [
    "ln_pop", "ln_density", "pop_growth", "ln_income", "pct_bach", "pct_hisp",
    "med_age", "gop24", "lag_d_youth15_29_pp",
]
CONTROLS = " + ".join(CONTROL_COLUMNS)


def republican_vote_share(returns):
    """Use state TOTAL rows, falling back only to unsplit (missing-mode) rows."""
    presidential = returns.loc[(returns.year == 2024) & (returns.office == "US PRESIDENT")].copy()
    has_total = presidential.groupby("state_po")["mode"].transform(lambda modes: modes.eq("TOTAL").any())
    presidential = presidential.loc[
        presidential["mode"].eq("TOTAL") | (~has_total & presidential["mode"].isna())
    ]
    counties = presidential.groupby(["state_po", "county_fips"]).agg(total=("totalvotes", "first"))
    counties["republican"] = (
        presidential.loc[presidential.party == "REPUBLICAN"]
        .groupby(["state_po", "county_fips"]).candidatevotes.sum()
        .reindex(counties.index, fill_value=0)
    )
    states = counties.groupby("state_po")[["republican", "total"]].sum()
    if states.empty or states.total.le(0).any():
        raise ValueError("Election returns require positive state vote totals")
    return (states.republican / states.total * 100).rename("gop24")


def require_control_coverage(panel, expected_states, years=(2023, 2024, 2025)):
    """Fail before complete-case OLS can silently discard states due to controls."""
    expected = pd.MultiIndex.from_product([sorted(expected_states), years], names=["state", "year"])
    if panel.duplicated(["state", "year"]).any():
        raise ValueError("Control coverage requires unique state-year rows")
    controls = panel.set_index(["state", "year"])[CONTROL_COLUMNS].reindex(expected)
    missing = ~np.isfinite(controls)
    if missing.any().any():
        failures = [
            f"{state}/{year}: {', '.join(missing.columns[row])}"
            for (state, year), row in missing.iterrows() if row.any()
        ]
        raise ValueError("Incomplete control coverage: " + "; ".join(failures))


def primary_bh(regressions, exposure_term):
    """Four 2025 lagged-outcome exposure tests; sensitivity p-values stay unadjusted."""
    regressions = regressions.copy()
    exposure = regressions.term.str.contains("arr_rate" if exposure_term == "arr_rate10" else "det_")
    primary = (
        (regressions.term == exposure_term) & (regressions.era == "New")
        & (regressions.spec == "M0 + lagged outcome")
    )
    selected = regressions.loc[primary]
    if len(selected) != 4 or selected.outcome.nunique() != 4 or not np.isfinite(selected.p).all():
        raise ValueError("Primary BH family requires exactly four finite outcome p-values")
    regressions["inference_family"] = np.where(primary, "primary", np.where(exposure, "sensitivity", "control"))
    regressions["q_bh"] = np.nan
    regressions.loc[primary, "q_bh"] = multipletests(selected.p, method="fdr_bh")[1]
    return regressions


def fit(formula, data):
    model = smf.ols(formula, data=data, missing="drop")
    used = data.loc[model.data.row_labels]
    if used.state.isna().any() or used.duplicated(["state", "year"]).any():
        raise ValueError("Regression requires nonmissing, unique state-year observations")
    rank = np.linalg.matrix_rank(model.exog)
    if rank < model.exog.shape[1] or len(used) <= rank:
        raise ValueError(f"Unidentified or saturated regression: n={len(used)}, rank={rank}")
    if used.state.nunique() == len(used):
        result = model.fit(cov_type="HC3", use_t=True)
    else:
        if used.state.nunique() < 2:
            raise ValueError("Clustered inference requires at least two states")
        result = model.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(used.state)[0]},
                           use_t=True)
    return result, len(used)


def coefficient(result, term):
    lower, upper = result.conf_int(alpha=0.05).loc[term]
    return {
        "coef": result.params[term], "se": result.bse[term], "p": result.pvalues[term],
        "ci_low": lower, "ci_high": upper, "cov_type": result.cov_type,
        "n_states": result.model.data.frame.loc[result.model.data.row_labels, "state"].nunique(),
        "df_resid": result.df_resid, "n_parameters": result.model.exog.shape[1],
        "r2": result.rsquared, "adj_r2": result.rsquared_adj,
    }
