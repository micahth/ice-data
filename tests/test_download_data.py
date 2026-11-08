import hashlib
import io

import pytest

import download_data


def test_download_checks_hash_and_atomically_replaces_file(tmp_path, monkeypatch):
    payload = b"synthetic parquet stand-in"
    monkeypatch.setitem(download_data.SOURCES, "arrests", (hashlib.sha256(payload).hexdigest(), len(payload)))
    monkeypatch.setattr(download_data, "urlopen", lambda url, timeout: io.BytesIO(payload))
    target = download_data.download("arrests", tmp_path)
    assert target.read_bytes() == payload
    assert not target.with_suffix(".parquet.part").exists()


def test_bad_download_does_not_replace_existing_data(tmp_path, monkeypatch):
    target = tmp_path / "arrests-latest.parquet"
    target.write_bytes(b"previous verified content")
    monkeypatch.setattr(download_data, "urlopen", lambda url, timeout: io.BytesIO(b"bad download"))
    with pytest.raises(ValueError, match="Checksum/size mismatch"):
        download_data.download("arrests", tmp_path)
    assert target.read_bytes() == b"previous verified content"
    assert not target.with_suffix(".parquet.part").exists()
