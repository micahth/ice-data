import hashlib
import os
from pathlib import Path

import pandas as pd
import pytest

import geo_common


def _write_payload(payload):
    def fake_run(cmd, check):
        Path(cmd[3]).write_bytes(payload)   # cmd = ["curl", "-sfL", "-o", <temp>, <url>]
    return fake_run


def test_fetch_verifies_checksum_and_replaces_atomically(tmp_path, monkeypatch):
    payload = b"synthetic source file"
    monkeypatch.setattr(geo_common, "CACHE", str(tmp_path))
    monkeypatch.setitem(geo_common.SOURCE_CHECKSUMS, "gdp.csv",
                        {"sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)})
    monkeypatch.setattr(geo_common.subprocess, "run", _write_payload(payload))
    path = geo_common.fetch("gdp.csv")
    assert Path(path).read_bytes() == payload
    assert not Path(path + ".part").exists()


def test_bad_download_raises_and_leaves_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(geo_common, "CACHE", str(tmp_path))
    monkeypatch.setitem(geo_common.SOURCE_CHECKSUMS, "gdp.csv", {"sha256": "0" * 64, "size": 999})
    monkeypatch.setattr(geo_common.subprocess, "run", _write_payload(b"corrupt bytes"))
    with pytest.raises(ValueError, match="Checksum/size mismatch"):
        geo_common.fetch("gdp.csv")
    assert not (tmp_path / "gdp.csv").exists()
    assert not (tmp_path / "gdp.csv.part").exists()


def test_corrupt_cache_is_reverified_and_replaced(tmp_path, monkeypatch):
    payload = b"good source bytes"
    monkeypatch.setattr(geo_common, "CACHE", str(tmp_path))
    (tmp_path / "gdp.csv").write_bytes(b"stale truncated cache")
    monkeypatch.setitem(geo_common.SOURCE_CHECKSUMS, "gdp.csv",
                        {"sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)})
    monkeypatch.setattr(geo_common.subprocess, "run", _write_payload(payload))
    assert Path(geo_common.fetch("gdp.csv")).read_bytes() == payload


def test_checksum_manifest_covers_every_source():
    assert set(geo_common.SOURCE_CHECKSUMS) == set(geo_common.SOURCES)
    assert len(geo_common.POP_SHARD_CHECKSUMS) == 256
    for entry in {**geo_common.SOURCE_CHECKSUMS, **geo_common.POP_SHARD_CHECKSUMS}.values():
        assert len(entry["sha256"]) == 64 and entry["size"] > 0


def test_require_columns_detects_missing_column():
    with pytest.raises(ValueError, match="missing expected column"):
        geo_common.require_columns(pd.DataFrame({"year": [1]}), "fbi_crime.csv")


def test_require_columns_rejects_empty_frame():
    columns = geo_common.REQUIRED_COLUMNS["fbi_crime.csv"]
    with pytest.raises(ValueError, match="no rows"):
        geo_common.require_columns(pd.DataFrame(columns=columns), "fbi_crime.csv")
