"""
Analysis 01 - ICE detention by region, state, metro/micro area and facility operator, old vs. new.

Run from the repo root:  python analysis/01_geo_detention_analysis.py
Writes tidy CSVs to analysis/results/ (consumed by 02_geo_regressions.py and the report).

Old = book-ins/bed-days Jan 2023 - Dec 2024.  New = Jan 2025 - Mar 11 2026 (end of the FOIA release).
"""
import os

import numpy as np
import pandas as pd

# Shared constants and helpers for the geographic analyses (paths, period windows,
# operator classification, Census/CBSA loaders, column checks).
from geo_common import (ANNUAL, CACHE, CUTOFF, ERAS, OPERATORS, PERIODS, REPO, RESULTS, TERRITORY, classify_operator,
                        fetch, load_cbsa_delineation, load_county_pop, period_population, region_of, require_columns)
# Detention-specific helpers: average daily population, annualizing counts,
# building detention intervals, and the right-censoring sensitivity check.
from ice_lib import adp, annualize, build_intervals, censoring_sensitivity
# Reads a named raw source table, restricted to the requested columns.
from data_common import read_source


def main():

    # Widen console output so the summary tables print without wrapping.
    pd.set_option("display.width", 220, "display.max_columns", 40)


    # 1. Load stints (de-duplicated by ICE's duplicate_drop_row flag)
    # Use a separate cache file when ICE_DATA_DIR is set, so locally cleaned data
    # and freshly downloaded data never overwrite each other.
    pkl = os.path.join(CACHE, "stints_clean.pkl") if not os.environ.get("ICE_DATA_DIR") else os.path.join(
        CACHE, "stints_downloaded.pkl")
    if os.path.exists(pkl):
        # Fast path: reuse the already-cleaned stints.
        st = pd.read_pickle(pkl)
    else:
        # Only load the columns this analysis needs.
        use = ["book_in_date_time", "book_out_date_time", "stay_book_out_date_time", "detention_facility",
               "detention_facility_code", "unique_identifier", "stay_ID", "state", "duplicate_drop_row",
               "book_in_criminality"]
        st = read_source("detention-stints", use)
        # Drop rows ICE flagged as duplicates; missing flags count as "keep".
        st = st[~st.duplicate_drop_row.fillna(False).astype(bool)].drop(columns="duplicate_drop_row")
        # Parse timestamps as UTC, then strip the timezone so comparisons with
        # naive period boundaries work. Unparseable values become NaT.
        for c in ["book_in_date_time", "book_out_date_time", "stay_book_out_date_time"]:
            st[c] = pd.to_datetime(st[c], utc=True, errors="coerce").dt.tz_localize(None)
        # Cache the cleaned result for the next run.
        st.to_pickle(pkl)
    print(f"stints (deduplicated): {len(st):,}")
    # Measure how much stays still open at the data cutoff could affect results.
    censoring_sensitivity(st, CUTOFF, PERIODS).round(4).to_csv(
        os.path.join(RESULTS, "detention_censoring_sensitivity.csv"), index=False)


    # 2. Facility table: location, CBSA type, operator

    # Latest facility list: names and locations, including county FIPS codes.
    fl = pd.read_parquet(fetch("facilities_latest.parquet"),
                         columns=["detention_facility_code", "name", "city", "county", "county_fips_code", "state"])
    require_columns(fl, "facilities_latest.parquet")
    # Facility attributes: detailed facility type, used for operator classification.
    at = pd.read_parquet(fetch("facilities_attributes.parquet"),
                         columns=["detention_facility_code", "type_detailed"]).dropna(subset=["detention_facility_code"])
    require_columns(at, "facilities_attributes.parquet")
    # One type per facility code, as a lookup Series.
    at = at.drop_duplicates("detention_facility_code").set_index("detention_facility_code")["type_detailed"]
    # County FIPS -> metro/micro area (CBSA) lookup.
    cbsa = load_cbsa_delineation().set_index("fips")

    # Start from every facility that appears in the stints, so facilities missing
    # from the facility list are still kept. Record a fallback name, the most
    # common state on its stints, and its stint count.
    fac = (st.groupby("detention_facility_code")
             .agg(stint_name=("detention_facility", "first"), stint_state=("state", lambda s: s.mode().iat[0] if s.notna().any() else np.nan),
                  n_stints=("state", "size"))
             .reset_index())
    # Attach location details from the facility list.
    fac = fac.merge(fl[["detention_facility_code", "name", "city", "county", "county_fips_code", "state"]],
                    on="detention_facility_code", how="left")
    # Prefer the facility list's state and name; fall back to the stint data.
    fac["state"] = fac.state.fillna(fac.stint_state)
    fac["name"] = fac.name.fillna(fac.stint_name)
    fac["type_detailed"] = fac.detention_facility_code.map(at)
    fac["region"] = fac.state.map(region_of)
    # Add CBSA code, title and type (metro/micro) via the county FIPS code.
    fac = fac.join(cbsa, on="county_fips_code")
    # Classify each facility's area: its CBSA type if it has one; rural if it has
    # a US county but no CBSA; "Unmapped" if there is no county at all.
    in_us_county = fac.county_fips_code.notna()
    fac["cbsa_class"] = np.where(fac.cbsa_type.notna(), fac.cbsa_type, np.where(in_us_county, "Non-CBSA (rural)", "Unmapped"))
    fac["cbsa_title"] = fac.cbsa_title.fillna("(none)")
    # Classify the operator; each result is (operator, reason for the classification).
    ops = [classify_operator(c, n, t) for c, n, t in zip(fac.detention_facility_code, fac.name, fac.type_detailed)]
    fac["operator"] = [o[0] for o in ops]
    fac["operator_basis"] = [o[1] for o in ops]
    # Save the facility table (minus the temporary fallback columns) for review.
    fac.drop(columns=["stint_name", "stint_state"]).to_csv(os.path.join(RESULTS, "facility_classification.csv"), index=False)


    # 3. Stint-level fields
    # Copy the facility's geography and operator onto each stint.
    cols = ["detention_facility_code", "state", "region", "cbsa_class", "cbsa_code", "cbsa_title", "operator"]
    st = st.merge(fac[cols].rename(columns={"state": "fac_state"}), on="detention_facility_code", how="left")
    # Facility state wins over the stint's own state; anything left is "Unknown".
    st["state"] = st.fac_state.fillna(st.state).fillna("Unknown")
    st["region"] = st.state.map(region_of)
    # Stints whose facility could not be matched get explicit placeholder labels.
    st["cbsa_class"] = st.cbsa_class.fillna("Unmapped")
    st["operator"] = st.operator.fillna("Unclassified")

    # Build each stint's detention interval, capped at the data cutoff.
    st = build_intervals(st, CUTOFF)
    # ADP uses build_intervals()' stay-level fallback; completed stint durations require a stint-level book-out.
    # Stint length in days; NaN when there is no book-out or it precedes the book-in.
    st["stint_days"] = ((st.book_out_date_time - st.book_in_date_time).dt.total_seconds() / 86400).where(
        st.book_out_date_time >= st.book_in_date_time)
    # The first character of the criminality field encodes the category.
    st["crim"] = st.book_in_criminality.str[0].map({"1": "convicted", "2": "pending", "3": "no_record"})
    print("interval status:", st.interval_status.value_counts().to_dict())

    # For each era, count how many book-ins have a usable stint duration and why
    # the rest don't. This documents the sample behind the duration statistics.
    duration_counts = []
    for period in ERAS:
        w0, w1 = PERIODS[period]
        # Stints booked in during this era.
        cohort = st[(st.book_in_date_time >= w0) & (st.book_in_date_time < w1)]
        valid_duration = cohort.stint_days.notna()
        # No stint-level book-out, but a valid stay-level one: excluded from
        # durations even though ADP can use it.
        stay_end_only = (
            cohort.book_out_date_time.isna()
            & cohort.stay_book_out_date_time.notna()
            & (cohort.stay_book_out_date_time >= cohort.book_in_date_time)
        )
        duration_counts.append({
            "period": period,
            "book_ins": len(cohort),
            "valid_stint_duration_observations": int(valid_duration.sum()),
            "excluded_stay_end_only": int(stay_end_only.sum()),
            # Remainder: still open at the cutoff, or bad/missing dates.
            "other_missing_or_invalid_stint_duration": int(len(cohort) - valid_duration.sum() - stay_end_only.sum()),
        })
    duration_counts = pd.DataFrame(duration_counts)
    duration_counts.to_csv(os.path.join(RESULTS, "duration_observation_counts.csv"), index=False)
    print("completed facility-stint duration observations:")
    print(duration_counts.to_string(index=False))

    # 4. Per-division statistics

    def window_stats(df, keys, label, w0, w1):
        """Book-in, duration, criminality and ADP statistics for one time window,
        grouped by `keys` (or a single "all" row when keys is empty)."""
        # ADP counts everyone detained during the window, whenever they were booked in.
        population = adp(df, w0, w1, keys=keys) if keys else pd.Series({"all": adp(df, w0, w1)})
        # Book-in statistics only count stints that started inside the window.
        b = df[(df.book_in_date_time >= w0) & (df.book_in_date_time < w1)]
        # dropna=False keeps groups with missing keys; with no keys, put every row in one "all" group.
        g = b.groupby(keys, dropna=False) if keys else b.groupby(lambda _: "all")
        out = pd.DataFrame({
            "book_ins": g.size(),
            "unique_people": g.unique_identifier.nunique(),
            "mean_stint_days": g.stint_days.mean(),
            "median_stint_days": g.stint_days.median(),
            # Criminality shares as percentages of book-ins (missing values count in the denominator).
            "pct_convicted": g.crim.apply(lambda s: (s == "convicted").mean() * 100),
            "pct_pending_charges": g.crim.apply(lambda s: (s == "pending").mean() * 100),
            "pct_no_record": g.crim.apply(lambda s: (s == "no_record").mean() * 100),
        })
        # Add groups that had people in detention but no new book-ins this window.
        out = out.reindex(out.index.union(population.index, sort=False))
        # Those groups get zero book-ins rather than NaN.
        out["book_ins"] = out.book_ins.fillna(0)
        out["unique_people"] = out.unique_people.fillna(0)
        out["adp"] = population
        out["adp"] = out.adp.fillna(0)
        # Scale book-ins to a yearly rate so windows of different lengths compare.
        out["book_ins_annualized"] = annualize(out.book_ins, w0, w1)
        out["period"] = label
        return out.reset_index()


    def summarize(keys, pop=None):
        """Run window_stats for every period and stack the results. If a
        population table is given, also add per-100k rates."""
        parts = [window_stats(st, keys, lab, *PERIODS[lab]) for lab in PERIODS]
        res = pd.concat(parts, ignore_index=True)
        if pop is not None:
            # Reshape population (geography x period) to long form and merge it in.
            pm = pop.stack().rename("population").reset_index()
            pm.columns = keys_for_pop(keys) + ["period", "population"]
            res = res.merge(pm, on=keys_for_pop(keys) + ["period"], how="left")
            res["adp_per_100k"] = res.adp / res.population * 1e5
            res["book_ins_per_100k_annualized"] = res.book_ins_annualized / res.population * 1e5
        return res


    def keys_for_pop(keys):
        """Keep only the grouping keys that population tables are indexed by
        (e.g. drops cbsa_title, which is a label rather than a join key)."""
        return [k for k in keys if k in POP_KEYS]


    # population tables
    # County population joined to CBSA; counties outside any CBSA are rural.
    cp = load_county_pop()
    cp = cp.join(cbsa, on="fips")
    cp["cbsa_class"] = cp.cbsa_type.fillna("Non-CBSA (rural)")
    # Keys that population tables can be joined on. Defined here, but read by
    # keys_for_pop() only when it runs below, so the order is fine.
    POP_KEYS = {"state", "region", "cbsa_class", "cbsa_code"}
    # Resident population per period at each geographic level.
    pop_state = period_population(cp.dropna(subset=["state"]), ["state"])
    pop_region = period_population(cp.assign(region=cp.state.map(region_of)), ["region"])
    pop_class = period_population(cp, ["cbsa_class"])
    pop_cbsa = period_population(cp.dropna(subset=["cbsa_code"]), ["cbsa_code"])
    # National total: one row with a column per period.
    pop_us = period_population(cp.assign(country="US"), ["country"]).iloc[0]
    pop_us = pd.DataFrame([pop_us.values], columns=pop_us.index)
    pop_us.to_csv(os.path.join(RESULTS, "us_population_by_period.csv"), index=False)
    pop_state.to_csv(os.path.join(RESULTS, "state_population_by_period.csv"))

    # Build every summary table.
    tables = {}
    tables["overall"] = summarize([])
    tables["by_region"] = summarize(["region"], pop_region)
    tables["by_state"] = summarize(["state"], pop_state)
    tables["by_cbsa_class"] = summarize(["cbsa_class"], pop_class)
    # cbsa_title rides along as a readable label; population joins on cbsa_code only.
    cb = summarize(["cbsa_code", "cbsa_title"], pop_cbsa)
    tables["by_cbsa"] = cb
    # Operators aren't geographic, so their rates use the national population.
    tables["by_operator"] = summarize(["operator"]).merge(
        pd.DataFrame({"period": list(pop_us.columns), "population": pop_us.iloc[0].values}), on="period")
    tables["by_operator"]["adp_per_100k"] = tables["by_operator"].adp / tables["by_operator"].population * 1e5
    tables["by_operator"]["book_ins_per_100k_annualized"] = (
        tables["by_operator"].book_ins_annualized / tables["by_operator"].population * 1e5)
    # Geography x operator cross-tabs; population is added in the loop below.
    tables["by_region_operator"] = summarize(["region", "operator"], None)
    tables["by_cbsa_class_operator"] = summarize(["cbsa_class", "operator"], None)
    tables["by_state_operator"] = summarize(["state", "operator"], None)

    # per-capita for cross-tabs (rates per 100k residents of the geography)
    # Only ADP per 100k is added here, not annualized book-ins per 100k.
    for name, geo, pop in [("by_region_operator", "region", pop_region), ("by_cbsa_class_operator", "cbsa_class", pop_class),
                           ("by_state_operator", "state", pop_state)]:
        t = tables[name]
        pm = pop.stack().rename("population").reset_index()
        pm.columns = [geo, "period", "population"]
        t = t.merge(pm, on=[geo, "period"], how="left")
        t["adp_per_100k"] = t.adp / t.population * 1e5
        tables[name] = t

    # Write each table to its own CSV.
    for name, t in tables.items():
        t.round(4).to_csv(os.path.join(RESULTS, f"{name}.csv"), index=False)
        print("wrote", name, t.shape)

    # Share of ADP that sits in each CBSA class and operator, plus facilities summary
    # Number of facilities and total stints per operator.
    fac_summary = fac.groupby(["operator"]).agg(facilities=("detention_facility_code", "nunique"),
                                                stints=("n_stints", "sum")).reset_index()
    fac_summary.to_csv(os.path.join(RESULTS, "facility_counts_by_operator.csv"), index=False)

  
    # 5. Quick console report
  
    def show(name, cols, by, per=ERAS):
        """Print one table pivoted wide: rows are `by`, columns are metric x period."""
        t = tables[name]
        t = t[t.period.isin(per)]
        print(f"\n=== {name} ===")
        print(t.pivot(index=by, columns="period", values=cols).round(1).to_string())


    show("by_region", ["adp", "adp_per_100k"], "region")
    show("by_cbsa_class", ["adp", "adp_per_100k"], "cbsa_class")
    show("by_operator", ["adp", "book_ins_annualized"], "operator")
    print(tables["overall"][["period", "book_ins", "unique_people", "adp", "median_stint_days", "mean_stint_days"]].round(1))
    # Facility counts by operator and by area type.
    print(fac.operator.value_counts())
    print(fac.cbsa_class.value_counts())


if __name__ == "__main__":
    main()
