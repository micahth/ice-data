"""Chart and table builders for the dashboard.

These functions are intentionally free of Streamlit so they can be unit-tested and
reused. Each reads a committed table from ``notebooks/results/`` and returns a pandas
DataFrame and/or a Plotly figure. No raw LFS data is required.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

RESULTS = Path(__file__).resolve().parents[1] / "notebooks" / "results"

ERA_LABEL = {"old": "2023–2024", "new": "Jan 2025 – Mar 10, 2026"}
CAVEAT = "Records, not unique people. Apprehension/facility location is not residence or workplace."
SPECS = ("M0 + lagged outcome", "M2 + controls")
SENSITIVITY_SPEC = "M0 excluding highest-rate state (TX)"


def _read(name):
    return pd.read_csv(RESULTS / f"{name}.csv")


# ---- Page 1: enforcement over time -----------------------------------------
def summary_kpis():
    """Headline KPIs: arrests/day by era and the convicted-criminal share by era."""
    summary = _read("arrest_summary").set_index("era")
    crim = _read("arrest_criminality").set_index("era")
    convicted = crim["1 Convicted Criminal"] / crim.sum(axis=1) * 100
    detention = _read("overall").set_index("period").adp
    return {
        "old_per_day": float(summary.loc["old", "arrests_per_day"]),
        "new_per_day": float(summary.loc["new", "arrests_per_day"]),
        "pct_change": float(summary.loc["new", "arrests_per_day"] / summary.loc["old", "arrests_per_day"] * 100 - 100),
        "convicted_old": float(convicted.loc["old"]),
        "convicted_new": float(convicted.loc["new"]),
        "adp_old": float(detention.loc["Old (2023-2024)"]),
        "adp_new": float(detention.loc["New (2025-Mar 2026)"]),
    }


def monthly_arrests_figure(era="both"):
    monthly = _read("monthly_arrests")
    if era not in ("both", "old", "new"):
        raise ValueError(f"Unknown era: {era}")
    if era != "both":
        newer = monthly.month >= "2025-01"
        monthly = monthly[newer if era == "new" else ~newer]
    colors = ["#d0d7de" if p else "#1f77b4" for p in monthly["partial_month"]]
    fig = go.Figure(go.Bar(x=monthly["month"], y=monthly["arrests"], marker_color=colors,
                           hovertemplate="%{x}: %{y:,} records<extra></extra>"))
    fig.update_layout(title="Monthly deduplicated arrest records (grey = partial month)",
                      xaxis_title=None, yaxis_title="Arrest records", bargap=0.15)
    return monthly, fig


# ---- Page 2: geography ------------------------------------------------------
def arrest_rate_choropleth(year, region="All"):
    panel = _read("arrest_rate_panel")
    data = panel[panel["year"] == year]
    if region != "All":
        data = data[data.region == region]
    fig = px.choropleth(data, locations="state", locationmode="USA-states", scope="usa",
                        color="arr_rate", color_continuous_scale="Reds",
                        hover_name="state", labels={"arr_rate": "Arrests per 100k"},
                        range_color=(0, panel.arr_rate.max()))
    fig.update_layout(title=f"Arrest records per 100,000 residents by apprehension state, {year}",
                      coloraxis_colorbar_title="per 100k", clickmode="event+select")
    return data, fig


def state_locations(year, state, dimension):
    data = _read("arrests_state_locations")
    return data[(data.year == year) & (data.state == state) &
                (data.dimension == dimension)].sort_values(
                    ["arrests", "location"], ascending=[False, True])


def top_aor_figure(era="new", top=12):
    aor = _read("arrests_by_aor").sort_values(era, ascending=False).head(top).iloc[::-1]
    fig = px.bar(aor, x=era, y="aor", orientation="h",
                 labels={era: f"Arrest records ({ERA_LABEL[era]})"},
                 title=f"Top ICE Areas of Responsibility by arrest records, {ERA_LABEL[era]}")
    fig.update_yaxes(title=None)
    return aor, fig


# ---- Page 3: detention geography -------------------------------------------
DETENTION_DIMENSIONS = {"Region": ("by_region", "region"),
                        "CBSA class": ("by_cbsa_class", "cbsa_class"),
                        "Operator": ("by_operator", "operator")}


def detention_figure(dimension="Region", metric="adp_per_100k", era="both"):
    table, key = DETENTION_DIMENSIONS[dimension]
    data = _read(table)
    if era != "both":
        data = data[data.period.str.startswith("Old" if era == "old" else "New")]
    population_basis = "U.S. residents" if dimension == "Operator" else "local residents"
    label = {"adp": "Facility average daily population",
             "adp_per_100k": f"Facility ADP per 100k {population_basis}"}[metric]
    fig = px.bar(data, x=key, y=metric, color="period", barmode="group",
                 labels={metric: label, "period": "Period"},
                 title=f"{label} by {dimension.lower()}")
    fig.update_xaxes(title=None)
    return data, fig


# ---- Page 4: model uncertainty ---------------------------------------------
def coefficient_forest(outcome=None, specs=SPECS, sensitivity=False):
    reg = _read("arrest_regressions")
    selected = list(specs) + ([SENSITIVITY_SPEC] if sensitivity else [])
    reg = reg[(reg["term"] == "arr_rate10") & (reg["era"] == "New") & reg["spec"].isin(selected)]
    if outcome:
        reg = reg[reg["outcome"] == outcome]
    reg = reg.copy()
    if reg.empty:
        raise ValueError("Select at least one model specification.")
    outcomes = list(reg.outcome.unique())
    fig = make_subplots(rows=len(outcomes), cols=1, subplot_titles=outcomes,
                        vertical_spacing=0.12 if len(outcomes) > 1 else 0)
    for index, name in enumerate(outcomes, 1):
        subset = reg[reg.outcome == name]
        fig.add_trace(go.Scatter(
            x=subset.coef, y=subset.spec, mode="markers", showlegend=False,
            error_x=dict(type="data", symmetric=False, array=subset.ci_high - subset.coef,
                         arrayminus=subset.coef - subset.ci_low),
            customdata=subset[["ci_low", "ci_high", "q_bh", "n"]].to_numpy(),
            hovertemplate=(
                "%{y}<br>Estimate: %{x:.3f}<br>95% CI [%{customdata[0]:.3f}, "
                "%{customdata[1]:.3f}]<br>BH q=%{customdata[2]:.3f}, n=%{customdata[3]}"
                "<extra></extra>")), row=index, col=1)
        fig.add_vline(x=0, line_dash="dash", row=index, col=1)
        unit = "percentage points" if name in (
            "Real GDP growth (%)", "Unemployment change (pp)") else "percent change"
        fig.update_xaxes(title_text=f"{unit} per +10 arrests per 100k", row=index, col=1)
    fig.update_layout(height=max(340, 300 * len(outcomes)), margin=dict(l=260))
    return reg, fig
