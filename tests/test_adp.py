import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analysis"))
from adp_common import (derive_monthly_from_fytd, fiscal_year, fytd_check, fytd_revisions,  # noqa: E402
                        validate_monthly)

DATA = os.path.join(os.path.dirname(__file__), "..", "analysis", "data", "ice_published_adp_monthly.csv")


def frame(months, adp):
    months = pd.to_datetime(months)
    return pd.DataFrame({"month": months, "adp": adp, "fiscal_year": [fiscal_year(m) for m in months]})


def test_october_starts_the_fiscal_year():
    assert fiscal_year("2018-09-01") == 2018 and fiscal_year("2018-10-01") == 2019


def test_validation_flags_gaps_duplicates_and_bad_values():
    assert validate_monthly(frame(["2020-01-01", "2020-02-01", "2020-03-01"], [1.0, 2.0, 3.0])) == []
    assert any("missing" in p for p in validate_monthly(frame(["2020-01-01", "2020-03-01"], [1.0, 2.0])))
    assert validate_monthly(frame(["2020-01-01", "2020-03-01"], [1.0, 2.0]), documented_gaps=["2020-02-01"]) == []
    assert "duplicate months" in validate_monthly(frame(["2020-01-01", "2020-01-01"], [1.0, 2.0]))
    assert any("greater than 0" in p for p in validate_monthly(frame(["2020-01-01"], [0.0])))
    bad = frame(["2019-10-01"], [1.0]).assign(fiscal_year=2018)
    assert any("fiscal_year" in p for p in validate_monthly(bad))


def test_fytd_derivation_is_exact():
    oct_adp, nov_adp = 100.0, 160.0
    ytd_oct, ytd_nov = oct_adp, (oct_adp * 31 + nov_adp * 30) / 61
    assert derive_monthly_from_fytd(ytd_oct, 31, ytd_nov, 61) == pytest.approx(nov_adp)


def test_fytd_check_and_revisions_report_without_raising():
    s = frame(pd.date_range("2019-10-01", periods=12, freq="MS"), [100.0, 160.0] + [120.0] * 10)
    ytd = pd.DataFrame({"fiscal_year": [2020, 2020], "file_date": ["2020-09-30", "2020-12-31"],
                        "adp_fy_ytd": [129.0, 140.0]})
    check = fytd_check(s, ytd, tolerance=0.01)
    assert check.loc[0, "months"] == 12
    assert check.loc[0, "recomputed_ytd"] == pytest.approx((100 * 31 + 160 * 30 + 120 * 305) / 366)
    assert check.loc[0, "published_ytd"] == 140.0
    assert not check.loc[0, "ok"]
    rev = fytd_revisions(ytd)
    assert rev.loc[0, "pct_revision"] == pytest.approx((140 / 129 - 1) * 100)


def test_fytd_check_skips_incomplete_years_and_missing_published_values():
    s = frame(pd.date_range("2019-10-01", periods=12, freq="MS"), [100.0] * 12)
    ytd = pd.DataFrame({"fiscal_year": [2020], "file_date": ["2020-09-30"], "adp_fy_ytd": [100.0]})
    assert fytd_check(s.iloc[:2], ytd).empty
    assert fytd_check(s.drop(index=5), ytd).empty
    assert fytd_check(s, ytd.iloc[:0]).empty
    assert fytd_check(s, ytd).loc[0, "ok"]


def test_committed_published_series_is_valid():
    s = pd.read_csv(DATA)
    assert validate_monthly(s) == []
    assert s["month"].iloc[0] == "2018-10-01"
    assert (s["ice_adp"] + s["cbp_adp"] - s["adp"]).abs().max() < 1e-3


from ice_lib import build_intervals, monthly_adp, transfer_safe_intervals  # noqa: E402

CUT = pd.Timestamp("2026-03-11")


def safe(rows, cutoff=CUT):
    df = pd.DataFrame(rows, columns=["stay_ID", "unique_identifier", "book_in_date_time", "book_out_date_time",
                                     "stay_book_out_date_time"])
    for c in df.columns[2:]:
        df[c] = pd.to_datetime(df[c])
    return transfer_safe_intervals(build_intervals(df, cutoff))


def person_days(iv):
    return ((iv["end"] - iv["start"]).dt.total_seconds() / 86400).sum()


def test_transfer_with_missing_middle_book_out_equals_stay_interval():
    iv = safe([("s", "p", "2024-01-01", "2024-01-05", "2024-01-20"),
               ("s", "p", "2024-01-05", None, "2024-01-20"),
               ("s", "p", "2024-01-10", "2024-01-20", "2024-01-20")])
    assert person_days(iv) == 19 and len(iv) == 1


def test_gap_between_stints_is_kept():
    iv = safe([("s", "p", "2024-01-01", "2024-01-05", "2024-01-20"),
               ("s", "p", "2024-01-10", "2024-01-20", "2024-01-20")])
    assert len(iv) == 2 and person_days(iv) == 14


def test_concurrent_stays_count_once():
    iv = safe([("a", "p", "2024-01-01", "2024-01-11", "2024-01-11"),
               ("b", "p", "2024-01-05", "2024-01-15", "2024-01-15")])
    assert person_days(iv) == 14


def test_transfer_across_month_boundary_splits():
    iv = safe([("s", "p", "2024-01-25", "2024-02-02", "2024-02-10"),
               ("s", "p", "2024-02-02", "2024-02-10", "2024-02-10")])
    m = monthly_adp(iv, "2024-01", "2024-02", CUT).set_index("month")
    assert m.loc["2024-01", "adp"] * 31 == pytest.approx(7)
    assert m.loc["2024-02", "adp"] * 29 == pytest.approx(9)  # leap year


def test_partial_final_month_uses_observed_days_only():
    iv = safe([("s", "p", "2026-03-01", None, None)])
    m = monthly_adp(iv, "2026-02", "2026-04", CUT)
    assert m["month"].tolist() == ["2026-02", "2026-03"]
    assert m.loc[1, "partial_month"] and m.loc[1, "days_observed"] == 11 and m.loc[1, "adp"] == pytest.approx(1.0)


def test_adp_days_sum_to_total_person_days():
    iv = safe([("a", "p", "2024-01-15", "2024-03-10", "2024-03-10"),
               ("b", "q", "2024-02-20", "2024-04-01", "2024-04-01")])
    m = monthly_adp(iv, "2024-01", "2024-04", CUT)
    assert (m["adp"] * m["days_observed"]).sum() == pytest.approx(person_days(iv))


from forecast_adp import backtest as adp_backtest, complete_months as adp_complete, predict_baselines  # noqa: E402


def adp_series(values, partial_last=False, source="published"):
    months = pd.period_range("2019-01", periods=len(values), freq="M").astype(str)
    partial = [False] * (len(values) - 1) + [partial_last]
    return pd.DataFrame({"month": months, "adp": values, "partial_month": partial, "source": source})


def wavy(n=40):
    return [100.0 + 5 * (i % 12) + i for i in range(n)]


def test_backtest_uses_only_past_and_matches_shifted_actuals():
    bt = adp_backtest(adp_series(wavy()), 24)
    assert (pd.PeriodIndex(bt.train_end, freq="M") < pd.PeriodIndex(bt.month, freq="M")).all()
    y = pd.Series(wavy(), index=pd.period_range("2019-01", periods=40, freq="M"))
    for model, lag in [("last_month", 1), ("seasonal_naive", 12)]:
        g = bt[bt.model == model]
        expected = [y[pd.Period(m, "M") - lag] for m in g.month]
        assert g.forecast.tolist() == expected
    assert predict_baselines(wavy(14))["seasonal_naive_drift"] == pytest.approx(
        wavy(14)[-12] * wavy(14)[-1] / wavy(14)[-13])


def test_future_and_partial_months_do_not_change_earlier_forecasts():
    base = adp_backtest(adp_series(wavy(40)), 24)
    values = wavy(41)
    values[35] *= 3  # perturb a future month relative to early origins
    values[-1] = 1.0
    changed = adp_backtest(adp_series(values, partial_last=True), 24)
    early = base[pd.PeriodIndex(base.month, freq="M") <= pd.Period("2021-12", "M")]
    same = changed[changed.month.isin(early.month)]
    assert same.reset_index(drop=True)[["month", "model", "forecast"]].equals(
        early.reset_index(drop=True)[["month", "model", "forecast"]])
    assert adp_complete(adp_series(values, partial_last=True)).index[-1] == pd.Period("2022-04", "M")


def test_adp_forecast_inputs_are_validated():
    good = adp_series(wavy())
    for bad in [good.drop(5), pd.concat([good, good.iloc[[3]]]), good.assign(adp=[-1.0] + wavy()[1:]),
                good.assign(partial_month=[True] + [False] * 39), good.assign(source=["a"] * 20 + ["b"] * 20),
                good.assign(adp=[np.nan] + wavy()[1:])]:
        with pytest.raises(ValueError):
            adp_complete(bad)
    with pytest.raises(ValueError):
        adp_backtest(adp_series(wavy(20)), 24)


from forecast_adp import MODELS, predict  # noqa: E402


def hist(n, start="2019-01"):
    idx = pd.period_range(start, periods=n, freq="M")
    return pd.Series([100.0 * (1.01 ** i) * (1 + 0.05 * np.sin(i)) for i in range(n)], index=idx)


def arrests_for(h):
    idx = pd.period_range(h.index[0], periods=len(h) + 3, freq="M")
    return pd.Series(1000.0 + 10 * np.arange(len(idx)) + 50 * np.cos(np.arange(len(idx))), index=idx)


def test_models_ignore_data_after_the_origin():
    base, ex = hist(40), arrests_for(hist(40))
    ref = predict(base, ex)
    longer = pd.concat([base, pd.Series([1e6], index=[base.index[-1] + 1])])
    ex2 = ex.copy()
    ex2.loc[base.index[-1] + 1:] = 1e9  # arrests at the target month and later
    again = predict(longer.iloc[:40], ex2)
    for model in MODELS:
        assert ref[model][1] == "ok"
        assert again[model][0] == pytest.approx(ref[model][0])


def test_arrests_model_uses_lagged_arrests_and_flags_missing_exog():
    h = hist(30)
    ex = arrests_for(h)
    low = predict(h, ex)["log_ar1_arrests"][0]
    ex_changed = ex.copy()
    ex_changed.loc[h.index[-1]] *= 2  # last observed month does matter
    assert predict(h, ex_changed)["log_ar1_arrests"][0] != pytest.approx(low)
    value, status = predict(h, ex.drop(h.index[3]))["log_ar1_arrests"]
    assert np.isnan(value) and status == "missing_exog"
    assert predict(h)["log_ar1_arrests"][1] == "not_applicable"


def test_seasonal_model_needs_36_training_months():
    assert np.isnan(predict(hist(35))["log_ar1_seasonal"][0])
    assert predict(hist(35))["log_ar1_seasonal"][1] == "not_applicable"
    assert np.isfinite(predict(hist(36))["log_ar1_seasonal"][0])


def test_backtest_records_failed_fits_without_dropping_rows():
    bt = adp_backtest(adp_series(wavy(40)), 24)
    assert len(bt) == 16 * len(MODELS)
    assert (bt[bt.model == "log_ar1_arrests"].fit_status == "not_applicable").all()
    assert (bt.source == "published").all()


from forecast_adp import evaluate, prediction_intervals  # noqa: E402


def synthetic_predictions(n=400, sigma=0.05, seed=0):
    rng = np.random.default_rng(seed)
    months = pd.period_range("1990-01", periods=n, freq="M").astype(str)
    forecast = np.full(n, 100.0)
    actual = forecast * np.exp(rng.normal(0, sigma, n))
    return pd.DataFrame({"source": "s", "month": months, "model": "m", "actual": actual, "forecast": forecast,
                         "error": forecast - actual})


def test_intervals_missing_before_min_errors_and_use_only_earlier_errors():
    p = synthetic_predictions(60)
    out = prediction_intervals(p)
    assert out["lower80"].iloc[:12].isna().all() and out["lower80"].iloc[12:].notna().all()
    changed = p.copy()
    changed.loc[40, "actual"] *= 5
    after = prediction_intervals(changed)
    assert after["lower95"].iloc[:41].equals(out["lower95"].iloc[:41])
    assert not after["lower95"].iloc[41:].equals(out["lower95"].iloc[41:])


def test_interval_coverage_is_close_to_nominal_on_iid_noise():
    out = prediction_intervals(synthetic_predictions(1500)).dropna(subset=["lower80"])
    inside = lambda lo, hi: ((out.actual >= out[lo]) & (out.actual <= out[hi])).mean()  # noqa: E731
    assert inside("lower80", "upper80") == pytest.approx(0.8, abs=0.04)
    assert inside("lower95", "upper95") == pytest.approx(0.95, abs=0.03)


def test_metrics_match_hand_computation():
    p = pd.DataFrame({"source": "s", "month": ["2022-01", "2022-02"], "model": "last_month",
                      "actual": [100.0, 200.0], "forecast": [110.0, 190.0], "error": [10.0, -10.0],
                      "lower95": [90.0, 150.0], "upper95": [120.0, 190.0],
                      "lower80": [95.0, 185.0], "upper80": [115.0, 195.0]})
    row = evaluate(p).query("period == 'full'").iloc[0]
    assert row.mae == 10 and row.rmse == 10 and row.mean_error == 0 and row.pct_over == 50
    assert row.mape == pytest.approx(7.5) and row.mase_vs_last_month == 1
    assert row.cover95 == 0.5 and row.width95 == pytest.approx(35.0)
    # Winkler: row 1 = 30 (covered); row 2 = 40 + (2 / 0.05) * 10 = 440; mean 235
    assert row.interval_score95 == pytest.approx(235.0)


def test_diebold_mariano_detects_a_clearly_better_model_and_skips_short_samples():
    import forecast_adp as fa
    months = [str(p) for p in pd.period_range("2022-01", periods=20, freq="M")]
    rng = np.random.default_rng(0)
    rows = []
    for source, n in [("s", 20), ("short", 5)]:
        for model, scale in [("last_month", 10.0), ("good", 1.0)]:
            for m in months[:n]:
                e = rng.normal(0, scale)
                rows.append({"source": source, "month": m, "model": model, "actual": 100 + e, "forecast": 100.0,
                             "error": e})
    dm = fa.diebold_mariano(pd.DataFrame(rows))
    full = dm[(dm.period == "full") & (dm["loss"] == "abs")].set_index("source")
    assert full.loc["s", "mean_loss_diff"] > 0 and full.loc["s", "p_value"] < 0.01
    assert np.isnan(full.loc["short", "p_value"]) and full.loc["short", "n"] == 5
