"""
Analysis #5 — "Who Gets Out?"  Release & Bond Equity Analysis
ICE detention data (Deportation Data Project), extracted 7/24/2026.

Run from the repo root:
    python notebooks/analysis_05_release_outcomes.py            # 7/24/2026 CSV extract
    python notebooks/analysis_05_release_outcomes.py updated    # newer parquet data in data_updated/
                                                                # (fetch with notebooks/fetch_latest_data.py)
Figures are saved to notebooks/figures/ (or notebooks/figures_updated/ for "updated").

Memory-safe: every CSV is read in chunks with a column subset; only the
reduced frame is kept in memory. All results are descriptive (no causal claims).
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")  # headless — no display needed

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
HERE = os.path.dirname(os.path.abspath(__file__))
UPDATED = len(sys.argv) > 1 and sys.argv[1] == "updated"
FIGURES = os.path.join(HERE, "figures_updated" if UPDATED else "figures")
os.makedirs(FIGURES, exist_ok=True)

# ---------------------------------------------------------------------------
# Constants / analysis parameters
# ---------------------------------------------------------------------------
EXTRACT_DATE = pd.Timestamp("2026-07-24")     # data extraction date (re-derived for "updated")
BIDEN_START = pd.Timestamp("2021-01-20")      # administration boundaries
TRUMP2_START = pd.Timestamp("2025-01-20")
MAX_PLAUSIBLE_DAYS = 1825                     # released stays: keep 0..5 years
SMALL_N = 50                                  # groups below this are "unreliable"
CHUNKSIZE = 500_000
ENC = "latin-1"

if UPDATED:
    JOINED = os.path.join(HERE, "..", "data_updated", "joined-arrests-detention-stays-latest.parquet")
    STAYS = [os.path.join(HERE, "..", "data_updated", "detention-stays-latest.parquet")]
else:
    JOINED = "joined-arrests-detention-stays-latest 7-24-2026.csv"
    STAYS = ["detention-stays (sheet 1) 7-24-2026.csv",
             "detention-stays (sheet 2) 7-24-2026.csv"]


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


def parse_date(series):
    """Parse a date series (UTC strings ok) and strip tz so subtraction works."""
    s = pd.to_datetime(series, errors="coerce", utc=True)
    return s.dt.tz_localize(None)


def admin_period(dates):
    """Label each date with an administration period."""
    out = pd.Series("Pre-Biden", index=dates.index, dtype="object")
    out[dates >= BIDEN_START] = "Biden"
    out[dates >= TRUMP2_START] = "Trump 2nd"
    out[dates.isna()] = np.nan
    return out


def read_subset(path, wanted, date_cols=()):
    """
    Chunked read keeping only the columns in `wanted`.
    `wanted` maps canonical name -> list of candidate header names.
    Text columns become categoricals to keep memory low.
    Returns a DataFrame with canonical column names.
    """
    is_parquet = path.endswith(".parquet")
    if is_parquet:
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(path)
        raw_header = pf.schema_arrow.names
    else:
        raw_header = pd.read_csv(path, nrows=0, encoding=ENC).columns
    raw_names = {raw.strip().lower().replace(" ", "_"): raw for raw in raw_header}
    mapping = {}
    for canon, cands in wanted.items():
        col = next((c for c in cands if c in raw_names), None)
        if col is not None:
            mapping[canon] = col
    usecols = [raw_names[v] for v in mapping.values()]
    inv = {raw_names[v]: k for k, v in mapping.items()}

    if is_parquet:
        chunks = (b.to_pandas() for b in pf.iter_batches(batch_size=CHUNKSIZE, columns=usecols))
    else:
        chunks = pd.read_csv(path, usecols=usecols, chunksize=CHUNKSIZE,
                             encoding=ENC, low_memory=False)
    parts = []
    for chunk in chunks:
        chunk = chunk.rename(columns=inv)
        for c in date_cols:
            if c in chunk.columns:
                chunk[c] = parse_date(chunk[c])
        for c in chunk.columns:
            if chunk[c].dtype == object:
                chunk[c] = chunk[c].astype("category")
        parts.append(chunk)
    df = pd.concat(parts, ignore_index=True)
    for c in df.columns:   # re-unify categories after concat
        if str(df[c].dtype) == "object":
            df[c] = df[c].astype("category")
    return df


def group_table(df, by, value="stay_days", min_n=SMALL_N):
    """n / median / mean / p90 of `value` per group, flagged when n is small."""
    g = df.groupby(by, observed=True)[value]
    t = pd.DataFrame({"n": g.size(), "median": g.median(), "mean": g.mean(),
                      "p90": g.quantile(0.9)}).round(1)
    t["reliable"] = np.where(t["n"] >= min_n, "", "SMALL N")
    return t.sort_values("median", ascending=False)


def top_countries(series, k=10):
    return series.astype(object).value_counts().head(k).index.tolist()


def group_release_reason(s):
    """Collapse the ~dozens of free-ish release reasons into broad outcomes."""
    s = s.astype(object).fillna("").str.lower()
    out = pd.Series("Other", index=s.index, dtype="object")
    out[s.str.contains("remov|deport")] = "Removed"
    out[s.str.contains("bond")] = "Bonded out"
    out[s.str.contains("recognizance")] = "Order of recognizance"
    out[s.str.contains("supervision")] = "Order of supervision"
    out[s.str.contains("parole")] = "Paroled"
    out[s.str.contains("voluntary")] = "Voluntary departure/return"
    out[s.str.contains("transfer|marshal|other agency")] = "Transferred / other agency"
    out[s.str.contains("relief|terminated|dismiss")] = "Relief / proceedings ended"
    out[s == ""] = np.nan
    return out


# Approximate GDP per capita (current US$, rounded, ~2023 World Bank scale),
# hand-entered ONLY to order countries roughly by income; not precise.
APPROX_GDP_PC = {
    "MEXICO": 13800, "GUATEMALA": 5500, "HONDURAS": 3300, "EL SALVADOR": 5000,
    "COLOMBIA": 6900, "NICARAGUA": 2500, "ECUADOR": 6500, "HAITI": 1700,
    "INDIA": 2500, "BRAZIL": 10400, "CHINA": 12600, "DOMINICAN REPUBLIC": 10700,
    "PERU": 7600, "VENEZUELA": 4000, "CANADA": 53000, "JAMAICA": 6000,
    "TURKEY": 13100, "RUSSIA": 13000, "UKRAINE": 5100, "CUBA": 9500,
}

# ===========================================================================
# Section 1 — Detention funnel (joined arrests + detention stays)
# ===========================================================================
print("\n=== Loading joined arrests/detention file (chunked) ===")
joined = read_subset(JOINED, {
    "apprehension_date": ["apprehension_date", "apprehension_date_time"],
    "criminality": ["apprehension_criminality", "case_criminality"],
    "country": ["citizenship_country", "citizenship"],
    "has_detention": ["has_detention_stay", "has_detention"],
    "dup": ["duplicate_drop_row"],
    "book_in": ["stay_book_in_date_time", "book_in_date_time", "stay_book_in_date"],
    "book_out": ["stay_book_out_date_time", "stay_book_out_date"],
    "release_reason": ["stay_release_reason", "detention_release_reason"],
}, date_cols=("apprehension_date", "book_in", "book_out"))
print(f"  Shape: {joined.shape}")
if UPDATED:
    EXTRACT_DATE = max(joined["book_in"].max(), joined["book_out"].max()).normalize()
    print(f"  Updated data: using latest recorded book-in/out date as 'extract' date: {EXTRACT_DATE:%Y-%m-%d}")
if "dup" in joined.columns:
    n_dup = int((joined["dup"].astype(str).str.lower() == "true").sum())
    joined = joined[joined["dup"].astype(str).str.lower() != "true"]
    print(f"  Dropped duplicate_drop_row=True rows: {n_dup:,}")
# The stays data stops before the extraction date; arrests after the last observed
# book-in cannot yet show a detention stay, so they are excluded from the funnel.
STAYS_CUTOFF = joined["book_in"].max().normalize()
n_late = int((joined["apprehension_date"] > STAYS_CUTOFF).sum())
print(f"  Last book-in in joined file: {STAYS_CUTOFF:%Y-%m-%d}; excluding {n_late:,} "
      f"arrests apprehended after that date (detention outcome not yet observable)")
joined = joined[joined["apprehension_date"] <= STAYS_CUTOFF]
joined["has_detention"] = joined["has_detention"].astype(str).str.lower().eq("true")
joined["admin"] = admin_period(joined["apprehension_date"])
print(f"  Arrests: {len(joined):,}; apprehension dates "
      f"{joined['apprehension_date'].min():%Y-%m-%d} to {joined['apprehension_date'].max():%Y-%m-%d}")

print("\n=== Section 1: The Detention Funnel ===")
tot = len(joined)
n_det = int(joined["has_detention"].sum())
det = joined[joined["has_detention"]]
n_out = int(det["book_out"].notna().sum())
rr = group_release_reason(det["release_reason"])
n_removed = int((rr[det["book_out"].notna()] == "Removed").sum())
print(f"  Arrests: {tot:,} | detained: {n_det:,} ({n_det/tot:.1%}) | "
      f"never detained: {tot-n_det:,} ({(tot-n_det)/tot:.1%})")
print(f"  Of detained: booked out {n_out:,} ({n_out/n_det:.1%}); of those removed "
      f"{n_removed:,} ({n_removed/max(n_out,1):.1%})")


def funnel_table(by, subset=None):
    d = joined if subset is None else joined[subset]
    g = d.groupby(by, observed=True)["has_detention"]
    t = pd.DataFrame({"arrests": g.size(), "detained": g.sum()})
    t["never_detained"] = t["arrests"] - t["detained"]
    t["pct_detained"] = (100 * t["detained"] / t["arrests"]).round(1)
    t["flag"] = np.where(t["arrests"] < SMALL_N, "SMALL N", "")
    return t


f_admin = funnel_table("admin")
print("\n  By administration (apprehension date):")
print(f_admin.to_string())

f_crim = funnel_table("criminality")
print("\n  By apprehension criminality:")
print(f_crim.to_string())

top_c_join = top_countries(joined["country"])
f_ctry = funnel_table("country", joined["country"].isin(top_c_join)).sort_values(
    "pct_detained", ascending=False)
print("\n  By top-10 citizenship (by arrests):")
print(f_ctry.to_string())

# Stage funnel by administration: arrests -> detained -> booked out -> removed
rows = []
for a in ["Biden", "Trump 2nd"]:
    d = joined[joined["admin"] == a]
    dd = d[d["has_detention"]]
    bo = dd[dd["book_out"].notna()]
    rem = int((group_release_reason(bo["release_reason"]) == "Removed").sum())
    rows.append({"admin": a, "arrests": len(d), "detained": len(dd),
                 "booked_out": len(bo), "removed": rem,
                 "still_in_or_no_bookout": len(dd) - len(bo)})
stage = pd.DataFrame(rows).set_index("admin")
print("\n  Funnel stages by administration:")
print(stage.to_string())

# Figure: 3-panel 100% stacked horizontal bars
fig, axes = plt.subplots(1, 3, figsize=(20, 6), sharex=True)
for ax, (tbl, title) in zip(axes, [(f_admin, "Administration"),
                                    (f_crim, "Apprehension criminality"),
                                    (f_ctry, "Top-10 citizenship")]):
    t = tbl.copy()
    t["det"] = t["detained"] / t["arrests"] * 100
    t["nodet"] = 100 - t["det"]
    t = t.sort_values("det")
    ax.barh(t.index.astype(str), t["det"], color="steelblue", label="Detained")
    ax.barh(t.index.astype(str), t["nodet"], left=t["det"], color="lightgray",
            label="Never detained")
    for i, (d_, n_) in enumerate(zip(t["det"], t["arrests"])):
        ax.text(2, i, f"{d_:.0f}%  (n={n_:,})", va="center", fontsize=8, color="white")
    ax.set(title=title, xlabel="% of arrests")
axes[0].legend(loc="lower right")
plt.suptitle("Detention Funnel: Arrested → Detained vs. Never Booked In")
plt.tight_layout()
savefig("release_funnel_detained_share.png")

fig, ax = plt.subplots(figsize=(10, 5))
for a, color in [("Biden", "tab:blue"), ("Trump 2nd", "tab:red")]:
    s = stage.loc[a]
    vals = [s["arrests"], s["detained"], s["booked_out"], s["removed"]]
    ax.plot(["Arrested", "Detained", "Booked out", "Removed"],
            np.array(vals) / s["arrests"] * 100, marker="o", color=color, label=a)
ax.set(ylabel="% of arrests", title="Funnel stages as share of arrests")
ax.legend()
plt.tight_layout()
savefig("release_funnel_stages.png")

# ---------------------------------------------------------------------------
# Section 1b — Average detention length per ARREST (never-detained counted as 0 days)
# ---------------------------------------------------------------------------
print("\n=== Section 1b: Average days in detention per arrest (never detained = 0) ===")
j_days = (joined["book_out"] - joined["book_in"]).dt.total_seconds() / 86400
closed = joined["has_detention"] & j_days.between(0, MAX_PLAUSIBLE_DAYS)
never = ~joined["has_detention"]
print(f"  Population: closed stays (0-{MAX_PLAUSIBLE_DAYS}d) + never-detained arrests; "
      f"detained arrests with no book-out (still open) are EXCLUDED (unknown length).")
rows = []
for label, m in [("All", pd.Series(True, index=joined.index)),
                 ("Biden", joined["admin"] == "Biden"),
                 ("Trump 2nd", joined["admin"] == "Trump 2nd")]:
    d_closed = j_days[m & closed]
    pool = np.concatenate([d_closed.values, np.zeros(int((m & never).sum()))])
    rows.append({"group": label, "arrests": int(m.sum()),
                 "never_detained": int((m & never).sum()),
                 "open_excluded": int((m & joined["has_detention"] & ~closed).sum()),
                 "mean_detained_only": round(d_closed.mean(), 1),
                 "median_detained_only": round(d_closed.median(), 1),
                 "mean_incl_never_detained": round(pool.mean(), 1),
                 "median_incl_never_detained": round(float(np.median(pool)), 1)})
avg_arrest = pd.DataFrame(rows).set_index("group")
print(avg_arrest.to_string())

fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(avg_arrest))
ax.bar(x - 0.2, avg_arrest["mean_detained_only"], 0.4, label="Detained only", color="steelblue")
ax.bar(x + 0.2, avg_arrest["mean_incl_never_detained"], 0.4,
       label="Incl. never-detained (0 days)", color="firebrick")
ax.set_xticks(x)
ax.set_xticklabels(avg_arrest.index)
ax.set(ylabel="Mean days", title="Mean detention length: detained only vs. per arrest")
ax.legend()
plt.tight_layout()
savefig("release_avg_days_per_arrest.png")

del joined, det, rr

# ===========================================================================
# Section 2 — Load detention stays (both sheets)
# ===========================================================================
print("\n=== Loading detention stays (sheets 1 & 2, chunked) ===")
wanted = {
    "stay_id": ["stay_id"],
    "book_in": ["stay_book_in_date_time", "book_in_date_time", "stay_book_in_date"],
    "book_out": ["stay_book_out_date_time", "stay_book_out_date", "book_out_date_time"],
    "release_reason": ["stay_release_reason", "detention_release_reason"],
    "criminality": ["book_in_criminality", "apprehension_criminality", "criminality"],
    "country": ["citizenship_country", "citizenship", "country_of_citizenship"],
    "gender": ["gender", "sex"],
    "facility": ["detention_facility_longest", "detention_facility", "facility"],
    "state": ["state_longest"],
    "bond_set": ["initial_bond_set_amount_lowest_seen", "initial_bond_set_amount"],
    "bond_posted": ["bond_posted_amount_lowest_seen", "bond_posted_amount"],
    "bond_posted_date": ["bond_posted_date_earliest_seen", "bond_posted_date"],
}
sheets = []
for i, path in enumerate(STAYS, 1):
    d = read_subset(path, wanted, date_cols=("book_in", "book_out", "bond_posted_date"))
    d["sheet"] = i
    sheets.append(d)
    print(f"  Sheet {i}: {len(d):,} rows")

print("\n=== Section 2a: Sheet 1 vs. sheet 2 ===")
cmp_rows = []
for i, d in enumerate(sheets, 1):
    cmp_rows.append({
        "sheet": i, "rows": len(d),
        "book_in_min": d["book_in"].min().date(), "book_in_max": d["book_in"].max().date(),
        "median_book_in": d["book_in"].median().date(),
        "pct_no_book_out": round(100 * d["book_out"].isna().mean(), 1),
        "pct_bond_set": round(100 * d["bond_set"].notna().mean(), 1),
        "n_countries": d["country"].nunique(),
    })
print(pd.DataFrame(cmp_rows).to_string(index=False))
if len(sheets) > 1:
    overlap = len(set(sheets[0]["stay_id"].astype(str)) & set(sheets[1]["stay_id"].astype(str)))
    print(f"  stay_ID overlap between sheets: {overlap:,}")
print("  Top 3 states (facility, longest): " + "; ".join(
    f"sheet {i}: {d['state'].astype(object).value_counts().head(3).to_dict()}"
    for i, d in enumerate(sheets, 1)))

stays = pd.concat(sheets, ignore_index=True)
del sheets
for c in ["release_reason", "criminality", "country", "gender", "facility", "state"]:
    stays[c] = stays[c].astype(object).astype("category")
stays = stays.drop_duplicates(subset="stay_id")
print(f"  Combined unique stays: {len(stays):,}")

stays["stay_days"] = (stays["book_out"] - stays["book_in"]).dt.total_seconds() / 86400
stays["released"] = stays["book_out"].notna()
stays["rr_group"] = group_release_reason(stays["release_reason"])
stays["bond_posted_flag"] = stays["bond_posted"].notna() | stays["bond_posted_date"].notna()
stays["bond_set_flag"] = stays["bond_set"].notna()
stays["admin"] = admin_period(stays["book_in"])

rel = stays[stays["released"]]
n_neg = int((rel["stay_days"] < 0).sum())
n_huge = int((rel["stay_days"] > MAX_PLAUSIBLE_DAYS).sum())
plaus = rel[(rel["stay_days"] >= 0) & (rel["stay_days"] <= MAX_PLAUSIBLE_DAYS)].copy()
print(f"\n  Released stays: {len(rel):,}; negative duration: {n_neg:,}; "
      f"> {MAX_PLAUSIBLE_DAYS} days: {n_huge:,}")
print(f"  FILTER: released stays with 0 <= stay_days <= {MAX_PLAUSIBLE_DAYS} "
      f"-> {len(plaus):,} stays used for length-of-stay analyses")

# ===========================================================================
# Section 2b — Length-of-stay drivers
# ===========================================================================
print("\n=== Section 2b: Length-of-stay drivers (released, plausible) ===")
print(plaus["stay_days"].describe(percentiles=[.25, .5, .75, .9, .95, .99]).round(1).to_string())

p99 = plaus["stay_days"].quantile(0.99)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].hist(plaus["stay_days"].clip(upper=p99), bins=60, color="steelblue", edgecolor="white")
axes[0].axvline(plaus["stay_days"].median(), color="red", ls="--",
                label=f"median {plaus['stay_days'].median():.0f}d")
axes[0].set(xlabel="Days (clipped at 99th pct)", ylabel="Stays",
            title="Stay length, released detainees")
axes[0].legend()
axes[1].hist(np.log1p(plaus["stay_days"]), bins=60, color="steelblue", edgecolor="white")
axes[1].set(xlabel="log(1 + days)", title="Log scale")
plt.suptitle(f"Distribution of Stay Length (released, 0–{MAX_PLAUSIBLE_DAYS} days)")
plt.tight_layout()
savefig("release_stay_length_distribution.png")

for label, by in [("Release reason (grouped)", "rr_group"),
                  ("Release reason (raw, top 15 by n)", "release_reason"),
                  ("Book-in criminality", "criminality"),
                  ("Gender", "gender"),
                  ("Bond posted", "bond_posted_flag"),
                  ("Administration (book-in)", "admin")]:
    t = group_table(plaus, by)
    if by == "release_reason":
        t = t.sort_values("n", ascending=False).head(15)
    print(f"\n  Stay days by {label}:")
    print(t.to_string())

top_c = top_countries(stays["country"])
t_ctry = group_table(plaus[plaus["country"].isin(top_c)], "country")
print("\n  Stay days by top-10 citizenship (by all stays):")
print(t_ctry.to_string())

# Heatmap: median days, criminality x grouped release reason
hm_n = plaus.pivot_table(index="criminality", columns="rr_group", values="stay_days",
                         aggfunc="size", observed=True)
hm_med = plaus.pivot_table(index="criminality", columns="rr_group", values="stay_days",
                           aggfunc="median", observed=True)
hm_med = hm_med.where(hm_n >= SMALL_N)   # mask unreliable cells
fig, ax = plt.subplots(figsize=(13, 4.5))
sns.heatmap(hm_med, annot=True, fmt=".0f", cmap="YlOrRd", ax=ax,
            cbar_kws={"label": "Median days"})
ax.set(title=f"Median stay (days) by criminality × release reason  (cells with n<{SMALL_N} blank)",
       xlabel="", ylabel="")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
savefig("release_los_heatmap.png")
print("\n  Heatmap cell n:")
print(hm_n.fillna(0).astype(int).to_string())

fig, ax = plt.subplots(figsize=(10, 5))
t_ctry.sort_values("median").plot.barh(y="median", ax=ax, color="steelblue", legend=False)
ax.set(xlabel="Median days (released)", ylabel="", title="Median stay by top-10 citizenship")
plt.tight_layout()
savefig("release_los_by_country.png")

# ===========================================================================
# Section 3 — Bond equity
# ===========================================================================
print("\n=== Section 3: Bond equity ===")
bs = stays[stays["bond_set_flag"]]
print(f"  Stays with an initial bond amount: {len(bs):,} ({len(bs)/len(stays):.1%} of stays)")
print(f"  Stays with bond posted (amount or date): {int(stays['bond_posted_flag'].sum()):,}")
print("  Initial bond amount distribution ($):")
print(bs["bond_set"].describe(percentiles=[.1, .25, .5, .75, .9, .99]).round(0).to_string())
print(f"  Bond posted among bond-set stays: {bs['bond_posted_flag'].mean():.1%}")
bp = stays[stays["bond_posted"].notna()]
print("  Posted bond amount ($):")
print(bp["bond_posted"].describe(percentiles=[.1, .25, .5, .75, .9]).round(0).to_string())

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
b = bs["bond_set"][bs["bond_set"] > 0]
axes[0].hist(np.log10(b), bins=50, color="seagreen", edgecolor="white")
axes[0].set(xlabel="log10(initial bond $)", ylabel="Stays", title="Initial bond amount set")
axes[0].axvline(np.log10(b.median()), color="red", ls="--", label=f"median ${b.median():,.0f}")
axes[0].legend()
bpp = bp["bond_posted"][bp["bond_posted"] > 0]
axes[1].hist(np.log10(bpp), bins=50, color="darkorange", edgecolor="white")
axes[1].set(xlabel="log10(posted bond $)", title="Bond amount posted")
plt.suptitle("Bond Amount Distributions (log scale)")
plt.tight_layout()
savefig("release_bond_distribution.png")


def bond_table(by, subset):
    d = bs[subset] if subset is not None else bs
    g = d.groupby(by, observed=True)
    t = pd.DataFrame({"n_bond_set": g.size(),
                      "posted_rate_pct": (100 * g["bond_posted_flag"].mean()).round(1),
                      "median_bond_set": g["bond_set"].median().round(0),
                      "median_bond_posted": g["bond_posted"].median().round(0)})
    t["flag"] = np.where(t["n_bond_set"] < SMALL_N, "SMALL N", "")
    return t


bt_crim = bond_table("criminality", None).sort_values("posted_rate_pct", ascending=False)
print("\n  Bond by book-in criminality:")
print(bt_crim.to_string())

bt_ctry = bond_table("country", bs["country"].isin(top_c)).sort_values(
    "posted_rate_pct", ascending=False)
bt_ctry["approx_gdp_pc"] = [APPROX_GDP_PC.get(str(c)) for c in bt_ctry.index]
print("\n  Bond by top-10 citizenship (approx_gdp_pc hand-entered, rough):")
print(bt_ctry.to_string())
valid = bt_ctry.dropna(subset=["approx_gdp_pc"])
if len(valid) >= 5:
    ranks = valid[["approx_gdp_pc", "posted_rate_pct", "median_bond_set"]].rank()
    r1 = ranks["approx_gdp_pc"].corr(ranks["posted_rate_pct"])   # Spearman = Pearson on ranks
    r2 = ranks["approx_gdp_pc"].corr(ranks["median_bond_set"])
    print(f"  Spearman (n={len(valid)} countries): GDP/cap vs posted rate = {r1:.2f}; "
          f"GDP/cap vs median bond set = {r2:.2f}  (descriptive, tiny n)")

fig, ax = plt.subplots(figsize=(10, 7))
sizes = bt_ctry["n_bond_set"] / bt_ctry["n_bond_set"].max() * 1500 + 50
sc = ax.scatter(bt_ctry["median_bond_set"], bt_ctry["posted_rate_pct"], s=sizes,
                c=np.log10(bt_ctry["approx_gdp_pc"].astype(float)), cmap="viridis", alpha=0.8)
for c, r in bt_ctry.iterrows():
    ax.annotate(str(c).title(), (r["median_bond_set"], r["posted_rate_pct"]),
                xytext=(6, 6), textcoords="offset points", fontsize=9)
plt.colorbar(sc, label="log10 approx. GDP per capita (rough, hand-entered)")
ax.set(xlabel="Median initial bond set ($)", ylabel="Bond-posted rate (% of bond-set stays)",
       title="Bond equity by country: bond amount vs. share who post (bubble = n)")
plt.tight_layout()
savefig("release_bond_equity_country.png")

fig, ax = plt.subplots(figsize=(8, 4))
bt_crim.sort_values("posted_rate_pct").plot.barh(y="posted_rate_pct", ax=ax,
                                                   color="seagreen", legend=False)
ax.set(xlabel="Bond-posted rate (%)", ylabel="", title="Bond posted rate by criminality")
plt.tight_layout()
savefig("release_bond_by_criminality.png")

# ===========================================================================
# Section 4 — Release reason mix over time
# ===========================================================================
print("\n=== Section 4: Release reason mix over time ===")
mo = stays[stays["released"] & stays["rr_group"].notna()].copy()
mo["month"] = mo["book_out"].dt.to_period("M")
mo = mo[(mo["month"] >= "2019-01") & (mo["month"] <= EXTRACT_DATE.to_period("M"))]
mix = pd.crosstab(mo["month"], mo["rr_group"])
mix = mix[mix.sum(axis=1) >= SMALL_N]          # drop months with unreliable counts
mix_pct = mix.div(mix.sum(axis=1), axis=0) * 100
print(f"  Months plotted: {len(mix)}  ({mix.index.min()} to {mix.index.max()})")
print("  Overall release-reason mix (all released stays):")
print((100 * stays.loc[stays['released'], 'rr_group'].value_counts(normalize=True)).round(1).to_string())
adm_mix = (pd.crosstab(mo["admin"], mo["rr_group"], normalize="index") * 100).round(1)
adm_mix["n"] = mo["admin"].value_counts()
print("\n  Mix by administration (book-in period, % of released):")
print(adm_mix.to_string())

fig, ax = plt.subplots(figsize=(14, 6))
x = mix_pct.index.to_timestamp()
ax.stackplot(x, mix_pct.T.values, labels=mix_pct.columns, alpha=0.9)
for d_, lab in [("2021-01-20", "Biden"), ("2025-01-20", "Trump 2nd")]:
    ax.axvline(pd.Timestamp(d_), color="black", ls="--", lw=1)
    ax.text(pd.Timestamp(d_), 101, lab, ha="center", fontsize=9)
ax.set(ylabel="% of releases in month", ylim=(0, 105),
       title="Release reason mix by month of book-out")
ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
plt.tight_layout()
savefig("release_reason_mix_over_time.png")

# ===========================================================================
# Section 5 — Still-detained cohort
# ===========================================================================
print("\n=== Section 5: Still-detained cohort (no book-out date) ===")
cur = stays[~stays["released"] & stays["book_in"].notna()].copy()
cur["days_in"] = (EXTRACT_DATE - cur["book_in"]).dt.total_seconds() / 86400
DATA_END = stays["book_in"].max()
cur["days_in_data"] = (DATA_END - cur["book_in"]).dt.total_seconds() / 86400
print(f"  Latest book-in in stays files: {DATA_END:%Y-%m-%d} "
      f"({(EXTRACT_DATE - DATA_END).days} days before extraction date)")
print(f"  No book-out: {len(cur):,} of {len(stays):,} stays ({len(cur)/len(stays):.1%})")
print(cur["days_in"].describe(percentiles=[.25, .5, .75, .9, .99]).round(1).to_string())
print("  Days in detention measured to the last book-in in the data (data end):")
print(cur["days_in_data"].describe(percentiles=[.25, .5, .75, .9, .99]).round(1).to_string())
stale = cur[cur["days_in"] > MAX_PLAUSIBLE_DAYS]
print(f"  Open > {MAX_PLAUSIBLE_DAYS} days (likely stale/unclosed records): {len(stale):,}")
active = cur[(cur["days_in"] >= 0) & (cur["days_in"] <= MAX_PLAUSIBLE_DAYS)]
print(f"  Open within plausible window (0–{MAX_PLAUSIBLE_DAYS}d): {len(active):,}; "
      f"median {active['days_in'].median():.0f}d, mean {active['days_in'].mean():.0f}d")
print(f"  Open <= 90 days (most plausibly current detainees): {int((active['days_in'] <= 90).sum()):,}")
print("\n  By criminality:")
print(active["criminality"].value_counts().to_frame("n").assign(
    pct=lambda t: (100 * t["n"] / t["n"].sum()).round(1)).to_string())
print("\n  Top 10 citizenship:")
print(active["country"].value_counts().head(10).to_frame("n").assign(
    pct=lambda t: (100 * t["n"] / len(active)).round(1)).to_string())
print("\n  Top 10 facilities (longest):")
print(active["facility"].value_counts().head(10).to_frame("n").to_string())
print("\n  Open stays by book-in year:")
print(cur["book_in"].dt.year.value_counts().sort_index().to_string())

fig, axes = plt.subplots(1, 3, figsize=(20, 5))
axes[0].hist(active["days_in"], bins=60, color="firebrick", edgecolor="white")
axes[0].set(xlabel="Days since book-in (to 2026-07-24)", ylabel="Open stays",
            title="Time in detention so far")
active["criminality"].value_counts().plot.barh(ax=axes[1], color="firebrick")
axes[1].set(title="Criminality at book-in", xlabel="Open stays")
active["country"].value_counts().head(10).sort_values().plot.barh(ax=axes[2], color="firebrick")
axes[2].set(title="Top-10 citizenship", xlabel="Open stays")
plt.suptitle("Still-Detained Cohort (no book-out date)")
plt.tight_layout()
savefig("release_still_detained.png")

print("\nDone.")
