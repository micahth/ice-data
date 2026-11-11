import numpy as np
import pandas as pd
import pytest
import statsmodels.formula.api as smf

from regression_common import (
    CONTROL_COLUMNS, coefficient, fit, primary_bh, republican_vote_share, require_control_coverage,
)


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


def test_election_modes_are_selected_per_state_without_double_counting():
    rows = []
    for state, modes, votes in [
        ("NC", [None], 509), ("WI", [None], 496), ("WY", [None], 716),
        ("TX", ["TOTAL", "EARLY", None], 600), ("ID", [None], 665),
        ("RI", [None], 420), ("UT", [None], 590), ("WA", [None], 390),
        ("WV", [None], 700),
    ]:
        for mode in modes:
            for party, count in [("REPUBLICAN", votes), ("DEMOCRAT", 1000 - votes)]:
                rows.append({"year": 2024, "office": "US PRESIDENT", "state_po": state,
                             "county_fips": state + "001", "mode": mode, "party": party,
                             "candidatevotes": count, "totalvotes": 1000})
    result = republican_vote_share(pd.DataFrame(rows))
    assert len(result) == 9
    assert result["NC"] == pytest.approx(50.9)
    assert result["WI"] == pytest.approx(49.6)
    assert result["WY"] == pytest.approx(71.6)
    assert result["TX"] == pytest.approx(60)


@pytest.mark.parametrize("failure", ["missing_control", "missing_state", "infinite_control"])
def test_control_coverage_fails_with_state_and_column_details(failure):
    data = panel([2023, 2024, 2025])
    for column in CONTROL_COLUMNS:
        data[column] = 1.0
    expected_states = data.state.unique()
    require_control_coverage(data, expected_states)
    if failure == "missing_state":
        data = data.loc[data.state != "S00"]
    else:
        data.loc[0, "gop24"] = np.inf if failure == "infinite_control" else np.nan
    with pytest.raises(ValueError, match="S00/2023:.*gop24"):
        require_control_coverage(data, expected_states)


def test_only_four_primary_tests_receive_bh_q_values():
    primary = pd.DataFrame({
        "term": ["arr_rate10"] * 4, "era": ["New"] * 4,
        "spec": ["M0 + lagged outcome"] * 4, "outcome": list("ABCD"),
        "p": [0.01, 0.02, 0.03, 0.5],
    })
    sensitivity = primary.assign(spec="M2 + controls", p=0.001)
    controls = primary.assign(term="gop24", p=0.001)
    result = primary_bh(pd.concat([primary, sensitivity, controls], ignore_index=True), "arr_rate10")
    np.testing.assert_allclose(result.q_bh.iloc[:4], [0.04, 0.04, 0.04, 0.5])
    assert result.q_bh.iloc[4:].isna().all()
    assert result.inference_family.tolist() == ["primary"] * 4 + ["sensitivity"] * 4 + ["control"] * 4
    from statsmodels.stats.multitest import multipletests
    exposure = result.term == "arr_rate10"
    np.testing.assert_allclose(
        result.loc[exposure, "q_bh_all_exposure"],
        multipletests(result.loc[exposure, "p"], method="fdr_bh")[1])
    assert result.loc[~exposure, "q_bh_all_exposure"].isna().all()
    with pytest.raises(ValueError, match="exactly four"):
        primary_bh(primary.iloc[:3], "arr_rate10")
