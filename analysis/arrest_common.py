"""Shared arrest cohort filters and monthly output used by the report and EDA."""
import pandas as pd

ARREST_START = pd.Timestamp("2023-01-01")
ARREST_SPLIT = pd.Timestamp("2025-01-01")
ARREST_END = pd.Timestamp("2026-03-11")  # exclusive: March 11 has only one record
ARREST_DAYS = {"old": (ARREST_SPLIT - ARREST_START).days, "new": (ARREST_END - ARREST_SPLIT).days}


def load_arrests(columns=None):
    from data_common import read_source
    return read_source("arrests", columns)


def clean_arrests(data):
    data = data.loc[~data.duplicate_drop_row.fillna(False).astype(bool)].copy()
    data["date"] = pd.to_datetime(data.apprehension_date, errors="coerce")
    missing = data.date.isna().sum()
    outside = ((data.date < ARREST_START) | (data.date >= ARREST_END)).sum()
    print(f"Arrest dates: {missing} missing; {outside} outside [{ARREST_START.date()}, {ARREST_END.date()})")
    data = data.loc[data.date.ge(ARREST_START) & data.date.lt(ARREST_END)].copy()
    data["era"] = data.date.ge(ARREST_SPLIT).map({False: "old", True: "new"})
    return data


def monthly_arrests(data):
    months = pd.period_range(ARREST_START, ARREST_END - pd.Timedelta(days=1), freq="M")
    counts = data.groupby(data.date.dt.to_period("M")).size().reindex(months, fill_value=0)
    days_observed = [(min(month.end_time.normalize() + pd.Timedelta(days=1), ARREST_END)
                      - month.start_time.normalize()).days for month in months]
    return pd.DataFrame({"month": months.astype(str), "arrests": counts.values,
                         "days_observed": days_observed,
                         "partial_month": months == ARREST_END.to_period("M")})


def location_breakdown(data):
    """Joint state/year/location counts from the cleaned arrest cohort."""
    data = data.assign(
        year=data.date.dt.year,
        state=data.apprehension_state_filled_in.fillna(
            data.apprehension_state_original).fillna("Unknown"),
        aor=data.apprehension_aor.fillna("Unknown"),
        landmark=data.apprehension_site_landmark.str.strip().str.upper().fillna("Unknown"),
    )
    long = data.melt(id_vars=["state", "year"], value_vars=["aor", "landmark"],
                     var_name="dimension", value_name="location")
    return long.groupby(["state", "year", "dimension", "location"]).size().rename(
        "arrests").reset_index()
