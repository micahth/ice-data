import numpy as np
import pandas as pd
import pytest

from predict_stay_outcome import evaluate, prepare_splits


def test_splits_purge_immature_training_labels_and_censor_recent_admissions():
    raw = pd.DataFrame([
        ["a", "2025-01-01", "2025-01-31", "A"],
        ["b", "2025-10-02", None, "B"],
        ["c", "2025-10-03", "2025-10-04", "A"],
        ["d", "2025-11-01", "2025-12-02", "new"],
        ["e", "2026-02-10", "2026-03-12", "A"],
        ["f", "2026-02-10 00:01", None, "A"],
        ["g", "2025-01-01", "2024-12-31", "A"],
        ["h", "2025-01-01", "bad", "A"],
        [None, "2025-01-01", None, "A"],
    ], columns=["unique_identifier", "stay_book_in_date_time",
                "stay_book_out_date_time", "detention_facility_code_first"])
    train, test, counts = prepare_splits(raw)
    assert train.person.tolist() == ["a", "b"]
    assert train.out_within_30_days.tolist() == [1, 0]
    assert test.person.tolist() == ["d", "e"]
    assert test.out_within_30_days.tolist() == [0, 1]
    assert counts.set_index("reason").records.to_dict() == {
        "eligible": 4, "invalid_end": 2, "split_gap": 1,
        "insufficient_followup": 1, "missing_person_id": 1,
    }


def test_metrics_use_training_prevalence_and_handle_unseen_facilities():
    train = pd.DataFrame({
        "person": ["a", "b", "c", "d"], "admission_day": [0, 1, 2, 3],
        "facility": ["A", "A", "B", "B"], "out_within_30_days": [1, 1, 1, 0],
    })
    test = pd.DataFrame({
        "person": ["a", "e"], "admission_day": [40, 41],
        "facility": ["new", "A"], "out_within_30_days": [0, 1],
    })
    metrics = evaluate(train, test).set_index("model")
    assert metrics.loc["training_prevalence", "brier"] == pytest.approx((0.75**2 + 0.25**2) / 2)
    assert metrics.loc["training_prevalence", "roc_auc"] == 0.5
    assert (metrics.test_people_seen_in_train == 1).all()
    assert np.isfinite(metrics[["accuracy", "brier", "log_loss", "roc_auc"]].to_numpy()).all()


def test_training_labels_do_not_depend_on_later_bookouts():
    raw = pd.DataFrame([
        ["a", "2025-09-01", None, "A"],
        ["b", "2025-11-01", "2025-11-02", "B"],
    ], columns=["unique_identifier", "stay_book_in_date_time",
                "stay_book_out_date_time", "detention_facility_code_first"])
    before, _, _ = prepare_splits(raw)
    raw.loc[0, "stay_book_out_date_time"] = "2025-12-01"
    after, _, _ = prepare_splits(raw)
    pd.testing.assert_frame_equal(before, after)


def test_evaluate_rejects_single_class():
    frame = pd.DataFrame({"out_within_30_days": [1]})
    with pytest.raises(ValueError, match="each outcome"):
        evaluate(frame, frame)
