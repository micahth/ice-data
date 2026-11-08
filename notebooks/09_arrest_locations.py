"""
Analysis 09 - ICE arrests by location (state, AOR, landmark), old vs. new.

Run from the repo root:  python notebooks/09_arrest_locations.py
Writes CSVs to notebooks/results/arrests_by_*.csv. Old = CY2023-2024, New = 2025-01-01 onward.
"""
import os

import pandas as pd
from arrest_common import ARREST_DAYS, clean_arrests, load_arrests, monthly_arrests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(REPO, "notebooks", "results")
pd.set_option("display.width", 200, "display.max_columns", 30, "display.max_rows", 100)

use = ["apprehension_date", "apprehension_state_filled_in", "apprehension_state_original", "apprehension_aor",
       "apprehension_site_landmark", "apprehension_criminality", "arresting_agency", "operation",
       "duplicate_drop_row"]
a = load_arrests(use)
print(f"rows: {len(a):,}")
a = clean_arrests(a)
days = ARREST_DAYS
print("days per era:", days, "| last date:", a.date.max().date())
a["state"] = a.apprehension_state_filled_in.fillna(a.apprehension_state_original).fillna("Unknown")
a["aor"] = a.apprehension_aor.fillna("Unknown")
a["landmark"] = a.apprehension_site_landmark.str.strip().str.upper().fillna("Unknown")
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
criminality = pd.crosstab(a.era, a.crim)
criminality.to_csv(os.path.join(RES, "arrest_criminality.csv"))
pd.DataFrame([{"era": era, "arrests": len(d), "days": days[era],
               "arrests_per_day": len(d) / days[era]} for era, d in a.groupby("era")]).to_csv(
    os.path.join(RES, "arrest_summary.csv"), index=False)
print("\n=== top arresting agencies by era ===")
print((pd.crosstab(a.arresting_agency, a.era).sort_values("new", ascending=False).head(10)))
print("\n=== missing location share by era ===")
print((a.groupby("era")[["state", "aor", "landmark"]].agg(lambda s: s.isna().mean() * 100)).round(1))

m = monthly_arrests(a)
m.to_csv(os.path.join(RES, "monthly_arrests.csv"), index=False)
print("\n=== monthly arrests, last 18 months ===")
print(m.tail(18))
