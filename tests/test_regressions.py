import numpy as np
import pandas as pd
import pytest
import statsmodels.formula.api as smf

from regression_common import coefficient, fit


def panel(years):
    rng = np.random.default_rng(23)
    data = pd.DataFrame([(f"S{s:02}", y) for s in range(50) for y in years], columns=["state", "year"])
    data["x"] = rng.normal(size=len(data))
    data["y"] = 0.3 * data.x + rng.normal(size=len(data))
    return data


def test_single_year_uses_hc3_t_intervals():
    data = panel([2025])
    model, n = fit("y ~ x", data)
    expected = smf.ols("y ~ x", data=data).fit(cov_type="HC3", use_t=True)
    assert model.cov_type == "HC3"
    assert n == 50
    assert model.use_t
    np.testing.assert_allclose(model.conf_int(), expected.conf_int())
    output = coefficient(model, "x")
    assert output["n_states"] == 50 and output["df_resid"] == 48
    assert output["ci_low"] < output["coef"] < output["ci_high"]


def test_repeated_states_use_clustered_t_intervals_on_complete_cases():
    data = panel([2023, 2024])
    data.loc[0, "y"] = np.nan
    model, n = fit("y ~ x + C(year)", data)
    used = data.dropna()
    expected = smf.ols("y ~ x + C(year)", data=used).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(used.state)[0]}, use_t=True)
    assert model.cov_type == "cluster"
    assert n == 99
    np.testing.assert_allclose(model.conf_int(), expected.conf_int())


def test_unidentified_model_fails_explicitly():
    data = panel([2025])
    data["copy_x"] = data.x
    with pytest.raises(ValueError, match="Unidentified"):
        fit("y ~ x + copy_x", data)


def test_duplicate_state_year_fails_explicitly():
    data = panel([2025])
    with pytest.raises(ValueError, match="unique state-year"):
        fit("y ~ x", pd.concat([data, data.iloc[:1]], ignore_index=True))
