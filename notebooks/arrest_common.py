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
    return pd.DataFrame({"month": months.astype(str), "arrests": counts.values,
                         "partial_month": months == ARREST_END.to_period("M")})
