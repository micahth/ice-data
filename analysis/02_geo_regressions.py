"""
Analysis 02 - Do per-capita detention rates track changes in GDP, unemployment and crime?

Run after 01_geo_detention_analysis.py:  python analysis/02_geo_regressions.py

Unit of analysis: state x year (50 states). Old era = 2023 and 2024, new era = 2025.
Outcomes (year-over-year change): real GDP growth (BEA), unemployment-rate change (BLS LAUS, annual avg),
violent-crime and property-crime ("nonviolent") rate change (Real-Time Crime Index state sample; FBI as a check).
Key regressor: detention ADP per 100,000 residents of the state in year t (scaled per +10).
Added control: lagged change in youth share (ages 15-29) of state population.
"""
import json
import os

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

# State name/abbreviation maps, file fetching, county population, region lookup and column checks.
from geo_common import (ABBR_STATE, RESULTS, STATE_ABBR, fetch, load_county_pop, region_of, require_columns)
# Average daily population and detention-interval builder, shared with script 01.
from ice_lib import adp, build_intervals
# End date of the FOIA data, used to cap open detention intervals.
from geo_common import CUTOFF
# Shared regression pieces: the control-variable formula string, coefficient extraction,
# model fitting, Benjamini-Hochberg correction on the primary term, GOP vote share,
# and a check that every state has its controls.
from regression_common import CONTROLS, coefficient, fit, primary_bh, republican_vote_share, require_control_coverage


def main():

    # Widen console output so the summary tables print without wrapping.
    pd.set_option("display.width", 220, "display.max_columns", 40)
    # Outcome years in the panel, and which era each belongs to.
    YEARS = [2023, 2024, 2025]
    ERA_OF = {2023: "Old", 2024: "Old", 2025: "New"}

    # 1. Detention exposure (state x year)

    # State-level detention table written by script 01. Keep the calendar-year periods only.
    bs = pd.read_csv(os.path.join(RESULTS, "by_state.csv"))
    bs = bs[bs.period.isin(["2023", "2024", "2025", "2026 YTD (to Mar 11)"])].copy()
    # The first four characters of the period label are the year (works for "2026 YTD ..." too).
    bs["year"] = bs.period.str[:4].astype(int)
    # Keep ADP and the two per-capita rates under shorter names.
    det = bs[["state", "year", "adp", "adp_per_100k", "book_ins_per_100k_annualized"]].rename(
        columns={"adp": "adp", "adp_per_100k": "det_rate", "book_ins_per_100k_annualized": "bookin_rate"})

    # State x operator detention table from script 01, same period filtering.
    bso = pd.read_csv(os.path.join(RESULTS, "by_state_operator.csv"))
    bso = bso[bso.period.isin(["2023", "2024", "2025", "2026 YTD (to Mar 11)"])].copy()
    bso["year"] = bso.period.str[:4].astype(int)
    # Operator labels -> column names for the panel. Operators not listed here are dropped.
    OPCOL = {"ICE": "det_ice", "CoreCivic": "det_corecivic", "GEO Group": "det_geo", "Other private": "det_otherpriv",
             "Local/state government": "det_localstate", "Federal (BOP/CBP/other)": "det_federal"}
    bso = bso[bso.operator.isin(OPCOL)]
    # One row per state-year, one ADP-per-100k column per operator.
    op = bso.pivot_table(index=["state", "year"], columns="operator", values="adp_per_100k").rename(columns=OPCOL)
    op = op.reset_index()

    # detention by CBSA class of the facility, per 100k state residents
    # Facility metro/micro/rural classification and state populations from script 01.
    fac = pd.read_csv(os.path.join(RESULTS, "facility_classification.csv"))
    pop_state = pd.read_csv(os.path.join(RESULTS, "state_population_by_period.csv"), index_col=0)
    # state x cbsa_class ADP computed in script 05 is not stored per state, so rebuild it from stints cache
    # Note: the stints cache is the one script 01 writes; GEO_CACHE can point elsewhere.
    cache = os.environ.get("GEO_CACHE", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache"))
    # Pick the same cache file script 01 used, depending on ICE_DATA_DIR.
    st = pd.read_pickle(os.path.join(cache, "stints_downloaded.pkl" if os.environ.get("ICE_DATA_DIR") else "stints_clean.pkl"))
    # Attach each facility's state and CBSA class to its stints.
    st = st.merge(fac[["detention_facility_code", "state", "cbsa_class"]].rename(columns={"state": "fstate"}),
                  on="detention_facility_code", how="left")
    # Facility state wins over the stint's own state.
    st["state"] = st.fstate.fillna(st.state)
    st = build_intervals(st, CUTOFF)
    rows = []
    # ADP by state and CBSA class for each calendar year, plus 2026 up to the cutoff.
    for y in YEARS + [2026]:
        w0 = pd.Timestamp(f"{y}-01-01")
        # 2026 ends the day after the last data date (Mar 11), since the window end is exclusive.
        w1 = pd.Timestamp(f"{y + 1}-01-01") if y < 2026 else pd.Timestamp("2026-03-12")
        # Wide table: one row per state, one column per CBSA class; missing combinations are 0.
        a = adp(st, w0, w1, keys=["state", "cbsa_class"]).unstack().fillna(0)
        a["year"] = y
        rows.append(a.reset_index())
    cls = pd.concat(rows)
    # Map each year to the matching population column label.
    pop_for = {2023: "2023", 2024: "2024", 2025: "2025", 2026: "2026 YTD (to Mar 11)"}
    # Convert each class's ADP to a rate per 100k residents of the facility's state.
    # States without a population row (e.g. territories) get NaN.
    for c, nm in [("Metropolitan", "det_metro"), ("Micropolitan", "det_micro"), ("Non-CBSA (rural)", "det_rural")]:
        cls[nm] = cls.apply(lambda r: r.get(c, 0) / pop_state.loc[r.state, pop_for[r.year]] * 1e5
                            if r.state in pop_state.index else np.nan, axis=1)
    cls = cls[["state", "year", "det_metro", "det_micro", "det_rural"]]

    # 2. Outcomes

    # State population by year (summed from counties): rows are states, columns are years.
    cp = load_county_pop()
    st_pop = cp.groupby(["state", "year"])["pop"].sum().unstack()
    # Two-digit state FIPS code -> state abbreviation, taken from the county file.
    fips_state = cp.assign(f2=cp.fips.str[:2]).drop_duplicates("f2").set_index("f2").state
    # Same map with integer keys, for files that store FIPS as numbers.
    state_by_fips_num = {int(k): v for k, v in fips_state.items() if str(k).isdigit()}

    # Youth share (ages 15-29) by state/year from the Census state agesex civilian file.
    youth_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sc-est2024-agesex-civ.csv")
    youth_raw = pd.read_csv(youth_path)
    # State-level rows (SUMLEV 40), both sexes combined (SEX 0), excluding the US total (STATE 0).
    youth_raw = youth_raw[(youth_raw["SUMLEV"] == 40) & (youth_raw["SEX"] == 0) & (youth_raw["STATE"] > 0)].copy()
    youth_raw["state"] = youth_raw["STATE"].map(state_by_fips_num)
    # The file covers 2020-2024, so 2025 rows rely on lagged values below.
    years_age = [2020, 2021, 2022, 2023, 2024]
    # Reshape to long form: one row per state, single year of age and year.
    youth_long = youth_raw.melt(id_vars=["state", "AGE"], value_vars=[f"POPEST{y}_CIV" for y in years_age],
                                var_name="year_col", value_name="pop")
    youth_long["year"] = youth_long.year_col.str.extract(r"POPEST(\d{4})_CIV").astype(int)
    # AGE 999 is the all-ages total in Census age files.
    tot = youth_long[youth_long.AGE == 999].set_index(["state", "year"])["pop"]
    young = youth_long[youth_long.AGE.between(15, 29)].groupby(["state", "year"])["pop"].sum()
    youth_share = (young / tot * 100).unstack()             # percent of state population ages 15-29
    youth_d_share = youth_share.diff(axis=1)                # year-over-year pp change

    # GDP (real, chained 2017 $)
    # BEA file; latin-1 handles non-UTF-8 characters in it.
    g = pd.read_csv(fetch("gdp.csv"), encoding="latin-1")
    require_columns(g, "gdp.csv")
    # Keep the real GDP rows (in millions of dollars).
    g = g[g.Description.str.startswith("Real GDP (millions", na=False)].copy()
    # State names -> abbreviations; rows that aren't states (regions, US total) become NaN and are dropped.
    g["state"] = g.GeoName.str.strip().map(STATE_ABBR | {"District of Columbia": "DC"})
    g = g.dropna(subset=["state"]).set_index("state")
    # Year columns may hold text markers; force them to numbers.
    for y in range(2021, 2026):
        g[str(y)] = pd.to_numeric(g[str(y)], errors="coerce")
    # States x years (integer column labels), 2021-2025.
    gdp = pd.DataFrame({y: g[str(y)] for y in range(2021, 2026)})

    # Unemployment (annual average of monthly seasonally adjusted rates)
    # Older years: BLS API JSON export.
    lo = pd.DataFrame(json.load(open(fetch("laus_old.json"))))
    require_columns(lo, "laus_old.json")
    # Keep monthly observations M01-M12 (drops the M13 annual-average rows).
    lo = lo[lo.period.str.match(r"M(0[1-9]|1[0-2])")]
    # Characters 5-6 of a LAUS series ID are the state FIPS code.
    lo["state"] = lo.series_id.str[5:7].map(fips_state)
    lo["rate"] = lo.value.astype(float)
    # Newer years: CSV export with a numeric GeoID; pad it back to two-digit FIPS.
    ln = pd.read_csv(fetch("laus_new.csv"))
    require_columns(ln, "laus_new.csv")
    ln["state"] = ln.GeoID.astype(int).astype(str).str.zfill(2).map(fips_state)
    ln = ln.rename(columns={"Year": "year", "Unemployment Rate": "rate"})
    # Stack both sources and drop anything unparseable.
    un = pd.concat([lo[["state", "year", "rate"]], ln[["state", "year", "rate"]]])
    un["rate"] = pd.to_numeric(un.rate, errors="coerce")
    un = un.dropna()
    # Annual average rate: rows are states, columns are years.
    unemp = un.groupby(["state", "year"]).rate.mean().unstack()

    # Crime: RTCI state sample (fixed agency sample, monthly counts) - rates per 100k sample population
    rt = pd.read_csv(fetch("rtci.csv"), low_memory=False)
    require_columns(rt, "rtci.csv")
    # State rows only: two-letter IDs, all agency sizes combined, excluding the national row.
    rt = rt[(rt.id.str.len() == 2) & (rt["size"] == "all") & (rt.id != "us")]
    rt["state"] = rt.id.str.upper()
    # Sum monthly counts to annual totals; average the sample population; count months reported.
    ann = rt.groupby(["state", "year"]).agg(v=("violent_total", "sum"), p=("property_total", "sum"),
                                             pop=("population", "mean"), months=("month", "nunique")).reset_index()
    # Only use complete years, so partial years don't look like crime drops.
    ann = ann[ann.months == 12]
    ann["violent_rate"] = ann.v / ann["pop"] * 1e5
    ann["property_rate"] = ann.p / ann["pop"] * 1e5
    # Rows are states, columns are years.
    viol = ann.pivot(index="state", columns="year", values="violent_rate")
    prop = ann.pivot(index="state", columns="year", values="property_rate")

    # FBI check (2022-2024 state rates)
    fb = pd.read_csv(fetch("fbi_crime.csv"))
    require_columns(fb, "fbi_crime.csv")
    # Normalize upper-case state names (title() turns "OF" into "Of"; fix it back to "of").
    fb["state"] = fb.state.str.title().str.replace("Of", "of").map(STATE_ABBR | {"District of Columbia": "DC"})
    fb = fb.dropna(subset=["state"])
    fviol = fb.pivot(index="state", columns="year", values="violent_crime_rate")
    fprop = fb.pivot(index="state", columns="year", values="property_crime_rate")

    # 3. Controls

    # ACS county estimates; FIPS kept as text so leading zeros survive.
    acs = pd.read_csv(fetch("acs.csv"), dtype={"FIPS": str})
    require_columns(acs, "acs.csv")
    acs["st"] = acs.FIPS.str[:2].map(fips_state)
    # Make the estimate columns numeric.
    for c in acs.columns[1:16]:
        acs[c] = pd.to_numeric(acs[c], errors="coerce")
    # The Census API uses large negative numbers as "not available" codes.
    acs.loc[acs.B19013_001E < 0, "B19013_001E"] = np.nan    # median household income
    acs.loc[acs.B01002_001E < 0, "B01002_001E"] = np.nan    # median age
    # County total population, used as weights.
    w = acs.B01003_001E


    def wmean(col):
        # Population-weighted state mean of a county-level column, skipping missing counties.
        # (An approximation for medians, which can't be aggregated exactly.)
        m = acs[col].notna()
        return (acs[col][m] * w[m]).groupby(acs.st[m]).sum() / w[m].groupby(acs.st[m]).sum()


    # One row per state with demographic and economic controls.
    ctl = pd.DataFrame({
        "med_age": wmean("B01002_001E"),
        "med_income": wmean("B19013_001E"),
        # Bachelor's, master's, professional and doctorate holders as a share of adults 25+.
        "pct_bach": acs.groupby("st").apply(lambda d: d[["B15003_022E", "B15003_023E", "B15003_024E", "B15003_025E"]].sum().sum()
                                           / d.B15003_001E.sum() * 100),
        # Hispanic or Latino share of total population.
        "pct_hisp": acs.groupby("st").apply(lambda d: d.B03002_012E.sum() / d.B03002_001E.sum() * 100),
        # Black or African American alone share of total population.
        "pct_black": acs.groupby("st").apply(lambda d: d.B02001_003E.sum() / d.B01003_001E.sum() * 100),
    })
    # Census Gazetteer file: land area per county, summed to states (for density).
    gz = pd.read_csv(fetch("gaz.txt"), sep="\t", dtype={"GEOID": str})
    # Gazetteer headers can carry trailing whitespace.
    gz.columns = [c.strip() for c in gz.columns]
    require_columns(gz, "gaz.txt")
    land = gz.groupby("USPS").ALAND_SQMI.sum()
    # County presidential returns; keep the 2024 presidential race.
    pr = pd.read_csv(fetch("pres.csv"), dtype={"county_fips": str})
    require_columns(pr, "pres.csv")
    pr = pr[(pr.year == 2024) & (pr.office == "US PRESIDENT")]
    gop = republican_vote_share(pr)
    # Stop if any state is missing the vote-share control.
    missing_votes = set(STATE_ABBR.values()) - set(gop.dropna().index)
    if missing_votes:
        raise ValueError(f"Election control missing jurisdictions: {sorted(missing_votes)}")

    # 4. Panel: outcome changes for years 2023, 2024, 2025

    recs = []
    # Only states that have both detention data and population data.
    for s in sorted(set(det.state) & set(st_pop.index)):
        for y in YEARS:
            r = {"state": s, "year": y, "era": ERA_OF[y], "region": region_of(s)}
            # Real GDP growth (%), and log GDP per capita in the prior year as a starting-level control.
            r["d_gdp"] = (gdp.loc[s, y] / gdp.loc[s, y - 1] - 1) * 100 if s in gdp.index else np.nan
            r["lag_gdp_pc"] = np.log(gdp.loc[s, y - 1] * 1e6 / st_pop.loc[s, y - 1]) if s in gdp.index else np.nan
            # Unemployment change (percentage points) and prior-year level.
            r["d_unemp"] = unemp.loc[s, y] - unemp.loc[s, y - 1] if s in unemp.index else np.nan
            r["lag_unemp"] = unemp.loc[s, y - 1] if s in unemp.index else np.nan
            # RTCI crime: percent change and prior-year rate, only when both years are complete.
            if s in viol.index and y in viol.columns and (y - 1) in viol.columns:
                r["d_violent"] = (viol.loc[s, y] / viol.loc[s, y - 1] - 1) * 100
                r["lag_violent"] = viol.loc[s, y - 1]
                r["d_property"] = (prop.loc[s, y] / prop.loc[s, y - 1] - 1) * 100
                r["lag_property"] = prop.loc[s, y - 1]
            # FBI crime changes, available for the old era only.
            if s in fviol.index and y in fviol.columns and (y - 1) in fviol.columns:
                r["d_violent_fbi"] = (fviol.loc[s, y] / fviol.loc[s, y - 1] - 1) * 100
                r["d_property_fbi"] = (fprop.loc[s, y] / fprop.loc[s, y - 1] - 1) * 100
            # Population size, growth and density controls.
            r["pop"] = st_pop.loc[s, y]
            r["ln_pop"] = np.log(st_pop.loc[s, y])
            r["pop_growth"] = (st_pop.loc[s, y] / st_pop.loc[s, y - 1] - 1) * 100
            r["ln_density"] = np.log(st_pop.loc[s, y] / land[s]) if s in land.index else np.nan
            # Use lagged youth-share level/change so 2025 rows can still use observed 2024 data.
            r["lag_youth15_29_pct"] = youth_share.loc[s, y - 1] if s in youth_share.index and (y - 1) in youth_share.columns else np.nan
            r["lag_d_youth15_29_pp"] = youth_d_share.loc[s, y - 1] if s in youth_d_share.index and (y - 1) in youth_d_share.columns else np.nan
            recs.append(r)
    panel = pd.DataFrame(recs)
    # Add overall, by-operator and by-location detention rates.
    panel = panel.merge(det, on=["state", "year"], how="left").merge(op, on=["state", "year"], how="left") \
                 .merge(cls, on=["state", "year"], how="left")
    # No detention recorded means zero detention, not missing data.
    for c in list(OPCOL.values()) + ["det_metro", "det_micro", "det_rural", "det_rate", "bookin_rate"]:
        panel[c] = panel[c].fillna(0)
    # All privately operated detention combined.
    panel["det_private"] = panel.det_corecivic + panel.det_geo + panel.det_otherpriv
    # Sort so diff() compares consecutive years within each state.
    panel = panel.sort_values(["state", "year"])
    # Year-over-year change in detention rate (NaN for each state's first year, 2023).
    panel["d_det_rate"] = panel.groupby("state").det_rate.diff()
    # Add the time-invariant state controls and 2024 GOP vote share.
    panel = panel.join(ctl, on="state").join(gop.rename("gop24"), on="state")
    panel["ln_income"] = np.log(panel.med_income)
    # Stop if any of the 50 states lacks a control value.
    require_control_coverage(panel, set(STATE_ABBR.values()) - {"DC"})
    for c in list(OPCOL.values()) + ["det_metro", "det_micro", "det_rural", "det_rate", "det_private", "d_det_rate"]:
        panel[c + "10"] = panel[c] / 10     # coefficients read "per +10 detention ADP per 100k residents"
    panel.round(4).to_csv(os.path.join(RESULTS, "state_year_panel.csv"), index=False)
    print("panel", panel.shape, "| states:", panel.state.nunique())
    # Quick check of yearly averages for the main variables.
    print(panel.groupby("year")[["det_rate", "d_gdp", "d_unemp", "d_violent", "d_property"]].mean().round(2))

    # 5. Correlations (Pearson + Spearman), overall and by region / era

    # Readable labels for outcomes (RTCI and FBI) and detention measures.
    OUT = {"d_gdp": "Real GDP growth (%)", "d_unemp": "Unemployment change (pp)",
           "d_violent": "Violent crime rate change (%)", "d_property": "Property (nonviolent) crime rate change (%)"}
    OUT_FBI = {"d_violent_fbi": "Violent crime change, FBI (%)", "d_property_fbi": "Property crime change, FBI (%)"}
    XS = {"det_rate": "Detention ADP per 100k", "d_det_rate": "Change in detention ADP per 100k",
          "det_ice": "ICE-run ADP per 100k", "det_corecivic": "CoreCivic ADP per 100k", "det_geo": "GEO ADP per 100k",
          "det_otherpriv": "Other-private ADP per 100k", "det_localstate": "Local/state-run ADP per 100k",
          "det_metro": "ADP per 100k in metro-area facilities", "det_micro": "ADP per 100k in micropolitan facilities",
          "det_rural": "ADP per 100k in non-CBSA facilities"}


    def corr_row(d, x, y):
        # Pearson and Spearman correlations between x and y, using complete pairs only.
        d = d[[x, y]].dropna()
        # Skip tiny samples or near-constant detention measures.
        if len(d) < 8 or d[x].nunique() < 3:
            return None
        pr_, pp = stats.pearsonr(d[x], d[y])
        sr, sp = stats.spearmanr(d[x], d[y])
        return {"n": len(d), "pearson_r": pr_, "pearson_p": pp, "spearman_rho": sr, "spearman_p": sp}


    crow = []
    # Groups to test: all states, then each region separately.
    groups = {"All states": panel}
    for r in sorted(panel.region.unique()):
        groups[f"Region: {r}"] = panel[panel.region == r]
    for era in ["Old", "New"]:
        for gname, gd in groups.items():
            sub = gd[gd.era == era]
            for yv, yl in {**OUT, **OUT_FBI}.items():
                # FBI data doesn't cover the new era.
                if era == "New" and yv.endswith("_fbi"):
                    continue
                for xv, xl in XS.items():
                    # Detention change only exists from 2024 on, so the old era uses 2024 alone.
                    # (The other two branches do the same thing.)
                    if xv == "d_det_rate" and era == "Old":
                        sub_ = sub[sub.year == 2024]
                    elif xv == "d_det_rate":
                        sub_ = sub
                    else:
                        sub_ = sub
                    res = corr_row(sub_, xv, yv)
                    if res:
                        crow.append({"era": era, "group": gname, "outcome": yl, "detention_measure": xl, **res})
    corr = pd.DataFrame(crow)
    # Benjamini-Hochberg false discovery rate adjustment across every correlation tested.
    corr["pearson_q_bh"] = multipletests(corr.pearson_p, method="fdr_bh")[1]
    corr["spearman_q_bh"] = multipletests(corr.spearman_p, method="fdr_bh")[1]
    corr.round(4).to_csv(os.path.join(RESULTS, "correlations.csv"), index=False)

    # 6. OLS associations (year effects, clustered panel / HC3 cross-sectional inference)

    # Prior-year level control for each outcome.
    LAG = {"d_gdp": "lag_gdp_pc", "d_unemp": "lag_unemp", "d_violent": "lag_violent", "d_property": "lag_property"}


    # Collected coefficient rows from every model.
    mrows = []


    def collect(model, n, outcome, era, spec):
        # Save every coefficient except the intercept and year dummies.
        for t in model.params.index:
            if t.startswith("C(year)") or t == "Intercept":
                continue
            mrows.append({"outcome": OUT.get(outcome, outcome), "era": era, "spec": spec, "term": t,
                          "n": n, **coefficient(model, t)})


    for yv in OUT:
        lag = LAG[yv]
        for era, sub in [("Old", panel[panel.era == "Old"]), ("New", panel[panel.era == "New"]), ("Pooled", panel)]:
            # Year fixed effects only when the sample spans more than one year (not for 2025 alone).
            fe = " + C(year)" if sub.year.nunique() > 1 else ""
            specs = {
                "M0 + lagged outcome": f"{yv} ~ det_rate10 + {lag}{fe}",
                "M1 bivariate": f"{yv} ~ det_rate10{fe}",
                "M2 + controls": f"{yv} ~ det_rate10 + {lag} + {CONTROLS}{fe}",
                # Detention split by who runs the facility (federal-run omitted).
                "M3 by operator": f"{yv} ~ det_ice10 + det_corecivic10 + det_geo10 + det_otherpriv10 + det_localstate10 + {lag} + {CONTROLS}{fe}",
                # Detention split by the facility's area type.
                "M4 by facility location": f"{yv} ~ det_metro10 + det_micro10 + det_rural10 + {lag} + {CONTROLS}{fe}",
            }
            for sp, f in specs.items():
                m, n = fit(f, sub)
                collect(m, n, yv, era, sp)
        # first-difference model: change in detention rate vs change in outcome
        for era, sub in [("Old", panel[panel.year == 2024]), ("New", panel[panel.year == 2025])]:
            m, n = fit(f"{yv} ~ d_det_rate10 + {lag} + {CONTROLS}", sub)
            collect(m, n, yv, era, "M5 first-difference")
        # era interaction: does the detention-outcome slope differ in the new era?
        # (The indicator is recreated each pass of the loop; the value doesn't change.)
        panel["new"] = (panel.era == "New").astype(int)
        m, n = fit(f"{yv} ~ det_rate10 + det_rate10:new + new + {lag} + {CONTROLS}", panel)
        collect(m, n, yv, "Pooled", "M6 era interaction")

    # FBI robustness (old era, years 2023 and 2024)
    # Prior-year FBI rates as lag controls.
    panel["lag_fbi_v"] = panel.apply(lambda r: fviol.loc[r.state, r.year - 1] if r.state in fviol.index and r.year - 1 in fviol.columns else np.nan, axis=1)
    panel["lag_fbi_p"] = panel.apply(lambda r: fprop.loc[r.state, r.year - 1] if r.state in fprop.index and r.year - 1 in fprop.columns else np.nan, axis=1)
    old = panel[panel.era == "Old"]
    for yv, lag in [("d_violent_fbi", "lag_fbi_v"), ("d_property_fbi", "lag_fbi_p")]:
        for sp, f in {"M1 bivariate": f"{yv} ~ det_rate10 + C(year)",
                      "M2 + controls": f"{yv} ~ det_rate10 + {lag} + {CONTROLS} + C(year)"}.items():
            m, n = fit(f, old)
            collect(m, n, yv, "Old", sp)
    reg = pd.DataFrame(mrows)
    # FBI outcomes were stored under their raw names; swap in readable labels.
    reg["outcome"] = reg.outcome.replace(OUT_FBI)
    # Unused: overwritten in section 7 before it is read.
    key = reg.term.str.contains("det_")
    # Multiple-testing adjustment applied to the main det_rate10 coefficients.
    reg = primary_bh(reg, "det_rate10")
    reg.round(5).to_csv(os.path.join(RESULTS, "regressions.csv"), index=False)

    # 7. Console summary of the key detention coefficients

    # Detention coefficients from the bivariate, controlled and first-difference models.
    key = reg[reg.term.str.contains("det_|d_det") & reg.spec.isin(["M1 bivariate", "M2 + controls", "M5 first-difference"])]
    print(key.round(3).to_string(index=False))
    # Nominally significant all-state correlations (unadjusted p-values).
    sig = corr[(corr.pearson_p < 0.05) & (corr.group == "All states")]
    print("\nSignificant (p<.05) all-state correlations:")
    print(sig.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
