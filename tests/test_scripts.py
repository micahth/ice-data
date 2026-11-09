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
    subprocess.run([sys.executable, str(REPO / "notebooks/eda.py")], env=env, check=True, capture_output=True)
    assert (figures / "monthly_arrests.png").stat().st_size > 10000
    assert (figures / "detention_length_distribution.png").stat().st_size > 10000


def test_publication_figures_run_from_small_committed_tables(tmp_path):
    env = os.environ | {"ICE_FIGURES_DIR": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, str(REPO / "notebooks/08_figures.py")], env=env, check=True, capture_output=True)
    assert len(list(tmp_path.glob("*.png"))) == 8
    assert (tmp_path / "fig6_arrest_coefficients.png").stat().st_size > 10000
