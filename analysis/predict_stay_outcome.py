"""Exploratory time-split prediction of recorded stay book-out within 30 days."""
import argparse
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from data_common import read_source

START = pd.Timestamp("2025-01-01")
SPLIT = pd.Timestamp("2025-11-01")
CUTOFF = pd.Timestamp("2026-03-12")
HORIZON = pd.Timedelta(days=30)
FIELDS = ["unique_identifier", "stay_book_in_date_time", "stay_book_out_date_time",
          "detention_facility_code_first"]
FEATURES = ["admission_day", "facility"]


def prepare_splits(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Keep admissions with a fully observable horizon, and purge the split boundary."""
    start = pd.to_datetime(raw["stay_book_in_date_time"], format="mixed", errors="coerce", utc=True).dt.tz_localize(None)
    end = pd.to_datetime(raw["stay_book_out_date_time"], format="mixed", errors="coerce", utc=True).dt.tz_localize(None)
    reason = pd.Series("eligible", index=raw.index)
    reason.loc[start.isna()] = "invalid_start"
    reason.loc[reason.eq("eligible") & raw["unique_identifier"].isna()] = "missing_person_id"
    invalid_end = (raw["stay_book_out_date_time"].notna() & end.isna()) | (end < start)
    reason.loc[reason.eq("eligible") & invalid_end] = "invalid_end"
    reason.loc[reason.eq("eligible") & (start < START)] = "before_cohort"
    reason.loc[reason.eq("eligible") & (start + HORIZON > CUTOFF)] = "insufficient_followup"
    reason.loc[reason.eq("eligible") & (start < SPLIT) & (start + HORIZON > SPLIT)] = "split_gap"
    train_mask = reason.eq("eligible") & (start < SPLIT)
    test_mask = reason.eq("eligible") & (start >= SPLIT)
    cohort = pd.DataFrame({
        "person": raw["unique_identifier"],
        "admission_day": (start - START).dt.total_seconds() / 86400,
        "facility": raw["detention_facility_code_first"].fillna("Unknown").astype(str),
        "out_within_30_days": (end.notna() & (end <= start + HORIZON)).astype(int),
    }, index=raw.index)
    counts = reason.value_counts().rename_axis("reason").reset_index(name="records")
    return cohort.loc[train_mask].copy(), cohort.loc[test_mask].copy(), counts


def evaluate(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    if train.empty or test.empty or train.out_within_30_days.nunique() != 2 or test.out_within_30_days.nunique() != 2:
        raise ValueError("Both time windows need observations of each outcome")
    preprocessing = ColumnTransformer([
        ("facility", OneHotEncoder(handle_unknown="ignore"), ["facility"]),
        ("date", StandardScaler(), ["admission_day"]),
    ])
    models = {
        "training_prevalence": DummyClassifier(strategy="prior"),
        "logistic_regression": make_pipeline(
            preprocessing, LogisticRegression(max_iter=1000, random_state=0)),
    }
    y_train = train.out_within_30_days
    y_test = test.out_within_30_days
    rows = []
    for name, model in models.items():
        model.fit(train[FEATURES], y_train)
        probabilities = model.predict_proba(test[FEATURES])[:, 1]
        rows.append({
            "model": name,
            "train_stays": len(train),
            "test_stays": len(test),
            "train_event_rate": y_train.mean(),
            "test_event_rate": y_test.mean(),
            "test_people_seen_in_train": test.person.isin(train.person).sum(),
            "accuracy": accuracy_score(y_test, probabilities >= 0.5),
            "brier": brier_score_loss(y_test, probabilities),
            "log_loss": log_loss(y_test, probabilities, labels=[0, 1]),
            "roc_auc": roc_auc_score(y_test, probabilities),
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for aggregate output CSVs")
    args = parser.parse_args()
    train, test, counts = prepare_splits(read_source("detention-stays", FIELDS))
    metrics = evaluate(train, test)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    counts.to_csv(args.output_dir / "stay_prediction_cohort_counts.csv", index=False)
    metrics.to_csv(args.output_dir / "stay_prediction_metrics.csv", index=False)
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
