"""Data-derived list of facility activity and name changes
since the start of Trump's second term (2025-01-20). Writes results/facility_changes.csv."""
import os
import pandas as pd


def main():

    CACHE = os.environ.get("GEO_CACHE", os.path.join(os.path.dirname(__file__), ".cache"))
    OUT = os.path.join(os.path.dirname(__file__), "results")
    START, CUT = pd.Timestamp("2025-01-20"), pd.Timestamp("2026-03-11")

    s = pd.read_pickle(os.path.join(CACHE, "stints_downloaded.pkl" if os.environ.get("ICE_DATA_DIR") else "stints_clean.pkl"))
    s["bi"] = pd.to_datetime(s.book_in_date_time, errors="coerce")
    s = s[s.bi.notna() & (s.bi < CUT + pd.Timedelta(days=1))]
    cls = pd.read_csv(os.path.join(OUT, "facility_classification.csv")).set_index("detention_facility_code")

    g = s.groupby("detention_facility_code")
    f = pd.DataFrame({
        "first_bookin": g.bi.min(), "last_bookin": g.bi.max(),
        "pre_stints": g.apply(lambda d: (d.bi < START).sum()),
        "post_stints": g.apply(lambda d: (d.bi >= START).sum()),
        "recent_90d": g.apply(lambda d: (d.bi >= CUT - pd.Timedelta(days=90)).sum()),
        "names": g.detention_facility.agg(lambda x: " | ".join(pd.unique(x.dropna()))),
        "n_names": g.detention_facility.nunique(),
    })
    f = f.join(cls[["name", "city", "state", "operator", "type_detailed"]], how="left")

    # Same code observed under more than one name; keep the earliest/latest name by time for the rename list
    names_t = s.sort_values("bi").groupby("detention_facility_code").detention_facility.agg(
        lambda x: x.dropna().iloc[0] if x.notna().any() else None)
    names_l = s.sort_values("bi").groupby("detention_facility_code").detention_facility.agg(
        lambda x: x.dropna().iloc[-1] if x.notna().any() else None)
    f["first_name"], f["last_name"] = names_t, names_l

    rows = []
    for code, r in f.iterrows():
        kinds = []
        if r.pre_stints == 0 and r.post_stints >= 25:
            kinds.append("FIRST OBSERVED AFTER 2025-01-20 (no earlier book-ins in extract)")
        elif r.pre_stints > 0 and r.post_stints >= 25 and r.first_bookin >= pd.Timestamp("2024-07-01") and r.pre_stints < 0.1 * r.post_stints:
            kinds.append("RECENT START (few book-ins before inauguration)")
        if r.post_stints > 0 and r.pre_stints >= 25 and r.recent_90d == 0 and r.last_bookin < CUT - pd.Timedelta(days=90):
            kinds.append("STOPPED BOOKING (>90 days no book-ins; used after 2025-01-20)")
        if r.n_names > 1 and r.first_name != r.last_name:
            kinds.append("NAME CHANGE")
        if kinds:
            rows.append(dict(code=code, facility=r["name"] if pd.notna(r["name"]) else r.last_name,
                             state=r.state, operator_class=r.operator, change_type="; ".join(kinds),
                             first_bookin=r.first_bookin.date(), last_bookin=r.last_bookin.date(),
                             pre_stints=r.pre_stints, post_stints=r.post_stints, names_seen=r.names))
    out = pd.DataFrame(rows).sort_values(["change_type", "post_stints"], ascending=[True, False])
    out.to_csv(os.path.join(OUT, "facility_changes.csv"), index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 60, "display.max_rows", 500)
    print(out.change_type.value_counts())
    print(out.drop(columns="names_seen").to_string(index=False))


if __name__ == "__main__":
    main()
