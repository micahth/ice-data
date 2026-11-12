import hashlib
import subprocess
from pathlib import Path

import pytest

import geo_common


def test_geo_fetch_retries_and_rechecks_cached_sha256(tmp_path, monkeypatch):
    payload = b"frozen secondary input"
    monkeypatch.setattr(geo_common, "CACHE", str(tmp_path))
    monkeypatch.setitem(geo_common.SOURCES, "fixture.json", "https://example.test/fixture.json")
    calls = 0

    def run(command, **kwargs):
        nonlocal calls
        calls += 1
        assert command[command.index("--retry") + 1] == "3"
        assert "--retry-all-errors" in command
        Path(command[command.index("-o") + 1]).write_bytes(payload)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(geo_common.subprocess, "run", run)
    target = Path(geo_common.fetch("fixture.json"))
    assert calls == 1
    assert target.read_bytes() == payload
    assert Path(str(target) + ".sha256").read_text().strip() == hashlib.sha256(payload).hexdigest()

    target.write_bytes(b"corrupted cache")
    assert Path(geo_common.fetch("fixture.json")).read_bytes() == payload
    assert calls == 2


def test_geo_fetch_reports_source_and_curl_error(tmp_path, monkeypatch):
    monkeypatch.setattr(geo_common, "CACHE", str(tmp_path))
    monkeypatch.setitem(geo_common.SOURCES, "fixture.json", "https://example.test/fixture.json")

    def fail(command, **kwargs):
        raise subprocess.CalledProcessError(22, command, stderr="404 not found")

    monkeypatch.setattr(geo_common.subprocess, "run", fail)
    with pytest.raises(RuntimeError, match=r"fixture\.json.*404 not found"):
        geo_common.fetch("fixture.json")
    assert not list(tmp_path.glob("*.part"))
