"""
Pure, unit-tested helpers for stint intervals, average daily population (ADP) and annualization.

Scripts 01 and 02 both import these so the interval rules live in one place.
Windows are half-open: [w0, w1). A stint [start, end) contributes the overlap with the window in days.
"""
import numpy as np
import pandas as pd

OPEN_STINT_START = pd.Timestamp("2025-01-01")  # open stints are only censored if booked in on/after this date


def build_intervals(df, cutoff, open_from=OPEN_STINT_START, *, open_policy="primary"):
    """Return `df` with `start`, `end` and `interval_status` columns.

    end = book_out, else the stay's book-out, else (for stints booked in on/after `open_from`)
    the day after `cutoff` (right-censoring). Older open stints stay NaT and are excluded.
    Stints whose end is before their start are marked 'invalid_negative' and their end set to NaT.
    Sensitivity policies `censor_all` and `exclude_all` override only the treatment of unknown ends.
    """
    if open_policy not in {"primary", "censor_all", "exclude_all"}:
        raise ValueError(f"Unknown open-record policy: {open_policy}")
    df = df.copy()
    end = df["book_out_date_time"].fillna(df["stay_book_out_date_time"])
    open_recent = end.isna() & (df["book_in_date_time"] >= open_from)
    if open_policy == "censor_all":
        open_recent = end.isna() & df["book_in_date_time"].notna()
    elif open_policy == "exclude_all":
        open_recent = pd.Series(False, index=df.index)
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


def censoring_sensitivity(df, cutoff, periods):
    """National ADP under three unknown-end policies, holding all other rules fixed."""
    dates = df[["book_in_date_time", "book_out_date_time", "stay_book_out_date_time"]]
    rows = []
    primary = {}
    for specification in ["primary", "censor_all", "exclude_all"]:
        intervals = build_intervals(dates, cutoff, open_policy=specification)
        for period, (w0, w1) in periods.items():
            population = adp(intervals, w0, w1)
            if specification == "primary":
                primary[period] = population
            difference = population - primary[period]
            rows.append({
                "specification": specification, "period": period,
                "days": window_days(w0, w1), "adp": population,
                "adp_difference_from_primary": difference,
                "pct_difference_from_primary": (
                    difference / primary[period] * 100 if primary[period] else np.nan),
            })
    return pd.DataFrame(rows)


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
    return bed.groupby([d[k] for k in keys], dropna=False).sum() / days


def annualize(count, w0, w1):
    """Scale a count observed in [w0, w1) to a 365.25-day year using the window's actual length."""
    return count / (window_days(w0, w1) / 365.25)


def interval_diagnostics(df):
    """Per-record transfer/overlap flags for the output of `build_intervals()`.

    `df` needs stay_ID, unique_identifier, book_in_date_time, book_out_date_time, start, end.
    Adds `stay_end_fallback`, `overlaps_next_stint`, `overlap_days` (this interval's end past the
    next stint's start in the same stay) and `concurrent_stay` (another stay of the same person
    overlaps this interval). Row order and index are preserved.
    """
    out = df.copy()
    out["stay_end_fallback"] = out["book_out_date_time"].isna() & out["end"].notna() & (
        out["interval_status"] == "closed")
    order = out.sort_values(["stay_ID", "book_in_date_time"], kind="stable")
    next_start = order.groupby("stay_ID", sort=False)["book_in_date_time"].shift(-1)
    over = (order["end"] - next_start).dt.total_seconds() / 86400
    over = over.where(order["end"].notna() & next_start.notna(), 0).clip(lower=0)
    out["overlap_days"] = over.reindex(out.index)
    out["overlaps_next_stint"] = out["overlap_days"] > 0

    out["concurrent_stay"] = False
    valid = out[out["end"].notna() & out["start"].notna()]
    stay = valid.groupby(["unique_identifier", "stay_ID"], sort=False).agg(s=("start", "min"), e=("end", "max"))
    stay = stay.reset_index().sort_values(["unique_identifier", "s"], kind="stable")
    prev_max_end = stay.groupby("unique_identifier", sort=False)["e"].transform(
        lambda x: x.shift().cummax())
    next_start_s = stay.groupby("unique_identifier", sort=False)["s"].shift(-1)
    stay["flag"] = (stay["s"] < prev_max_end) | (stay["e"] > next_start_s)
    flagged = set(stay.loc[stay["flag"], "stay_ID"])
    out.loc[valid.index, "concurrent_stay"] = valid["stay_ID"].isin(flagged)
    return out
