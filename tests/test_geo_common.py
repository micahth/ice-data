import hashlib
from pathlib import Path

import pandas as pd
import pytest

import geo_common


def test_external_inputs_have_publisher_retrieval_and_checksum_metadata():
    assert set(geo_common.PROVENANCE) == set(geo_common.SOURCES) == set(geo_common.CHECKSUMS)
    for source in geo_common.PROVENANCE.values():
        assert source["publisher"]
        assert source["original_url"].startswith("https://")
        assert source["retrieval_url"].startswith("https://")
        assert source["retrieved_on"] == geo_common.RETRIEVED_ON
        assert len(source["sha256"]) == 64

    assert geo_common.POP_PROVENANCE["publisher"]
    assert geo_common.POP_PROVENANCE["original_url"].startswith("https://")
    assert geo_common.POP_PROVENANCE["retrieval_url_template"].startswith("https://")
    assert geo_common.POP_PROVENANCE["retrieved_on"] == geo_common.RETRIEVED_ON
    assert len(geo_common.POP_PROVENANCE["sha256"]) == 64


def _write_payload(payload):
    def fake_run(cmd, **kwargs):
        Path(cmd[cmd.index("-o") + 1]).write_bytes(payload)
    return fake_run


def test_fetch_verifies_checksum_and_replaces_atomically(tmp_path, monkeypatch):
    payload = b"synthetic source file"
    monkeypatch.setattr(geo_common, "CACHE", str(tmp_path))
    monkeypatch.setitem(geo_common.SOURCES, "gdp.csv", "https://example.test/data.csv")
    monkeypatch.setitem(geo_common.SOURCE_CHECKSUMS, "gdp.csv",
                        {"sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)})
    monkeypatch.setattr(geo_common.subprocess, "run", _write_payload(payload))
    path = geo_common.fetch("gdp.csv")
    assert Path(path).read_bytes() == payload
    assert not Path(path + ".part").exists()


def test_fetch_rejects_bad_download_and_tampered_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(geo_common, "CACHE", str(tmp_path))
    monkeypatch.setattr(geo_common.subprocess, "run", _write_payload(b"unexpected"))
    monkeypatch.setitem(geo_common.SOURCE_CHECKSUMS, "gdp.csv",
                        {"sha256": hashlib.sha256(b"expected").hexdigest(), "size": len(b"expected")})
    target = tmp_path / "gdp.csv"
    with pytest.raises(ValueError, match="Checksum/size mismatch"):
        geo_common.fetch("gdp.csv")
    assert not target.exists()
    assert not (tmp_path / "gdp.csv.part").exists()

    target.write_bytes(b"tampered cache")
    with pytest.raises(ValueError, match="Checksum/size mismatch"):
        geo_common.fetch("gdp.csv")
    assert not target.exists()


def test_population_shards_are_verified_against_individual_and_aggregate_checksums(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    shards = cache / "pop"
    shards.mkdir(parents=True)
    payloads = {f"{i:02x}.json": f"shard {i:02x}".encode() for i in range(256)}
    checksums = {
        name: {"sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}
        for name, payload in payloads.items()
    }
    aggregate = hashlib.sha256()
    for name, entry in sorted(checksums.items()):
        aggregate.update(f"pop/{name} {entry['sha256']}\n".encode())
    monkeypatch.setattr(geo_common, "CACHE", str(cache))
    monkeypatch.setattr(geo_common, "POP_SHARD_CHECKSUMS", checksums)
    monkeypatch.setitem(geo_common.POP_PROVENANCE, "sha256", aggregate.hexdigest())
    for name, payload in payloads.items():
        (shards / name).write_bytes(payload)

    assert Path(geo_common.fetch_pop_shards()) == shards

    def fake_run(cmd, **kwargs):
        name = cmd[-1].rsplit("/", 1)[-1]
        Path(cmd[cmd.index("-o") + 1]).write_bytes(payloads[name])

    monkeypatch.setattr(geo_common.subprocess, "run", fake_run)
    (shards / "80.json").write_text("changed")
    assert Path(geo_common.fetch_pop_shards()) == shards
    assert (shards / "80.json").read_bytes() == payloads["80.json"]


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
