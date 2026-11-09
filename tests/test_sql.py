from pathlib import Path

import pandas as pd
import pytest

from arrest_common import clean_arrests

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests/fixtures/arrests.csv"
SQL = REPO / "sql/arrests_by_state.sql"


def _pandas_by_state(frame):
    """The imperative (pandas) version of sql/arrests_by_state.sql, per analysis 09."""
    data = clean_arrests(frame)
    data["state"] = data.apprehension_state_filled_in.fillna(data.apprehension_state_original).fillna("Unknown")
    counts = data.groupby(["state", "era"]).size().unstack(fill_value=0)
    return counts.reindex(columns=["old", "new"], fill_value=0).astype(int)


def test_sql_arrests_by_state_matches_pandas():
    """The declarative SQL and the imperative pandas pipeline must agree on the same input."""
    duckdb = pytest.importorskip("duckdb")
    connection = duckdb.connect()
    connection.execute(f"CREATE VIEW arrests AS SELECT * FROM read_csv_auto('{FIXTURE}')")
    sql = connection.execute(SQL.read_text()).fetchdf().set_index("state")[["old", "new"]].astype(int).sort_index()

    expected = _pandas_by_state(pd.read_csv(FIXTURE)).sort_index()
    pd.testing.assert_frame_equal(sql, expected, check_names=False)
