"""Read the original CSV exports or explicitly selected DDP parquet downloads."""
import os
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV_INPUTS = {
    "arrests": ["arrests-latest 7-24-2026.csv"],
    "detention-stays": ["detention-stays (sheet 1) 7-24-2026.csv", "detention-stays (sheet 2) 7-24-2026.csv"],
    "detention-stints": ["detention-stints (sheet 1) 7-24-2026.csv",
                        "detention-stints (sheet 2) 7-24-2026.csv", "detention-stints (sheet 3).csv"],
}


def read_source(name, columns=None):
    directory = os.environ.get("ICE_DATA_DIR")
    if directory:
        return pd.read_parquet(Path(directory) / f"{name}-latest.parquet", columns=columns)
    frames = []
    for filename in CSV_INPUTS[name]:
        path = REPO / filename
        with path.open("rb") as source:
            if source.read(42).startswith(b"version https://git-lfs.github.com/spec/v1"):
                raise ValueError(f"{filename} is an LFS pointer; hydrate this input or set ICE_DATA_DIR")
        frames.append(pd.read_csv(path, usecols=columns, low_memory=False, encoding="latin-1"))
    return pd.concat(frames, ignore_index=True)
