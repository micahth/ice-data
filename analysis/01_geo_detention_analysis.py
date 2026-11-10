"""
Analysis 01 - ICE detention by region, state, metro/micro area and facility operator, old vs. new.

Run from the repo root:  python analysis/01_geo_detention_analysis.py
Writes tidy CSVs to analysis/results/ (consumed by 02_geo_regressions.py and the report).

Old = book-ins/bed-days Jan 2023 - Dec 2024.  New = Jan 2025 - Mar 11 2026 (end of the FOIA release).
"""
import os

import numpy as np
import pandas as pd

from geo_common import (ANNUAL, CACHE, CUTOFF, ERAS, OPERATORS, PERIODS, REPO, RESULTS, TERRITORY, classify_operator,
                        fetch, load_cbsa_delineation, load_county_pop, period_population, region_of)
from ice_lib import adp, annualize, build_intervals
from data_common import read_source


def main():

    pd.set_option("display.width", 220, "display.max_columns", 40)

    # ---------------------------------------------------------------------------
    # 1. Load stints (de-duplicated by ICE's duplicate_drop_row flag)
    # ---------------------------------------------------------------------------
    pkl = os.path.join(CACHE, "stints_clean.pkl") if not os.environ.get("ICE_DATA_DIR") else os.path.join(
        CACHE, "stints_downloaded.pkl")
    if os.path.exists(pkl):
        st = pd.read_pickle(pkl)
    else:
        use = ["book_in_date_time", "book_out_date_time", "stay_book_out_date_time", "detention_facility",
               "detention_facility_code", "unique_identifier", "stay_ID", "state", "duplicate_drop_row",
               "book_in_criminality"]
        st = read_source("detention-stints", use)
        st = st[~st.duplicate_drop_row.fillna(False).astype(bool)].drop(columns="duplicate_drop_row")
        for c in ["book_in_date_time", "book_out_date_time", "stay_book_out_date_time"]:
            st[c] = pd.to_datetime(st[c], utc=True, errors="coerce").dt.tz_localize(None)
        st.to_pickle(pkl)
    print(f"stints (deduplicated): {len(st):,}")

    # ---------------------------------------------------------------------------
    # 2. Facility table: location, CBSA type, operator
    # ---------------------------------------------------------------------------
    fl = pd.read_parquet(fetch("facilities_latest.parquet"),
                         columns=["detention_facility_code", "name", "city", "county", "county_fips_code", "state"])
    at = pd.read_parquet(fetch("facilities_attributes.parquet"),
                         columns=["detention_facility_code", "type_detailed"]).dropna(subset=["detention_facility_code"])
    at = at.drop_duplicates("detention_facility_code").set_index("detention_facility_code")["type_detailed"]
    cbsa = load_cbsa_delineation().set_index("fips")

    fac = (st.groupby("detention_facility_code")
             .agg(stint_name=("detention_facility", "first"), stint_state=("state", lambda s: s.mode().iat[0] if s.notna().any() else np.nan),
                  n_stints=("state", "size"))
             .reset_index())
    fac = fac.merge(fl[["detention_facility_code", "name", "city", "county", "county_fips_code", "state"]],
                    on="detention_facility_code", how="left")
    fac["state"] = fac.state.fillna(fac.stint_state)
    fac["name"] = fac.name.fillna(fac.stint_name)
    fac["type_detailed"] = fac.detention_facility_code.map(at)
    fac["region"] = fac.state.map(region_of)
    fac = fac.join(cbsa, on="county_fips_code")
    in_us_county = fac.county_fips_code.notna()
    fac["cbsa_class"] = np.where(fac.cbsa_type.notna(), fac.cbsa_type, np.where(in_us_county, "Non-CBSA (rural)", "Unmapped"))
    fac["cbsa_title"] = fac.cbsa_title.fillna("(none)")
    ops = [classify_operator(c, n, t) for c, n, t in zip(fac.detention_facility_code, fac.name, fac.type_detailed)]
    fac["operator"] = [o[0] for o in ops]
    fac["operator_basis"] = [o[1] for o in ops]
    fac.drop(columns=["stint_name", "stint_state"]).to_csv(os.path.join(RESULTS, "facility_classification.csv"), index=False)

    # ---------------------------------------------------------------------------
    # 3. Stint-level fields
    # ---------------------------------------------------------------------------
    cols = ["detention_facility_code", "state", "region", "cbsa_class", "cbsa_code", "cbsa_title", "operator"]
    st = st.merge(fac[cols].rename(columns={"state": "fac_state"}), on="detention_facility_code", how="left")
    st["state"] = st.fac_state.fillna(st.state).fillna("Unknown")
    st["region"] = st.state.map(region_of)
    st["cbsa_class"] = st.cbsa_class.fillna("Unmapped")
    st["operator"] = st.operator.fillna("Unclassified")

    st = build_intervals(st, CUTOFF)
    # ADP uses build_intervals()' stay-level fallback; completed stint durations require a stint-level book-out.
    st["stint_days"] = ((st.book_out_date_time - st.book_in_date_time).dt.total_seconds() / 86400).where(
        st.book_out_date_time >= st.book_in_date_time)
    st["crim"] = st.book_in_criminality.str[0].map({"1": "convicted", "2": "pending", "3": "no_record"})
    print("interval status:", st.interval_status.value_counts().to_dict())

    duration_counts = []
    for period in ERAS:
        w0, w1 = PERIODS[period]
        cohort = st[(st.book_in_date_time >= w0) & (st.book_in_date_time < w1)]
        valid_duration = cohort.stint_days.notna()
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
            "other_missing_or_invalid_stint_duration": int(len(cohort) - valid_duration.sum() - stay_end_only.sum()),
        })
    duration_counts = pd.DataFrame(duration_counts)
    duration_counts.to_csv(os.path.join(RESULTS, "duration_observation_counts.csv"), index=False)
    print("completed facility-stint duration observations:")
    print(duration_counts.to_string(index=False))

    # ---------------------------------------------------------------------------
    # 4. Per-division statistics
    # ---------------------------------------------------------------------------
    def window_stats(df, keys, label, w0, w1):
        population = adp(df, w0, w1, keys=keys) if keys else pd.Series({"all": adp(df, w0, w1)})
        b = df[(df.book_in_date_time >= w0) & (df.book_in_date_time < w1)]
        g = b.groupby(keys, dropna=False) if keys else b.groupby(lambda _: "all")
        out = pd.DataFrame({
            "book_ins": g.size(),
            "unique_people": g.unique_identifier.nunique(),
            "mean_stint_days": g.stint_days.mean(),
            "median_stint_days": g.stint_days.median(),
            "pct_convicted": g.crim.apply(lambda s: (s == "convicted").mean() * 100),
            "pct_pending_charges": g.crim.apply(lambda s: (s == "pending").mean() * 100),
            "pct_no_record": g.crim.apply(lambda s: (s == "no_record").mean() * 100),
        })
        out = out.reindex(out.index.union(population.index, sort=False))
        out["book_ins"] = out.book_ins.fillna(0)
        out["unique_people"] = out.unique_people.fillna(0)
        out["adp"] = population
        out["adp"] = out.adp.fillna(0)
        out["book_ins_annualized"] = annualize(out.book_ins, w0, w1)
        out["period"] = label
        return out.reset_index()


    def summarize(keys, pop=None):
        parts = [window_stats(st, keys, lab, *PERIODS[lab]) for lab in PERIODS]
        res = pd.concat(parts, ignore_index=True)
        if pop is not None:
            pm = pop.stack().rename("population").reset_index()
            pm.columns = keys_for_pop(keys) + ["period", "population"]
            res = res.merge(pm, on=keys_for_pop(keys) + ["period"], how="left")
            res["adp_per_100k"] = res.adp / res.population * 1e5
            res["book_ins_per_100k_annualized"] = res.book_ins_annualized / res.population * 1e5
        return res


    def keys_for_pop(keys):
        return [k for k in keys if k in POP_KEYS]


    # population tables
    cp = load_county_pop()
    cp = cp.join(cbsa, on="fips")
    cp["cbsa_class"] = cp.cbsa_type.fillna("Non-CBSA (rural)")
    POP_KEYS = {"state", "region", "cbsa_class", "cbsa_code"}
    pop_state = period_population(cp.dropna(subset=["state"]), ["state"])
    pop_region = period_population(cp.assign(region=cp.state.map(region_of)), ["region"])
    pop_class = period_population(cp, ["cbsa_class"])
    pop_cbsa = period_population(cp.dropna(subset=["cbsa_code"]), ["cbsa_code"])
    pop_us = period_population(cp.assign(country="US"), ["country"]).iloc[0]
    pop_us = pd.DataFrame([pop_us.values], columns=pop_us.index)
    pop_us.to_csv(os.path.join(RESULTS, "us_population_by_period.csv"), index=False)
    pop_state.to_csv(os.path.join(RESULTS, "state_population_by_period.csv"))

    tables = {}
    tables["overall"] = summarize([])
    tables["by_region"] = summarize(["region"], pop_region)
    tables["by_state"] = summarize(["state"], pop_state)
    tables["by_cbsa_class"] = summarize(["cbsa_class"], pop_class)
    cb = summarize(["cbsa_code", "cbsa_title"], pop_cbsa)
    tables["by_cbsa"] = cb
    tables["by_operator"] = summarize(["operator"]).merge(
        pd.DataFrame({"period": list(pop_us.columns), "population": pop_us.iloc[0].values}), on="period")
    tables["by_operator"]["adp_per_100k"] = tables["by_operator"].adp / tables["by_operator"].population * 1e5
    tables["by_operator"]["book_ins_per_100k_annualized"] = (
        tables["by_operator"].book_ins_annualized / tables["by_operator"].population * 1e5)
    tables["by_region_operator"] = summarize(["region", "operator"], None)
    tables["by_cbsa_class_operator"] = summarize(["cbsa_class", "operator"], None)
    tables["by_state_operator"] = summarize(["state", "operator"], None)

    # per-capita for cross-tabs (rates per 100k residents of the geography)
    for name, geo, pop in [("by_region_operator", "region", pop_region), ("by_cbsa_class_operator", "cbsa_class", pop_class),
                           ("by_state_operator", "state", pop_state)]:
        t = tables[name]
        pm = pop.stack().rename("population").reset_index()
        pm.columns = [geo, "period", "population"]
        t = t.merge(pm, on=[geo, "period"], how="left")
        t["adp_per_100k"] = t.adp / t.population * 1e5
        tables[name] = t

    for name, t in tables.items():
        t.round(4).to_csv(os.path.join(RESULTS, f"{name}.csv"), index=False)
        print("wrote", name, t.shape)

    # Share of ADP that sits in each CBSA class and operator, plus facilities summary
    fac_summary = fac.groupby(["operator"]).agg(facilities=("detention_facility_code", "nunique"),
                                                stints=("n_stints", "sum")).reset_index()
    fac_summary.to_csv(os.path.join(RESULTS, "facility_counts_by_operator.csv"), index=False)

    # ---------------------------------------------------------------------------
    # 5. Quick console report
    # ---------------------------------------------------------------------------
    def show(name, cols, by, per=ERAS):
        t = tables[name]
        t = t[t.period.isin(per)]
        print(f"\n=== {name} ===")
        print(t.pivot(index=by, columns="period", values=cols).round(1).to_string())


    show("by_region", ["adp", "adp_per_100k"], "region")
    show("by_cbsa_class", ["adp", "adp_per_100k"], "cbsa_class")
    show("by_operator", ["adp", "book_ins_annualized"], "operator")
    print(tables["overall"][["period", "book_ins", "unique_people", "adp", "median_stint_days", "mean_stint_days"]].round(1))
    print(fac.operator.value_counts())
    print(fac.cbsa_class.value_counts())


if __name__ == "__main__":
    main()
