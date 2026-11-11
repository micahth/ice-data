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
    all_exposure = reg.loc[reg.q_bh_all_exposure.notna()]
    assert (all_exposure.q_bh_all_exposure >= 0.1).all()
    assert f"all {len(all_exposure)} arrest exposure coefficients" in report
    assert f"{all_exposure.q_bh_all_exposure.min():.2f}".lstrip("0") in report
    mde = pd.read_csv(REPO / "analysis/results/arrest_mde.csv")
    for value in mde.mde_across_iqr:
        assert f"{value:.2f}" in report


def test_facility_counts_are_supported_by_activity_table():
    changes = pd.read_csv(REPO / "analysis/results/facility_changes.csv")
    document = (REPO / "analysis/FACILITY_CHANGES.md").read_text()
    assert f"**{changes.change_type.str.contains('NEW SINCE').sum()} codes first observed" in document
    assert f"**{changes.change_type.str.contains('STOPPED BOOKING').sum()} codes with no final-90-day bookings" in document
