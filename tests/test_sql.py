from pathlib import Path

import pandas as pd
import pytest

from arrest_common import clean_arrests

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests/fixtures/arrests.csv"
SQL = REPO / "sql/arrests_by_state.sql"


def _pandas_by_state(frame):
    """The imperative (pandas) version of sql/arrests_by_state.sql, per analysis 09."""
    from arrest_common import ARREST_DAYS

    data = clean_arrests(frame)
    data["state"] = data.apprehension_state_filled_in.fillna(data.apprehension_state_original).fillna("Unknown")
    counts = data.groupby(["state", "era"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=["old", "new"], fill_value=0).astype(int)
    counts["old_per_day"] = counts["old"] / ARREST_DAYS["old"]
    counts["new_per_day"] = counts["new"] / ARREST_DAYS["new"]
    counts["change_pct"] = (counts["new_per_day"] / counts["old_per_day"].where(counts["old_per_day"] > 0) - 1) * 100
    counts["share_new_pct"] = counts["new"] / counts["new"].sum() * 100
    return counts


def test_sql_arrests_by_state_matches_pandas():
    """The declarative SQL and the imperative pandas pipeline must agree on the same input."""
    duckdb = pytest.importorskip("duckdb")
    connection = duckdb.connect()
    connection.execute(f"CREATE VIEW arrests AS SELECT * FROM read_csv_auto('{FIXTURE}')")
    sql = connection.execute(SQL.read_text()).fetchdf().set_index("state").sort_index()

    expected = _pandas_by_state(pd.read_csv(FIXTURE)).sort_index()
    pd.testing.assert_frame_equal(sql, expected, check_names=False, check_exact=False, rtol=1e-10, atol=1e-12)
