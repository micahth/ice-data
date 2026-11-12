"""Figures for MASTER_RESULTS.md. Reads results/*.csv, writes figures/*.png."""
import os
import matplotlib
# Non-interactive backend so figures render without a display (must come before importing pyplot).
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# Shared era colors, plot style, and the monthly arrest/ADP plotting helpers.
from figure_common import (OLD_COLOR, NEW_COLOR, plot_calendar_month_arrests,
                           plot_monthly_adp_forecast, plot_monthly_arrests, set_style)


def main():

    # Input results folder, and output figures folder (ICE_FIGURES_DIR can override it).
    HERE = os.path.dirname(__file__)
    R, F = os.path.join(HERE, "results"), os.environ.get("ICE_FIGURES_DIR", os.path.join(HERE, "figures"))
    os.makedirs(F, exist_ok=True)
    set_style()
    # Period labels as written by script 01; these must match exactly.
    OLD, NEW = "Old (2023-2024)", "New (2025-Mar 2026)"


    def paired_bar(df, key, value, title, fname, ylabel, order=None):
        # Side-by-side old vs new bars for each value of `key`, saved as a PNG.
        # One row per group, one column per era, in old-then-new order.
        p = df[df.period.isin([OLD, NEW])].pivot_table(index=key, columns="period", values=value)[[OLD, NEW]]
        # Drop groups missing either era.
        p = p.dropna()
        # Use a fixed order if given; otherwise sort by the new-era value, largest first.
        p = p.loc[order] if order else p.sort_values(NEW, ascending=False)
        ax = p.plot.bar(figsize=(9, 5), color=[OLD_COLOR, NEW_COLOR])
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("")
        ax.legend(["2023-2024", "2025-Mar 11, 2026"], frameon=False)
        # Angle the group labels so long names don't overlap.
        plt.xticks(rotation=25, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(F, fname), dpi=150)
        plt.close()


    # Figures 1-3: detention per capita by region and area type, and ADP by operator.
    paired_bar(pd.read_csv(f"{R}/by_region.csv"), "region", "adp_per_100k",
               "Facility-located detention rose in every region", "fig1_region_per_capita.png", "Facility ADP per 100k residents")
    paired_bar(pd.read_csv(f"{R}/by_cbsa_class.csv"), "cbsa_class", "adp_per_100k",
               "Rural facility capacity is high relative to local population", "fig2_area_type_per_capita.png", "Facility ADP per 100k residents")
    paired_bar(pd.read_csv(f"{R}/by_operator.csv"), "operator", "adp",
               "Inferred operator groups all held more detainees", "fig3_operator_adp.png", "ADP (operator inferred from name/code)")

    # Figure 4: the 15 states with the highest new-era detention per capita.
    s = pd.read_csv(f"{R}/by_state.csv")
    p = s[s.period.isin([OLD, NEW])].pivot_table(index="state", columns="period", values="adp_per_100k")
    p = p.sort_values(NEW, ascending=False).head(15)[[OLD, NEW]]
    ax = p.plot.bar(figsize=(9, 4.5), color=[OLD_COLOR, NEW_COLOR])
    # Title is hard-coded; it needs updating if another state takes the top spot.
    ax.set_title("Louisiana has the highest facility ADP relative to population")
    ax.set_ylabel("Facility ADP per 100k residents")
    ax.legend(["2023-2024", "2025-Mar 11, 2026"], frameon=False)
    plt.tight_layout()
    plt.savefig(os.path.join(F, "fig4_top_states.png"), dpi=150)
    plt.close()

    # Scatter: detention rate vs outcomes, 2025 only for crime
    # Figure 5: one panel per outcome, all using 2025 rows.
    pan = pd.read_csv(f"{R}/state_year_panel.csv")
    cols = {"d_gdp": "Real GDP growth (%)", "d_unemp": "Unemployment change (pp)",
            "d_violent": "Violent crime change (%)", "d_property": "Property crime change (%)"}
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, (c, lab) in zip(axes.flat, cols.items()):
        d = pan[pan.year == 2025].dropna(subset=["det_rate", c])
        ax.scatter(d.det_rate, d[c], s=24, color=OLD_COLOR, alpha=0.8)
        # Label the two states with the highest detention rates.
        for _, point in d.nlargest(2, "det_rate").iterrows():
            ax.annotate(point.state, (point.det_rate, point[c]), xytext=(4, 4), textcoords="offset points", fontsize=9)
        # Symmetric log scale spreads out the many low-rate states while keeping zeros visible.
        ax.set_xscale("symlog", linthresh=1)
        ax.set_xlabel("Facility ADP per 100k (symlog; linear below 1)")
        ax.set_ylabel(lab)
        # Show the correlation with and without Louisiana, the main outlier (hard-coded).
        without_la = d[d.state != "LA"]
        ax.set_title(f"r={d.det_rate.corr(d[c]):.2f}; excluding LA: r={without_la.det_rate.corr(without_la[c]):.2f}"
                     f"\n(n={len(d)}; unadjusted)", fontsize=10)
    fig.suptitle("2025 facility detention rates show weak unadjusted outcome correlations")
    plt.tight_layout()
    plt.savefig(os.path.join(F, "fig5_scatter_2025.png"), dpi=150)
    plt.close()

    # Monthly arrest charts: a time series, and the same data arranged by calendar month.
    monthly = pd.read_csv(f"{R}/monthly_arrests.csv")
    plot_monthly_arrests(monthly, os.path.join(F, "monthly_arrests.png"))
    plot_calendar_month_arrests(monthly, os.path.join(F, "monthly_arrests_by_calendar_month.png"))

    # Monthly ADP forecast chart: ICE's published ADP, the record-based ADP, and the forecast backtest.
    plot_monthly_adp_forecast(
        pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ice_published_adp_monthly.csv")),
        pd.read_csv(f"{R}/monthly_adp_records.csv"), pd.read_csv(f"{R}/adp_forecast_backtest.csv"),
        os.path.join(F, "monthly_adp_forecast.png"))

    # Figure 6: 2025 arrest-rate coefficients with 95% confidence intervals, one panel per outcome.
    reg = pd.read_csv(f"{R}/arrest_regressions.csv")
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for ax, label in zip(axes.flat, cols.values()):
        # Map the short crime labels used here to the longer labels stored by script 05.
        outcome = "Violent crime rate change (%)" if label == "Violent crime change (%)" else (
            "Property (nonviolent) crime rate change (%)" if label == "Property crime change (%)" else label)
        # New-era arr_rate10 estimates from the M0 models (with and without the top state) and full controls.
        d = reg[(reg.outcome == outcome) & (reg.era == "New") & (reg.term == "arr_rate10") &
                (reg.spec.str.startswith("M0") | (reg.spec == "M2 + controls"))].copy()
        positions = np.arange(len(d))
        # Horizontal error bars: distance from the estimate to each end of the interval.
        ax.errorbar(d.coef, positions, xerr=[d.coef - d.ci_low, d.ci_high - d.coef],
                    fmt="o", capsize=4, color=OLD_COLOR)
        # Readable row labels with sample size and standard-error type.
        # The excluded state (TX) is hard-coded; if it changes, the raw spec name shows instead.
        labels = d.apply(lambda r: f"{r.spec.replace('M0 + lagged outcome', 'Lagged outcome only').replace('M0 excluding highest-rate state (TX)', 'Lagged outcome only, excl. TX').replace('M2 + controls', 'Full controls')}"
                                  f"\n(n={int(r.n)}, {r.cov_type})", axis=1)
        ax.set_yticks(positions, labels, fontsize=8)
        # Dashed line at zero: intervals crossing it are consistent with no association.
        ax.axvline(0, linestyle="--", color=NEW_COLOR, linewidth=1)
        # List the specifications top to bottom in the order they appear in the table.
        ax.invert_yaxis()
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Outcome change per +10 arrests per 100k")
    fig.suptitle("2025 arrest-rate estimates remain uncertain across specifications\nPointwise 95% confidence intervals; not causal effects",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(F, "fig6_arrest_coefficients.png"), dpi=160)
    plt.close(fig)

    # Figure 7: each era's share of arrests in the top 10 states and top 10 AORs.
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    # (file key, axis label, text to strip from AOR names).
    for ax, (key, label, trim) in zip(axes, [("state", "State", None), ("aor", "ICE Area of Responsibility", " Area of Responsibility")]):
        d = pd.read_csv(f"{R}/arrests_by_{key}.csv")
        # Old-era share, computed before dropping "Unknown" so it matches share_new_pct from script 04.
        d["share_old"] = d.old / d.old.sum() * 100
        # Top 10 by new-era arrests, reversed so the largest is drawn at the top.
        d = d[d[key] != "Unknown"].nlargest(10, "new").iloc[::-1]
        # Shorten AOR names; title-case the upper-case state names.
        names = d[key].str.replace(trim, "", regex=False) if trim else d[key].str.title()
        y = np.arange(len(d))
        # Paired horizontal bars, offset up and down around each label.
        ax.barh(y - 0.2, d.share_old, 0.4, color=OLD_COLOR, label="2023-2024")
        ax.barh(y + 0.2, d.share_new_pct, 0.4, color=NEW_COLOR, label="Jan 2025-Mar 10, 2026")
        ax.set_yticks(y, names)
        ax.set_title("Top 10 states" if key == "state" else "Top 10 ICE Areas of Responsibility")
        ax.set_xlabel("Share of arrest records (%)")
    # One legend is enough for both panels.
    axes[0].legend(frameon=False, loc="lower right")
    fig.suptitle("Where recorded apprehensions occurred\nApprehension location, not residence or workplace", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(F, "fig7_arrest_geography.png"), dpi=160)
    plt.close(fig)
    # List every file in the figures folder as a final check.
    print(sorted(os.listdir(F)))


if __name__ == "__main__":
    main()
