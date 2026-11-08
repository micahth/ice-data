"""Download checksum-verified public DDP parquet sources, without repository LFS."""
import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen

REF = "bfc8b3fa7602fbf810fb811e6d07ef603e528b78"
SOURCES = {
    "arrests": ("2b0e6bdc990d2da198ce03b80e559819ad4d00382e2a152e08b86e3992867d09", 29460683),
    "detention-stints": ("286c00f63cc35d4878a2010704ffa91697e80213010cd948fc07c1f5b90af964", 252930354),
    "detention-stays": ("cf689865b2165b40a10c49ecc4217048a08f25e62dcf370c939fa885c7688446", 109630322),
}


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
    parser.add_argument("--datasets", nargs="+", choices=SOURCES, default=["arrests", "detention-stints"])
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "raw")
    args = parser.parse_args()
    for name in args.datasets:
        download(name, args.output_dir)


if __name__ == "__main__":
    main()
