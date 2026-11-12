"""
Download the newest Deportation Data Project ICE core data (parquet) from
github.com/deportationdata/ice (LFS-backed, served via media.githubusercontent.com).

Run from the repo root:  python notebooks/fetch_latest_data.py
Files are saved to data_updated/ (git-ignored; ~580 MB total).

Each download is written atomically and validated as a readable parquet that
exposes the columns the analyses depend on and contains at least one row, so a
truncated transfer or a reshaped upstream schema fails loudly instead of leaving
a plausible-looking file in place.
"""

import os
import tempfile
import urllib.request

import pyarrow.parquet as pq

BASE = "https://media.githubusercontent.com/media/deportationdata/ice/main/data/"

# A few columns every downstream script reads; enough to catch a wrong/empty file.
FILES = {
    "arrests-latest.parquet": ["apprehension_date", "apprehension_state_filled_in", "apprehension_aor"],
    "detainers-latest.parquet": ["detainer_prepare_date", "facility_state"],
    "detention-stays-latest.parquet": ["stay_ID", "n_stints"],
    "detention-stints-latest.parquet": ["book_in_date_time", "detention_facility_code", "stay_ID"],
    "joined-arrests-detention-stays-latest.parquet": ["unique_identifier", "apprehension_date"],
}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_updated")
os.makedirs(OUT, exist_ok=True)


def validate(path, name, required):
    parquet = pq.ParquetFile(path)
    missing = [column for column in required if column not in parquet.schema_arrow.names]
    if missing:
        raise ValueError(f"{name} is missing expected column(s): {missing}")
    if parquet.metadata.num_rows == 0:
        raise ValueError(f"{name} contained no rows")
    return parquet.metadata.num_rows


for name, required in FILES.items():
    dest = os.path.join(OUT, name)
    print(f"Downloading {name} ...")
    handle, temporary = tempfile.mkstemp(dir=OUT, suffix=".part")
    os.close(handle)
    try:
        urllib.request.urlretrieve(BASE + name, temporary)
        rows = validate(temporary, name, required)
        os.replace(temporary, dest)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    print(f"  {os.path.getsize(dest) / 1e6:.0f} MB, {rows:,} rows -> {dest}")
