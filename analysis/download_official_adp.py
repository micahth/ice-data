"""Download DDP's ICE detention-management ADP tables (pinned, checksum-verified) and reduce them to small CSVs.

Source: https://github.com/deportationdata/ice-detention-management (Git LFS parquet, ICE spreadsheets parsed by DDP).
Writes analysis/data/ice_published_adp_monthly.csv and analysis/results/published_adp_revisions.csv.
"""
import hashlib
import os
import sys
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from adp_common import fytd_check, fytd_revisions, reduce_monthly, validate_monthly  # noqa: E402

HERE = Path(__file__).resolve().parent
REF = "5126c6e8482cb8d28d5a7704e96a9cab0df8b528"
SOURCES = {
    "adp-and-stay-length-by-agency-monthly": (
        "27a9969b5b68751cc58a71f9e3bfe427f875a2e3984f44c0781882ebeb32207f", 19700),
    "adp-and-stay-length-by-agency-fy-ytd": (
        "be5e12df6e2d7a0b44f106b809f3aa0210bd4ad9305191fd7879865d3de07e69", 28757),
}
CACHE = HERE / ".cache"


def download(name):
    expected_hash, expected_size = SOURCES[name]
    CACHE.mkdir(exist_ok=True)
    target = CACHE / f"{name}-{REF[:8]}.parquet"
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected_hash:
        return target
    url = f"https://media.githubusercontent.com/media/deportationdata/ice-detention-management/{REF}/data/{name}.parquet"
    with urlopen(url, timeout=120) as response:
        content = response.read()
    if len(content) != expected_size or hashlib.sha256(content).hexdigest() != expected_hash:
        raise ValueError(f"Checksum/size mismatch for {name}")
    target.write_bytes(content)
    return target


def main():
    monthly = pd.read_parquet(download("adp-and-stay-length-by-agency-monthly"))
    fytd = pd.read_parquet(download("adp-and-stay-length-by-agency-fy-ytd"))
    series = reduce_monthly(monthly)
    problems = validate_monthly(series)
    if problems:
        raise ValueError("; ".join(problems))
    series.round(6).to_csv(HERE / "data" / "ice_published_adp_monthly.csv", index=False)
    total = fytd[(fytd["agency"] == "Total") & (fytd["criminality"] == "Total")]
    fytd_revisions(total).round(6).to_csv(HERE / "results" / "published_adp_revisions.csv", index=False)
    print(fytd_check(series, total).round(4).to_string())
    print(f"Wrote {len(series)} months, {series['month'].min():%Y-%m} to {series['month'].max():%Y-%m}")


if __name__ == "__main__":
    main()
