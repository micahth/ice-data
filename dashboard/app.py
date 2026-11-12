"""Run with: streamlit run dashboard/app.py"""
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

import panels

REPO = Path(__file__).resolve().parents[1]
SOURCE = "https://github.com/micahth/ice-data/blob/main/analysis/results/"
st.set_page_config(page_title="ICE Enforcement Dashboard", layout="wide")


def data_expander(df, source, key=None):
    with st.expander("Data behind this chart"):
        st.markdown(f"[Source table]({SOURCE}{source}.csv)")
        st.dataframe(df, use_container_width=True)
        st.download_button("Download displayed data", df.to_csv(index=False),
                           file_name=f"{source}.csv", key=key or f"download_{source}")


st.sidebar.title("ICE enforcement")
page = st.sidebar.radio("View", ["Enforcement over time", "Geography", "Detention geography",
                                 "Model uncertainty", "SQL"])
era = "both"
if page in ("Enforcement over time", "Detention geography"):
    era = st.sidebar.radio("Period", ["both", "old", "new"],
                           format_func=lambda value: panels.ERA_LABEL.get(value, "Both periods"))
st.sidebar.subheader("Methods & limitations")
st.sidebar.markdown(
    "- Arrests are **deduplicated records**, not unique people or completed removals.\n"
    "- Locations are **not residences or workplaces**.\n"
    "- March 2026 is partial. Annual state models/maps exclude 2026.\n"
    "- The January 1 split is not an intervention-date design.\n"
    "- Regression intervals are pointwise, **not** multiplicity-adjusted.\n"
    "- Source: DDP CSV exports dated July 24, 2026."
)
st.sidebar.caption("Period filters affect trends/detention; year/region affect geography only. "
                   "Models are precomputed national state-level fits, not refitted by filters.")
st.sidebar.markdown("[Report and provenance](https://github.com/micahth/ice-data)")
st.sidebar.caption("AI-assisted implementation; analytical requirements, methodological "
                   "evaluation, validation, and interpretation remain the author's responsibility.")

if page == "Enforcement over time":
    st.title("Enforcement over time")
    k = panels.summary_kpis()
    st.caption("Comparison KPIs always show both complete analysis windows; the period filter "
               "changes only the monthly chart. Arrests end March 10; detention ends March 11, 2026.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Arrests/day: 2023-2024", f"{k['old_per_day']:,.0f}")
    c2.metric("Arrests/day: Jan 2025-Mar 10, 2026", f"{k['new_per_day']:,.0f}",
              f"{k['pct_change']:+.0f}%", delta_color="off")
    c3.metric("Convicted-criminal share (new)", f"{k['convicted_new']:.1f}%",
              f"{k['convicted_new'] - k['convicted_old']:+.1f} pp", delta_color="off")
    st.metric("Detention average daily population (new)", f"{k['adp_new']:,.0f}",
              f"{k['adp_new'] - k['adp_old']:+,.0f} vs. {k['adp_old']:,.0f} old", delta_color="off")
    monthly, fig = panels.monthly_arrests_figure(era)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(panels.CAVEAT)
    data_expander(monthly, "monthly_arrests")

elif page == "Geography":
    st.title("Where apprehensions occurred")
    panel = pd.read_csv(panels.RESULTS / "arrest_rate_panel.csv")
    year = st.select_slider("Year", options=[2023, 2024, 2025], value=2025)
    region = st.selectbox("Region", ["All"] + sorted(panel.region.unique()))
    data, fig = panels.arrest_rate_choropleth(year, region)
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun",
                            selection_mode="points", key=f"map_{year}_{region}",
                            config={"topojsonURL": "app/static/"})
    st.caption("50-state panel only. Rates are annual, not the longer new-era totals. "
               "Apprehension location, not residence or workplace.")
    data_expander(data, "arrest_rate_panel")
    points = event.selection.points
    # State names are source labels; the selector and map share the Census state mapping.
    import sys
    sys.path.insert(0, str(REPO / "analysis"))
    from geo_common import STATE_ABBR
    names = {abbr: name.upper() for name, abbr in STATE_ABBR.items()}
    options = sorted(data.state)
    clicked = points[0].get("location") if points else None
    state = st.selectbox("State (or select on map)", options,
                         index=options.index(clicked) if clicked in options else 0,
                         key=f"state_{year}_{region}_{clicked}")
    for dimension in ("aor", "landmark"):
        breakdown = panels.state_locations(year, names[state], dimension)
        st.subheader(f"{state}: {'Areas of Responsibility' if dimension == 'aor' else 'Landmarks'}")
        st.caption("Counts from joint source records for the selected state/year, not a join "
                   "of separate marginal totals. Chart shows top 15; download includes all.")
        st.plotly_chart(px.bar(breakdown.head(15).iloc[::-1], x="arrests", y="location",
                               orientation="h"), use_container_width=True)
        data_expander(breakdown, "arrests_state_locations", key=f"download_{dimension}")

elif page == "Detention geography":
    st.title("Detention geography")
    dimension = st.radio("Break down by", list(panels.DETENTION_DIMENSIONS), horizontal=True)
    metric = st.radio("Measure", ["adp_per_100k", "adp"], horizontal=True,
                      format_func=lambda value: {"adp": "Raw ADP",
                                                  "adp_per_100k": "ADP per 100k residents"}[value])
    data, fig = panels.detention_figure(dimension, metric, era)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Where facilities hold people, not residents' detention risk. Operator "
               "categories are inferred; their per-capita rates use national population, "
               "not operator-specific local catchments.")
    data_expander(data, panels.DETENTION_DIMENSIONS[dimension][0])

elif page == "Model uncertainty":
    st.title("State-level model estimates")
    st.markdown("**0 of 64 arrest-related coefficients survive Benjamini-Hochberg q<.10.** "
                "This is not proof of no relationship or an estimate of causal effects.")
    reg_all = pd.read_csv(panels.RESULTS / "arrest_regressions.csv")
    outcomes = sorted(reg_all.loc[reg_all.era == "New", "outcome"].unique())
    choice = st.selectbox("Outcome", outcomes + ["All (separate scales)"])
    specs = st.multiselect("Specifications", panels.SPECS, default=list(panels.SPECS))
    sensitivity = st.checkbox("Include M0 excluding Texas (highest 2025 arrest rate)")
    if specs or sensitivity:
        reg, fig = panels.coefficient_forest(
            None if choice == "All (separate scales)" else choice, specs, sensitivity)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("2025 models use HC3 robust, t-based pointwise 95% intervals. "
                   "Texas exclusion applies to M0 only. Outcomes have different units/scales.")
        data_expander(reg, "arrest_regressions")
    else:
        st.warning("Select a specification or the Texas-exclusion sensitivity.")

elif page == "SQL":
    st.title("Declarative SQL view")
    st.markdown("SQL specifies the grouped result; DuckDB plans execution. Pandas groupby/joins "
                "are also vectorized, set-oriented operations, not inherently row-by-row loops.")
    sql_text = (REPO / "sql/arrests_by_state.sql").read_text()
    st.code(sql_text, language="sql")
    try:
        with duckdb.connect() as con:
            con.register("arrests", pd.read_csv(REPO / "tests/fixtures/arrests.csv"))
            result = con.execute(sql_text).fetchdf()
    except duckdb.Error as exc:
        st.error(f"DuckDB query failed: {exc}")
    except (OSError, pd.errors.ParserError) as exc:
        st.error(f"Cannot read the synthetic demonstration input: {exc}")
    else:
        st.caption("Synthetic demonstration only. All output columns are checked against pandas.")
        st.dataframe(result, use_container_width=True)
