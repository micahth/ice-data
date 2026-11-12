"""Pure helpers for the published monthly ICE detention ADP series (Deportation Data Project)."""
import numpy as np
import pandas as pd


def fiscal_year(month):
    """US federal fiscal year (October starts the next fiscal year)."""
    month = pd.Timestamp(month)
    # True counts as 1, so October-December roll into the next fiscal year.
    return month.year + (month.month >= 10)


def reduce_monthly(monthly):
    """Total-population monthly ADP, with ICE and CBP components, from DDP's monthly agency table."""
    # Keep the all-criminality rows; the table also breaks ADP down by criminality.
    d = monthly[monthly["criminality"] == "Total"].copy()
    # Normalize every date to the first of its month.
    d["month"] = pd.to_datetime(d["date"]).dt.to_period("M").dt.to_timestamp()
    # One row per month, one column per agency (Total, ICE, CBP).
    # pivot() raises if a month appears twice for the same agency.
    wide = d.pivot(index="month", columns="agency", values="adp")
    # Fiscal year and file/pull dates, taken from the Total rows.
    meta = d[d["agency"] == "Total"].set_index("month")[["fiscal_year", "file_date", "pull_date"]]
    # Raises KeyError if the table has no ICE or CBP rows.
    out = pd.DataFrame({"adp": wide["Total"], "ice_adp": wide["ICE"], "cbp_adp": wide["CBP"]}).join(meta)
    # Record where each value came from.
    out["source_table"] = "adp-and-stay-length-by-agency-monthly"
    # These values are read directly, not derived from fiscal-year-to-date averages.
    out["is_fytd_derived"] = False
    out["vintage_rank"] = 1  # the monthly table holds one vintage per month
    out = out.reset_index().sort_values("month")
    return out[["month", "adp", "ice_adp", "cbp_adp", "source_table", "fiscal_year", "file_date", "pull_date",
                "is_fytd_derived", "vintage_rank"]]


def derive_monthly_from_fytd(ytd_prev, days_prev, ytd_cur, days_cur):
    """Exact monthly ADP from two fiscal-year-to-date averages taken at consecutive month ends.

    `days_*` are the days elapsed in the fiscal year at each snapshot.
    """
    # Average x days = total detention-days. The difference between snapshots is the
    # month's detention-days; divide by the month's length to get its average.
    return (ytd_cur * days_cur - ytd_prev * days_prev) / (days_cur - days_prev)


def validate_monthly(series, documented_gaps=()):
    """Return a list of problems with a monthly ADP frame (`month`, `adp`, `fiscal_year`); empty means valid."""
    problems = []
    months = pd.to_datetime(series["month"])
    # Each month should appear once.
    if months.duplicated().any():
        problems.append("duplicate months")
    # Months should be stored as the first day of the month.
    if not (months.dt.day == 1).all():
        problems.append("months are not month starts")
    # Every month between the first and last should be present, apart from known gaps.
    expected = pd.date_range(months.min(), months.max(), freq="MS").difference(pd.to_datetime(list(documented_gaps)))
    missing = expected.difference(months)
    if len(missing):
        problems.append(f"missing months: {[str(m.date()) for m in missing]}")
    # ADP must be a real, positive number (no NaN, infinity, zero or negatives).
    if not np.isfinite(series["adp"]).all() or not (series["adp"] > 0).all():
        problems.append("adp must be finite and greater than 0")
    # Each row's stored fiscal year must match the one implied by its month.
    wrong = [str(m.date()) for m, fy in zip(months, series["fiscal_year"]) if fiscal_year(m) != fy]
    if wrong:
        problems.append(f"fiscal_year disagrees with October-start rule: {wrong}")
    return problems


def fytd_check(series, fytd, tolerance=0.01):
    """Compare day-weighted mean of monthly ADP with the latest published FYTD ADP for each full fiscal year.

    `fytd` has fiscal_year, file_date and adp_fy_ytd. Returns a frame with relative differences and `ok`.
    Fiscal years missing any of their 12 months are skipped.
    Revised FYTD values can differ from monthly ones, so a failure is reported, not raised.
    """
    s = series.assign(month=pd.to_datetime(series["month"]))
    # Weight each month by its length, so 31-day months count more than February.
    s["days"] = s["month"].dt.days_in_month
    rows = []
    for fy, g in s.groupby("fiscal_year"):
        # The 12 month starts in this fiscal year: October of the prior year through September.
        # int() guards against fiscal years read from CSV as floats (e.g. 2024.0).
        full_year = pd.date_range(f"{int(fy) - 1}-10-01", f"{int(fy)}-09-01", freq="MS")
        # Skip partial fiscal years; their average wouldn't cover the same period as a full-year FYTD figure.
        if not full_year.isin(g["month"]).all():
            continue
        # Most recent published FYTD value for this fiscal year.
        latest = fytd[fytd["fiscal_year"] == fy].sort_values("file_date")
        # Skip fiscal years with no published FYTD figure.
        if latest.empty:
            continue
        published = latest.iloc[-1]["adp_fy_ytd"]
        # Day-weighted average of the monthly values, which should equal the FYTD average.
        recomputed = (g["adp"] * g["days"]).sum() / g["days"].sum()
        rel = recomputed / published - 1
        # Within 1% (by default) counts as agreeing.
        rows.append({"fiscal_year": fy, "months": len(g), "recomputed_ytd": recomputed,
                     "published_ytd": published, "rel_diff": rel, "ok": abs(rel) <= tolerance})
    return pd.DataFrame(rows)


def fytd_revisions(fytd):
    """First and latest published FYTD ADP (Total/Total) per fiscal year and the percent revision."""
    # Expects fytd already filtered to Total/Total rows by the caller.
    rows = []
    # Sorting by file date makes the first row the earliest vintage and the last row the latest.
    for fy, g in fytd.sort_values("file_date").groupby("fiscal_year"):
        first, last = g.iloc[0], g.iloc[-1]
        # How much the published figure moved between its first and latest release.
        rows.append({"fiscal_year": fy, "vintages": len(g), "first_file_date": first["file_date"],
                     "first_adp_fy_ytd": first["adp_fy_ytd"], "latest_file_date": last["file_date"],
                     "latest_adp_fy_ytd": last["adp_fy_ytd"],
                     "pct_revision": (last["adp_fy_ytd"] / first["adp_fy_ytd"] - 1) * 100})
    return pd.DataFrame(rows)
