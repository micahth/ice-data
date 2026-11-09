"""
Download the newest Deportation Data Project ICE core data (parquet) from
github.com/deportationdata/ice (LFS-backed, served via media.githubusercontent.com).

Run from the repo root:  python notebooks/fetch_latest_data.py
Files are saved to data_updated/ (git-ignored; ~580 MB total).
"""

import os
import urllib.request

BASE = "https://media.githubusercontent.com/media/deportationdata/ice/main/data/"
FILES = [
    "arrests-latest.parquet",
    "detainers-latest.parquet",
    "detention-stays-latest.parquet",
    "detention-stints-latest.parquet",
    "joined-arrests-detention-stays-latest.parquet",
]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_updated")
os.makedirs(OUT, exist_ok=True)

for name in FILES:
    dest = os.path.join(OUT, name)
    print(f"Downloading {name} ...")
    urllib.request.urlretrieve(BASE + name, dest)
    print(f"  {os.path.getsize(dest) / 1e6:.0f} MB -> {dest}")
