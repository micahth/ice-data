"""Obtain the exact published CSV inputs, or explicitly select alternative parquet."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

REF = "bfc8b3fa7602fbf810fb811e6d07ef603e528b78"
SOURCES = {
    "arrests": ("2b0e6bdc990d2da198ce03b80e559819ad4d00382e2a152e08b86e3992867d09", 29460683),
    "detention-stints": ("286c00f63cc35d4878a2010704ffa91697e80213010cd948fc07c1f5b90af964", 252930354),
    "detention-stays": ("cf689865b2165b40a10c49ecc4217048a08f25e62dcf370c939fa885c7688446", 109630322),
}
MANIFEST = Path(__file__).with_name("published_inputs.json")


def published_manifest():
    return json.loads(MANIFEST.read_text())


def verify_file(path, expected_hash, expected_size):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    if size != expected_size or digest.hexdigest() != expected_hash:
        raise ValueError(f"Checksum/size mismatch for {path}: {size} bytes, sha256={digest.hexdigest()}")


def verify_published(directory):
    for name, metadata in published_manifest()["files"].items():
        path = Path(directory) / name
        verify_file(path, metadata["sha256"], metadata["size"])
        print(f"Verified {path}: sha256={metadata['sha256']}", flush=True)


def download_published(directory):
    manifest = published_manifest()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, metadata in manifest["files"].items():
        target = directory / name
        if target.exists() and target.stat().st_size == metadata["size"]:
            verify_file(target, metadata["sha256"], metadata["size"])
            print(f"Verified existing {target}", flush=True)
            continue
        source_name = metadata.get("source_filename", name)
        url = (f"https://media.githubusercontent.com/media/{manifest['repository']}/"
               f"{manifest['revision']}/data/{source_name}")
        temporary = target.with_suffix(".csv.part")
        print(f"Downloading published input {name}", flush=True)
        try:
            with urlopen(url, timeout=120) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            verify_file(temporary, metadata["sha256"], metadata["size"])
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"Verified {target}: sha256={metadata['sha256']}", flush=True)


def download(name, directory):
    expected_hash, expected_size = SOURCES[name]
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{name}-latest.parquet"
    temporary = target.with_suffix(".parquet.part")
    url = f"https://media.githubusercontent.com/media/deportationdata/ice/{REF}/data/{target.name}"
    digest = hashlib.sha256()
    size = 0
    try:
        with urlopen(url, timeout=120) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                output.write(chunk)
        if size != expected_size or digest.hexdigest() != expected_hash:
            raise ValueError(f"Checksum/size mismatch for {name}: {size} bytes, sha256={digest.hexdigest()}")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Verified {target}: {size} bytes, sha256={expected_hash}")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["published", "alternative"], default="published")
    parser.add_argument("--verify-only", action="store_true", help="Verify existing published CSVs without downloading")
    parser.add_argument("--datasets", nargs="+", choices=SOURCES, help="Alternative parquet datasets only")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    data = Path(__file__).resolve().parent.parent / "data"
    if args.source == "published":
        if args.datasets:
            parser.error("--datasets requires --source alternative; published reproduction needs all four CSVs")
        directory = args.output_dir or data
        if args.verify_only:
            verify_published(directory)
        else:
            download_published(directory)
        return
    if args.verify_only:
        parser.error("--verify-only requires --source published")
    for name in args.datasets or ["arrests", "detention-stints"]:
        download(name, args.output_dir or data / "raw")


if __name__ == "__main__":
    main()
