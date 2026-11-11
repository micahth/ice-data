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

from geo_common import (ABBR_STATE, RESULTS, STATE_ABBR, fetch, load_county_pop, region_of, require_columns)
from ice_lib import adp, build_intervals
from geo_common import CUTOFF
from regression_common import CONTROLS, coefficient, fit, primary_bh, republican_vote_share, require_control_coverage


def main():

    pd.set_option("display.width", 220, "display.max_columns", 40)
    YEARS = [2023, 2024, 2025]
    ERA_OF = {2023: "Old", 2024: "Old", 2025: "New"}

    # ---------------------------------------------------------------------------
    # 1. Detention exposure (state x year)
    # ---------------------------------------------------------------------------
    bs = pd.read_csv(os.path.join(RESULTS, "by_state.csv"))
    bs = bs[bs.period.isin(["2023", "2024", "2025", "2026 YTD (to Mar 11)"])].copy()
    bs["year"] = bs.period.str[:4].astype(int)
    det = bs[["state", "year", "adp", "adp_per_100k", "book_ins_per_100k_annualized"]].rename(
        columns={"adp": "adp", "adp_per_100k": "det_rate", "book_ins_per_100k_annualized": "bookin_rate"})

    bso = pd.read_csv(os.path.join(RESULTS, "by_state_operator.csv"))
    bso = bso[bso.period.isin(["2023", "2024", "2025", "2026 YTD (to Mar 11)"])].copy()
    bso["year"] = bso.period.str[:4].astype(int)
    OPCOL = {"ICE": "det_ice", "CoreCivic": "det_corecivic", "GEO Group": "det_geo", "Other private": "det_otherpriv",
             "Local/state government": "det_localstate", "Federal (BOP/CBP/other)": "det_federal"}
    bso = bso[bso.operator.isin(OPCOL)]
    op = bso.pivot_table(index=["state", "year"], columns="operator", values="adp_per_100k").rename(columns=OPCOL)
    op = op.reset_index()

    # detention by CBSA class of the facility, per 100k state residents
    fac = pd.read_csv(os.path.join(RESULTS, "facility_classification.csv"))
    pop_state = pd.read_csv(os.path.join(RESULTS, "state_population_by_period.csv"), index_col=0)
    # state x cbsa_class ADP computed in script 05 is not stored per state, so rebuild it from stints cache
    cache = os.environ.get("GEO_CACHE", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache"))
    st = pd.read_pickle(os.path.join(cache, "stints_downloaded.pkl" if os.environ.get("ICE_DATA_DIR") else "stints_clean.pkl"))
    st = st.merge(fac[["detention_facility_code", "state", "cbsa_class"]].rename(columns={"state": "fstate"}),
                  on="detention_facility_code", how="left")
    st["state"] = st.fstate.fillna(st.state)
    st = build_intervals(st, CUTOFF)
    rows = []
    for y in YEARS + [2026]:
        w0 = pd.Timestamp(f"{y}-01-01")
        w1 = pd.Timestamp(f"{y + 1}-01-01") if y < 2026 else pd.Timestamp("2026-03-12")
        a = adp(st, w0, w1, keys=["state", "cbsa_class"]).unstack().fillna(0)
        a["year"] = y
        rows.append(a.reset_index())
    cls = pd.concat(rows)
    pop_for = {2023: "2023", 2024: "2024", 2025: "2025", 2026: "2026 YTD (to Mar 11)"}
    for c, nm in [("Metropolitan", "det_metro"), ("Micropolitan", "det_micro"), ("Non-CBSA (rural)", "det_rural")]:
        cls[nm] = cls.apply(lambda r: r.get(c, 0) / pop_state.loc[r.state, pop_for[r.year]] * 1e5
                            if r.state in pop_state.index else np.nan, axis=1)
    cls = cls[["state", "year", "det_metro", "det_micro", "det_rural"]]

    # ---------------------------------------------------------------------------
    # 2. Outcomes
    # ---------------------------------------------------------------------------
    cp = load_county_pop()
    st_pop = cp.groupby(["state", "year"])["pop"].sum().unstack()
    fips_state = cp.assign(f2=cp.fips.str[:2]).drop_duplicates("f2").set_index("f2").state
    state_by_fips_num = {int(k): v for k, v in fips_state.items() if str(k).isdigit()}

    # Youth share (ages 15-29) by state/year from the Census state agesex civilian file.
    youth_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sc-est2024-agesex-civ.csv")
    youth_raw = pd.read_csv(youth_path)
    youth_raw = youth_raw[(youth_raw["SUMLEV"] == 40) & (youth_raw["SEX"] == 0) & (youth_raw["STATE"] > 0)].copy()
    youth_raw["state"] = youth_raw["STATE"].map(state_by_fips_num)
    years_age = [2020, 2021, 2022, 2023, 2024]
    youth_long = youth_raw.melt(id_vars=["state", "AGE"], value_vars=[f"POPEST{y}_CIV" for y in years_age],
                                var_name="year_col", value_name="pop")
    youth_long["year"] = youth_long.year_col.str.extract(r"POPEST(\d{4})_CIV").astype(int)
    tot = youth_long[youth_long.AGE == 999].set_index(["state", "year"])["pop"]
    young = youth_long[youth_long.AGE.between(15, 29)].groupby(["state", "year"])["pop"].sum()
    youth_share = (young / tot * 100).unstack()             # percent of state population ages 15-29
    youth_d_share = youth_share.diff(axis=1)                # year-over-year pp change

    # GDP (real, chained 2017 $)
    g = pd.read_csv(fetch("gdp.csv"), encoding="latin-1")
    require_columns(g, "gdp.csv")
    g = g[g.Description.str.startswith("Real GDP (millions", na=False)].copy()
    g["state"] = g.GeoName.str.strip().map(STATE_ABBR | {"District of Columbia": "DC"})
    g = g.dropna(subset=["state"]).set_index("state")
    for y in range(2021, 2026):
        g[str(y)] = pd.to_numeric(g[str(y)], errors="coerce")
    gdp = pd.DataFrame({y: g[str(y)] for y in range(2021, 2026)})

    # Unemployment (annual average of monthly seasonally adjusted rates)
    lo = pd.DataFrame(json.load(open(fetch("laus_old.json"))))
    require_columns(lo, "laus_old.json")
    lo = lo[lo.period.str.match(r"M(0[1-9]|1[0-2])")]
    lo["state"] = lo.series_id.str[5:7].map(fips_state)
    lo["rate"] = lo.value.astype(float)
    ln = pd.read_csv(fetch("laus_new.csv"))
    require_columns(ln, "laus_new.csv")
    ln["state"] = ln.GeoID.astype(int).astype(str).str.zfill(2).map(fips_state)
    ln = ln.rename(columns={"Year": "year", "Unemployment Rate": "rate"})
    un = pd.concat([lo[["state", "year", "rate"]], ln[["state", "year", "rate"]]])
    un["rate"] = pd.to_numeric(un.rate, errors="coerce")
    un = un.dropna()
    unemp = un.groupby(["state", "year"]).rate.mean().unstack()

    # Crime: RTCI state sample (fixed agency sample, monthly counts) - rates per 100k sample population
    rt = pd.read_csv(fetch("rtci.csv"), low_memory=False)
    require_columns(rt, "rtci.csv")
    rt = rt[(rt.id.str.len() == 2) & (rt["size"] == "all") & (rt.id != "us")]
    rt["state"] = rt.id.str.upper()
    ann = rt.groupby(["state", "year"]).agg(v=("violent_total", "sum"), p=("property_total", "sum"),
                                             pop=("population", "mean"), months=("month", "nunique")).reset_index()
    ann = ann[ann.months == 12]
    ann["violent_rate"] = ann.v / ann["pop"] * 1e5
    ann["property_rate"] = ann.p / ann["pop"] * 1e5
    viol = ann.pivot(index="state", columns="year", values="violent_rate")
    prop = ann.pivot(index="state", columns="year", values="property_rate")

    # FBI check (2022-2024 state rates)
    fb = pd.read_csv(fetch("fbi_crime.csv"))
    require_columns(fb, "fbi_crime.csv")
    fb["state"] = fb.state.str.title().str.replace("Of", "of").map(STATE_ABBR | {"District of Columbia": "DC"})
    fb = fb.dropna(subset=["state"])
    fviol = fb.pivot(index="state", columns="year", values="violent_crime_rate")
    fprop = fb.pivot(index="state", columns="year", values="property_crime_rate")

    # ---------------------------------------------------------------------------
    # 3. Controls
    # ---------------------------------------------------------------------------
    acs = pd.read_csv(fetch("acs.csv"), dtype={"FIPS": str})
    require_columns(acs, "acs.csv")
    acs["st"] = acs.FIPS.str[:2].map(fips_state)
    for c in acs.columns[1:16]:
        acs[c] = pd.to_numeric(acs[c], errors="coerce")
    acs.loc[acs.B19013_001E < 0, "B19013_001E"] = np.nan
    acs.loc[acs.B01002_001E < 0, "B01002_001E"] = np.nan
    w = acs.B01003_001E


    def wmean(col):
        m = acs[col].notna()
        return (acs[col][m] * w[m]).groupby(acs.st[m]).sum() / w[m].groupby(acs.st[m]).sum()


    ctl = pd.DataFrame({
        "med_age": wmean("B01002_001E"),
        "med_income": wmean("B19013_001E"),
        "pct_bach": acs.groupby("st").apply(lambda d: d[["B15003_022E", "B15003_023E", "B15003_024E", "B15003_025E"]].sum().sum()
                                           / d.B15003_001E.sum() * 100),
        "pct_hisp": acs.groupby("st").apply(lambda d: d.B03002_012E.sum() / d.B03002_001E.sum() * 100),
        "pct_black": acs.groupby("st").apply(lambda d: d.B02001_003E.sum() / d.B01003_001E.sum() * 100),
    })
    gz = pd.read_csv(fetch("gaz.txt"), sep="\t", dtype={"GEOID": str})
    gz.columns = [c.strip() for c in gz.columns]
    require_columns(gz, "gaz.txt")
    land = gz.groupby("USPS").ALAND_SQMI.sum()
    pr = pd.read_csv(fetch("pres.csv"), dtype={"county_fips": str})
    require_columns(pr, "pres.csv")
    pr = pr[(pr.year == 2024) & (pr.office == "US PRESIDENT")]
    gop = republican_vote_share(pr)
    missing_votes = set(STATE_ABBR.values()) - set(gop.dropna().index)
    if missing_votes:
        raise ValueError(f"Election control missing jurisdictions: {sorted(missing_votes)}")

    # ---------------------------------------------------------------------------
    # 4. Panel: outcome changes for years 2023, 2024, 2025
    # ---------------------------------------------------------------------------
    recs = []
    for s in sorted(set(det.state) & set(st_pop.index)):
        for y in YEARS:
            r = {"state": s, "year": y, "era": ERA_OF[y], "region": region_of(s)}
            r["d_gdp"] = (gdp.loc[s, y] / gdp.loc[s, y - 1] - 1) * 100 if s in gdp.index else np.nan
            r["lag_gdp_pc"] = np.log(gdp.loc[s, y - 1] * 1e6 / st_pop.loc[s, y - 1]) if s in gdp.index else np.nan
            r["d_unemp"] = unemp.loc[s, y] - unemp.loc[s, y - 1] if s in unemp.index else np.nan
            r["lag_unemp"] = unemp.loc[s, y - 1] if s in unemp.index else np.nan
            if s in viol.index and y in viol.columns and (y - 1) in viol.columns:
                r["d_violent"] = (viol.loc[s, y] / viol.loc[s, y - 1] - 1) * 100
                r["lag_violent"] = viol.loc[s, y - 1]
                r["d_property"] = (prop.loc[s, y] / prop.loc[s, y - 1] - 1) * 100
                r["lag_property"] = prop.loc[s, y - 1]
            if s in fviol.index and y in fviol.columns and (y - 1) in fviol.columns:
                r["d_violent_fbi"] = (fviol.loc[s, y] / fviol.loc[s, y - 1] - 1) * 100
                r["d_property_fbi"] = (fprop.loc[s, y] / fprop.loc[s, y - 1] - 1) * 100
            r["pop"] = st_pop.loc[s, y]
            r["ln_pop"] = np.log(st_pop.loc[s, y])
            r["pop_growth"] = (st_pop.loc[s, y] / st_pop.loc[s, y - 1] - 1) * 100
            r["ln_density"] = np.log(st_pop.loc[s, y] / land[s]) if s in land.index else np.nan
            # Use lagged youth-share level/change so 2025 rows can still use observed 2024 data.
            r["lag_youth15_29_pct"] = youth_share.loc[s, y - 1] if s in youth_share.index and (y - 1) in youth_share.columns else np.nan
            r["lag_d_youth15_29_pp"] = youth_d_share.loc[s, y - 1] if s in youth_d_share.index and (y - 1) in youth_d_share.columns else np.nan
            recs.append(r)
    panel = pd.DataFrame(recs)
    panel = panel.merge(det, on=["state", "year"], how="left").merge(op, on=["state", "year"], how="left") \
                 .merge(cls, on=["state", "year"], how="left")
    for c in list(OPCOL.values()) + ["det_metro", "det_micro", "det_rural", "det_rate", "bookin_rate"]:
        panel[c] = panel[c].fillna(0)
    panel["det_private"] = panel.det_corecivic + panel.det_geo + panel.det_otherpriv
    panel = panel.sort_values(["state", "year"])
    panel["d_det_rate"] = panel.groupby("state").det_rate.diff()
    panel = panel.join(ctl, on="state").join(gop.rename("gop24"), on="state")
    panel["ln_income"] = np.log(panel.med_income)
    require_control_coverage(panel, set(STATE_ABBR.values()) - {"DC"})
    for c in list(OPCOL.values()) + ["det_metro", "det_micro", "det_rural", "det_rate", "det_private", "d_det_rate"]:
        panel[c + "10"] = panel[c] / 10     # coefficients read "per +10 detention ADP per 100k residents"
    panel.round(4).to_csv(os.path.join(RESULTS, "state_year_panel.csv"), index=False)
    print("panel", panel.shape, "| states:", panel.state.nunique())
    print(panel.groupby("year")[["det_rate", "d_gdp", "d_unemp", "d_violent", "d_property"]].mean().round(2))

    # ---------------------------------------------------------------------------
    # 5. Correlations (Pearson + Spearman), overall and by region / era
    # ---------------------------------------------------------------------------
    OUT = {"d_gdp": "Real GDP growth (%)", "d_unemp": "Unemployment change (pp)",
           "d_violent": "Violent crime rate change (%)", "d_property": "Property (nonviolent) crime rate change (%)"}
    OUT_FBI = {"d_violent_fbi": "Violent crime change, FBI (%)", "d_property_fbi": "Property crime change, FBI (%)"}
    XS = {"det_rate": "Detention ADP per 100k", "d_det_rate": "Change in detention ADP per 100k",
          "det_ice": "ICE-run ADP per 100k", "det_corecivic": "CoreCivic ADP per 100k", "det_geo": "GEO ADP per 100k",
          "det_otherpriv": "Other-private ADP per 100k", "det_localstate": "Local/state-run ADP per 100k",
          "det_metro": "ADP per 100k in metro-area facilities", "det_micro": "ADP per 100k in micropolitan facilities",
          "det_rural": "ADP per 100k in non-CBSA facilities"}


    def corr_row(d, x, y):
        d = d[[x, y]].dropna()
        if len(d) < 8 or d[x].nunique() < 3:
            return None
        pr_, pp = stats.pearsonr(d[x], d[y])
        sr, sp = stats.spearmanr(d[x], d[y])
        return {"n": len(d), "pearson_r": pr_, "pearson_p": pp, "spearman_rho": sr, "spearman_p": sp}


    crow = []
    groups = {"All states": panel}
    for r in sorted(panel.region.unique()):
        groups[f"Region: {r}"] = panel[panel.region == r]
    for era in ["Old", "New"]:
        for gname, gd in groups.items():
            sub = gd[gd.era == era]
            for yv, yl in {**OUT, **OUT_FBI}.items():
                if era == "New" and yv.endswith("_fbi"):
                    continue
                for xv, xl in XS.items():
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
    corr["pearson_q_bh"] = multipletests(corr.pearson_p, method="fdr_bh")[1]
    corr["spearman_q_bh"] = multipletests(corr.spearman_p, method="fdr_bh")[1]
    corr.round(4).to_csv(os.path.join(RESULTS, "correlations.csv"), index=False)

    # ---------------------------------------------------------------------------
    # 6. OLS associations (year effects, clustered panel / HC3 cross-sectional inference)
    # ---------------------------------------------------------------------------
    LAG = {"d_gdp": "lag_gdp_pc", "d_unemp": "lag_unemp", "d_violent": "lag_violent", "d_property": "lag_property"}


    mrows = []


    def collect(model, n, outcome, era, spec):
        for t in model.params.index:
            if t.startswith("C(year)") or t == "Intercept":
                continue
            mrows.append({"outcome": OUT.get(outcome, outcome), "era": era, "spec": spec, "term": t,
                          "n": n, **coefficient(model, t)})


    for yv in OUT:
        lag = LAG[yv]
        for era, sub in [("Old", panel[panel.era == "Old"]), ("New", panel[panel.era == "New"]), ("Pooled", panel)]:
            fe = " + C(year)" if sub.year.nunique() > 1 else ""
            specs = {
                "M0 + lagged outcome": f"{yv} ~ det_rate10 + {lag}{fe}",
                "M1 bivariate": f"{yv} ~ det_rate10{fe}",
                "M2 + controls": f"{yv} ~ det_rate10 + {lag} + {CONTROLS}{fe}",
                "M3 by operator": f"{yv} ~ det_ice10 + det_corecivic10 + det_geo10 + det_otherpriv10 + det_localstate10 + {lag} + {CONTROLS}{fe}",
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
        panel["new"] = (panel.era == "New").astype(int)
        m, n = fit(f"{yv} ~ det_rate10 + det_rate10:new + new + {lag} + {CONTROLS}", panel)
        collect(m, n, yv, "Pooled", "M6 era interaction")

    # FBI robustness (old era, years 2023 and 2024)
    panel["lag_fbi_v"] = panel.apply(lambda r: fviol.loc[r.state, r.year - 1] if r.state in fviol.index and r.year - 1 in fviol.columns else np.nan, axis=1)
    panel["lag_fbi_p"] = panel.apply(lambda r: fprop.loc[r.state, r.year - 1] if r.state in fprop.index and r.year - 1 in fprop.columns else np.nan, axis=1)
    old = panel[panel.era == "Old"]
    for yv, lag in [("d_violent_fbi", "lag_fbi_v"), ("d_property_fbi", "lag_fbi_p")]:
        for sp, f in {"M1 bivariate": f"{yv} ~ det_rate10 + C(year)",
                      "M2 + controls": f"{yv} ~ det_rate10 + {lag} + {CONTROLS} + C(year)"}.items():
            m, n = fit(f, old)
            collect(m, n, yv, "Old", sp)
    reg = pd.DataFrame(mrows)
    reg["outcome"] = reg.outcome.replace(OUT_FBI)
    key = reg.term.str.contains("det_")
    reg = primary_bh(reg, "det_rate10")
    reg.round(5).to_csv(os.path.join(RESULTS, "regressions.csv"), index=False)

    # ---------------------------------------------------------------------------
    # 7. Console summary of the key detention coefficients
    # ---------------------------------------------------------------------------
    key = reg[reg.term.str.contains("det_|d_det") & reg.spec.isin(["M1 bivariate", "M2 + controls", "M5 first-difference"])]
    print(key.round(3).to_string(index=False))
    sig = corr[(corr.pearson_p < 0.05) & (corr.group == "All states")]
    print("\nSignificant (p<.05) all-state correlations:")
    print(sig.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
