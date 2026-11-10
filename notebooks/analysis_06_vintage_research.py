"""
Analysis #6 — Additional research on BOTH data vintages + vintage comparison.
  OLD = 7/24/2026 CSV extract (repo root);  NEW = Sept 2026 parquet release (data_updated/).

Run from the repo root (after python notebooks/fetch_latest_data.py):
    python notebooks/analysis_06_vintage_research.py
Figures -> notebooks/figures_06/.  Everything is descriptive.
Topics: arrest volume & backfill, arrest methods, AOR geography, age, final orders,
detainers, detention population (ADP), facilities, and open->closed stay revisions.
"""
import os
import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pyarrow.parquet as pq

sns.set_theme(style="whitegrid")
HERE = os.path.dirname(os.path.abspath(__file__))
FIGURES = os.path.join(HERE, "figures_06")
os.makedirs(FIGURES, exist_ok=True)
ENC = "latin-1"
BIDEN, TRUMP2 = pd.Timestamp("2021-01-20"), pd.Timestamp("2025-01-20")
MAX_DAYS = 1825
SMALL_N = 50
NEW_DIR = os.path.join(HERE, "..", "data_updated")


def savefig(name):
    path = os.path.join(FIGURES, name)
    plt.savefig(path, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def find_col(df, *candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load(old_csv, new_parquet, wanted):
    """Load a column subset (canonical name -> candidates) from OLD csv and NEW parquet."""
    out = {}
    for tag, path in [("old", old_csv), ("new", os.path.join(NEW_DIR, new_parquet))]:
        if path.endswith(".parquet"):
            names = pq.ParquetFile(path).schema_arrow.names
            pick = {k: next((c for c in v if c in names), None) for k, v in wanted.items()}
            pick = {k: v for k, v in pick.items() if v}
            df = pd.read_parquet(path, columns=list(pick.values()))
        else:
            names = list(pd.read_csv(path, nrows=0, encoding=ENC).columns)
            pick = {k: next((c for c in v if c in names), None) for k, v in wanted.items()}
            pick = {k: v for k, v in pick.items() if v}
            df = pd.read_csv(path, usecols=list(pick.values()), encoding=ENC, low_memory=False)
        out[tag] = df.rename(columns={v: k for k, v in pick.items()})
    return out


def utc_naive(s):
    s = pd.to_datetime(s, errors="coerce", utc=True)
    return s.dt.tz_localize(None)


def admin(d):
    a = pd.Series("Pre-Biden", index=d.index, dtype=object)
    a[d >= BIDEN] = "Biden"
    a[d >= TRUMP2] = "Trump 2nd"
    a[d.isna()] = np.nan
    return a


# =========================================================================
# 1. ARRESTS
# =========================================================================
print("=== 1. Arrests ===")
A = load("arrests-latest 7-24-2026.csv", "arrests-latest.parquet", {
    "date": ["apprehension_date"], "crim": ["apprehension_criminality"],
    "aor": ["apprehension_aor"], "state": ["apprehension_state_filled_in"],
    "method": ["apprehension_method"], "method_simple": ["apprehension_method_simple"],
    "birth_year": ["birth_year"], "age_new": ["age_at_apprehension_approximate"],
    "final_order": ["final_order_yes_no"], "fo_before": ["final_order_before_apprehension"],
    "dup": ["duplicate_drop_row"], "country": ["citizenship_country"], "gender": ["gender"],
})
for tag, d in A.items():
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    if "dup" in d:
        d["dup"] = d["dup"].astype(str).str.lower().eq("true")
        print(f"  [{tag}] rows {len(d):,}; duplicate_drop_row=True: {int(d['dup'].sum()):,}")
        A[tag] = d = d[~d["dup"]].copy()
    if tag == "old":   # one record is dated after the 7/24/2026 extraction (2026-09-17): data error, drop
        n_future = int((d["date"] > "2026-07-24").sum())
        print(f"  [old] dropping {n_future} arrest(s) dated after the 7/24/2026 extraction")
        A[tag] = d = d[d["date"] <= "2026-07-24"].copy()
    d["admin"] = admin(d["date"])
    d["month"] = d["date"].dt.to_period("M")
    print(f"  [{tag}] arrests kept {len(d):,}; dates {d['date'].min():%Y-%m-%d}..{d['date'].max():%Y-%m-%d}")

# 1a monthly volume, administration averages (full months only)
mon = {t: d.groupby("month").size() for t, d in A.items()}
last_full = {t: m.index.max() - 1 for t, m in mon.items()}
rows = []
for t, d in A.items():
    m = mon[t][mon[t].index <= last_full[t]]
    for a, lo, hi in [("Biden (Oct22-Jan25)", "2022-10", "2025-01"), ("Trump 2nd (Feb25+)", "2025-02", str(last_full[t]))]:
        mm = m[(m.index >= lo) & (m.index <= hi)]
        rows.append({"vintage": t, "period": a, "months": len(mm), "arrests": int(mm.sum()),
                     "per_month": round(mm.mean())})
print("\n  Arrests per month (full months):")
print(pd.DataFrame(rows).to_string(index=False))
peak = {t: (m.idxmax(), int(m.max())) for t, m in mon.items()}
print(f"  Peak month: old {peak['old']}, new {peak['new']}")

# 1b backfill: same months, old vs new
both = pd.DataFrame({"old": mon["old"], "new": mon["new"]}).fillna(0)
ov = both[(both.index >= "2022-10") & (both.index <= "2026-02")]
print(f"\n  Overlap 2022-10..2026-02: old {int(ov['old'].sum()):,} vs new {int(ov['new'].sum()):,} "
      f"(diff {int(ov['new'].sum() - ov['old'].sum()):+,}, {100*(ov['new'].sum()/ov['old'].sum()-1):+.1f}%)")
ov = ov.assign(diff=ov["new"] - ov["old"], pct=lambda t: 100 * t["diff"] / t["old"])
print("  Largest monthly revisions (new - old):")
print(ov.reindex(ov["diff"].abs().sort_values(ascending=False).index).head(6).round(1).to_string())

fig, ax = plt.subplots(figsize=(14, 5))
for t, c in [("old", "tab:blue"), ("new", "tab:red")]:
    m = mon[t][mon[t].index <= last_full[t]]
    ax.plot(m.index.to_timestamp(), m.values, label=f"{t} vintage", color=c)
for d_ in (BIDEN, TRUMP2):
    ax.axvline(d_, color="k", ls="--", lw=1)
ax.set(title="Monthly ICE arrests: old (7/24/2026) vs new (Sept 2026) data", ylabel="Arrests")
ax.legend()
plt.tight_layout()
savefig("arrests_monthly_old_vs_new.png")

# 1c arrest method (new has simplified variable; old raw top values)
print("\n  Arrest method (NEW simplified), share by administration (%):")
nm = A["new"].dropna(subset=["admin"])
nm = nm[nm["admin"].isin(["Biden", "Trump 2nd"])]
mt = (pd.crosstab(nm["admin"], nm["method_simple"].fillna("Missing"), normalize="index") * 100).round(1)
mt = mt[mt.max().sort_values(ascending=False).index[:8]]
print(mt.to_string())
print("  Arrest method (OLD raw), top 8 overall:")
print(A["old"]["method"].value_counts(normalize=True).head(8).mul(100).round(1).to_string())

fig, ax = plt.subplots(figsize=(10, 4))
mt.plot.barh(stacked=True, ax=ax, colormap="tab20")
ax.set(xlabel="% of arrests", ylabel="", title="Arrest method (simplified), by administration — new data")
ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8)
plt.tight_layout()
savefig("arrests_method_by_admin.png")

# 1d AOR geography
print("\n  Top 10 AORs by share of arrests, by administration (new data):")
aor = pd.crosstab(nm["aor"], nm["admin"], normalize="columns").mul(100).round(1)
aor["n_total"] = nm["aor"].value_counts()
aor["shift_pts"] = (aor["Trump 2nd"] - aor["Biden"]).round(1)
print(aor.sort_values("n_total", ascending=False).head(10).to_string())
print("  Biggest AOR share gainers/losers (pts, n_total>=5000):")
big = aor[aor["n_total"] >= 5000].sort_values("shift_pts")
print(big.head(3)[["Biden", "Trump 2nd", "shift_pts"]].to_string())
print(big.tail(3)[["Biden", "Trump 2nd", "shift_pts"]].to_string())

# 1e age
for tag, d in A.items():
    by = pd.to_numeric(d["birth_year"], errors="coerce")
    d["age"] = d["date"].dt.year - by
    d.loc[(d["age"] < 0) | (d["age"] > 100), "age"] = np.nan
print("\n  Age at arrest (apprehension year - birth_year), by administration:")
rows = []
for t, d in A.items():
    for a in ["Biden", "Trump 2nd"]:
        x = d[d["admin"] == a]["age"].dropna()
        rows.append({"vintage": t, "admin": a, "n": len(x), "median": x.median(), "mean": round(x.mean(), 1),
                     "pct_under_18": round(100 * (x < 18).mean(), 2), "pct_60plus": round(100 * (x >= 60).mean(), 2)})
print(pd.DataFrame(rows).to_string(index=False))
if "age_new" in A["new"].columns:
    x = pd.to_numeric(A["new"]["age_new"], errors="coerce")
    print(f"  New approximate-age variable: non-missing {x.notna().mean():.1%}, median {x.median():.0f}; "
          f"corr with birth-year age {x.corr(A['new']['age']):.3f}")

# 1f final order before apprehension (new) / final_order_yes_no (old)
print("\n  Final order at arrest:")
if "fo_before" in A["new"].columns:
    f = A["new"][A["new"]["admin"].isin(["Biden", "Trump 2nd"])]
    print(f"  NEW final_order_before_apprehension value counts: {f['fo_before'].value_counts(dropna=False).to_dict()}")
    f2 = f.assign(fo=f["fo_before"].astype(str).str.lower().isin(["true", "1", "yes", "y"]))
    print("  Share arrested with an existing final order (new):")
    print((f2.groupby("admin")["fo"].mean() * 100).round(1).to_string())
    print("  ... by apprehension criminality (Trump 2nd):")
    print((f2[f2["admin"] == "Trump 2nd"].groupby("crim")["fo"].mean() * 100).round(1).to_string())

# 1g nationality shift
print("\n  Top-10 nationalities share of arrests, Biden vs Trump 2nd (new data, %):")
nat = pd.crosstab(nm["country"], nm["admin"], normalize="columns").mul(100).round(1)
nat["n_total"] = nm["country"].value_counts()
print(nat.sort_values("n_total", ascending=False).head(10).to_string())
print("  Gender share female (%): " + ", ".join(
    f"{a} {100*(nm[nm['admin']==a]['gender'].astype(str).str.lower()=='female').mean():.1f}"
    for a in ["Biden", "Trump 2nd"]))
del A, nm

# =========================================================================
# 2. DETAINERS
# =========================================================================
print("\n=== 2. Detainers ===")
D = load("detainers-latest 7-24-2026.csv", "detainers-latest.parquet", {
    "date": ["detainer_prepare_date"], "crim": ["detainer_prepared_criminality"],
    "state": ["facility_state"], "type": ["detainer_type"], "dup": ["duplicate_drop_row"],
    "dup_likely": ["duplicate_likely"], "gender": ["gender"],
})
rows = []
for tag, d in D.items():
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    n0 = len(d)
    if "dup" in d.columns:
        d = d[~d["dup"].astype(str).str.lower().eq("true")]
    d = d.copy()
    d["month"] = d["date"].dt.to_period("M")
    d["admin"] = admin(d["date"])
    D[tag] = d
    print(f"  [{tag}] rows {n0:,} -> {len(d):,} after drop-dupes; dates {d['date'].min():%Y-%m-%d}..{d['date'].max():%Y-%m-%d}")
    lf = d["month"].max() - 1
    m = d.groupby("month").size()
    for a, lo, hi in [("Biden (Oct22-Jan25)", "2022-10", "2025-01"), ("Trump 2nd (Feb25+)", "2025-02", str(lf))]:
        mm = m[(m.index >= lo) & (m.index <= hi)]
        rows.append({"vintage": tag, "period": a, "per_month": round(mm.mean()), "total": int(mm.sum())})
print("  Detainers per month (full months):")
print(pd.DataFrame(rows).to_string(index=False))
nd = D["new"][D["new"]["admin"].isin(["Biden", "Trump 2nd"])]
print("\n  Detainer criminality mix by administration (new, %):")
print((pd.crosstab(nd["admin"], nd["crim"].fillna("Missing"), normalize="index") * 100).round(1).to_string())
print("  Top detainer types by administration (new, %):")
tt = (pd.crosstab(nd["admin"], nd["type"].fillna("Missing"), normalize="index") * 100).round(1)
print(tt[tt.max().sort_values(ascending=False).index[:5]].to_string())
print("  Top 8 facility states for detainers (new, share % Biden vs Trump 2nd):")
st = pd.crosstab(nd["state"], nd["admin"], normalize="columns").mul(100).round(1)
st["n"] = nd["state"].value_counts()
print(st.sort_values("n", ascending=False).head(8).to_string())
fig, ax = plt.subplots(figsize=(14, 4.5))
for t, c in [("old", "tab:blue"), ("new", "tab:red")]:
    d = D[t]
    m = d.groupby("month").size()
    m = m[(m.index >= "2022-10") & (m.index <= d["month"].max() - 1)]
    ax.plot(m.index.to_timestamp(), m.values, label=f"{t} vintage", color=c)
ax.axvline(TRUMP2, color="k", ls="--", lw=1)
ax.set(title="Monthly detainers prepared: old vs new data", ylabel="Detainers")
ax.legend()
plt.tight_layout()
savefig("detainers_monthly_old_vs_new.png")
del D, nd

# =========================================================================
# 3. DETENTION STAYS: population, facilities, revisions
# =========================================================================
print("\n=== 3. Detention stays ===")
sw = {"uid": ["unique_identifier"], "by": ["birth_year"], "gen": ["gender"], "bi": ["stay_book_in_date_time"], "bo": ["stay_book_out_date_time"],
      "fac": ["detention_facility_longest"], "state": ["state_longest", "detention_facility_state_longest"],
      "crim": ["book_in_criminality"], "country": ["citizenship_country"]}
old_parts = []
for f in ["detention-stays (sheet 1) 7-24-2026.csv", "detention-stays (sheet 2) 7-24-2026.csv"]:
    names = list(pd.read_csv(f, nrows=0, encoding=ENC).columns)
    pick = {k: next((c for c in v if c in names), None) for k, v in sw.items()}
    pick = {k: v for k, v in pick.items() if v}
    old_parts.append(pd.read_csv(f, usecols=list(pick.values()), encoding=ENC, low_memory=False)
                     .rename(columns={v: k for k, v in pick.items()}))
S = {"old": pd.concat(old_parts, ignore_index=True)}
del old_parts
path = os.path.join(NEW_DIR, "detention-stays-latest.parquet")
names = pq.ParquetFile(path).schema_arrow.names
pick = {k: next((c for c in v if c in names), None) for k, v in sw.items()}
pick = {k: v for k, v in pick.items() if v}
S["new"] = pd.read_parquet(path, columns=list(pick.values())).rename(columns={v: k for k, v in pick.items()})

for tag, d in S.items():
    d["bi"], d["bo"] = utc_naive(d["bi"]), utc_naive(d["bo"])
    # unique_identifier / stay_ID are re-anonymized between vintages (zero shared IDs), so link stays
    # on book-in minute + birth year + citizenship + gender; keep only keys unique in BOTH vintages
    d["id"] = (d["bi"].dt.strftime("%Y-%m-%d %H:%M") + "|" + pd.to_numeric(d["by"], errors="coerce").astype("Int64").astype(str)
               + "|" + d["country"].astype(str).str.upper() + "|" + d["gen"].astype(str).str.upper())
    d["days"] = (d["bo"] - d["bi"]).dt.total_seconds() / 86400
    print(f"  [{tag}] stays {len(d):,}; book-ins {d['bi'].min():%Y-%m-%d}..{d['bi'].max():%Y-%m-%d}; open {d['bo'].isna().mean():.1%}")

# 3a average daily population (ADP) by month, from book-in/out, stale open stays dropped
def adp(d):
    end = d["bi"].max().normalize()
    x = d[d["bi"].notna()].copy()
    x["bo2"] = x["bo"].fillna(end + pd.Timedelta(days=1))
    x = x[((x["bo2"] - x["bi"]).dt.days <= MAX_DAYS) & (x["bo2"] >= x["bi"])]
    days = pd.date_range("2022-10-01", end)
    ins = x["bi"].dt.normalize().value_counts().reindex(days, fill_value=0)
    outs = x["bo2"].dt.normalize().value_counts().reindex(days, fill_value=0)
    base = ((x["bi"] < days[0]) & (x["bo2"] >= days[0])).sum()
    pop = base + (ins - outs).cumsum()
    return pop

pops = {t: adp(d) for t, d in S.items()}
rows = []
for t, p in pops.items():
    mm = p.groupby(p.index.to_period("M")).mean()
    rows.append({"vintage": t, "peak_daily_pop": int(p.max()), "peak_date": p.idxmax().date(),
                 "pop_2025-01": round(mm.get(pd.Period("2025-01"), np.nan)),
                 "pop_2025-06": round(mm.get(pd.Period("2025-06"), np.nan)),
                 "pop_2026-01": round(mm.get(pd.Period("2026-01"), np.nan)),
                 "pop_last_full_month": round(mm.iloc[-2]), "last_month": str(mm.index[-2])})
print("\n  Reconstructed detention population (stays with plausible duration; open stays held to data end):")
print(pd.DataFrame(rows).to_string(index=False))
print("  Biden-era mean daily pop (Oct22-Jan25): " + ", ".join(
    f"{t}: {pops[t][:'2025-01-19'].mean():,.0f}" for t in pops))
fig, ax = plt.subplots(figsize=(14, 5))
for t, c in [("old", "tab:blue"), ("new", "tab:red")]:
    ax.plot(pops[t].index, pops[t].values, label=f"{t} vintage", color=c)
for d_ in (BIDEN, TRUMP2):
    ax.axvline(d_, color="k", ls="--", lw=1)
ax.set(title="Reconstructed daily detention population (from stay book-in/out)", ylabel="People in detention")
ax.legend()
plt.tight_layout()
savefig("detention_population_old_vs_new.png")

# 3b facilities: stays and median stay (new), n>=500
n = S["new"]
rel = n[n["bo"].notna() & n["days"].between(0, MAX_DAYS)]
fac = rel.groupby("fac").agg(stays=("days", "size"), median_days=("days", "median"), mean_days=("days", "mean")).round(1)
fac = fac[fac["stays"] >= 500]
print(f"\n  Facilities with >=500 released stays (new data): {len(fac)}")
print("  Longest median stays:")
print(fac.sort_values("median_days", ascending=False).head(8).to_string())
print("  Shortest median stays:")
print(fac.sort_values("median_days").head(5).to_string())
print("  Busiest facilities by stays:")
print(fac.sort_values("stays", ascending=False).head(8).to_string())
print("  Stays by facility state, top 8 (share %):")
print((n["state"].value_counts(normalize=True).head(8) * 100).round(1).to_string())
print(f"  Share of stays in TX+LA: {100*n['state'].isin(['TX','LA']).mean():.1f}%")

# 3c revisions: open stays in OLD that are closed in NEW
if S["old"]["id"].notna().any() and S["new"]["id"].notna().any():
    print(f"\n  Shared unique_identifier values between vintages: "
          f"{len(set(S['old']['uid']) & set(S['new']['uid'])):,} (IDs are re-anonymized each release)")
    o = S["old"][~S["old"]["id"].duplicated(keep=False)].set_index("id")
    nw = S["new"][~S["new"]["id"].duplicated(keep=False)].set_index("id")
    common = o.index.intersection(nw.index)
    print(f"  Linked on composite key (unique in both): old {len(o):,}, new {len(nw):,}, matched {len(common):,}")
    oo, nn = o.loc[common], nw.loc[common]
    was_open = oo["bo"].isna()
    now_closed = nn["bo"].notna()
    print(f"  Open in old: {int(was_open.sum()):,}; of these now closed in new: {int((was_open & now_closed).sum()):,} "
          f"({100*(was_open & now_closed).sum()/max(was_open.sum(),1):.1f}%)")
    x = nn[was_open & now_closed]
    dd = (x["bo"] - x["bi"]).dt.total_seconds() / 86400
    print(f"  Duration of those newly closed stays: median {dd.median():.1f}d, mean {dd.mean():.1f}d, p90 {dd.quantile(.9):.1f}d")
    both_closed = oo["bo"].notna() & nn["bo"].notna()
    chg = (oo.loc[both_closed, "bo"] != nn.loc[both_closed, "bo"]).sum()
    print(f"  Closed in both: {int(both_closed.sum()):,}; book-out date changed in {int(chg):,}")
    in_range = oo["bo"].isna() & ~nn["bo"].notna()
    print(f"  Still open in both: {int(in_range.sum()):,}")
    ob = o.loc[o.index.difference(nw.index)]
    print(f"  Old-only stays: n={len(ob):,}; book-in range {ob['bi'].min()}..{ob['bi'].max()}")
    # long-run summary
    for t, d in S.items():
        r = d[d["bo"].notna() & d["days"].between(0, MAX_DAYS)]
        print(f"  [{t}] released stays {len(r):,}; median {r['days'].median():.1f}d; mean {r['days'].mean():.1f}d")
    # open-stay median time in custody
    for t, d in S.items():
        end = d["bi"].max()
        op = d[d["bo"].isna()]
        print(f"  [{t}] open {len(op):,}; median days since book-in (to data end) "
              f"{((end-op['bi']).dt.total_seconds()/86400).median():.1f}")
print("\nDone.")
