"""Stage 3: transfer-safe monthly ADP from stint records, reconciled with the published series.

Writes analysis/results/monthly_adp_records.csv and analysis/results/adp_series_reconciliation.csv.
Requires the raw stints (Git LFS, or ICE_DATA_DIR pointing at parquet files).
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from audit_detention_intervals import load_stints  # noqa: E402
from geo_common import CUTOFF, RESULTS  # noqa: E402
from ice_lib import build_intervals, monthly_adp, transfer_safe_intervals  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIRST_TRUSTED_MONTH = "2023-01"  # from analysis/ADP_DATA_AUDIT.md burn-in curve


def monthly_series(st, cutoff, first, last):
    out = {}
    for label, policy, safe in [("adp", "primary", True), ("adp_current_method", "primary", False),
                                ("adp_censor_all", "censor_all", True), ("adp_exclude_all", "exclude_all", True)]:
        iv = build_intervals(st, cutoff, open_policy=policy)
        if safe:
            iv = transfer_safe_intervals(iv)
        out[label] = monthly_adp(iv, first, last, cutoff).set_index("month")
    base = out["adp"][["adp", "days_observed", "partial_month"]].copy()
    for label in ["adp_current_method", "adp_censor_all", "adp_exclude_all"]:
        base[label] = out[label]["adp"]
    base["burn_in_ok"] = base.index >= FIRST_TRUSTED_MONTH
    return base.reset_index()[["month", "adp", "adp_current_method", "adp_censor_all", "adp_exclude_all",
                               "days_observed", "partial_month", "burn_in_ok"]]


def reconcile(records, published):
    p = published.assign(month=pd.to_datetime(published["month"]).dt.strftime("%Y-%m"))
    # Only one vintage per month exists in the monthly table, so first and latest coincide.
    p = p[["month", "adp"]].rename(columns={"adp": "adp_published_latest"}).assign(
        adp_published_first=lambda x: x["adp_published_latest"])
    r = records[records["burn_in_ok"] & ~records["partial_month"]][["month", "adp"]].rename(
        columns={"adp": "adp_records"}).merge(p, on="month")
    r["difference"] = r["adp_records"] - r["adp_published_latest"]
    r["pct_difference"] = r["difference"] / r["adp_published_latest"] * 100
    r["ratio"] = r["adp_records"] / r["adp_published_latest"]
    return r


def main():
    st = load_stints()
    first = st["book_in_date_time"].min().to_period("M")
    records = monthly_series(st, CUTOFF, first, pd.Timestamp(CUTOFF).to_period("M"))
    records.round(4).to_csv(os.path.join(RESULTS, "monthly_adp_records.csv"), index=False)
    published = pd.read_csv(os.path.join(HERE, "data", "ice_published_adp_monthly.csv"))
    rec = reconcile(records, published).round(4)
    rec.to_csv(os.path.join(RESULTS, "adp_series_reconciliation.csv"), index=False)
    d = rec["adp_records"].diff().iloc[1:]
    dp = rec["adp_published_latest"].diff().iloc[1:]
    slope = np.polyfit(np.arange(len(rec)), rec["pct_difference"], 1)[0]
    print(f"months={len(rec)} mean_diff={rec['difference'].mean():.1f} median_diff={rec['difference'].median():.1f} "
          f"range=({rec['difference'].min():.1f}, {rec['difference'].max():.1f})")
    print(f"mean_pct={rec['pct_difference'].mean():.2f} median_pct={rec['pct_difference'].median():.2f} "
          f"pct_trend_per_month={slope:.3f} corr_monthly_changes={d.corr(dp):.3f}")
    print(rec.to_string())


if __name__ == "__main__":
    main()
