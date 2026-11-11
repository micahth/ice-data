"""Data-derived list of facility activity and name changes
since the start of Trump's second term (2025-01-20). Writes results/facility_changes.csv."""
import os
import pandas as pd


def main():

    # Stints cache location (same one script 01 writes) and the results folder.
    CACHE = os.environ.get("GEO_CACHE", os.path.join(os.path.dirname(__file__), ".cache"))
    OUT = os.path.join(os.path.dirname(__file__), "results")
    # Inauguration day, and the last date in the FOIA data.
    START, CUT = pd.Timestamp("2025-01-20"), pd.Timestamp("2026-03-11")

    # Pick the same cache file script 01 used, depending on ICE_DATA_DIR.
    s = pd.read_pickle(os.path.join(CACHE, "stints_downloaded.pkl" if os.environ.get("ICE_DATA_DIR") else "stints_clean.pkl"))
    # Book-in time as a datetime; unparseable values become NaT.
    s["bi"] = pd.to_datetime(s.book_in_date_time, errors="coerce")
    # Keep stints with a valid book-in on or before the cutoff date (adding a day includes all of Mar 11).
    s = s[s.bi.notna() & (s.bi < CUT + pd.Timedelta(days=1))]
    # Facility names, locations and operators from script 01, indexed by facility code.
    cls = pd.read_csv(os.path.join(OUT, "facility_classification.csv")).set_index("detention_facility_code")

    # One row per facility code with its activity summary.
    g = s.groupby("detention_facility_code")
    f = pd.DataFrame({
        # Earliest and latest book-in at the facility.
        "first_bookin": g.bi.min(), "last_bookin": g.bi.max(),
        # Book-ins before and after inauguration day.
        "pre_stints": g.apply(lambda d: (d.bi < START).sum()),
        "post_stints": g.apply(lambda d: (d.bi >= START).sum()),
        # Book-ins in the last 90 days of the data.
        "recent_90d": g.apply(lambda d: (d.bi >= CUT - pd.Timedelta(days=90)).sum()),
        # Every distinct name recorded for this code, in order of first appearance.
        "names": g.detention_facility.agg(lambda x: " | ".join(pd.unique(x.dropna()))),
        "n_names": g.detention_facility.nunique(),
    })
    # Add the classified name, location and operator for each facility.
    f = f.join(cls[["name", "city", "state", "operator", "type_detailed"]], how="left")

    # Same code observed under more than one name; keep the earliest/latest name by time for the rename list
    # Name on the earliest book-in.
    names_t = s.sort_values("bi").groupby("detention_facility_code").detention_facility.agg(
        lambda x: x.dropna().iloc[0] if x.notna().any() else None)
    # Name on the latest book-in.
    names_l = s.sort_values("bi").groupby("detention_facility_code").detention_facility.agg(
        lambda x: x.dropna().iloc[-1] if x.notna().any() else None)
    # Both Series line up with f by facility code.
    f["first_name"], f["last_name"] = names_t, names_l

    rows = []
    # Check each facility against the change rules; a facility can match more than one.
    for code, r in f.iterrows():
        kinds = []
        # New facility: no book-ins before inauguration and at least 25 after.
        if r.pre_stints == 0 and r.post_stints >= 25:
            kinds.append("First observed booking activity after January 20, 2025.")
        # Recent start: first used from July 2024 on, with pre-inauguration book-ins
        # under 10% of post-inauguration book-ins.
        elif r.pre_stints > 0 and r.post_stints >= 25 and r.first_bookin >= pd.Timestamp("2024-07-01") and r.pre_stints < 0.1 * r.post_stints:
            kinds.append("RECENT START (few book-ins before inauguration)")
        # Stopped: established before inauguration, used after it, but nothing in the last 90 days.
        # (The recent_90d and last_bookin checks test the same thing.)
        if r.post_stints > 0 and r.pre_stints >= 25 and r.recent_90d == 0 and r.last_bookin < CUT - pd.Timedelta(days=90):
            kinds.append("STOPPED BOOKING (>90 days no book-ins; used after 2025-01-20)")
        # Renamed: the first and last recorded names differ.
        # (A facility renamed and later changed back won't be flagged.)
        if r.n_names > 1 and r.first_name != r.last_name:
            kinds.append("NAME CHANGE")
        if kinds:
            # Prefer the classified name; fall back to the latest name in the stints.
            rows.append(dict(code=code, facility=r["name"] if pd.notna(r["name"]) else r.last_name,
                             state=r.state, operator_class=r.operator, change_type="; ".join(kinds),
                             first_bookin=r.first_bookin.date(), last_bookin=r.last_bookin.date(),
                             pre_stints=r.pre_stints, post_stints=r.post_stints, names_seen=r.names))
    # Group by change type (alphabetically), largest post-inauguration activity first within each.
    out = pd.DataFrame(rows).sort_values(["change_type", "post_stints"], ascending=[True, False])
    out.to_csv(os.path.join(OUT, "facility_changes.csv"), index=False)
    # Wide console settings so the full list prints readably.
    pd.set_option("display.width", 250, "display.max_colwidth", 60, "display.max_rows", 500)
    print(out.change_type.value_counts())
    # Print everything except the long list of names.
    print(out.drop(columns="names_seen").to_string(index=False))


if __name__ == "__main__":
    main()
