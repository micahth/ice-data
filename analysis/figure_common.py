"""Consistent chart styling and the deduplicated monthly arrest figure."""
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
import pandas as pd

OLD_COLOR, NEW_COLOR = "#476a89", "#bc5a36"


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
    fig.text(0.01, 0.01, "Source: Deportation Data Project, July 24, 2026 exports. Apprehension location, not residence.",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_calendar_month_arrests(monthly, path):
    set_style()
    dates = pd.to_datetime(monthly.month)
    daily = monthly.arrests / monthly.days_observed
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for year in sorted(dates.dt.year.unique()):
        mask = dates.dt.year == year
        partial_months = dates[mask & monthly.partial_month]
        label = f"{year} ({partial_months.iloc[-1]:%b} partial)" if not partial_months.empty else str(year)
        ax.plot(dates[mask].dt.month, daily[mask], marker="o", linewidth=2,
                color=NEW_COLOR if year >= 2025 else OLD_COLOR,
                alpha=1 if year >= 2025 else 0.65,
                label=label)
    ax.set(title="Monthly arrest pace by calendar month",
           ylabel="Arrest records per observed day", xlabel="Calendar month")
    ax.set_xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.legend(loc="upper left", frameon=False, ncol=2)
    partial = monthly.loc[monthly.partial_month]
    note = "Monthly rates account for days observed."
    if not partial.empty:
        month = pd.Period(partial.iloc[-1].month, freq="M")
        note += f" {month.strftime('%B %Y')} covers {int(partial.iloc[-1].days_observed)} days."
    fig.text(0.01, 0.01, note, fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)
