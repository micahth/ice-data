import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pandas as pd

REPO = Path(__file__).resolve().parents[1]


def load_builder():
    spec = importlib.util.spec_from_file_location("build_site", REPO / "dashboard/build_site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_standalone_site_and_tableau_package(tmp_path):
    load_builder().build(tmp_path)
    data = json.loads((tmp_path / "data.json").read_text())
    assert data["kpis"]["adp_new"] == 55073.345
    assert len(data["arrests_state_locations"]) > 0
    assert data["sql_result"][0]["new"] == 3
    assert "Plotly" in (tmp_path / "plotly.min.js").read_text()
    viewer = (tmp_path / "figures.html").read_text()
    assert "../analysis/figures/" not in viewer
    assert (tmp_path / "figures/monthly_arrests.png").exists()
    topology = json.loads((tmp_path / "static/usa_110m.json").read_text())
    assert topology["type"] == "Topology"
    assert "subunits" in topology["objects"]
    assert (tmp_path / "static/LICENSE.plotly").exists()
    with ZipFile(tmp_path / "ice-geography.twbx") as archive:
        assert archive.testzip() is None
        root = ET.fromstring(archive.read("ice-geography.twb"))
        assert len(root.findall("./worksheets/worksheet")) == 2
        connection = root.find("./datasources/datasource/connection")
        assert connection.attrib["directory"] == "data"
        assert archive.read("data/arrest_rate_panel.csv") == (
            REPO / "analysis/results/arrest_rate_panel.csv").read_bytes()
        for sheet in root.findall("./worksheets/worksheet"):
            year_filter = sheet.find("./table/view/filter/groupfilter")
            assert year_filter.attrib["member"] == "2025"
    expected = pd.read_csv(REPO / "analysis/results/arrest_rate_panel.csv")
    assert sum(row["arrests"] for row in data["arrest_rate_panel"]) == expected.arrests.sum()
