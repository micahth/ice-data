"""Chart and table builders for the dashboard.

These functions are intentionally free of Streamlit so they can be unit-tested and
reused. Each reads a committed table from ``notebooks/results/`` and returns a pandas
DataFrame and/or a Plotly figure. No raw LFS data is required.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

RESULTS = Path(__file__).resolve().parents[1] / "notebooks" / "results"

ERA_LABEL = {"old": "2023–2024", "new": "Jan 2025 – Mar 10, 2026"}
CAVEAT = "Records, not unique people. Apprehension/facility location is not residence or workplace."


def _read(name):
    return pd.read_csv(RESULTS / f"{name}.csv")


# ---- Page 1: enforcement over time -----------------------------------------
def summary_kpis():
    """Headline KPIs: arrests/day by era and the convicted-criminal share by era."""
    summary = _read("arrest_summary").set_index("era")
    crim = _read("arrest_criminality").set_index("era")
    convicted = crim["1 Convicted Criminal"] / crim.sum(axis=1) * 100
    return {
        "old_per_day": float(summary.loc["old", "arrests_per_day"]),
        "new_per_day": float(summary.loc["new", "arrests_per_day"]),
        "pct_change": float(summary.loc["new", "arrests_per_day"] / summary.loc["old", "arrests_per_day"] * 100 - 100),
        "convicted_old": float(convicted.loc["old"]),
        "convicted_new": float(convicted.loc["new"]),
    }


def monthly_arrests_figure():
    monthly = _read("monthly_arrests")
    colors = ["#d0d7de" if p else "#1f77b4" for p in monthly["partial_month"]]
    fig = go.Figure(go.Bar(x=monthly["month"], y=monthly["arrests"], marker_color=colors,
                           hovertemplate="%{x}: %{y:,} records<extra></extra>"))
    fig.update_layout(title="Monthly deduplicated arrest records (grey = partial month)",
                      xaxis_title=None, yaxis_title="Arrest records", bargap=0.15)
    return monthly, fig


# ---- Page 2: geography ------------------------------------------------------
def arrest_rate_choropleth(year):
    panel = _read("arrest_rate_panel")
    data = panel[panel["year"] == year]
    fig = px.choropleth(data, locations="state", locationmode="USA-states", scope="usa",
                        color="arr_rate", color_continuous_scale="Reds",
                        hover_name="state", labels={"arr_rate": "Arrests per 100k"})
    fig.update_layout(title=f"Arrest records per 100,000 residents by apprehension state, {year}",
                      coloraxis_colorbar_title="per 100k")
    return data, fig


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


def detention_figure(dimension="Region"):
    table, key = DETENTION_DIMENSIONS[dimension]
    data = _read(table)
    fig = px.bar(data, x=key, y="adp_per_100k", color="period", barmode="group",
                 labels={"adp_per_100k": "Facility ADP per 100k local residents", "period": "Period"},
                 title=f"Detention facility ADP per 100,000 local residents by {dimension.lower()}")
    fig.update_xaxes(title=None)
    return data, fig


# ---- Page 4: model uncertainty ---------------------------------------------
def coefficient_forest(outcome=None, specs=("M0 + lagged outcome", "M2 + controls")):
    reg = _read("arrest_regressions")
    reg = reg[reg["term"].str.contains("arr_rate") & (reg["era"] == "New") & reg["spec"].isin(specs)]
    if outcome:
        reg = reg[reg["outcome"] == outcome]
    reg = reg.copy()
    reg["label"] = reg["outcome"] + " — " + reg["spec"]
    fig = go.Figure()
    for _, row in reg.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["ci_low"], row["ci_high"]], y=[row["label"], row["label"]],
            mode="lines", line=dict(color="#57606a"), showlegend=False,
            hovertemplate="95% CI: [%{x:.3f}]<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=[row["coef"]], y=[row["label"]], mode="markers",
            marker=dict(color="#1f77b4", size=9), showlegend=False,
            hovertemplate=f"{row['label']}<br>coef %{{x:.3f}} (q_bh={row['q_bh']:.2f})<extra></extra>"))
    fig.add_vline(x=0, line_dash="dash", line_color="#d0d7de")
    fig.update_layout(title="Arrest-rate coefficients with pointwise 95% CIs (2025); none survives BH q<.10",
                      xaxis_title="Outcome change per +10 arrests per 100k", yaxis_title=None)
    return reg, fig
