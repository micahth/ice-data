"""Pure helpers for the published monthly ICE detention ADP series (Deportation Data Project)."""
import numpy as np
import pandas as pd


def fiscal_year(month):
    """US federal fiscal year (October starts the next fiscal year)."""
    month = pd.Timestamp(month)
    return month.year + (month.month >= 10)


def reduce_monthly(monthly):
    """Total-population monthly ADP, with ICE and CBP components, from DDP's monthly agency table."""
    d = monthly[monthly["criminality"] == "Total"].copy()
    d["month"] = pd.to_datetime(d["date"]).dt.to_period("M").dt.to_timestamp()
    wide = d.pivot(index="month", columns="agency", values="adp")
    meta = d[d["agency"] == "Total"].set_index("month")[["fiscal_year", "file_date", "pull_date"]]
    out = pd.DataFrame({"adp": wide["Total"], "ice_adp": wide["ICE"], "cbp_adp": wide["CBP"]}).join(meta)
    out["source_table"] = "adp-and-stay-length-by-agency-monthly"
    out["is_fytd_derived"] = False
    out["vintage_rank"] = 1  # the monthly table holds one vintage per month
    out = out.reset_index().sort_values("month")
    return out[["month", "adp", "ice_adp", "cbp_adp", "source_table", "fiscal_year", "file_date", "pull_date",
                "is_fytd_derived", "vintage_rank"]]


def derive_monthly_from_fytd(ytd_prev, days_prev, ytd_cur, days_cur):
    """Exact monthly ADP from two fiscal-year-to-date averages taken at consecutive month ends.

    `days_*` are the days elapsed in the fiscal year at each snapshot.
    """
    return (ytd_cur * days_cur - ytd_prev * days_prev) / (days_cur - days_prev)


def validate_monthly(series, documented_gaps=()):
    """Return a list of problems with a monthly ADP frame (`month`, `adp`, `fiscal_year`); empty means valid."""
    problems = []
    months = pd.to_datetime(series["month"])
    if months.duplicated().any():
        problems.append("duplicate months")
    if not (months.dt.day == 1).all():
        problems.append("months are not month starts")
    expected = pd.date_range(months.min(), months.max(), freq="MS").difference(pd.to_datetime(list(documented_gaps)))
    missing = expected.difference(months)
    if len(missing):
        problems.append(f"missing months: {[str(m.date()) for m in missing]}")
    if not np.isfinite(series["adp"]).all() or not (series["adp"] > 0).all():
        problems.append("adp must be finite and greater than 0")
    wrong = [str(m.date()) for m, fy in zip(months, series["fiscal_year"]) if fiscal_year(m) != fy]
    if wrong:
        problems.append(f"fiscal_year disagrees with October-start rule: {wrong}")
    return problems


def fytd_check(series, fytd, tolerance=0.01):
    """Compare day-weighted mean of monthly ADP with the latest published FYTD ADP for each full fiscal year.

    `fytd` has fiscal_year, file_date and adp_fy_ytd. Returns a frame with relative differences and `ok`.
    Revised FYTD values can differ from monthly ones, so a failure is reported, not raised.
    """
    s = series.assign(month=pd.to_datetime(series["month"]))
    s["days"] = s["month"].dt.days_in_month
    rows = []
    for fy, g in s.groupby("fiscal_year"):
        latest = fytd[fytd["fiscal_year"] == fy].sort_values("file_date")
        if latest.empty:
            continue
        published = latest.iloc[-1]["adp_fy_ytd"]
        recomputed = (g["adp"] * g["days"]).sum() / g["days"].sum()
        rel = recomputed / published - 1
        rows.append({"fiscal_year": fy, "months": len(g), "recomputed_ytd": recomputed,
                     "published_ytd": published, "rel_diff": rel, "ok": abs(rel) <= tolerance})
    return pd.DataFrame(rows)


def fytd_revisions(fytd):
    """First and latest published FYTD ADP (Total/Total) per fiscal year and the percent revision."""
    rows = []
    for fy, g in fytd.sort_values("file_date").groupby("fiscal_year"):
        first, last = g.iloc[0], g.iloc[-1]
        rows.append({"fiscal_year": fy, "vintages": len(g), "first_file_date": first["file_date"],
                     "first_adp_fy_ytd": first["adp_fy_ytd"], "latest_file_date": last["file_date"],
                     "latest_adp_fy_ytd": last["adp_fy_ytd"],
                     "pct_revision": (last["adp_fy_ytd"] / first["adp_fy_ytd"] - 1) * 100})
    return pd.DataFrame(rows)
