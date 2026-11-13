# ICE arrests and detention, 2023–2026

**Arrests classified as involving convicted criminals nearly doubled per day**, from
154 to 301, even as their share fell from 43.0% to 33.1%. These are arrest
records, not unique people or completed removals; the comparison adjusts for
window length, not seasonality.

![Daily arrest pace by calendar month and year](analysis/figures/monthly_arrests_by_calendar_month.png)

- Overall arrests rose from 359 to 909 per day (+153%).
- Facility average daily population per local resident rose in every region; this measures where people are held, not where they live.
- None of four primary 2025 arrest-rate tests survived BH adjustment at q < .10; associations are exploratory, not causal.

**Stack:** Python, pandas, DuckDB, statsmodels, Matplotlib, Streamlit, pytest, GitHub Actions.

**Explore:** [Dashboard (local setup)](docs/reproduction.md#dashboard) · [Case study](CASE_STUDY.md) · [Report](final_report.md) · [Methods and reproduction](docs/reproduction.md) · [Data source](https://deportationdata.org/data/ice.html) · [AI use](docs/reproduction.md#ai-use)

## Start here

Requires Python 3.11 or 3.12.

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

### Retrieve the source data

Install [Git LFS](https://git-lfs.com/), then initialize it before cloning:

```bash
git lfs install
git clone https://github.com/micahth/ice-data.git
cd ice-data
```

If the CSVs are still small Git LFS pointer files, retrieve their contents from
the repository directory:

```bash
git lfs pull
```

An ordinary Git LFS pointer is only a reference to the data, not the underlying
CSV.

### Published data inventory

These four checksum-pinned source files are all from the `2026-07-24` snapshot;
their hashes and immutable source revision are in the
[input manifest](analysis/published_inputs.json).

| File |
|---|
| `data/arrests_2026-07-24.csv` |
| `data/detention_stints_2026-07-24_part1.csv` |
| `data/detention_stints_2026-07-24_part2.csv` |
| `data/detention_stints_2026-07-24_part3.csv` |

## License and data terms

The project’s original code is licensed under the [MIT License](LICENSE). This
license does not grant rights to the source data. The arrest and detention
records are published by the [Deportation Data Project](https://deportationdata.org/data/ice.html)
from data received from ICE; its [data documentation](https://deportationdata.org/docs/ice.html)
does not specify reuse or redistribution terms for these files. Those terms are
therefore unclear; check with the source before redistributing the data.
