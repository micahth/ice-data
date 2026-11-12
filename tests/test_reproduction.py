import hashlib
import io
from pathlib import Path
import subprocess

import pandas as pd
import pytest

import download_data
from data_common import CSV_INPUTS
import reproduce

REPO = Path(__file__).resolve().parents[1]


def test_manifest_covers_exact_pipeline_inputs_and_matches_pinned_lfs_objects():
    manifest = download_data.published_manifest()
    assert set(manifest["files"]) == set(CSV_INPUTS["arrests"] + CSV_INPUTS["detention-stints"])
    guide = (REPO / "analysis/MASTER_RESULTS.md").read_text()
    for name, metadata in manifest["files"].items():
        pointer = subprocess.check_output(
            ["git", "show", f"{manifest['revision']}:data/{name}"], cwd=REPO, text=True,
        )
        assert f"oid sha256:{metadata['sha256']}\n" in pointer
        assert f"size {metadata['size']}\n" in pointer
        assert name in guide and metadata["sha256"] in guide


@pytest.fixture
def published_payload(monkeypatch):
    payload = b"synthetic published CSV content"
    manifest = {
        "repository": "micahth/ice-data",
        "revision": "fixed-revision",
        "files": {"example.csv": {"sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}},
    }
    monkeypatch.setattr(download_data, "published_manifest", lambda: manifest)
    return payload


def test_published_download_verifies_and_replaces_pointer(tmp_path, monkeypatch, published_payload):
    (tmp_path / "example.csv").write_bytes(b"version https://git-lfs.github.com/spec/v1")
    urls = []

    def response(url, timeout):
        urls.append(url)
        return io.BytesIO(published_payload)

    monkeypatch.setattr(download_data, "urlopen", response)
    download_data.download_published(tmp_path)
    download_data.verify_published(tmp_path)
    assert (tmp_path / "example.csv").read_bytes() == published_payload
    assert urls == ["https://media.githubusercontent.com/media/micahth/ice-data/fixed-revision/data/example.csv"]
    assert not (tmp_path / "example.csv.part").exists()
    download_data.download_published(tmp_path)
    assert len(urls) == 1


def test_published_bad_download_preserves_existing_file(tmp_path, monkeypatch, published_payload):
    target = tmp_path / "example.csv"
    target.write_bytes(b"old content")
    monkeypatch.setattr(download_data, "urlopen", lambda url, timeout: io.BytesIO(b"bad"))
    with pytest.raises(ValueError, match="Checksum/size mismatch"):
        download_data.download_published(tmp_path)
    assert target.read_bytes() == b"old content"
    assert not (tmp_path / "example.csv.part").exists()


def test_published_verification_rejects_missing_or_corrupt_input(tmp_path, published_payload):
    with pytest.raises(FileNotFoundError):
        download_data.verify_published(tmp_path)
    (tmp_path / "example.csv").write_bytes(b"x" * len(published_payload))
    with pytest.raises(ValueError, match="Checksum/size mismatch"):
        download_data.verify_published(tmp_path)


@pytest.fixture
def result_directories(tmp_path):
    expected, actual = tmp_path / "expected", tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    data = pd.DataFrame({"era": ["old", "new"], "arrests": [262329, 394590], "rate": [358.8632, 909.1935]})
    data.to_csv(expected / "summary.csv", index=False)
    data.to_csv(actual / "summary.csv", index=False)
    return expected, actual


def test_comparison_ignores_row_order_and_tiny_roundoff(result_directories):
    expected, actual = result_directories
    data = pd.read_csv(actual / "summary.csv").iloc[::-1]
    data["rate"] += 1e-8
    data.to_csv(actual / "summary.csv", index=False)
    reproduce.compare_results(expected, actual)


@pytest.mark.parametrize("change", ["count", "rate", "text", "missing", "extra", "column", "null", "row"])
def test_comparison_rejects_changed_results(result_directories, change):
    expected, actual = result_directories
    path = actual / "summary.csv"
    data = pd.read_csv(path)
    if change == "missing":
        path.unlink()
    elif change == "extra":
        data.to_csv(actual / "extra.csv", index=False)
    else:
        if change == "count":
            data.loc[0, "arrests"] += 1
        elif change == "rate":
            data.loc[0, "rate"] += 0.00001
        elif change == "text":
            data.loc[0, "era"] = "changed"
        elif change == "column":
            data = data.rename(columns={"rate": "wrong"})
        elif change == "null":
            data.loc[0, "rate"] = float("nan")
        elif change == "row":
            data = data.iloc[:1]
        data.to_csv(path, index=False)
    with pytest.raises(AssertionError):
        reproduce.compare_results(expected, actual)


def test_reproduction_rejects_alternative_source_before_running(tmp_path, monkeypatch):
    monkeypatch.setenv("ICE_DATA_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="Unset ICE_DATA_DIR"):
        reproduce.reproduce(tmp_path / "work")
    assert not (tmp_path / "work").exists()


def test_reproduction_refuses_reused_workspace(tmp_path, monkeypatch):
    monkeypatch.delenv("ICE_DATA_DIR", raising=False)
    monkeypatch.setattr(reproduce, "verify_published", lambda directory: None)
    with pytest.raises(FileExistsError):
        reproduce.reproduce(tmp_path)
