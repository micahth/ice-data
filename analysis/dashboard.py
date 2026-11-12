"""Local, aggregate-only stakeholder view: streamlit run analysis/dashboard.py."""
from pathlib import Path

import pandas as pd
import streamlit as st

from arrest_common import ARREST_DAYS

RESULTS = Path(__file__).resolve().parent / "results"
PERIODS = {
    f"2023-2024 ({ARREST_DAYS['old']} days)": ("old", ARREST_DAYS["old"]),
    f"Jan 2025-Mar 10, 2026 ({ARREST_DAYS['new']} days)": ("new", ARREST_DAYS["new"]),
}


def location_view(table, location, era, days):
    if era not in ("old", "new") or days <= 0:
        raise ValueError("Choose a supported era and positive observation window")
    view = table[[location, era]].rename(columns={location: "Location", era: "Arrest records"}).copy()
    total = view["Arrest records"].sum()
    if total <= 0:
        raise ValueError("Location aggregates must have a positive arrest total")
    view["Share (%)"] = view["Arrest records"] / total * 100
    view["Records per day"] = view["Arrest records"] / days
    return view.sort_values(["Arrest records", "Location"], ascending=[False, True])


def main():
    st.set_page_config(page_title="ICE arrest geography", layout="wide")
    st.title("Where were ICE apprehensions recorded?")
    st.caption("Aggregate records, not unique people, residence locations, or completed removals.")
    geography = st.selectbox("Geography", ["State", "ICE Area of Responsibility"])
    period = st.selectbox("Observation window", list(PERIODS))
    era, days = PERIODS[period]
    location = "state" if geography == "State" else "aor"
    table = pd.read_csv(RESULTS / f"arrests_by_{location}.csv")
    view = location_view(table, location, era, days)
    st.metric("Included arrest records", f"{view['Arrest records'].sum():,}")
    st.metric("Average records per day", f"{view['Arrest records'].sum() / days:,.1f}")
    metric = st.selectbox("Chart measure", ["Share (%)", "Records per day", "Arrest records"])
    top_n = st.slider("Locations shown", min_value=5, max_value=min(30, len(view)), value=10)
    st.bar_chart(view.head(top_n).set_index("Location")[[metric]], horizontal=True)
    st.caption("Shares use all locations, including Unknown; the chart shows only the selected top locations.")
    st.dataframe(view, hide_index=True)
    st.download_button("Download all locations", view.to_csv(index=False), f"arrests_{location}_{era}.csv", "text/csv")
    st.warning("The observation windows have different lengths. Compare daily rates, not raw counts. "
               "Classification and geography reflect administrative recording conventions.")


if __name__ == "__main__":
    main()
