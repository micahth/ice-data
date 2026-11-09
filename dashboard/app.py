"""Streamlit dashboard for the ICE enforcement analysis.

Run from the repo root:
    python -m pip install -r dashboard/requirements.txt
    streamlit run dashboard/app.py

Reads only the committed tables in notebooks/results/ (no raw LFS data needed).
"""
from pathlib import Path

import pandas as pd
import streamlit as st

import panels

REPO = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="ICE Enforcement Dashboard", layout="wide")


def data_expander(df, caption=None):
    with st.expander("Data behind this chart"):
        if caption:
            st.caption(caption)
        st.dataframe(df, use_container_width=True)


# ---- sidebar: always-visible methods and caveats ---------------------------
st.sidebar.title("ICE enforcement")
page = st.sidebar.radio("View", ["Enforcement over time", "Geography", "Detention geography",
                                 "Model uncertainty", "SQL"])
st.sidebar.markdown("---")
st.sidebar.subheader("Methods & limitations")
st.sidebar.markdown(
    "- Arrests are **deduplicated records**, not unique people or completed removals.\n"
    "- Apprehension and facility locations are **not residences or workplaces**.\n"
    "- Rates normalize by exposure time (per day) and population (per 100k).\n"
    "- Regression intervals are pointwise and **not** multiplicity-adjusted.\n"
    "- Source: Deportation Data Project CSV exports dated July 24, 2026."
)
st.sidebar.caption("Reads committed result tables; no raw data required.")


# ---- Page 1 -----------------------------------------------------------------
if page == "Enforcement over time":
    st.title("Enforcement over time")
    k = panels.summary_kpis()
    c1, c2, c3 = st.columns(3)
    c1.metric("Arrests per day (2023–2024)", f"{k['old_per_day']:,.0f}")
    c2.metric("Arrests per day (2025 →)", f"{k['new_per_day']:,.0f}", f"{k['pct_change']:+.0f}%")
    c3.metric("Convicted-criminal share", f"{k['convicted_new']:.1f}%",
              f"{k['convicted_new'] - k['convicted_old']:+.1f} pp", delta_color="off")
    monthly, fig = panels.monthly_arrests_figure()
    st.plotly_chart(fig, use_container_width=True)
    st.caption(panels.CAVEAT)
    data_expander(monthly)

# ---- Page 2 -----------------------------------------------------------------
elif page == "Geography":
    st.title("Where apprehensions occurred")
    year = st.select_slider("Year", options=[2023, 2024, 2025], value=2025)
    data, fig = panels.arrest_rate_choropleth(year)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Apprehension location, not residence or workplace.")
    data_expander(data)

    era = st.radio("Era", ["new", "old"], format_func=panels.ERA_LABEL.get, horizontal=True)
    aor, aor_fig = panels.top_aor_figure(era)
    st.plotly_chart(aor_fig, use_container_width=True)
    data_expander(aor)

# ---- Page 3 -----------------------------------------------------------------
elif page == "Detention geography":
    st.title("Detention geography")
    dimension = st.radio("Break down by", list(panels.DETENTION_DIMENSIONS), horizontal=True)
    data, fig = panels.detention_figure(dimension)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Where facilities hold people — not local residents' likelihood of detention.")
    data_expander(data)

# ---- Page 4 -----------------------------------------------------------------
elif page == "Model uncertainty":
    st.title("State-level model estimates")
    st.markdown("**0 of 64 arrest-related coefficients survive Benjamini–Hochberg q<.10.** "
                "Wide intervals are reported honestly; this is not evidence of no effect.")
    reg_all = pd.read_csv(panels.RESULTS / "arrest_regressions.csv")
    outcomes = sorted(reg_all.loc[reg_all.era == "New", "outcome"].unique())
    choice = st.selectbox("Outcome", ["All"] + outcomes)
    reg, fig = panels.coefficient_forest(None if choice == "All" else choice)
    st.plotly_chart(fig, use_container_width=True)
    data_expander(reg[["outcome", "spec", "coef", "ci_low", "ci_high", "cov_type", "q_bh", "n"]])

# ---- Page 5 -----------------------------------------------------------------
elif page == "SQL":
    st.title("Declarative SQL view")
    st.markdown("The same arrests-by-state logic as the pandas pipeline, expressed as SQL and "
                "cross-checked in `tests/test_sql.py`.")
    sql_text = (REPO / "sql" / "arrests_by_state.sql").read_text()
    st.code(sql_text, language="sql")
    try:
        import duckdb
        con = duckdb.connect()
        fixture = REPO / "tests" / "fixtures" / "arrests.csv"
        con.execute(f"CREATE VIEW arrests AS SELECT * FROM read_csv_auto('{fixture}')")
        st.caption("Run against the synthetic fixture (no raw data required):")
        st.dataframe(con.execute(sql_text).fetchdf(), use_container_width=True)
    except Exception as exc:  # noqa: BLE001 - surface any engine/data issue in the UI
        st.info(f"Install duckdb to run this query live ({exc}).")
