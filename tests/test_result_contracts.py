from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import t
from geo_common import STATE_ABBR
from regression_common import require_control_coverage

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "analysis/results"


def test_all_50_states_have_every_control_in_every_year():
    panel = pd.read_csv(RESULTS / "state_year_panel.csv")
    require_control_coverage(panel, set(STATE_ABBR.values()) - {"DC"})
    assert len(panel) == 150
    election = panel.drop_duplicates("state").set_index("state").gop24
    for state, expected in {"NC": 50.9, "WI": 49.6, "WY": 71.6}.items():
        assert election[state] == pytest.approx(expected, abs=0.1)


@pytest.mark.parametrize("name", ["arrest_regressions", "regressions"])
def test_primary_family_is_four_2025_lagged_outcome_coefficients(name):
    from statsmodels.stats.multitest import multipletests
    regressions = pd.read_csv(RESULTS / f"{name}.csv")
    primary = regressions.loc[regressions.inference_family == "primary"]
    assert len(primary) == 4 and primary.outcome.nunique() == 4
    assert set(primary.era) == {"New"}
    assert set(primary.spec) == {"M0 + lagged outcome"}
    np.testing.assert_allclose(primary.q_bh, multipletests(primary.p, method="fdr_bh")[1], atol=0.00002)
    assert regressions.loc[regressions.inference_family != "primary", "q_bh"].isna().all()


def test_small_tables_are_not_lfs_pointers():
    for path in [*RESULTS.glob("*.csv"), *REPO.glob("analysis/data/*.csv")]:
        assert not path.read_bytes().startswith(b"version https://git-lfs.github.com/spec/v1"), path
        assert len(pd.read_csv(path)) > 0, path


def test_arrest_totals_and_criminality_reconcile():
    summary = pd.read_csv(RESULTS / "arrest_summary.csv").set_index("era")
    monthly = pd.read_csv(RESULTS / "monthly_arrests.csv")
    assert monthly.arrests.sum() == summary.arrests.sum()
    counts = pd.read_csv(RESULTS / "arrest_criminality.csv").set_index("era")
    np.testing.assert_array_equal(counts.sum(axis=1).sort_index(), summary.arrests.sort_index())
    for name in ["state", "aor", "landmark"]:
        location = pd.read_csv(RESULTS / f"arrests_by_{name}.csv")
        for era in ["old", "new"]:
            assert location[era].sum() == summary.loc[era, "arrests"]
    np.testing.assert_allclose(summary.arrests_per_day, summary.arrests / summary.days)


@pytest.mark.parametrize("name", ["by_state", "by_region", "by_cbsa_class", "by_operator"])
def test_facility_adp_reconciles_to_national_total(name):
    national = pd.read_csv(RESULTS / "overall.csv").set_index("period").adp.sort_index()
    division = pd.read_csv(RESULTS / f"{name}.csv").groupby("period").adp.sum().sort_index()
    np.testing.assert_allclose(division, national, atol=0.1, rtol=0)


def test_duration_observation_counts_distinguish_stay_end_fallback():
    duration = pd.read_csv(RESULTS / "duration_observation_counts.csv").set_index("period")
    overall = pd.read_csv(RESULTS / "overall.csv").set_index("period")
    for period in ["Old (2023-2024)", "New (2025-Mar 2026)"]:
        assert duration.loc[period, "book_ins"] == overall.loc[period, "book_ins"]
        assert duration.loc[period, "book_ins"] == (
            duration.loc[period, "valid_stint_duration_observations"]
            + duration.loc[period, "excluded_stay_end_only"]
            + duration.loc[period, "other_missing_or_invalid_stint_duration"]
        )
    assert duration.loc["Old (2023-2024)", "excluded_stay_end_only"] == 0
    assert duration.loc["New (2025-Mar 2026)", "excluded_stay_end_only"] == 1


@pytest.mark.parametrize("name", ["arrest_regressions", "regressions"])
def test_confidence_intervals_and_model_metadata(name):
    reg = pd.read_csv(RESULTS / f"{name}.csv")
    assert reg[["coef", "se", "ci_low", "ci_high"]].notna().all().all()
    assert (reg.ci_low <= reg.coef).all() and (reg.coef <= reg.ci_high).all()
    df = np.where(reg.cov_type == "cluster", reg.n_states - 1, reg.df_resid)
    np.testing.assert_allclose(reg.ci_high - reg.coef, t.ppf(0.975, df) * reg.se, atol=0.00004, rtol=0)
    assert (reg.n > reg.n_parameters).all()
    assert set(reg.loc[reg.era == "New", "cov_type"]) == {"HC3"}
    assert reg.q_bh.dropna().between(0, 1).all()
