"""
Pure, unit-tested helpers for stint intervals, average daily population (ADP) and annualization.

Scripts 05 and 06 both import these so the cutoff and interval rules live in one place.
Windows are half-open: [w0, w1). A stint [start, end) contributes the overlap with the window in days.
"""
import numpy as np
import pandas as pd

OPEN_STINT_START = pd.Timestamp("2025-01-01")  # open stints are only censored if booked in on/after this date


def build_intervals(df, cutoff, open_from=OPEN_STINT_START):
    """Return `df` with `start`, `end` and `status` columns.

    end = book_out, else the stay's book-out, else (for stints booked in on/after `open_from`)
    the day after `cutoff` (right-censoring). Older open stints stay NaT and are excluded.
    Stints whose end is before their start are marked 'invalid_negative' and their end set to NaT.
    """
    df = df.copy()
    end = df["book_out_date_time"].fillna(df["stay_book_out_date_time"])
    open_recent = end.isna() & (df["book_in_date_time"] >= open_from)
    end = end.mask(open_recent, cutoff + pd.Timedelta(days=1))
    start = df["book_in_date_time"]
    status = pd.Series("closed", index=df.index)
    status[end.isna()] = "open_excluded"
    status[open_recent] = "open_censored"
    status[start.isna()] = "missing_book_in"
    negative = end.notna() & start.notna() & (end < start)
    status[negative] = "invalid_negative"
    end = end.mask(negative | start.isna())
    df["start"], df["end"], df["interval_status"] = start, end, status
    return df


def overlap_days(start, end, w0, w1):
    """Days of [start, end) falling inside [w0, w1); zero when there is no overlap."""
    lo = start.clip(lower=w0)
    hi = end.clip(upper=w1)
    return ((hi - lo).dt.total_seconds() / 86400).clip(lower=0)


def window_days(w0, w1):
    """Actual length of the window in days (used for ADP and annualization)."""
    return (w1 - w0).total_seconds() / 86400


def adp(df, w0, w1, keys=None):
    """Average daily population = overlapped bed-days / actual window days. `df` needs start/end."""
    d = df[df["end"].notna() & df["start"].notna() & (df["start"] < w1) & (df["end"] > w0)]
    bed = overlap_days(d["start"], d["end"], w0, w1)
    days = window_days(w0, w1)
    if not keys:
        return bed.sum() / days
    return bed.groupby([d[k] for k in keys]).sum() / days


def annualize(count, w0, w1):
    """Scale a count observed in [w0, w1) to a 365.25-day year using the window's actual length."""
    return count / (window_days(w0, w1) / 365.25)
