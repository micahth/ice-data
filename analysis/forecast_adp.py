"""Baselines and expanding-window, one-month-ahead backtests for monthly ICE detention ADP.

Separate from forecast_arrests.py (arrests are a flow, ADP is a stock). Each run uses exactly one
source series; the published and record-level series are never combined.
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
BASELINES = ("last_month", "seasonal_naive", "seasonal_naive_drift")  # drift is an extra baseline
# Final model list, fixed before any backtest was run; settings are not tuned per origin.
MODELS = BASELINES + ("log_ar1", "log_ar1_seasonal", "ets_damped", "log_ar1_arrests")
MIN_TRAIN = {"published": 36, "records": 24}


def complete_months(series):
    """Validate a monthly frame (month, adp, partial_month, source) and return complete-month ADP."""
    data = series.copy()
    required = {"month", "adp", "partial_month", "source"}
    if not required <= set(data.columns):
        raise ValueError(f"Forecast input needs columns {sorted(required)}")
    data.index = pd.PeriodIndex(data.month, freq="M")
    if data.empty or data.index.has_duplicates or not data.index.is_monotonic_increasing:
        raise ValueError("Forecast input requires unique, ordered months")
    if not data.index.equals(pd.period_range(data.index.min(), data.index.max(), freq="M")):
        raise ValueError("Forecast input must include every calendar month")
    if data.source.nunique() != 1:
        raise ValueError("Forecast input must have exactly one source")
    if data.partial_month.isna().any() or not data.partial_month.isin([True, False]).all():
        raise ValueError("partial_month must be nonmissing booleans")
    if data.partial_month.iloc[:-1].any():
        raise ValueError("Only the final month may be partial")
    if not np.isfinite(data.adp).all() or data.adp.le(0).any():
        raise ValueError("Monthly ADP must be finite and greater than 0")
    return data.loc[~data.partial_month, "adp"].astype(float)


def predict_baselines(history):
    """Baseline forecasts for the month after `history`, using only the supplied past."""
    y = np.asarray(history, dtype=float)
    if len(y) < 13 or not np.isfinite(y).all() or (y <= 0).any():
        raise ValueError("Baselines need at least 13 finite, positive past months")
    return {"last_month": y[-1], "seasonal_naive": y[-12],
            "seasonal_naive_drift": y[-12] * (y[-1] / y[-13])}


def _lag1_design(log_y, extra=None):
    """Rows for y_t on [1, y_{t-1}, extra_t]; returns design, response and the predictor row builder."""
    columns = [np.ones(len(log_y) - 1), log_y[:-1]]
    if extra is not None:
        columns += [extra[1:, j] for j in range(extra.shape[1])]
    return np.column_stack(columns), log_y[1:]


def _ols_forecast(design, response, row):
    parameters, _, rank, _ = np.linalg.lstsq(design, response, rcond=None)
    if rank != design.shape[1]:
        raise ValueError("unidentified design")
    return float(np.exp(row @ parameters))  # median forecast of ADP


def _month_dummies(months):
    return np.column_stack([(np.asarray([m.month for m in months]) == k).astype(float) for k in range(2, 13)])


def _fit_ets(log_y):
    import warnings

    from statsmodels.tools.sm_exceptions import ConvergenceWarning
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fitted = ExponentialSmoothing(log_y, trend="add", damped_trend=True,
                                      initialization_method="estimated").fit()
        forecast = float(np.exp(fitted.forecast(1)[0]))
    if any(issubclass(w.category, ConvergenceWarning) for w in caught):
        raise RuntimeError("no_convergence")
    return forecast


def predict(history, exog=None):
    """Forecast the month after `history` (a Series of complete-month ADP with a monthly PeriodIndex).

    Returns {model: (forecast, fit_status)}. Fits use `history` only; `exog` is an optional Series of
    complete-month arrests, of which only values strictly before the target month are read.
    """
    y = np.asarray(history, dtype=float)
    if len(y) < 13 or not np.isfinite(y).all() or (y <= 0).any():
        raise ValueError("Prediction needs at least 13 finite, positive past months")
    log_y, target = np.log(y), history.index[-1] + 1
    out = {m: (v, "ok") for m, v in predict_baselines(y).items()}

    def attempt(model, function, available=True):
        if not available:
            out[model] = (np.nan, "not_applicable")
            return
        try:
            value = function()
            out[model] = (value, "ok") if np.isfinite(value) else (np.nan, "nonfinite")
        except RuntimeError as error:
            out[model] = (np.nan, str(error))
        except (ValueError, np.linalg.LinAlgError) as error:
            out[model] = (np.nan, f"fit_failed: {error}")

    attempt("log_ar1", lambda: _ols_forecast(*_lag1_design(log_y), np.array([1.0, log_y[-1]])))

    def seasonal():
        dummies = _month_dummies(list(history.index))
        design, response = _lag1_design(log_y, dummies)
        return _ols_forecast(design, response, np.concatenate(
            [[1.0, log_y[-1]], _month_dummies([target])[0]]))

    attempt("log_ar1_seasonal", seasonal, len(y) >= 36)
    attempt("ets_damped", lambda: _fit_ets(log_y))

    def with_arrests():
        # Arrests at t-1 predict ADP at t, so nothing at or after the target month is read.
        values = np.log(exog.reindex(history.index).to_numpy(dtype=float))
        if not np.isfinite(values).all():
            raise RuntimeError("missing_exog")
        design = np.column_stack([np.ones(len(y) - 1), log_y[:-1], values[:-1]])
        return _ols_forecast(design, log_y[1:], np.array([1.0, log_y[-1], values[-1]]))

    attempt("log_ar1_arrests", with_arrests, exog is not None)
    return out


def backtest(series, min_train, exog=None, models=MODELS):
    """One forecast per origin from an expanding training window; error = forecast - actual.

    Failed or inapplicable fits keep their row with a NaN forecast and a `fit_status`.
    """
    y = complete_months(series)
    if min_train < 13 or len(y) <= min_train:
        raise ValueError("Backtesting needs at least 13 training months and one later complete month")
    source = series["source"].iloc[0]
    rows = []
    for stop in range(min_train, len(y)):
        history = y.iloc[:stop]
        results = predict(history, exog)
        for model in models:
            forecast, status = results[model]
            rows.append({"source": source, "month": str(y.index[stop]), "train_end": str(history.index[-1]),
                         "n_train": len(history), "model": model, "actual": y.iloc[stop],
                         "forecast": forecast, "fit_status": status})
    out = pd.DataFrame(rows)
    out["error"] = out["forecast"] - out["actual"]
    return out


def project(series, exog=None, models=MODELS):
    """Forecast for the next month after the last complete month, with the training window stated."""
    y = complete_months(series)
    results = predict(y, exog)
    return pd.DataFrame([{"source": series["source"].iloc[0], "month": str(y.index[-1] + 1),
                          "train_start": str(y.index[0]), "train_end": str(y.index[-1]), "n_train": len(y),
                          "model": m, "forecast": results[m][0], "fit_status": results[m][1]} for m in models])


PERIODS = {"full": (None, None), "pre_covid": (None, "2020-02"), "covid": ("2020-03", "2021-12"),
           "2022_2024": ("2022-01", "2024-12"), "2025_on": ("2025-01", None)}


def prediction_intervals(predictions, levels=(0.8, 0.95), min_errors=12):
    """Add `lower{pct}`/`upper{pct}` columns from empirical quantiles of earlier log errors.

    For each source and model, the interval for month m uses log(actual/forecast) from months strictly
    before m only. Bounds are missing until `min_errors` earlier errors exist.
    """
    out = predictions.copy()
    for level in levels:
        out[f"lower{round(level * 100)}"] = np.nan
        out[f"upper{round(level * 100)}"] = np.nan
    for _, group in out.groupby(["source", "model"], sort=False):
        group = group.sort_values("month")
        log_error = np.log(group["actual"] / group["forecast"]).to_numpy()
        for position, index in enumerate(group.index):
            past = log_error[:position]
            past = past[np.isfinite(past)]
            if len(past) < min_errors:
                continue
            for level in levels:
                low, high = np.quantile(past, [(1 - level) / 2, (1 + level) / 2])
                pct = round(level * 100)
                out.loc[index, f"lower{pct}"] = group.at[index, "forecast"] * np.exp(low)
                out.loc[index, f"upper{pct}"] = group.at[index, "forecast"] * np.exp(high)
    return out


def _in_period(months, period):
    start, end = PERIODS[period]
    keep = pd.Series(True, index=months.index)
    if start:
        keep &= months >= start
    if end:
        keep &= months <= end
    return keep


def _interval_stats(g, pct, alpha):
    ok = g[f"lower{pct}"].notna()
    if not ok.any():
        return np.nan, np.nan, np.nan
    y, lo, hi = g.loc[ok, "actual"], g.loc[ok, f"lower{pct}"], g.loc[ok, f"upper{pct}"]
    covered = ((y >= lo) & (y <= hi)).mean()
    score = (hi - lo) + 2 / alpha * (lo - y).clip(lower=0) + 2 / alpha * (y - hi).clip(lower=0)
    return covered, (hi - lo).mean(), score.mean()


def evaluate(predictions):
    """Accuracy, bias and interval metrics per source, model and period (rows with a forecast only).

    MASE is the model's MAE divided by last_month's MAE over the same months. Requires interval columns.
    """
    rows = []
    for source, by_source in predictions.groupby("source", sort=False):
        for period in PERIODS:
            block = by_source[_in_period(by_source["month"], period)].dropna(subset=["forecast"])
            base = block[block.model == "last_month"].set_index("month")["error"].abs()
            for model, g in block.groupby("model", sort=False):
                mae = g["error"].abs().mean()
                last_mae = base.reindex(g["month"]).mean()
                c80, w80, _ = _interval_stats(g, 80, 0.2)
                c95, w95, score95 = _interval_stats(g, 95, 0.05)
                rows.append({
                    "source": source, "model": model, "period": period, "n_forecasts": len(g), "mae": mae,
                    "rmse": np.sqrt((g["error"] ** 2).mean()),
                    "mape": (g["error"].abs() / g["actual"]).mean() * 100,
                    "mase_vs_last_month": mae / last_mae if last_mae else np.nan,
                    "mean_error": g["error"].mean(), "pct_over": (g["error"] > 0).mean() * 100,
                    "cover80": c80, "cover95": c95, "width80": w80, "width95": w95,
                    "interval_score95": score95})
    return pd.DataFrame(rows)


def beats_last_month(table):
    """For every source and period, the models whose MAE is below last_month's (descriptive only)."""
    rows = []
    for (source, period), g in table.groupby(["source", "period"], sort=False):
        last = g.loc[g.model == "last_month", "mae"].iloc[0]
        better = g[(g.model != "last_month") & (g.mae < last)].sort_values("mae")
        rows.append((source, period, int(g["n_forecasts"].iloc[0]), list(better.model)))
    return rows


def load_published():
    d = pd.read_csv(HERE / "data" / "ice_published_adp_monthly.csv")
    out = pd.DataFrame({"month": pd.to_datetime(d["month"]).dt.strftime("%Y-%m"), "adp": d["adp"],
                        "partial_month": False, "source": "published"})
    # The latest file was pulled mid-month, so its final month does not cover the whole month.
    last_end = pd.Timestamp(d["month"].iloc[-1]) + pd.offsets.MonthEnd(0)
    out.loc[out.index[-1], "partial_month"] = bool(pd.Timestamp(d["pull_date"].iloc[-1]) < last_end)
    return out


def load_records():
    d = pd.read_csv(RESULTS / "monthly_adp_records.csv")
    d = d[d["burn_in_ok"]]
    return pd.DataFrame({"month": d["month"], "adp": d["adp"], "partial_month": d["partial_month"],
                         "source": "records"})


def load_arrests():
    from forecast_arrests import complete_months as complete_arrests
    counts = pd.read_csv(RESULTS / "monthly_arrests.csv")
    return complete_arrests(counts)


def main():
    arrests = load_arrests()
    runs = [("published", load_published(), None), ("records", load_records(), arrests)]
    backtests, projections = [], []
    for name, series, exog in runs:
        backtests.append(backtest(series, MIN_TRAIN[name], exog))
        projections.append(project(series, exog))
    predictions = prediction_intervals(pd.concat(backtests, ignore_index=True))
    table = evaluate(predictions)
    predictions.round(4).to_csv(RESULTS / "adp_forecast_backtest.csv", index=False)
    pd.concat(projections).round(4).to_csv(RESULTS / "adp_forecast_projection.csv", index=False)
    table.round(4).to_csv(RESULTS / "adp_forecast_metrics.csv", index=False)
    print("Models with lower MAE than last_month (descriptive; few, serially dependent origins):")
    for source, period, n, better in beats_last_month(table):
        print(f"  {source:9s} {period:10s} n={n:3d}: {', '.join(better) if better else 'none'}")


if __name__ == "__main__":
    main()
