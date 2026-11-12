"""Verify published inputs, regenerate in a fresh workspace, and compare every result CSV."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd

from download_data import verify_published

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "01_geo_detention_analysis.py",
    "02_geo_regressions.py",
    "03_facility_changes.py",
    "04_arrest_locations.py",
    "05_arrest_regressions.py",
    "forecast_arrests.py",
)


def compare_results(expected: str | Path, actual: str | Path) -> None:
    expected, actual = Path(expected), Path(actual)
    names = {path.name for path in expected.glob("*.csv")}
    actual_names = {path.name for path in actual.glob("*.csv")}
    if not names or names != actual_names:
        raise AssertionError(
            f"Result inventory differs: missing={sorted(names - actual_names)}, "
            f"unexpected={sorted(actual_names - names)}"
        )
    failures = []
    for name in sorted(names):
        baseline = pd.read_csv(expected / name)
        regenerated = pd.read_csv(actual / name)
        try:
            if list(baseline.columns) != list(regenerated.columns):
                raise AssertionError("Column names/order differ")
            columns = list(baseline.columns)
            baseline = baseline.sort_values(columns, kind="stable").reset_index(drop=True)
            regenerated = regenerated.sort_values(columns, kind="stable").reset_index(drop=True)
            pd.testing.assert_frame_equal(
                baseline, regenerated, check_dtype=False, check_exact=False, rtol=0, atol=1e-6,
            )
        except AssertionError as error:
            failures.append(f"{name}: {error}")
    if failures:
        raise AssertionError("Reproduction mismatch:\n" + "\n".join(failures))
    print(f"PASS: all {len(names)} result tables match (absolute numeric tolerance 1e-6).", flush=True)


def prepare_workspace(work_directory: str | Path) -> tuple[Path, Path, Path]:
    if os.environ.get("ICE_DATA_DIR"):
        raise ValueError("Unset ICE_DATA_DIR: published reproduction requires the July 24 CSVs")
    verify_published(REPO / "data")
    workspace = Path(work_directory).resolve()
    if workspace.is_relative_to(REPO / "analysis") or workspace.is_relative_to(REPO / "data"):
        raise ValueError("The reproduction workspace must be outside analysis/ and data/")
    workspace.mkdir(parents=True, exist_ok=False)
    analysis = workspace / "analysis"
    shutil.copytree(REPO / "analysis", analysis, ignore=shutil.ignore_patterns(
        ".cache", "__pycache__", "results", "figures",
    ))
    (workspace / "data").symlink_to(REPO / "data", target_is_directory=True)
    expected = workspace / "expected"
    expected.mkdir()
    return workspace, analysis, expected


def snapshot_results(expected: Path) -> str:
    # Compare against the committed snapshot rather than potentially edited results.
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", revision, "analysis/results/"], cwd=REPO, text=True,
    ).splitlines()
    for path in paths:
        if path.endswith(".csv"):
            (expected / Path(path).name).write_bytes(subprocess.check_output(
                ["git", "show", f"{revision}:{path}"], cwd=REPO,
            ))
    return revision


def run_scripts(workspace: Path, analysis: Path) -> None:
    env = os.environ | {"GEO_CACHE": str(analysis / ".cache"), "MPLBACKEND": "Agg"}
    for script in SCRIPTS:
        print(f"Running {script}; log: {workspace / (script + '.log')}", flush=True)
        with (workspace / (script + ".log")).open("w") as log:
            subprocess.run(
                [sys.executable, str(analysis / script)], cwd=workspace,
                env=env, stdout=log, stderr=subprocess.STDOUT, check=True,
            )


def reproduce(work_directory: str | Path) -> None:
    workspace, analysis, expected = prepare_workspace(work_directory)
    revision = snapshot_results(expected)
    run_scripts(workspace, analysis)
    compare_results(expected, analysis / "results")
    print(f"Published headline statistics and tables reproduced against {revision}.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", required=True, type=Path, help="New directory for outputs, fresh cache and logs")
    args = parser.parse_args()
    reproduce(args.work_dir)


if __name__ == "__main__":
    main()
