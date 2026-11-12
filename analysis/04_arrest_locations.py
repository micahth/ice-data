"""
Analysis 04 - ICE arrests by location (state, AOR, landmark), old vs. new.

Run from the repo root:  python analysis/04_arrest_locations.py
Writes CSVs to analysis/results/arrests_by_*.csv. Old = CY2023-2024, New = 2025-01-01 onward.
"""
import os
import argparse

import pandas as pd
# Shared arrest helpers: days covered by each era, cleaning, loading and monthly counts.
from arrest_common import ARREST_DAYS, clean_arrests, load_arrests, monthly_arrests


def main():
    # Command-line options: which engine to use and where to write results.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=["pandas", "duckdb"], default="pandas")
    parser.add_argument("--output-dir", default=os.path.join(os.path.dirname(__file__), "results"))
    arguments = parser.parse_args()
    # The DuckDB engine runs a separate SQL version of this analysis and skips everything below.
    if arguments.engine == "duckdb":
        from sql_arrests import run_sql
        run_sql(arguments.output_dir)
        return

    RES = arguments.output_dir
    # Create the output folder if it doesn't exist yet.
    os.makedirs(RES, exist_ok=True)
    # Widen console output so the tables print without wrapping.
    pd.set_option("display.width", 200, "display.max_columns", 30, "display.max_rows", 100)

    # Only load the columns this analysis needs.
    # (operation isn't used below; duplicate_drop_row is presumably used by clean_arrests.)
    source_columns = ["apprehension_date", "apprehension_state_filled_in", "apprehension_state_original", "apprehension_aor",
           "apprehension_site_landmark", "apprehension_criminality", "arresting_agency", "operation",
           "duplicate_drop_row"]
    arrests = load_arrests(source_columns)
    # Row count before cleaning.
    print(f"rows: {len(arrests):,}")
    # Cleaning adds the date and era columns used below.
    arrests = clean_arrests(arrests)
    # Number of days in each era, for per-day rates.
    days_by_era = ARREST_DAYS
    print("days per era:", days_by_era, "| last date:", arrests.date.max().date())
    # Prefer ICE's filled-in state, then the original state; otherwise "Unknown".
    arrests["state"] = arrests.apprehension_state_filled_in.fillna(arrests.apprehension_state_original).fillna("Unknown")
    # ICE area of responsibility (field office region).
    arrests["aor"] = arrests.apprehension_aor.fillna("Unknown")
    # Normalize landmark text (trim spaces, upper-case) so spelling variants group together.
    arrests["landmark"] = arrests.apprehension_site_landmark.str.strip().str.upper().fillna("Unknown")
    arrests["crim"] = arrests.apprehension_criminality.fillna("Unknown")


    def era_table(col, name):
        # Arrest counts by `col` for each era, converted to per-day rates, saved and printed.
        # Rows are values of col; columns are the old and new eras (0 where none).
        table = arrests.groupby([col, "era"]).size().unstack(fill_value=0).reindex(columns=["old", "new"], fill_value=0)
        # Per-day rates make eras of different lengths comparable.
        table["old_per_day"] = table.old / days_by_era["old"]
        table["new_per_day"] = table.new / days_by_era["new"]
        # Percent change in daily rate; NaN where there were no old-era arrests.
        table["change_pct"] = (table.new_per_day / table.old_per_day.where(table.old_per_day > 0) - 1) * 100
        # Each location's share of all new-era arrests.
        table["share_new_pct"] = table.new / table.new.sum() * 100
        table = table.sort_values("new", ascending=False)
        table.to_csv(os.path.join(RES, f"arrests_by_{name}.csv"))
        print(f"\n=== {name} (top 15 by new-era arrests) ===")
        print(table.head(15).round(1))
        return table


    # Build the three location tables (the returned tables aren't used further here).
    by_state = era_table("state", "state")
    by_aor = era_table("aor", "aor")
    by_landmark = era_table("landmark", "landmark")

    # Criminality category shares within each era (printed as percentages).
    print("\n=== criminality share by era ===")
    print((pd.crosstab(arrests.era, arrests.crim, normalize="index") * 100).round(1))
    # Saved as counts, not percentages.
    criminality = pd.crosstab(arrests.era, arrests.crim)
    criminality.to_csv(os.path.join(RES, "arrest_criminality.csv"))
    # Total arrests, days and arrests per day for each era.
    pd.DataFrame([{"era": era, "arrests": len(era_records), "days": days_by_era[era],
                   "arrests_per_day": len(era_records) / days_by_era[era]} for era, era_records in arrests.groupby("era")]).to_csv(
        os.path.join(RES, "arrest_summary.csv"), index=False)
    # Ten agencies with the most new-era arrests.
    print("\n=== top arresting agencies by era ===")
    print((pd.crosstab(arrests.arresting_agency, arrests.era).sort_values("new", ascending=False).head(10)))
    # Percent of arrests in each era with no recorded state, AOR or landmark.
    print("\n=== missing location share by era ===")
    print((arrests.groupby("era")[["state", "aor", "landmark"]].agg(lambda s: (s == "Unknown").mean() * 100)).round(1))

    # Arrests per month across the whole period.
    monthly = monthly_arrests(arrests)
    monthly.to_csv(os.path.join(RES, "monthly_arrests.csv"), index=False)
    print("\n=== monthly arrests, last 18 months ===")
    print(monthly.tail(18))


if __name__ == "__main__":
    main()
