import pytest

pytest.importorskip("plotly")

import panels  # noqa: E402


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
