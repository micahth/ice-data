import numpy as np
import pandas as pd
import pytest

from survival import fit_survival, prepare_cohort


def test_cohort_censors_at_cutoff_and_reports_exclusions():
    raw = pd.DataFrame([
        ["a", "2025-01-01", "2025-01-11", False],
        ["b", "2025-01-01", None, False],
        ["c", "2026-03-11", "2026-03-12", False],
        ["d", "2025-01-01", "2025-01-02", True],
        ["e", "2024-12-31", None, False],
        ["f", "2025-01-03", "2025-01-01", False],
        ["g", "2025-01-03", "not a date", False],
        [None, "2025-01-01", None, False],
        ["h", None, None, False],
    ], columns=["unique_identifier", "stay_book_in_date_time",
                "stay_book_out_date_time", "duplicate_drop_row"])
    cohort, counts = prepare_cohort(raw)
    assert cohort.event.tolist() == [1, 0, 0]
    assert cohort.days.tolist() == [10, 435, 1]
    assert counts.to_dict() == {"included": 3, "invalid_end": 2, "duplicate": 1,
                                "outside_cohort": 1, "missing_person_id": 1,
                                "missing_or_invalid_start": 1}


def test_km_and_cox_fit_with_person_clusters():
    cohort = pd.DataFrame({
        "days": np.tile([1, 2, 3, 4], 20),
        "event": np.tile([1, 1, 0, 1], 20),
        "admission_30_days": np.arange(80) / 10,
        "person": np.arange(80) // 2,
    })
    curve, coefficients = fit_survival(cohort)
    assert curve.days.tolist() == [1, 2, 4]
    np.testing.assert_allclose(curve.survival, [0.75, 0.5, 0.0])
    assert curve.at_risk.tolist() == [80, 60, 20]
    assert coefficients.clustered_se.iloc[0] > 0
    assert coefficients.ci_low.iloc[0] < coefficients.hazard_ratio.iloc[0] < coefficients.ci_high.iloc[0]


def test_cox_rejects_insufficient_events():
    cohort = pd.DataFrame({"days": [1, 2], "event": [1, 0], "person": ["a", "b"],
                           "admission_30_days": [0, 1]})
    with pytest.raises(ValueError, match="two observed exits"):
        fit_survival(cohort)
