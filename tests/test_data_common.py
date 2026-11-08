import pandas as pd

import data_common


def test_csv_loader_reads_named_sources_from_data_directory(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    pd.DataFrame({"value": [1]}).to_csv(data / "source.csv", index=False)
    monkeypatch.setattr(data_common, "REPO", tmp_path)
    monkeypatch.setitem(data_common.CSV_INPUTS, "synthetic", ["source.csv"])
    monkeypatch.delenv("ICE_DATA_DIR", raising=False)
    result = data_common.read_source("synthetic")
    assert result.value.tolist() == [1]
