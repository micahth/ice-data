import os
from pathlib import Path
import subprocess
import sys

import pandas as pd

REPO = Path(__file__).resolve().parents[1]


def test_eda_runs_on_synthetic_sources_without_lfs(tmp_path):
    pd.read_csv(REPO / "tests/fixtures/arrests.csv").to_parquet(tmp_path / "arrests-latest.parquet")
    pd.read_csv(REPO / "tests/fixtures/stays.csv").to_parquet(tmp_path / "detention-stays-latest.parquet")
    figures = tmp_path / "figures"
    env = os.environ | {"ICE_DATA_DIR": str(tmp_path), "ICE_FIGURES_DIR": str(figures), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, str(REPO / "analysis/eda.py")], env=env, check=True, capture_output=True)
    assert (figures / "monthly_arrests.png").stat().st_size > 10000
    assert (figures / "detention_length_distribution.png").stat().st_size > 10000


def test_arrest_location_cli_runs_end_to_end_on_frozen_fixture(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    pd.read_csv(REPO / "tests/fixtures/arrests.csv").to_parquet(data / "arrests-latest.parquet")
    output = tmp_path / "results"
    env = os.environ | {"ICE_DATA_DIR": str(data)}
    subprocess.run(
        [sys.executable, str(REPO / "analysis/04_arrest_locations.py"),
         "--output-dir", str(output)],
        env=env, check=True, capture_output=True,
    )
    summary = pd.read_csv(output / "arrest_summary.csv").set_index("era")
    assert summary.loc["old", "arrests"] == 2
    assert summary.loc["new", "arrests"] == 3
    assert pd.read_csv(output / "monthly_arrests.csv").shape[0] == 39
    locations = pd.read_csv(output / "arrests_by_state.csv").set_index("state")
    assert locations.loc["Texas", "old"] == 2
    assert locations.loc["Texas", "new"] == 3


def test_publication_figures_run_from_small_committed_tables(tmp_path):
    env = os.environ | {"ICE_FIGURES_DIR": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, str(REPO / "analysis/06_figures.py")], env=env, check=True, capture_output=True)
    assert len(list(tmp_path.glob("*.png"))) == 10
    assert (tmp_path / "fig6_arrest_coefficients.png").stat().st_size > 10000
    assert (tmp_path / "monthly_arrests_by_calendar_month.png").stat().st_size > 10000
    assert (tmp_path / "monthly_adp_forecast.png").stat().st_size > 10000
