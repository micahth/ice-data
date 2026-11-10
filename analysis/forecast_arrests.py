"""Expanding-window, one-month-ahead forecasts from complete monthly aggregates."""
from pathlib import Path

import numpy as np
import pandas as pd

RESULTS = Path(__file__).resolve().parent / "results"
MODELS = ("last_month", "seasonal_naive", "log_ar1")


def complete_months(monthly):
    data = monthly.copy()
    data.index = pd.PeriodIndex(data.month, freq="M")
    if data.empty or data.index.has_duplicates or not data.index.is_monotonic_increasing:
        raise ValueError("Forecast input requires unique, ordered months")
    if not data.index.equals(pd.period_range(data.index.min(), data.index.max(), freq="M")):
        raise ValueError("Forecast input must include every calendar month")
    if not data.partial_month.isin([True, False]).all() or data.partial_month.isna().any():
        raise ValueError("partial_month must be nonmissing booleans")
    if data.partial_month.iloc[:-1].any():
        raise ValueError("Only the final month may be partial")
    if not np.isfinite(data.arrests).all() or data.arrests.lt(0).any():
        raise ValueError("Monthly arrest counts must be finite and nonnegative")
    return data.loc[~data.partial_month, "arrests"].astype(float)


def predict(history):
    """Fit only the supplied past; log-AR(1) is a conditional-median projection."""
    counts = np.asarray(history, dtype=float)
    if len(counts) < 12 or not np.isfinite(counts).all() or (counts < 0).any():
        raise ValueError("Prediction requires at least 12 finite, nonnegative past counts")
    logged = np.log1p(counts)
    design = np.column_stack([np.ones(len(counts) - 1), logged[:-1]])
    parameters, _, rank, _ = np.linalg.lstsq(design, logged[1:], rcond=None)
    if rank != 2:
        raise ValueError("Log-AR(1) design is unidentified")
    projected = np.expm1(np.array([1.0, logged[-1]]) @ parameters)
    if not np.isfinite(projected):
        raise ValueError("Log-AR(1) projection is not finite")
    return {"last_month": counts[-1], "seasonal_naive": counts[-12],
            "log_ar1": max(0.0, projected)}


def backtest(monthly, min_train=24):
    counts = complete_months(monthly)
    if min_train < 12 or len(counts) <= min_train:
        raise ValueError("Backtesting requires at least 12 training months and one later complete month")
    rows = []
    for stop in range(min_train, len(counts)):
        history = counts.iloc[:stop]
        for model, forecast in predict(history).items():
            rows.append({"month": str(counts.index[stop]), "train_end": str(history.index[-1]),
                         "n_train": len(history), "model": model,
                         "actual": counts.iloc[stop], "forecast": forecast})
    predictions = pd.DataFrame(rows)
    predictions["error"] = predictions.forecast - predictions.actual
    metrics = pd.DataFrame([
        {"model": model, "n_forecasts": len(group), "mae": group.error.abs().mean(),
         "rmse": np.sqrt(np.mean(group.error ** 2))}
        for model, group in predictions.groupby("model", sort=False)
    ])
    projection = pd.DataFrame([
        {"month": str(counts.index[-1] + 1), "train_end": str(counts.index[-1]),
         "n_train": len(counts), "model": model, "forecast": forecast}
        for model, forecast in predict(counts).items()
    ])
    return predictions, metrics, projection


def main():
    predictions, metrics, projection = backtest(pd.read_csv(RESULTS / "monthly_arrests.csv"))
    predictions.round(4).to_csv(RESULTS / "arrest_forecast_backtest.csv", index=False)
    metrics.round(4).to_csv(RESULTS / "arrest_forecast_metrics.csv", index=False)
    projection.round(4).to_csv(RESULTS / "arrest_forecast_projection.csv", index=False)
    print(metrics.round(1).to_string(index=False))
    print("\nNext complete-month target (partial observations not used):")
    print(projection.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
