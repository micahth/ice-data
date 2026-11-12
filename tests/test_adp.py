import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analysis"))
from adp_common import (derive_monthly_from_fytd, fiscal_year, fytd_check, fytd_revisions,  # noqa: E402
                        validate_monthly)

DATA = os.path.join(os.path.dirname(__file__), "..", "analysis", "data", "ice_published_adp_monthly.csv")


def frame(months, adp):
    months = pd.to_datetime(months)
    return pd.DataFrame({"month": months, "adp": adp, "fiscal_year": [fiscal_year(m) for m in months]})


def test_october_starts_the_fiscal_year():
    assert fiscal_year("2018-09-01") == 2018 and fiscal_year("2018-10-01") == 2019


def test_validation_flags_gaps_duplicates_and_bad_values():
    assert validate_monthly(frame(["2020-01-01", "2020-02-01", "2020-03-01"], [1.0, 2.0, 3.0])) == []
    assert any("missing" in p for p in validate_monthly(frame(["2020-01-01", "2020-03-01"], [1.0, 2.0])))
    assert validate_monthly(frame(["2020-01-01", "2020-03-01"], [1.0, 2.0]), documented_gaps=["2020-02-01"]) == []
    assert "duplicate months" in validate_monthly(frame(["2020-01-01", "2020-01-01"], [1.0, 2.0]))
    assert any("greater than 0" in p for p in validate_monthly(frame(["2020-01-01"], [0.0])))
    bad = frame(["2019-10-01"], [1.0]).assign(fiscal_year=2018)
    assert any("fiscal_year" in p for p in validate_monthly(bad))


def test_fytd_derivation_is_exact():
    oct_adp, nov_adp = 100.0, 160.0
    ytd_oct, ytd_nov = oct_adp, (oct_adp * 31 + nov_adp * 30) / 61
    assert derive_monthly_from_fytd(ytd_oct, 31, ytd_nov, 61) == pytest.approx(nov_adp)


def test_fytd_check_and_revisions_report_without_raising():
    s = frame(["2019-10-01", "2019-11-01"], [100.0, 160.0])
    ytd = pd.DataFrame({"fiscal_year": [2020, 2020], "file_date": ["2019-11-30", "2019-12-31"],
                        "adp_fy_ytd": [129.0, 140.0]})
    check = fytd_check(s, ytd, tolerance=0.01)
    assert check.loc[0, "recomputed_ytd"] == pytest.approx((100 * 31 + 160 * 30) / 61)
    assert not check.loc[0, "ok"]
    rev = fytd_revisions(ytd)
    assert rev.loc[0, "pct_revision"] == pytest.approx((140 / 129 - 1) * 100)


def test_committed_published_series_is_valid():
    s = pd.read_csv(DATA)
    assert validate_monthly(s) == []
    assert s["month"].iloc[0] == "2018-10-01"
    assert (s["ice_adp"] + s["cbp_adp"] - s["adp"]).abs().max() < 1e-3
