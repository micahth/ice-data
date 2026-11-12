"""Exploratory Kaplan-Meier and Cox analysis of detention stays."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.duration.hazard_regression import PHReg
from statsmodels.duration.survfunc import SurvfuncRight

from data_common import read_source

COHORT_START = pd.Timestamp("2025-01-01")
END = pd.Timestamp("2026-03-12")
FIELDS = ["unique_identifier", "stay_book_in_date_time", "stay_book_out_date_time",
          "duplicate_drop_row"]


def prepare_cohort(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Construct incident stays and report mutually exclusive exclusions."""
    data = raw.copy()
    start = pd.to_datetime(data["stay_book_in_date_time"], errors="coerce", utc=True).dt.tz_localize(None)
    end = pd.to_datetime(data["stay_book_out_date_time"], errors="coerce", utc=True).dt.tz_localize(None)
    reason = pd.Series("included", index=data.index)
    duplicate = data["duplicate_drop_row"].fillna(False).astype(bool)
    reason.loc[duplicate] = "duplicate"
    eligible = reason.eq("included")
    invalid_start = start.isna()
    reason.loc[eligible & invalid_start] = "missing_or_invalid_start"
    eligible = reason.eq("included")
    reason.loc[eligible & ((start < COHORT_START) | (start >= END))] = "outside_cohort"
    eligible = reason.eq("included")
    invalid_end = (data["stay_book_out_date_time"].notna() & end.isna()) | (end < start)
    reason.loc[eligible & invalid_end] = "invalid_end"
    eligible = reason.eq("included")
    reason.loc[eligible & data["unique_identifier"].isna()] = "missing_person_id"
    included = reason.eq("included")
    observed_end = end[included]
    censor_at = observed_end.fillna(END).clip(upper=END)
    cohort = pd.DataFrame({
        "person": data.loc[included, "unique_identifier"].astype(str),
        "days": (censor_at - start[included]).dt.total_seconds() / 86400,
        "event": (observed_end.notna() & (observed_end < END)).astype(int),
        "admission_30_days": (start[included] - COHORT_START).dt.total_seconds() / (30 * 86400),
    }).reset_index(drop=True)
    return cohort, reason.value_counts().rename_axis("reason").rename("records")


def fit_survival(cohort: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit a KM curve and a Cox model with person-clustered standard errors."""
    if cohort.empty or cohort["event"].sum() < 2:
        raise ValueError("At least two observed exits are required")
    if cohort["person"].nunique() < 2 or cohort["admission_30_days"].nunique() < 2:
        raise ValueError("Cox model requires multiple people and admission dates")
    km = SurvfuncRight(cohort["days"], cohort["event"])
    curve = pd.DataFrame({
        "days": km.surv_times,
        "survival": km.surv_prob,
        "standard_error": km.surv_prob_se,
        "at_risk": km.n_risk,
        "events": km.n_events,
    })
    model = PHReg(cohort["days"], cohort[["admission_30_days"]], status=cohort["event"], ties="efron")
    fit = model.fit(groups=cohort["person"])
    ci = fit.conf_int()
    if not np.isfinite(np.r_[fit.params, fit.bse, ci.ravel()]).all():
        raise ValueError("Cox model produced non-finite estimates or standard errors")
    coefficients = pd.DataFrame({
        "term": ["admission_30_days"],
        "coefficient": fit.params,
        "clustered_se": fit.bse,
        "hazard_ratio": np.exp(fit.params),
        "ci_low": np.exp(ci[:, 0]),
        "ci_high": np.exp(ci[:, 1]),
        "p_value": fit.pvalues,
    })
    return curve, coefficients


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for exploratory output CSVs")
    args = parser.parse_args()
    cohort, counts = prepare_cohort(read_source("detention-stays", FIELDS))
    curve, coefficients = fit_survival(cohort)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    counts.to_csv(args.output_dir / "cohort_counts.csv", header=True)
    curve.to_csv(args.output_dir / "kaplan_meier.csv", index=False)
    coefficients.to_csv(args.output_dir / "cox.csv", index=False)
    print(f"Included {len(cohort):,} stays, {cohort.event.sum():,} observed exits; output: {args.output_dir}")


if __name__ == "__main__":
    main()
