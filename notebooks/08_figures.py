"""Figures for MASTER_RESULTS.md. Reads results/*.csv, writes figures/*.png."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(__file__)
R, F = os.path.join(HERE, "results"), os.path.join(HERE, "figures")
os.makedirs(F, exist_ok=True)
OLD, NEW = "Old (2023-2024)", "New (2025-Mar 2026)"


def paired_bar(df, key, value, title, fname, ylabel, order=None):
    p = df[df.period.isin([OLD, NEW])].pivot_table(index=key, columns="period", values=value)[[OLD, NEW]]
    p = p.dropna()
    p = p.loc[order] if order else p.sort_values(NEW, ascending=False)
    ax = p.plot.bar(figsize=(8, 4.5), color=["#8da0cb", "#d95f02"])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(F, fname), dpi=150)
    plt.close()


paired_bar(pd.read_csv(f"{R}/by_region.csv"), "region", "adp_per_100k",
           "Detention rate by region", "fig1_region_per_capita.png", "ADP per 100k residents")
paired_bar(pd.read_csv(f"{R}/by_cbsa_class.csv"), "cbsa_class", "adp_per_100k",
           "Detention rate by area type", "fig2_area_type_per_capita.png", "ADP per 100k residents")
paired_bar(pd.read_csv(f"{R}/by_operator.csv"), "operator", "adp",
           "Average daily population by operator", "fig3_operator_adp.png", "ADP")

s = pd.read_csv(f"{R}/by_state.csv")
p = s[s.period.isin([OLD, NEW])].pivot_table(index="state", columns="period", values="adp_per_100k")
p = p.sort_values(NEW, ascending=False).head(15)[[OLD, NEW]]
ax = p.plot.bar(figsize=(9, 4.5), color=["#8da0cb", "#d95f02"])
ax.set_title("Top 15 states by detention rate")
ax.set_ylabel("ADP per 100k residents")
plt.tight_layout()
plt.savefig(os.path.join(F, "fig4_top_states.png"), dpi=150)
plt.close()

# Scatter: detention rate vs outcomes, 2025 only for crime
pan = pd.read_csv(f"{R}/state_year_panel.csv")
cols = {"d_gdp": "Real GDP growth (%)", "d_unemp": "Unemployment change (pp)",
        "d_violent": "Violent crime change (%)", "d_property": "Property crime change (%)"}
fig, axes = plt.subplots(2, 2, figsize=(10, 7))
for ax, (c, lab) in zip(axes.flat, cols.items()):
    d = pan[pan.year == 2025].dropna(subset=["det_rate", c])
    ax.scatter(d.det_rate, d[c], s=18)
    if len(d) > 2:
        b = pd.Series(d[c].values).cov(pd.Series(d.det_rate.values)) / d.det_rate.var()
        a = d[c].mean() - b * d.det_rate.mean()
        xs = [d.det_rate.min(), d.det_rate.max()]
        ax.plot(xs, [a + b * x for x in xs], color="red")
    ax.set_xlabel("Detention ADP per 100k (2025)")
    ax.set_ylabel(lab)
    ax.set_title(f"{lab}  (r={d.det_rate.corr(d[c]):.2f}, n={len(d)})", fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(F, "fig5_scatter_2025.png"), dpi=150)
plt.close()
print(sorted(os.listdir(F)))
