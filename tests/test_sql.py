from pathlib import Path

import duckdb
import pandas as pd
import pytest

from arrest_common import ARREST_DAYS, clean_arrests

REPO = Path(__file__).resolve().parents[1]
SQL = REPO / "sql/arrests_by_state.sql"


def pandas_by_state(frame):
    data = clean_arrests(frame)
    data["state"] = data.apprehension_state_filled_in.fillna(
        data.apprehension_state_original).fillna("Unknown")
    counts = data.groupby(["state", "era"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=["old", "new"], fill_value=0)
    for era in ("old", "new"):
        counts[f"{era}_per_day"] = counts[era] / ARREST_DAYS[era]
    counts["change_pct"] = (
        counts.new_per_day / counts.old_per_day.where(counts.old > 0) - 1) * 100
    counts["share_new_pct"] = counts.new / counts.new.sum() * 100
    return counts.sort_index()


@pytest.mark.parametrize("case", ["fixture", "edge_cases", "old_only", "empty"])
def test_sql_matches_all_pandas_measures(case):
    frame = pd.read_csv(REPO / "tests/fixtures/arrests.csv")
    if case == "edge_cases":
        extra = pd.DataFrame({
            "apprehension_date": ["2025-02-01", "2024-01-01", "bad", "2026-03-11",
                                  "2025-03-01", "2025-04-01"],
            "apprehension_state_filled_in": [None, "Old only", "Invalid", "Cutoff", "", "Dropped"],
            "apprehension_state_original": [None, None, None, None, "Fallback", None],
            "duplicate_drop_row": [None, False, False, False, False, True],
        })
        frame = pd.concat([frame, extra], ignore_index=True)
    elif case == "old_only":
        frame = frame[frame.apprehension_date < "2025-01-01"]
    elif case == "empty":
        frame = frame.iloc[:0]
    with duckdb.connect() as con:
        con.register("arrests", frame)
        actual = con.execute(SQL.read_text()).fetchdf().set_index("state").sort_index()
    expected = pandas_by_state(frame)
    pd.testing.assert_frame_equal(actual, expected, check_names=False, check_dtype=False,
                                  rtol=1e-12, atol=1e-12)
