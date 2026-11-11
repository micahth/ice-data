from pathlib import Path

import pandas as pd

from arrest_common import ARREST_DAYS, clean_arrests, monthly_arrests

FIXTURES = Path(__file__).parent / "fixtures"


def test_cohort_excludes_duplicates_missing_dates_and_cutoff():
    raw = pd.read_csv(FIXTURES / "arrests.csv")
    clean = clean_arrests(raw)
    assert len(clean) == 5
    assert clean.groupby("era").size().to_dict() == {"old": 2, "new": 3}
    assert clean.date.max() == pd.Timestamp("2026-03-10")
    assert ARREST_DAYS == {"old": 731, "new": 434}


def test_monthly_output_retains_empty_months_and_marks_partial_month():
    data = clean_arrests(pd.read_csv(FIXTURES / "arrests.csv"))
    monthly = monthly_arrests(data)
    assert len(monthly) == 39
    assert monthly.arrests.sum() == 5
    assert monthly.partial_month.sum() == 1
    assert monthly.loc[monthly.partial_month, "month"].tolist() == ["2026-03"]
    assert monthly.loc[monthly.month == "2023-02", "arrests"].item() == 0
    assert monthly.loc[monthly.month == "2024-02", "days_observed"].item() == 29
    assert monthly.loc[monthly.month == "2026-03", "days_observed"].item() == 10
