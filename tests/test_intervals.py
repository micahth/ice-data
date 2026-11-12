import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analysis"))
from ice_lib import adp, annualize, build_intervals, censoring_sensitivity, interval_diagnostics, overlap_days, window_days  # noqa: E402

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


@pytest.mark.parametrize("policy,statuses", [
    ("primary", ["open_excluded", "open_censored"]),
    ("censor_all", ["open_censored", "open_censored"]),
    ("exclude_all", ["open_excluded", "open_excluded"]),
])
def test_open_policies_preserve_closed_fallback_and_invalid_intervals(policy, statuses):
    source = stints([
        ("2024-12-31", None, None), ("2025-01-01", None, None),
        ("2024-01-01", None, "2024-01-06"),
        ("2024-01-01", "2024-01-03", "2024-01-06"),
        (None, None, None), ("2024-01-10", "2024-01-02", None),
        ("2026-03-13", None, None),
    ])
    original = source.copy(deep=True)
    df = build_intervals(source, CUTOFF, open_policy=policy)
    assert list(df.interval_status[:2]) == statuses
    assert list(df.interval_status[2:6]) == ["closed", "closed", "missing_book_in", "invalid_negative"]
    assert df.end.iloc[2] == T("2024-01-06")
    assert df.end.iloc[3] == T("2024-01-03")
    assert df.end.iloc[4:].isna().all()
    pd.testing.assert_frame_equal(source, original)


def test_unknown_open_policy_is_rejected():
    with pytest.raises(ValueError, match="Unknown open-record policy"):
        build_intervals(stints([]), CUTOFF, open_policy="typo")


def test_censoring_sensitivity_uses_same_windows_and_includes_old_carryover():
    source = stints([
        ("2024-12-31", None, None), ("2025-01-01", None, None),
        ("2024-12-31", None, "2025-01-02"),
    ])
    periods = {"old": (T("2024-12-31"), T("2025-01-01")),
               "new": (T("2025-01-01"), T("2025-01-03"))}
    table = censoring_sensitivity(source, CUTOFF, periods)
    populations = table.pivot(index="specification", columns="period", values="adp")
    assert populations.loc["primary", "old"] == 1
    assert populations.loc["primary", "new"] == 1.5
    assert populations.loc["censor_all", "old"] == 2
    assert populations.loc["censor_all", "new"] == 2.5
    assert populations.loc["exclude_all", "old"] == 1
    assert populations.loc["exclude_all", "new"] == 0.5
    assert table.days.tolist() == [1, 2] * 3
    assert table.adp_difference_from_primary.tolist() == [0, 0, 1, 1, 0, -1]
    assert table.pct_difference_from_primary.tolist() == pytest.approx([0, 0, 100, 100 / 1.5, 0, -100 / 1.5])


def test_censoring_sensitivity_zero_primary_has_undefined_percent_difference():
    table = censoring_sensitivity(stints([("2024-01-01", None, None)]), CUTOFF,
                                  {"old": (T("2024-01-01"), T("2024-01-02"))})
    assert table.pct_difference_from_primary.isna().all()
    assert table.adp.tolist() == [0, 1, 0]


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


def diag(rows):
    df = pd.DataFrame(rows, columns=["stay_ID", "unique_identifier", "book_in_date_time", "book_out_date_time",
                                     "stay_book_out_date_time"])
    for c in df.columns[2:]:
        df[c] = pd.to_datetime(df[c])
    return interval_diagnostics(build_intervals(df, CUTOFF))


def test_missing_middle_book_out_flags_exact_overlap():
    d = diag([("s", "p", "2024-01-01", "2024-01-05", "2024-01-20"),
              ("s", "p", "2024-01-05", None, "2024-01-20"),
              ("s", "p", "2024-01-10", "2024-01-20", "2024-01-20")])
    assert d["overlaps_next_stint"].tolist() == [False, True, False]
    assert d["overlap_days"].tolist() == [0, 10, 0]
    assert d["stay_end_fallback"].tolist() == [False, True, False]


def test_clean_transfer_stay_has_no_overlap():
    d = diag([("s", "p", "2024-01-01", "2024-01-05", "2024-01-10"),
              ("s", "p", "2024-01-05", "2024-01-10", "2024-01-10")])
    assert d["overlap_days"].sum() == 0 and not d["concurrent_stay"].any()


def test_overlapping_stays_for_one_person_are_flagged():
    d = diag([("a", "p", "2024-01-01", "2024-01-10", "2024-01-10"),
              ("b", "p", "2024-01-05", "2024-01-15", "2024-01-15"),
              ("c", "q", "2024-01-05", "2024-01-15", "2024-01-15")])
    assert d["concurrent_stay"].tolist() == [True, True, False]
