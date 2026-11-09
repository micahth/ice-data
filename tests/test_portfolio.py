from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from arrest_common import ARREST_DAYS, clean_arrests, monthly_arrests
from dashboard import location_view
from forecast_arrests import backtest
from sql_arrests import aggregate_arrests, run_sql

REPO = Path(__file__).resolve().parents[1]


def test_sql_aggregates_match_pandas_cohort_and_denominators():
    raw = pd.read_csv(REPO / "tests/fixtures/arrests.csv")
    raw.loc[len(raw)] = ["2025-02-01", "Florida", None, None, "  test site  ", None, "TEST", "TEST", None]
    clean = clean_arrests(raw)
    with duckdb.connect() as connection:
        connection.register("raw_arrests", raw)
        tables = aggregate_arrests(connection)
    expected_monthly = monthly_arrests(clean)
    pd.testing.assert_frame_equal(tables["monthly_arrests"], expected_monthly, check_dtype=False)
    for location, source in [("state", clean.apprehension_state_filled_in.fillna(clean.apprehension_state_original)),
                             ("aor", clean.apprehension_aor),
                             ("landmark", clean.apprehension_site_landmark.str.strip().str.upper())]:
        expected = clean.assign(location=source.fillna("Unknown")).groupby(["location", "era"]).size().unstack(fill_value=0)
        actual = tables[f"arrests_by_{location}"].set_index(location)
        actual.index.name = "location"
        pd.testing.assert_frame_equal(actual[["old", "new"]].sort_index(), expected[["old", "new"]].sort_index(),
                                      check_dtype=False, check_names=False)
        for era in ("old", "new"):
            np.testing.assert_allclose(actual[f"{era}_per_day"], actual[era] / ARREST_DAYS[era])
        assert actual.share_new_pct.sum() == pytest.approx(100)
        assert actual.loc[actual.old == 0, "change_pct"].isna().all()
    summary = tables["arrest_summary"].set_index("era")
    pd.testing.assert_series_equal(summary.arrests.sort_index(), clean.groupby("era").size().sort_index(),
                                   check_dtype=False, check_names=False)
    actual_criminality = tables["arrest_criminality"].set_index("era")
    pd.testing.assert_frame_equal(actual_criminality.sort_index(axis=1),
                                  pd.crosstab(clean.era, clean.apprehension_criminality.fillna("Unknown")),
                                  check_dtype=False, check_names=False)


def test_sql_empty_cohort_fails_explicitly():
    raw = pd.read_csv(REPO / "tests/fixtures/arrests.csv").iloc[:1]
    with duckdb.connect() as connection:
        connection.register("raw_arrests", raw)
        with pytest.raises(ValueError, match="cohort is empty"):
            aggregate_arrests(connection)


def test_sql_reads_original_latin1_csv_without_pandas_conversion(tmp_path, monkeypatch):
    from data_common import CSV_INPUTS
    import sql_arrests
    monkeypatch.delenv("ICE_DATA_DIR", raising=False)
    monkeypatch.setattr(sql_arrests, "REPO", tmp_path)
    (tmp_path / "data").mkdir()
    raw = pd.read_csv(REPO / "tests/fixtures/arrests.csv")
    raw.loc[1, "apprehension_site_landmark"] = " caf\u00e9 "
    raw.to_csv(tmp_path / "data" / CSV_INPUTS["arrests"][0], index=False, encoding="latin-1")
    run_sql(tmp_path / "results")
    landmark = pd.read_csv(tmp_path / "results/arrests_by_landmark.csv").set_index("landmark")
    assert landmark.loc["CAF\u00c9", "old"] == 1
    assert pd.read_csv(tmp_path / "results/arrest_summary.csv").arrests.sum() == 5


def forecast_fixture():
    return pd.DataFrame({"month": pd.period_range("2023-01", periods=39, freq="M").astype(str),
                         "arrests": np.arange(39) * 137 + 1000, "partial_month": [False] * 38 + [True]})


def test_forecast_uses_only_past_complete_months():
    monthly = forecast_fixture()
    predictions, metrics, projection = backtest(monthly)
    assert len(predictions) == 14 * 3 and set(metrics.n_forecasts) == {14}
    assert (predictions.train_end < predictions.month).all()
    assert set(projection.month) == {"2026-03"}
    assert set(projection.n_train) == {38}
    perturbed = monthly.copy()
    perturbed.loc[25:, "arrests"] *= 100
    changed_predictions, _, _ = backtest(perturbed)
    np.testing.assert_allclose(predictions.loc[predictions.month <= "2025-02", "forecast"],
                               changed_predictions.loc[changed_predictions.month <= "2025-02", "forecast"])
    monthly.loc[38, "arrests"] *= 10000
    changed_predictions, changed_metrics, changed_projection = backtest(monthly)
    pd.testing.assert_frame_equal(predictions, changed_predictions)
    pd.testing.assert_frame_equal(metrics, changed_metrics)
    pd.testing.assert_frame_equal(projection, changed_projection)
    last_month = predictions.loc[predictions.model == "last_month"]
    np.testing.assert_allclose(last_month.forecast, monthly.arrests.iloc[23:37])
    for model, group in predictions.groupby("model"):
        metric = metrics.set_index("model").loc[model]
        assert metric.mae == pytest.approx(group.error.abs().mean())
        assert metric.rmse == pytest.approx(np.sqrt(np.mean(group.error ** 2)))


@pytest.mark.parametrize("failure", ["gap", "duplicate", "negative", "partial", "short"])
def test_forecast_rejects_invalid_monthly_input(failure):
    data = forecast_fixture()
    if failure == "gap":
        data = data.drop(index=5)
    elif failure == "duplicate":
        data.loc[5, "month"] = data.loc[4, "month"]
    elif failure == "negative":
        data.loc[5, "arrests"] = -1
    elif failure == "partial":
        data.loc[5, "partial_month"] = True
    else:
        data = data.iloc[:24]
    with pytest.raises(ValueError):
        backtest(data)


def test_dashboard_shares_use_all_locations_and_switch_periods():
    table = pd.DataFrame({"state": ["Texas", "Florida", "Unknown"], "old": [3, 1, 1], "new": [2, 4, 2]})
    view = location_view(table, "state", "new", 434)
    assert view.Location.iloc[0] == "Florida"
    assert view["Share (%)"].sum() == pytest.approx(100)
    assert view["Records per day"].sum() == pytest.approx(8 / 434)
    app = AppTest.from_file(str(REPO / "analysis/dashboard.py")).run()
    assert not app.exception
    assert app.metric[0].value == "262,329"
    app.selectbox[0].select("ICE Area of Responsibility")
    app.selectbox[1].select("Jan 2025-Mar 10, 2026 (434 days)")
    app.run()
    assert not app.exception
    assert app.metric[0].value == "394,590"
