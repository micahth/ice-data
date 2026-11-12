"""Stage 1 audit: monthly interval diagnostics and transfer double counting.

Writes analysis/results/detention_interval_audit.csv. Does not alter any published result.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from data_common import read_source  # noqa: E402
from geo_common import CUTOFF, RESULTS  # noqa: E402
from ice_lib import adp, build_intervals, interval_diagnostics, overlap_days, window_days  # noqa: E402

COLUMNS = ["book_in_date_time", "book_out_date_time", "stay_book_out_date_time", "unique_identifier",
           "stay_ID", "duplicate_drop_row"]


def load_stints():
    st = read_source("detention-stints", COLUMNS)
    st = st[~st.duplicate_drop_row.fillna(False).astype(bool)].drop(columns="duplicate_drop_row")
    for c in COLUMNS[:3]:
        st[c] = pd.to_datetime(st[c], utc=True, errors="coerce").dt.tz_localize(None)
    return st


def clip_to_next_stint(d):
    """Copy of `d` whose end is capped at the next stint's book-in within the same stay."""
    order = d.sort_values(["stay_ID", "book_in_date_time"], kind="stable")
    nxt = order.groupby("stay_ID", sort=False)["book_in_date_time"].shift(-1)
    clipped = order["end"].where(nxt.isna() | (order["end"] <= nxt), nxt)
    out = d.copy()
    out["end"] = clipped.reindex(out.index)
    return out


def share_from_old_stints(d, w0, w1, days):
    """Share of the window's person-days from stints booked in more than `days` before w0."""
    live = d[d["end"].notna() & d["start"].notna() & (d["start"] < w1) & (d["end"] > w0)]
    bed = overlap_days(live["start"], live["end"], w0, w1)
    return bed[live["start"] < w0 - pd.Timedelta(days=days)].sum() / bed.sum() if bed.sum() else float("nan")


def audit(st, cutoff):
    d = interval_diagnostics(build_intervals(st, cutoff))
    clipped = clip_to_next_stint(d)
    first, last = d["start"].min().to_period("M"), pd.Timestamp(cutoff).to_period("M")
    book_month = d["book_in_date_time"].dt.to_period("M")
    rows = []
    for m in pd.period_range(first, last, freq="M"):
        w0, w1 = m.start_time, (m + 1).start_time
        inm = d[book_month == m]
        live = d[d["overlaps_next_stint"] & d["end"].notna() & (d["start"] < w1) & (d["end"] > w0)]
        nxt_start = d.loc[live.index, "end"] - pd.to_timedelta(live["overlap_days"], unit="D")
        both = pd.DataFrame({"start": nxt_start, "end": live["end"]})
        overlap_pd = overlap_days(both["start"], both["end"], w0, w1).sum() if len(both) else 0.0
        rows.append({
            "month": str(m), "window_days": window_days(w0, w1),
            "book_ins": len(inm),
            "stints_closed": int((inm.interval_status == "closed").sum()),
            "stints_open_censored": int((inm.interval_status == "open_censored").sum()),
            "stints_open_excluded": int((inm.interval_status == "open_excluded").sum()),
            "invalid_negative": int((inm.interval_status == "invalid_negative").sum()),
            "stay_end_fallback": int(inm["stay_end_fallback"].sum()),
            "overlapping_stints": int(inm["overlaps_next_stint"].sum()),
            "concurrent_stay_stints": int(inm["concurrent_stay"].sum()),
            "overlap_person_days": overlap_pd,
            "adp_current_method": adp(d, w0, w1),
            "adp_overlap_removed": adp(clipped, w0, w1),
            "share_adp_booked_over_90d_before": share_from_old_stints(d, w0, w1, 90),
            "share_adp_booked_over_365d_before": share_from_old_stints(d, w0, w1, 365),
        })
    out = pd.DataFrame(rows)
    out["double_count_pct"] = (out["adp_current_method"] - out["adp_overlap_removed"]) / out[
        "adp_current_method"] * 100
    out.attrs["missing_book_in"] = int((d.interval_status == "missing_book_in").sum())
    return out


def main():
    out = audit(load_stints(), CUTOFF).round(4)
    out.to_csv(os.path.join(RESULTS, "detention_interval_audit.csv"), index=False)
    print(out.tail(15).to_string())
    print(f"Wrote {len(out)} months; stints with missing book-in: {out.attrs['missing_book_in']:,}")


if __name__ == "__main__":
    main()
