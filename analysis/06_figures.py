"""Figures for MASTER_RESULTS.md. Reads results/*.csv, writes figures/*.png."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from figure_common import (OLD_COLOR, NEW_COLOR, plot_calendar_month_arrests,
                           plot_monthly_arrests, set_style)


def main():

    HERE = os.path.dirname(__file__)
    R, F = os.path.join(HERE, "results"), os.environ.get("ICE_FIGURES_DIR", os.path.join(HERE, "figures"))
    os.makedirs(F, exist_ok=True)
    set_style()
    OLD, NEW = "Old (2023-2024)", "New (2025-Mar 2026)"


    def paired_bar(df, key, value, title, fname, ylabel, order=None):
        p = df[df.period.isin([OLD, NEW])].pivot_table(index=key, columns="period", values=value)[[OLD, NEW]]
        p = p.dropna()
        p = p.loc[order] if order else p.sort_values(NEW, ascending=False)
        ax = p.plot.bar(figsize=(9, 5), color=[OLD_COLOR, NEW_COLOR])
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("")
        ax.legend(["2023-2024", "2025-Mar 11, 2026"], frameon=False)
        plt.xticks(rotation=25, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(F, fname), dpi=150)
        plt.close()


    paired_bar(pd.read_csv(f"{R}/by_region.csv"), "region", "adp_per_100k",
               "Facility-located detention rose in every region", "fig1_region_per_capita.png", "Facility ADP per 100k residents")
    paired_bar(pd.read_csv(f"{R}/by_cbsa_class.csv"), "cbsa_class", "adp_per_100k",
               "Rural facility capacity is high relative to local population", "fig2_area_type_per_capita.png", "Facility ADP per 100k residents")
    paired_bar(pd.read_csv(f"{R}/by_operator.csv"), "operator", "adp",
               "Inferred operator groups all held more detainees", "fig3_operator_adp.png", "ADP (operator inferred from name/code)")

    s = pd.read_csv(f"{R}/by_state.csv")
    p = s[s.period.isin([OLD, NEW])].pivot_table(index="state", columns="period", values="adp_per_100k")
    p = p.sort_values(NEW, ascending=False).head(15)[[OLD, NEW]]
    ax = p.plot.bar(figsize=(9, 4.5), color=[OLD_COLOR, NEW_COLOR])
    ax.set_title("Louisiana has the highest facility ADP relative to population")
    ax.set_ylabel("Facility ADP per 100k residents")
    ax.legend(["2023-2024", "2025-Mar 11, 2026"], frameon=False)
    plt.tight_layout()
    plt.savefig(os.path.join(F, "fig4_top_states.png"), dpi=150)
    plt.close()

    # Scatter: detention rate vs outcomes, 2025 only for crime
    pan = pd.read_csv(f"{R}/state_year_panel.csv")
    cols = {"d_gdp": "Real GDP growth (%)", "d_unemp": "Unemployment change (pp)",
            "d_violent": "Violent crime change (%)", "d_property": "Property crime change (%)"}
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, (c, lab) in zip(axes.flat, cols.items()):
        d = pan[pan.year == 2025].dropna(subset=["det_rate", c])
        ax.scatter(d.det_rate, d[c], s=24, color=OLD_COLOR, alpha=0.8)
        for _, point in d.nlargest(2, "det_rate").iterrows():
            ax.annotate(point.state, (point.det_rate, point[c]), xytext=(4, 4), textcoords="offset points", fontsize=9)
        ax.set_xscale("symlog", linthresh=1)
        ax.set_xlabel("Facility ADP per 100k (symlog; linear below 1)")
        ax.set_ylabel(lab)
        without_la = d[d.state != "LA"]
        ax.set_title(f"r={d.det_rate.corr(d[c]):.2f}; excluding LA: r={without_la.det_rate.corr(without_la[c]):.2f}"
                     f"\n(n={len(d)}; unadjusted)", fontsize=10)
    fig.suptitle("2025 facility detention rates show weak unadjusted outcome correlations")
    plt.tight_layout()
    plt.savefig(os.path.join(F, "fig5_scatter_2025.png"), dpi=150)
    plt.close()

    monthly = pd.read_csv(f"{R}/monthly_arrests.csv")
    plot_monthly_arrests(monthly, os.path.join(F, "monthly_arrests.png"))
    plot_calendar_month_arrests(monthly, os.path.join(F, "monthly_arrests_by_calendar_month.png"))

    reg = pd.read_csv(f"{R}/arrest_regressions.csv")
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for ax, label in zip(axes.flat, cols.values()):
        outcome = "Violent crime rate change (%)" if label == "Violent crime change (%)" else (
            "Property (nonviolent) crime rate change (%)" if label == "Property crime change (%)" else label)
        d = reg[(reg.outcome == outcome) & (reg.era == "New") & (reg.term == "arr_rate10") &
                (reg.spec.str.startswith("M0") | (reg.spec == "M2 + controls"))].copy()
        positions = np.arange(len(d))
        ax.errorbar(d.coef, positions, xerr=[d.coef - d.ci_low, d.ci_high - d.coef],
                    fmt="o", capsize=4, color=OLD_COLOR)
        labels = d.apply(lambda r: f"{r.spec.replace('M0 + lagged outcome', 'Lagged outcome only').replace('M0 excluding highest-rate state (TX)', 'Lagged outcome only, excl. TX').replace('M2 + controls', 'Full controls')}"
                                  f"\n(n={int(r.n)}, {r.cov_type})", axis=1)
        ax.set_yticks(positions, labels, fontsize=8)
        ax.axvline(0, linestyle="--", color=NEW_COLOR, linewidth=1)
        ax.invert_yaxis()
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Outcome change per +10 arrests per 100k")
    fig.suptitle("2025 arrest-rate estimates remain uncertain across specifications\nPointwise 95% confidence intervals; not causal effects",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(F, "fig6_arrest_coefficients.png"), dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    for ax, (key, label, trim) in zip(axes, [("state", "State", None), ("aor", "ICE Area of Responsibility", " Area of Responsibility")]):
        d = pd.read_csv(f"{R}/arrests_by_{key}.csv")
        d["share_old"] = d.old / d.old.sum() * 100
        d = d[d[key] != "Unknown"].nlargest(10, "new").iloc[::-1]
        names = d[key].str.replace(trim, "", regex=False) if trim else d[key].str.title()
        y = np.arange(len(d))
        ax.barh(y - 0.2, d.share_old, 0.4, color=OLD_COLOR, label="2023-2024")
        ax.barh(y + 0.2, d.share_new_pct, 0.4, color=NEW_COLOR, label="Jan 2025-Mar 10, 2026")
        ax.set_yticks(y, names)
        ax.set_title("Top 10 states" if key == "state" else "Top 10 ICE Areas of Responsibility")
        ax.set_xlabel("Share of arrest records (%)")
    axes[0].legend(frameon=False, loc="lower right")
    fig.suptitle("Where recorded apprehensions occurred\nApprehension location, not residence or workplace", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(F, "fig7_arrest_geography.png"), dpi=160)
    plt.close(fig)
    print(sorted(os.listdir(F)))


if __name__ == "__main__":
    main()
