"""Consistent chart styling and the deduplicated monthly arrest figure."""
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
import pandas as pd

OLD_COLOR, NEW_COLOR = "#476a89", "#bc5a36"
YEAR_STYLES = [("#476a89", "-"), ("#2a7f62", "--"),
               ("#bc5a36", "-"), ("#824fa0", "--")]


def set_style():
    plt.rcParams.update({
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.titleweight": "bold", "axes.titlesize": 12,
        "axes.labelsize": 10, "font.size": 10, "figure.facecolor": "white",
        "axes.grid": True, "grid.alpha": 0.2, "axes.axisbelow": True,
    })


def plot_monthly_arrests(monthly, path):
    set_style()
    dates = pd.to_datetime(monthly.month)
    complete = ~monthly.partial_month
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(dates[complete], monthly.loc[complete, "arrests"], color=OLD_COLOR, linewidth=2)
    ax.scatter(dates[~complete], monthly.loc[~complete, "arrests"], facecolors="none",
               edgecolors=NEW_COLOR, label="Partial March 2026 (10 days)", zorder=3)
    ax.axvline(pd.Timestamp("2025-01-01"), color=NEW_COLOR, linestyle="--", linewidth=1,
               label="Calendar-year comparison split")
    peak = monthly.loc[complete].arrests.idxmax()
    ax.annotate(f"{monthly.loc[peak, 'arrests']:,}\n{dates.loc[peak]:%b %Y}",
                (dates.loc[peak], monthly.loc[peak, "arrests"]), xytext=(-65, -5),
                textcoords="offset points", ha="right", color=NEW_COLOR)
    ax.set(title="Monthly ICE arrests reached nearly 40,000 in December 2025",
           ylabel="Arrest records (duplicates excluded)", xlabel="")
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    fig.text(0.01, 0.01, "Source: Deportation Data Project, 2026-07-24 exports. Apprehension location, not residence.",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_calendar_month_arrests(monthly, path):
    set_style()
    dates = pd.to_datetime(monthly.month)
    daily = monthly.arrests / monthly.days_observed
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for index, year in enumerate(sorted(dates.dt.year.unique())):
        mask = dates.dt.year == year
        partial_months = dates[mask & monthly.partial_month]
        label = f"{year} ({partial_months.iloc[-1]:%b} partial)" if not partial_months.empty else str(year)
        ax.plot(dates[mask].dt.month, daily[mask], marker="o", linewidth=2,
                color=YEAR_STYLES[index % len(YEAR_STYLES)][0],
                linestyle=YEAR_STYLES[index % len(YEAR_STYLES)][1],
                label=label)
    ax.set(title="Monthly arrest pace by calendar month",
           ylabel="Arrest records per observed day", xlabel="Calendar month")
    ax.set_xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), frameon=False, ncol=4)
    partial = monthly.loc[monthly.partial_month]
    note = "Monthly rates account for days observed."
    if not partial.empty:
        month = pd.Period(partial.iloc[-1].month, freq="M")
        note += f" {month.strftime('%B %Y')} covers {int(partial.iloc[-1].days_observed)} days."
    fig.text(0.01, 0.01, note, fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_monthly_adp_forecast(published, records, predictions, path):
    """Published and record-level ADP with last-month and ETS backtest forecasts and 80% intervals."""
    set_style()
    fig, ax = plt.subplots(figsize=(11, 5))
    pub_dates = pd.to_datetime(published.month)
    partial = pub_dates == pub_dates.max()
    ax.plot(pub_dates[~partial], published.loc[~partial, "adp"], color=OLD_COLOR, linewidth=2,
            label="Published ADP (ICE statistics via DDP)")
    ax.scatter(pub_dates[partial], published.loc[partial, "adp"], facecolors="none", edgecolors=NEW_COLOR,
               zorder=3, label="Partial July 2026 (file pulled July 11)")
    rec = records[records.burn_in_ok & ~records.partial_month]
    ax.plot(pd.to_datetime(rec.month), rec.adp, color="#2a7f62", linewidth=1.6, label="Record-level ADP (transfer-safe)")
    pub = predictions[predictions.source == "published"]
    last = pub[pub.model == "last_month"]
    ets = pub[pub.model == "ets_damped"]
    ax.plot(pd.to_datetime(last.month), last.forecast, color="#888888", linestyle=":", linewidth=1.5,
            label="Last-month forecast")
    ax.plot(pd.to_datetime(ets.month), ets.forecast, color=NEW_COLOR, linestyle="--", linewidth=1.5,
            label="Damped-trend ETS forecast")
    bands = last.dropna(subset=["lower80"])
    ax.fill_between(pd.to_datetime(bands.month), bands.lower80, bands.upper80, color="#888888", alpha=0.2,
                    label="80% interval (last-month)")
    ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-12-31"), color="#cccccc", alpha=0.25)
    ax.axvspan(pd.Timestamp("2025-01-01"), pub_dates.max(), color=NEW_COLOR, alpha=0.06)
    ax.set(title="Average daily ICE detention population: one-month-ahead backtest",
           ylabel="Average daily population (ADP)", xlabel="")
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    fig.text(0.01, 0.01, "Sources: ICE detention-management statistics and detention stints via Deportation Data "
             "Project. Shading: 2020-03 to 2021-12 and 2025 onward. Series differ in level and are not combined.",
             fontsize=7.5, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)
