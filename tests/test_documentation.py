from pathlib import Path
import re
from urllib.parse import unquote

import pandas as pd

REPO = Path(__file__).resolve().parents[1]


def test_local_report_links_exist():
    documents = [REPO / "README.md", REPO / "outputs/README.md", REPO / "CASE_STUDY.md", REPO / "final_report.md", *REPO.glob("analysis/*.md")]
    for document in documents:
        for link in re.findall(r"\]\(([^)]+)\)", document.read_text()):
            if "://" not in link and not link.startswith("#"):
                target = document.parent / unquote(link.split("#")[0])
                assert target.exists(), f"{document.name}: {link}"


def test_report_headline_and_intervals_match_generated_tables():
    report = (REPO / "final_report.md").read_text()
    summary = pd.read_csv(REPO / "analysis/results/arrest_summary.csv").set_index("era")
    for _, row in summary.iterrows():
        assert f"{int(row.arrests):,}" in report
        assert f"{row.arrests_per_day:.1f}" in report
    monthly = pd.read_csv(REPO / "analysis/results/monthly_arrests.csv")
    assert f"{monthly.loc[~monthly.partial_month, 'arrests'].max():,}" in report
    reg = pd.read_csv(REPO / "analysis/results/arrest_regressions.csv")
    for _, row in reg[(reg.era == "New") & (reg.term == "arr_rate10") &
                      reg.spec.isin(["M0 + lagged outcome", "M2 + controls"])].iterrows():
        interval = f"[{row.ci_low:.3f}, {row.ci_high:.3f}]".replace("-", "−")
        assert interval in report
    primary = reg.loc[reg.inference_family == "primary"]
    assert len(primary) == 4
    assert "Across the four primary arrest-rate tests" in report
    assert (primary.q_bh >= 0.1).all()
    assert reg.loc[reg.inference_family == "sensitivity", "q_bh"].isna().all()
    mde = pd.read_csv(REPO / "analysis/results/arrest_mde.csv")
    for value in mde.mde_across_iqr:
        assert f"{value:.2f}" in report


def test_facility_counts_are_supported_by_activity_table():
    changes = pd.read_csv(REPO / "analysis/results/facility_changes.csv")
    document = (REPO / "analysis/FACILITY_CHANGES.md").read_text()
    first_observed = changes.loc[(changes.pre_stints == 0) & (changes.post_stints >= 25)]
    assert f"**{len(first_observed)} codes first observed" in document
    assert f"**{changes.change_type.str.contains('STOPPED BOOKING').sum()} codes with no final-90-day bookings" in document


def test_detention_sensitivity_report_matches_generated_table():
    report = (REPO / "final_report.md").read_text()
    table = pd.read_csv(REPO / "analysis/results/detention_censoring_sensitivity.csv")
    populations = table.pivot(index="period", columns="specification", values="adp")
    policies = ["primary", "censor_all", "exclude_all"]
    for period, row in populations.iterrows():
        expected = f"| {period} | " + " | ".join(f"{row[p]:,.1f}" for p in policies) + " |"
        assert expected in report
    growth = 100 * (populations.loc["New (2025-Mar 2026)"] / populations.loc["Old (2023-2024)"] - 1)
    expected = "| New vs. old change | " + " | ".join(f"{growth[p]:+.1f}%" for p in policies) + " |"
    assert expected in report


def test_duration_exclusions_are_reported_from_generated_table():
    report = (REPO / "final_report.md").read_text()
    duration = pd.read_csv(REPO / "analysis/results/duration_observation_counts.csv").set_index("period")
    old = int(duration.loc["Old (2023-2024)", "excluded_stay_end_only"])
    new = int(duration.loc["New (2025-Mar 2026)", "excluded_stay_end_only"])
    assert f"{old} and {new} book-ins, respectively" in report


def test_adp_forecast_documentation_matches_generated_tables():
    master = (REPO / "analysis/MASTER_RESULTS.md").read_text()
    report = (REPO / "final_report.md").read_text()
    metrics = pd.read_csv(REPO / "analysis/results/adp_forecast_metrics.csv")
    published = metrics[(metrics.source == "published") & (metrics.period == "full")].set_index("model")
    for model, label in [("last_month", "Last month"), ("seasonal_naive", "Seasonal naive"),
                         ("log_ar1", "Log-AR(1)"), ("ets_damped", "Damped-trend ETS")]:
        row = published.loc[model]
        expected = f"| {label} | {row.mae:,.1f} | {row.rmse:,.1f} | {row.mean_error:,.1f} |".replace(
            "| -", "| −")
        assert expected in master
    assert published.loc["last_month", "n_forecasts"] == 57
    assert f"{published.loc['last_month', 'mae']:,.1f}" in report
    assert f"{published.loc['ets_damped', 'mae']:,.1f}" in report
    recent = metrics[(metrics.source == "published") & (metrics.period == "2025_on")].set_index("model")
    assert f"{recent.loc['ets_damped', 'mae']:,.1f} vs {recent.loc['last_month', 'mae']:,.1f}" in master
    assert f"MASE {recent.loc['ets_damped', 'mase_vs_last_month']:.2f}" in master
    records = metrics[(metrics.source == "records") & (metrics.period == "full")].set_index("model")
    assert f"{records.loc['ets_damped', 'mae']:,.1f} vs {records.loc['last_month', 'mae']:,.1f}" in master
    for period in ["full", "2022_2024", "2025_on"]:
        block = metrics[(metrics.source == "published") & (metrics.period == period)].set_index("model")
        beaten = (block.drop(index="last_month").mae < block.loc["last_month", "mae"]).sum()
        assert beaten == (1 if period == "2025_on" else 0)
    last = published.loc["last_month"]
    assert f"cover {last.cover80:.2f} and {last.cover95:.2f}" in master
    gap = pd.read_csv(REPO / "analysis/results/adp_series_reconciliation.csv")
    assert len(gap) == 38
    assert f"{-gap.pct_difference.mean():.2f}%" in master and f"{-gap.pct_difference.mean():.2f}%" in report
    assert f"about {-gap.difference.mean():,.0f} ADP" in master
    audit = pd.read_csv(REPO / "analysis/results/detention_interval_audit.csv")
    assert f"{audit.double_count_pct.max():.4f}%" in master
    assert f"{audit.overlap_person_days.sum():,.0f} person-days" in master
