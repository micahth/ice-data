from pathlib import Path

import pandas as pd
import pytest
import duckdb
from streamlit.testing.v1 import AppTest

import panels


def _has_points(fig):
    def length(trace, attr):
        value = getattr(trace, attr, None)
        return 0 if value is None else len(value)
    return any(length(t, "x") or length(t, "locations") for t in fig.data)


def test_summary_kpis_are_consistent_with_tables():
    k = panels.summary_kpis()
    assert k["new_per_day"] > k["old_per_day"] > 0
    assert round(k["pct_change"]) == 153
    assert 0 < k["convicted_new"] < k["convicted_old"] < 100
    assert k["adp_old"] == pytest.approx(33571.7503)
    assert k["adp_new"] == pytest.approx(55073.345)


def test_monthly_and_detention_and_aor_figures_build():
    monthly, fig = panels.monthly_arrests_figure()
    assert len(monthly) > 0 and _has_points(fig)
    for dimension in panels.DETENTION_DIMENSIONS:
        data, dfig = panels.detention_figure(dimension)
        assert len(data) > 0 and _has_points(dfig)
    for era in ("old", "new"):
        aor, afig = panels.top_aor_figure(era)
        assert len(aor) > 0 and _has_points(afig)


def test_choropleth_filters_to_one_year():
    data, fig = panels.arrest_rate_choropleth(2025)
    assert (data["year"] == 2025).all()
    assert data["state"].nunique() == len(data)
    assert _has_points(fig)


def test_coefficient_forest_covers_new_era_arrest_terms():
    reg, fig = panels.coefficient_forest()
    assert (reg["era"] == "New").all()
    assert reg["term"].str.contains("arr_rate").all()
    assert (reg["ci_low"] <= reg["coef"]).all() and (reg["coef"] <= reg["ci_high"]).all()
    assert _has_points(fig)


def test_filters_change_actual_data():
    old, _ = panels.monthly_arrests_figure("old")
    new, _ = panels.monthly_arrests_figure("new")
    assert len(old) == 24 and len(new) == 15
    assert old.arrests.sum() == 262329 and new.arrests.sum() == 394590
    assert new.partial_month.sum() == 1
    for year in (2023, 2024, 2025):
        data, _ = panels.arrest_rate_choropleth(year, "South")
        assert data.region.eq("South").all() and len(data) > 0
    data, fig = panels.detention_figure("Region", "adp", "new")
    assert data.period.str.startswith("New").all()
    assert sum(sum(trace.y) for trace in fig.data) == pytest.approx(data.adp.sum())
    _, operator_fig = panels.detention_figure("Operator")
    assert "U.S. residents" in operator_fig.layout.title.text
    reg, _ = panels.coefficient_forest("Real GDP growth (%)", ["M2 + controls"], True)
    assert set(reg.spec) == {"M2 + controls", panels.SENSITIVITY_SPEC}
    assert reg.term.eq("arr_rate10").all()
    with pytest.raises(ValueError, match="specification"):
        panels.coefficient_forest(specs=[])


def test_joint_locations_reconcile_to_published_marginals():
    joint = pd.read_csv(panels.RESULTS / "arrests_state_locations.csv")
    joint["era"] = joint.year.ge(2025).map({True: "new", False: "old"})
    assert not joint.duplicated(["year", "state", "dimension", "location"]).any()
    for dimension, table in (("aor", "arrests_by_aor"), ("landmark", "arrests_by_landmark")):
        subset = joint[joint.dimension == dimension]
        for key, source in (("state", "arrests_by_state"), ("location", table)):
            actual = subset.groupby([key, "era"]).arrests.sum().unstack(fill_value=0)
            expected = pd.read_csv(panels.RESULTS / f"{source}.csv").set_index(
                "state" if key == "state" else dimension)[["new", "old"]]
            pd.testing.assert_frame_equal(actual.sort_index(), expected.sort_index(),
                                          check_names=False)
    tx = panels.state_locations(2025, "TEXAS", "aor")
    panel = pd.read_csv(panels.RESULTS / "arrest_rate_panel.csv")
    assert tx.arrests.sum() == panel.loc[(panel.state == "TX") & (panel.year == 2025), "arrests"].iloc[0]


def app():
    return AppTest.from_file(str(Path(panels.__file__).parent / "app.py"), default_timeout=20).run()


def test_streamlit_pages_and_controls():
    at = app()
    assert not at.exception
    at.sidebar.radio[1].set_value("new").run()
    assert not at.exception
    assert len(at.dataframe[0].value) == 15
    at.sidebar.radio[0].set_value("Geography").run()
    assert not at.exception
    at.selectbox[0].select("South").run()
    assert at.dataframe[0].value.region.eq("South").all()
    at.selectbox[1].select("TX").run()
    expected = panels.state_locations(2025, "TEXAS", "aor")
    pd.testing.assert_frame_equal(at.dataframe[1].value, expected)
    at.select_slider[0].set_value(2024).run()
    assert at.dataframe[0].value.year.eq(2024).all()
    at.sidebar.radio[0].set_value("Detention geography").run()
    at.radio[-1].set_value("adp").run()
    assert not at.exception
    at.sidebar.radio[0].set_value("Model uncertainty").run()
    at.multiselect[0].set_value(["M2 + controls"]).run()
    at.checkbox[0].check().run()
    assert set(at.dataframe[0].value.spec) == {"M2 + controls", panels.SENSITIVITY_SPEC}
    at.checkbox[0].uncheck().run()
    at.multiselect[0].set_value([]).run()
    assert len(at.warning) == 1 and not at.exception
    at.sidebar.radio[0].set_value("SQL").run()
    assert not at.exception and not at.error
    assert at.dataframe[0].value.new.sum() == 3


def test_streamlit_sql_errors_are_not_reported_as_missing_dependencies(monkeypatch):
    at = app()

    def broken_connection():
        raise duckdb.Error("synthetic query failure")

    monkeypatch.setattr(duckdb, "connect", broken_connection)
    at.sidebar.radio[0].set_value("SQL").run()
    assert not at.exception
    assert "DuckDB query failed" in at.error[0].value
    assert not at.info
