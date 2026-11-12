"""Stage 3: transfer-safe monthly ADP from stint records, reconciled with the published series.

Writes analysis/results/monthly_adp_records.csv and analysis/results/adp_series_reconciliation.csv.
Requires the raw stints (Git LFS, or ICE_DATA_DIR pointing at parquet files).
"""
import os
import sys

import numpy as np
import pandas as pd

# Make sibling modules importable when the script is run from another folder.
sys.path.insert(0, os.path.dirname(__file__))
# The noqa markers silence the linter warning about imports placed after code.
from audit_detention_intervals import load_stints  # noqa: E402
from geo_common import CUTOFF, RESULTS  # noqa: E402
# Interval builder, monthly ADP calculator, and the fix that keeps transfers from double-counting days.
from ice_lib import build_intervals, monthly_adp, transfer_safe_intervals  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# Earlier months undercount people who were booked in before the data starts, so they're flagged.
FIRST_TRUSTED_MONTH = "2023-01"  # from analysis/ADP_DATA_AUDIT.md burn-in curve


def monthly_series(st, cutoff, first, last):
    # Monthly ADP under the main method plus three alternatives, side by side.
    out = {}
    # (column name, how to treat stints still open at the cutoff, whether to apply the transfer fix).
    # "adp" is the main series; "adp_current_method" is the same without the transfer fix;
    # the other two bracket how open stints are handled.
    for label, policy, safe in [("adp", "primary", True), ("adp_current_method", "primary", False),
                                ("adp_censor_all", "censor_all", True), ("adp_exclude_all", "exclude_all", True)]:
        iv = build_intervals(st, cutoff, open_policy=policy)
        if safe:
            iv = transfer_safe_intervals(iv)
        out[label] = monthly_adp(iv, first, last, cutoff).set_index("month")
    # Start from the main series, keeping its coverage columns.
    base = out["adp"][["adp", "days_observed", "partial_month"]].copy()
    # Add each alternative series as its own column, aligned by month.
    for label in ["adp_current_method", "adp_censor_all", "adp_exclude_all"]:
        base[label] = out[label]["adp"]
    # Mark months after the burn-in period (string comparison works for "YYYY-MM" labels).
    base["burn_in_ok"] = base.index >= FIRST_TRUSTED_MONTH
    return base.reset_index()[["month", "adp", "adp_current_method", "adp_censor_all", "adp_exclude_all",
                               "days_observed", "partial_month", "burn_in_ok"]]


def reconcile(records, published):
    # Compare record-based monthly ADP with ICE's published monthly ADP.
    # Normalize published months to "YYYY-MM" strings so they match the records.
    p = published.assign(month=pd.to_datetime(published["month"]).dt.strftime("%Y-%m"))
    # Only one vintage per month exists in the monthly table, so first and latest coincide.
    p = p[["month", "adp"]].rename(columns={"adp": "adp_published_latest"}).assign(
        adp_published_first=lambda x: x["adp_published_latest"])
    # Trusted, complete months only; the inner merge keeps months present in both series.
    r = records[records["burn_in_ok"] & ~records["partial_month"]][["month", "adp"]].rename(
        columns={"adp": "adp_records"}).merge(p, on="month")
    # Gap between the two series in people, in percent, and as a ratio.
    r["difference"] = r["adp_records"] - r["adp_published_latest"]
    r["pct_difference"] = r["difference"] / r["adp_published_latest"] * 100
    r["ratio"] = r["adp_records"] / r["adp_published_latest"]
    return r


def main():
    st = load_stints()
    # Start at the month of the earliest book-in and run through the cutoff month.
    first = st["book_in_date_time"].min().to_period("M")
    records = monthly_series(st, CUTOFF, first, pd.Timestamp(CUTOFF).to_period("M"))
    records.round(4).to_csv(os.path.join(RESULTS, "monthly_adp_records.csv"), index=False)
    # ICE's published monthly ADP, kept in the repo.
    published = pd.read_csv(os.path.join(HERE, "data", "ice_published_adp_monthly.csv"))
    rec = reconcile(records, published).round(4)
    rec.to_csv(os.path.join(RESULTS, "adp_series_reconciliation.csv"), index=False)
    # Month-to-month changes in each series, to check whether they move together.
    d = rec["adp_records"].diff().iloc[1:]
    dp = rec["adp_published_latest"].diff().iloc[1:]
    # Linear trend in the percent gap per month; a nonzero slope means the gap is drifting.
    # (Uses row position, so it assumes no months are missing between rows.)
    slope = np.polyfit(np.arange(len(rec)), rec["pct_difference"], 1)[0]
    # Summary of the gap in people.
    print(f"months={len(rec)} mean_diff={rec['difference'].mean():.1f} median_diff={rec['difference'].median():.1f} "
          f"range=({rec['difference'].min():.1f}, {rec['difference'].max():.1f})")
    # Summary of the gap in percent, its trend, and how closely monthly changes line up.
    print(f"mean_pct={rec['pct_difference'].mean():.2f} median_pct={rec['pct_difference'].median():.2f} "
          f"pct_trend_per_month={slope:.3f} corr_monthly_changes={d.corr(dp):.3f}")
    print(rec.to_string())


if __name__ == "__main__":
    main()
