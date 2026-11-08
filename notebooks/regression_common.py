"""OLS inference for repeated-state panels and single-year cross-sections."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


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
