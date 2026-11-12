import matplotlib.pyplot as plt
import pandas as pd

from figure_common import plot_calendar_month_arrests


def test_calendar_chart_distinguishes_years_and_places_legend_above_axes(tmp_path, monkeypatch):
    monthly = pd.DataFrame({
        "month": ["2023-01", "2024-01", "2025-01", "2026-01"],
        "arrests": [100, 150, 200, 300],
        "days_observed": [31] * 4,
        "partial_month": [False] * 4,
    })
    monkeypatch.setattr(plt, "close", lambda fig: None)
    plot_calendar_month_arrests(monthly, tmp_path / "chart.png")
    fig = plt.gcf()
    ax = fig.axes[0]
    assert len({(line.get_color(), line.get_linestyle()) for line in ax.lines}) == 4
    fig.canvas.draw()
    assert ax.get_legend().get_window_extent().y0 >= ax.get_window_extent().y1
