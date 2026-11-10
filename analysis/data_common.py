"""Read the original CSV exports or explicitly selected DDP parquet downloads."""
import os
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV_INPUTS = {
    "arrests": ["arrests_2026-07-24.csv"],
    "detention-stays": ["detention_stays_2026-07-24_part1.csv", "detention_stays_2026-07-24_part2.csv"],
    "detention-stints": ["detention_stints_2026-07-24_part1.csv",
                        "detention_stints_2026-07-24_part2.csv", "detention_stints_part3.csv"],
}


def read_source(name, columns=None):
    directory = os.environ.get("ICE_DATA_DIR")
    if directory:
        return pd.read_parquet(Path(directory) / f"{name}-latest.parquet", columns=columns)
    frames = []
    for filename in CSV_INPUTS[name]:
        path = REPO / "data" / filename
        with path.open("rb") as source:
            if source.read(42).startswith(b"version https://git-lfs.github.com/spec/v1"):
                raise ValueError(f"{filename} is an LFS pointer; hydrate this input or set ICE_DATA_DIR")
        frames.append(pd.read_csv(path, usecols=columns, low_memory=False, encoding="latin-1"))
    return pd.concat(frames, ignore_index=True)
