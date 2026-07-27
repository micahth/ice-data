"""
ICE Detention Data — Exploratory Data Analysis
Run from the repo root: python notebooks/eda.py
Figures are saved to notebooks/figures/
"""

import os
import matplotlib
matplotlib.use("Agg")  # headless — no display needed

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
FIGURES = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIGURES, exist_ok=True)

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

# ---------------------------------------------------------------------------
# Load detention stays (sheet 1)
# ---------------------------------------------------------------------------
print("\n=== Loading detention stays (sheet 1) ===")
df = pd.read_csv("detention-stays (sheet 1) 7-24-2026.csv", low_memory=False)
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
print(f"  Shape: {df.shape}")

col_book_in  = find_col(df, "stay_book_in_date_time", "book_in_date_time", "stay_book_in_date")
col_book_out = find_col(df, "stay_book_out_date", "stay_book_out_date_time", "book_out_date_time")
col_criminal = find_col(df, "book_in_criminality", "apprehension_criminality", "criminality")
col_country  = find_col(df, "citizenship_country", "citizenship", "country_of_citizenship")
col_aor      = find_col(df, "apprehension_aor", "aor", "responsible_aor")
col_facility = find_col(df, "detention_facility_longest", "detention_facility", "facility")
col_gender   = find_col(df, "gender", "sex")

if col_book_in:
    df[col_book_in] = pd.to_datetime(df[col_book_in], errors="coerce")
if col_book_out:
    df[col_book_out] = pd.to_datetime(df[col_book_out], errors="coerce")

if col_book_in and col_book_out:
    df["stay_days"] = (df[col_book_out] - df[col_book_in]).dt.days

df["released"] = df[col_book_out].notna() if col_book_out else False

if col_book_in:
    df["fiscal_year"] = df[col_book_in].dt.year.where(
        df[col_book_in].dt.month < 10, df[col_book_in].dt.year + 1)
    df["book_in_month"] = df[col_book_in].dt.to_period("M")

# ---------------------------------------------------------------------------
# Section 1 — Missingness
# ---------------------------------------------------------------------------
print("\n=== Section 1: Missingness ===")
miss = (df.isnull().mean() * 100).sort_values(ascending=False)
print(miss.head(20).to_string())

# ---------------------------------------------------------------------------
# Section 2 — Detention length
# ---------------------------------------------------------------------------
print("\n=== Section 2: Detention Length ===")
if "stay_days" in df.columns:
    released = df[df["released"] & df["stay_days"].notna() & (df["stay_days"] >= 0)]
    pct_still = (~df["released"]).mean() * 100
    print(f"  Still detained: {pct_still:.1f}%")
    print(released["stay_days"].describe(percentiles=[.25,.5,.75,.9,.95,.99]).to_string())

    p99 = released["stay_days"].quantile(0.99)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].hist(released["stay_days"].clip(upper=p99), bins=60, color="steelblue", edgecolor="white")
    axes[0].set(xlabel="Days", ylabel="Count", title="Detention length (up to 99th pct)")
    axes[1].hist(np.log1p(released["stay_days"]), bins=60, color="steelblue", edgecolor="white")
    axes[1].set(xlabel="log(1 + days)", title="Detention length (log scale)")
    plt.suptitle("Distribution of Detention Length (Released Detainees)")
    plt.tight_layout()
    savefig("detention_length_distribution.png")

# ---------------------------------------------------------------------------
# Section 3 — Criminality
# ---------------------------------------------------------------------------
print("\n=== Section 3: Criminality ===")
if col_criminal:
    vc = df[col_criminal].value_counts()
    print(vc.to_string())
    fig, ax = plt.subplots(figsize=(10, 5))
    vc.plot(kind="bar", ax=ax, color="steelblue")
    ax.set(ylabel="Count", title="Book-In Criminality")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    savefig("criminality_counts.png")

# ---------------------------------------------------------------------------
# Section 4 — Top nationalities
# ---------------------------------------------------------------------------
print("\n=== Section 4: Top Nationalities ===")
if col_country:
    top20 = df[col_country].value_counts().head(20)
    fig, ax = plt.subplots(figsize=(12, 6))
    top20.plot(kind="bar", ax=ax, color="steelblue")
    ax.set(ylabel="Count", title="Top 20 Citizenship Countries")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    savefig("top_nationalities.png")
    if "stay_days" in df.columns:
        tbl = (df[df[col_country].isin(top20.index)]
               .groupby(col_country)["stay_days"]
               .agg(n="count", mean_days="mean", median_days="median")
               .sort_values("n", ascending=False))
        print(tbl.round(1).to_string())

# ---------------------------------------------------------------------------
# Section 5 — Field offices
# ---------------------------------------------------------------------------
print("\n=== Section 5: Field Offices ===")
if col_aor:
    top25 = df[col_aor].value_counts().head(25)
    fig, ax = plt.subplots(figsize=(12, 6))
    top25.plot(kind="bar", ax=ax, color="steelblue")
    ax.set(ylabel="Count", title="Top 25 Apprehension Areas of Responsibility")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    savefig("aor_counts.png")

    if "stay_days" in df.columns:
        top15 = df[col_aor].value_counts().head(15).index
        sub = df[df[col_aor].isin(top15) & df["stay_days"].notna() & (df["stay_days"] >= 0)]
        order = sub.groupby(col_aor)["stay_days"].median().sort_values().index
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.boxplot(data=sub, x="stay_days", y=col_aor, order=order,
                    ax=ax, color="steelblue", showfliers=False)
        ax.set(xlabel="Days", ylabel="", title="Detention Length by Field Office (top 15)")
        plt.tight_layout()
        savefig("aor_stay_days_boxplot.png")

# ---------------------------------------------------------------------------
# Section 6 — Facilities
# ---------------------------------------------------------------------------
print("\n=== Section 6: Detention Facilities ===")
if col_facility:
    top25f = df[col_facility].value_counts().head(25)
    fig, ax = plt.subplots(figsize=(12, 8))
    top25f.plot(kind="barh", ax=ax, color="steelblue")
    ax.set(xlabel="Count", title="Top 25 Detention Facilities")
    ax.invert_yaxis()
    plt.tight_layout()
    savefig("top_facilities.png")

# ---------------------------------------------------------------------------
# Section 7 — Monthly arrest trends
# ---------------------------------------------------------------------------
print("\n=== Section 7: Monthly Arrests ===")
try:
    arr = pd.read_csv("arrests-latest 7-24-2026.csv", low_memory=False)
    arr.columns = [c.strip().lower().replace(" ", "_") for c in arr.columns]
    col_date = find_col(arr, "apprehension_date", "arrest_date", "apprehension_date_time")
    if col_date:
        arr[col_date] = pd.to_datetime(arr[col_date], errors="coerce")
        monthly = arr.groupby(arr[col_date].dt.to_period("M")).size()
        monthly.index = monthly.index.astype(str)
        idx = list(monthly.index)
        fig, ax = plt.subplots(figsize=(16, 5))
        ax.plot(idx, monthly.values, color="steelblue", linewidth=1.5)
        for label, m in [("Biden (Jan 2021)", "2021-01"),
                         ("COVID (Mar 2020)", "2020-03"),
                         ("Trump 2nd term (Jan 2025)", "2025-01")]:
            if m in idx:
                x = idx.index(m)
                ax.axvline(x=x, color="red", linestyle="--", linewidth=1, alpha=0.7)
                ax.text(x + 0.2, ax.get_ylim()[1] * 0.9, label, fontsize=8, color="red")
        ax.set(ylabel="Arrests", title="Monthly ICE Arrest Trends")
        ax.set_xticks(range(0, len(idx), 6))
        ax.set_xticklabels([idx[i] for i in range(0, len(idx), 6)], rotation=45, ha="right")
        plt.tight_layout()
        savefig("monthly_arrests.png")
except FileNotFoundError:
    print("  arrests file not found, skipping.")

# ---------------------------------------------------------------------------
# Section 8 — Gender
# ---------------------------------------------------------------------------
print("\n=== Section 8: Gender ===")
if col_gender:
    vc_g = df[col_gender].value_counts()
    print((vc_g / vc_g.sum() * 100).round(1).to_string())
    fig, ax = plt.subplots(figsize=(8, 5))
    vc_g.plot(kind="bar", ax=ax, color="steelblue")
    ax.set(ylabel="Count", title="Detainees by Gender")
    plt.xticks(rotation=0)
    plt.tight_layout()
    savefig("gender_counts.png")

# ---------------------------------------------------------------------------
# Section 9 — Summary findings
# ---------------------------------------------------------------------------
print("\n=== Section 9: Key Findings ===")
if "stay_days" in df.columns:
    rel = df[df["released"] & df["stay_days"].notna() & (df["stay_days"] >= 0)]
    print(f"1. Median detention length (released): {rel['stay_days'].median():.0f} days, mean: {rel['stay_days'].mean():.0f} days.")
    print(f"2. {(~df['released']).mean()*100:.1f}% had no recorded release date.")
if col_criminal:
    top = df[col_criminal].value_counts()
    print(f"3. Top criminality category: '{top.idxmax()}' ({top.max()/top.sum()*100:.1f}%).")
if col_country:
    top = df[col_country].value_counts()
    print(f"4. Top citizenship country: {top.idxmax()} ({top.max()/top.sum()*100:.1f}%).")
if col_aor:
    print(f"5. Largest field office by volume: {df[col_aor].value_counts().idxmax()}.")
if col_facility:
    print(f"6. Most common longest-stay facility: {df[col_facility].value_counts().idxmax()}.")
if col_gender:
    top = df[col_gender].value_counts(normalize=True)
    print(f"7. Gender: " + ", ".join(f"{g}: {p*100:.1f}%" for g, p in top.items()))

print(f"\n=== Done. Figures saved to {FIGURES} ===")
