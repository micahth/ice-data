"""Build a self-contained, interactive Pages companion from committed result tables."""
import argparse
import json
from pathlib import Path
import shutil
import sys

import duckdb
import pandas as pd
from plotly.offline import get_plotlyjs

import panels

REPO = Path(__file__).resolve().parents[1]


def build(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    names = ["arrest_rate_panel", "arrests_state_locations", "monthly_arrests",
             "by_region", "by_cbsa_class", "by_operator", "arrest_regressions"]
    data = {name: json.loads(pd.read_csv(panels.RESULTS / f"{name}.csv").to_json(orient="records"))
            for name in names}
    data["kpis"] = panels.summary_kpis()
    sys.path.insert(0, str(REPO / "notebooks"))
    from geo_common import STATE_ABBR
    data["states"] = {abbr: name.upper() for name, abbr in STATE_ABBR.items()}
    data["sql"] = (REPO / "sql/arrests_by_state.sql").read_text()
    with duckdb.connect() as con:
        con.register("arrests", pd.read_csv(REPO / "tests/fixtures/arrests.csv"))
        data["sql_result"] = json.loads(con.execute(data["sql"]).fetchdf().to_json(orient="records"))
    (destination / "data.json").write_text(json.dumps(data, allow_nan=False))
    (destination / "plotly.min.js").write_text(get_plotlyjs())
    for name in ("site.js", "index.html"):
        shutil.copyfile(Path(__file__).parent / name, destination / name)
    shutil.copytree(Path(__file__).parent / "static", destination / "static", dirs_exist_ok=True)
    shutil.copytree(REPO / "notebooks/figures", destination / "figures", dirs_exist_ok=True)
    shutil.copytree(panels.RESULTS, destination / "results", dirs_exist_ok=True)
    viewer = (REPO / "outputs/index.html").read_text().replace("../notebooks/figures/", "figures/")
    for name in ("CASE_STUDY.md", "Final%20Report.md"):
        viewer = viewer.replace(f"../{name}", f"https://github.com/micahth/ice-data/blob/main/{name}")
    viewer = viewer.replace('href="README.md"', 'href="https://github.com/micahth/ice-data/tree/main/outputs"')
    (destination / "figures.html").write_text(viewer)
    (destination / ".nojekyll").touch()
    sys.path.insert(0, str(REPO / "bi"))
    from build_workbook import build_workbook
    build_workbook(destination / "ice-geography.twbx")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPO / "site")
    build(parser.parse_args().output)
