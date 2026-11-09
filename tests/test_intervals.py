import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analysis"))
from ice_lib import adp, annualize, build_intervals, overlap_days, window_days  # noqa: E402

T = pd.Timestamp
CUTOFF = T("2026-03-11")


def stints(rows):
    return pd.DataFrame(rows, columns=["book_in_date_time", "book_out_date_time", "stay_book_out_date_time"]).apply(
        pd.to_datetime)


def test_full_overlap_counts_every_day():
    df = build_intervals(stints([("2024-01-01", "2024-01-11", None)]), CUTOFF)
    assert adp(df, T("2024-01-01"), T("2024-01-11")) == pytest.approx(1.0)


def test_partial_overlap_is_clipped_to_window():
    df = build_intervals(stints([("2023-12-31", "2024-01-03", None)]), CUTOFF)
    assert adp(df, T("2024-01-01"), T("2024-01-11")) == pytest.approx(0.2)


def test_stint_ending_at_window_start_is_excluded():
    df = build_intervals(stints([("2023-12-20", "2024-01-01", None)]), CUTOFF)
    assert adp(df, T("2024-01-01"), T("2024-01-11")) == 0


def test_stint_starting_at_window_end_is_excluded():
    df = build_intervals(stints([("2024-01-11", "2024-01-20", None)]), CUTOFF)
    assert adp(df, T("2024-01-01"), T("2024-01-11")) == 0


def test_stint_spanning_window_contributes_window_length():
    df = build_intervals(stints([("2023-01-01", "2025-01-01", None)]), CUTOFF)
    assert adp(df, T("2024-01-01"), T("2024-01-11")) == pytest.approx(1.0)


def test_zero_length_stint_adds_nothing():
    df = build_intervals(stints([("2024-01-05", "2024-01-05", None)]), CUTOFF)
    assert adp(df, T("2024-01-01"), T("2024-01-11")) == 0


def test_negative_duration_is_flagged_and_excluded():
    df = build_intervals(stints([("2024-01-10", "2024-01-02", None)]), CUTOFF)
    assert df.interval_status.iat[0] == "invalid_negative"
    assert pd.isna(df.end.iat[0])
    assert adp(df, T("2024-01-01"), T("2024-01-11")) == 0


def test_missing_book_in_is_excluded():
    df = build_intervals(stints([(None, "2024-01-02", None)]), CUTOFF)
    assert df.interval_status.iat[0] == "missing_book_in"
    assert adp(df, T("2024-01-01"), T("2024-01-11")) == 0


def test_missing_book_out_falls_back_to_stay_book_out():
    df = build_intervals(stints([("2024-01-01", None, "2024-01-06")]), CUTOFF)
    assert df.interval_status.iat[0] == "closed"
    assert adp(df, T("2024-01-01"), T("2024-01-11")) == pytest.approx(0.5)


def test_old_open_stint_is_excluded_not_censored():
    df = build_intervals(stints([("2024-06-01", None, None)]), CUTOFF)
    assert df.interval_status.iat[0] == "open_excluded"
    assert adp(df, T("2024-06-01"), T("2024-07-01")) == 0


def test_recent_open_stint_is_censored_at_cutoff_inclusive():
    df = build_intervals(stints([("2026-03-01", None, None)]), CUTOFF)
    assert df.interval_status.iat[0] == "open_censored"
    assert df.end.iat[0] == T("2026-03-12")
    assert adp(df, T("2026-03-01"), T("2026-03-12")) == pytest.approx(1.0)


def test_open_stint_boundary_date_2025_01_01():
    df = build_intervals(stints([("2024-12-31", None, None), ("2025-01-01", None, None)]), CUTOFF)
    assert list(df.interval_status) == ["open_excluded", "open_censored"]


def test_overlap_days_never_negative():
    s = pd.Series(pd.to_datetime(["2024-02-01"]))
    e = pd.Series(pd.to_datetime(["2024-02-05"]))
    assert overlap_days(s, e, T("2024-03-01"), T("2024-04-01")).iat[0] == 0


def test_adp_groups_by_key():
    df = build_intervals(stints([("2024-01-01", "2024-01-11", None), ("2024-01-01", "2024-01-06", None)]), CUTOFF)
    df["state"] = ["TX", "LA"]
    out = adp(df, T("2024-01-01"), T("2024-01-11"), keys=["state"])
    assert out["TX"] == pytest.approx(1.0) and out["LA"] == pytest.approx(0.5)


def test_grouped_adp_retains_unknown_geography():
    df = build_intervals(stints([("2024-01-01", "2024-01-11", None), ("2024-01-01", "2024-01-06", None)]), CUTOFF)
    df["state"] = ["TX", None]
    out = adp(df, T("2024-01-01"), T("2024-01-11"), keys=["state"])
    assert len(out) == 2
    assert out.sum() == adp(df, T("2024-01-01"), T("2024-01-11"))


@pytest.mark.parametrize("w0,w1,days", [
    ("2023-01-01", "2024-01-01", 365),
    ("2024-01-01", "2025-01-01", 366),
    ("2026-01-01", "2026-03-12", 70),
    ("2025-01-01", "2026-03-12", 435),
])
def test_window_days_uses_actual_calendar_days(w0, w1, days):
    assert window_days(T(w0), T(w1)) == days


def test_annualization_uses_actual_days_in_each_window():
    assert annualize(100, T("2023-01-01"), T("2024-01-01")) == pytest.approx(100 * 365.25 / 365)
    assert annualize(100, T("2024-01-01"), T("2025-01-01")) == pytest.approx(100 * 365.25 / 366)
    assert annualize(70, T("2026-01-01"), T("2026-03-12")) == pytest.approx(365.25)
