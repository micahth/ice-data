"""
Analysis 09 - ICE arrests by location (state, AOR, landmark), old vs. new.

Run from the repo root:  python notebooks/09_arrest_locations.py
Writes CSVs to notebooks/results/arrests_by_*.csv. Old = CY2023-2024, New = 2025-01-01 onward.
"""
import os

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(REPO, "notebooks", "results")
pd.set_option("display.width", 200, "display.max_columns", 30, "display.max_rows", 100)

use = ["apprehension_date", "apprehension_state_filled_in", "apprehension_state_original", "apprehension_aor",
       "apprehension_site_landmark", "apprehension_criminality", "arresting_agency", "operation",
       "duplicate_drop_row"]
a = pd.read_csv(os.path.join(REPO, "data", "arrests-latest 7-24-2026.csv"), usecols=use, low_memory=False,
                encoding="latin-1")
print(f"rows: {len(a):,}")
a = a[~a.duplicate_drop_row.fillna(False).astype(bool)].copy()
print(f"rows after dropping duplicate_drop_row: {len(a):,}")
a["date"] = pd.to_datetime(a.apprehension_date, errors="coerce")
print("date range:", a.date.min(), "->", a.date.max(), "| missing dates:", a.date.isna().sum())
# Source has 1 record on 2026-03-11 (partial day) and 1 stray 2026-09-17 record; end at the last full day.
END = pd.Timestamp("2026-03-10")
a = a[(a.date >= "2023-01-01") & (a.date <= END)]
a["era"] = (a.date >= "2025-01-01").map({False: "old", True: "new"})
days = {"old": 731, "new": (END - pd.Timestamp("2025-01-01")).days + 1}
print("days per era:", days, "| last date:", a.date.max().date())
a["state"] = a.apprehension_state_filled_in.fillna(a.apprehension_state_original)
a["aor"] = a.apprehension_aor
a["landmark"] = a.apprehension_site_landmark.str.strip().str.upper()
a["crim"] = a.apprehension_criminality.fillna("Unknown")


def era_table(col, name):
    t = a.groupby([col, "era"]).size().unstack(fill_value=0).reindex(columns=["old", "new"], fill_value=0)
    t["old_per_day"] = t.old / days["old"]
    t["new_per_day"] = t.new / days["new"]
    t["change_pct"] = (t.new_per_day / t.old_per_day.where(t.old_per_day > 0) - 1) * 100
    t["share_new_pct"] = t.new / t.new.sum() * 100
    t = t.sort_values("new", ascending=False)
    t.to_csv(os.path.join(RES, f"arrests_by_{name}.csv"))
    print(f"\n=== {name} (top 15 by new-era arrests) ===")
    print(t.head(15).round(1))
    return t


by_state = era_table("state", "state")
by_aor = era_table("aor", "aor")
by_land = era_table("landmark", "landmark")

print("\n=== criminality share by era ===")
print((pd.crosstab(a.era, a.crim, normalize="index") * 100).round(1))
print("\n=== top arresting agencies by era ===")
print((pd.crosstab(a.arresting_agency, a.era).sort_values("new", ascending=False).head(10)))
print("\n=== missing location share by era ===")
print((a.groupby("era")[["state", "aor", "landmark"]].agg(lambda s: s.isna().mean() * 100)).round(1))

m = a.groupby([a.date.dt.to_period("M")]).size()
print("\n=== monthly arrests, last 18 months ===")
print(m.tail(18))
