import hashlib
from pathlib import Path

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


def test_fetch_verifies_download_before_caching(tmp_path, monkeypatch):
    payload = b"verified source"
    expected = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(geo_common, "CACHE", str(tmp_path))
    monkeypatch.setitem(geo_common.SOURCES, "synthetic.csv", "https://example.test/data.csv")
    monkeypatch.setitem(geo_common.CHECKSUMS, "synthetic.csv", expected)

    def fake_curl(command, check):
        Path(command[4]).write_bytes(payload)

    monkeypatch.setattr(geo_common.subprocess, "run", fake_curl)
    target = Path(geo_common.fetch("synthetic.csv"))
    assert target.read_bytes() == payload
    assert not target.with_suffix(".csv.part").exists()


def test_fetch_rejects_bad_download_and_tampered_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(geo_common, "CACHE", str(tmp_path))
    monkeypatch.setitem(geo_common.SOURCES, "synthetic.csv", "https://example.test/data.csv")
    monkeypatch.setitem(geo_common.CHECKSUMS, "synthetic.csv", hashlib.sha256(b"expected").hexdigest())

    def fake_curl(command, check):
        Path(command[4]).write_bytes(b"unexpected")

    monkeypatch.setattr(geo_common.subprocess, "run", fake_curl)
    target = tmp_path / "synthetic.csv"
    with pytest.raises(ValueError, match="Checksum mismatch"):
        geo_common.fetch("synthetic.csv")
    assert not target.exists()
    assert not (tmp_path / "synthetic.csv.part").exists()

    target.write_bytes(b"tampered cache")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        geo_common.fetch("synthetic.csv")


def test_population_shard_cache_is_checked_as_a_complete_manifest(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    shards = cache / "pop"
    shards.mkdir(parents=True)
    for i in range(256):
        (shards / f"{i:02x}.json").write_text(f"shard {i:02x}")
    expected = geo_common._pop_manifest_digest(str(shards))
    monkeypatch.setattr(geo_common, "CACHE", str(cache))
    monkeypatch.setitem(geo_common.POP_PROVENANCE, "sha256", expected)

    assert Path(geo_common.fetch_pop_shards()) == shards
    (shards / "80.json").write_text("changed")
    with pytest.raises(ValueError, match="Checksum mismatch for population shards"):
        geo_common.fetch_pop_shards()
