# SQL views

Declarative (SQL) reproductions of selected result tables, as a counterpart to the
pandas pipelines in `notebooks/`. The goal is to show the same analysis
expressed as set-based queries and to prove the two implementations agree.

| Query | Reproduces | Pandas source of truth |
|---|---|---|
| [`arrests_by_state.sql`](arrests_by_state.sql) | `notebooks/results/arrests_by_state.csv` | `notebooks/09_arrest_locations.py` |

Each query expects a table or view named `arrests` holding the raw DDP arrest columns,
so the same SQL runs against a CSV export, a parquet file, or a warehouse table.

## Run with DuckDB

[DuckDB](https://duckdb.org/) reads CSV and parquet directly, so no database server is
needed (`duckdb` is pinned in `requirements.txt`):

```bash
python - <<'PY'
import duckdb
con = duckdb.connect()
import pandas as pd
con.register("arrests", pd.read_csv("data/arrests-latest 7-24-2026.csv",
                                   encoding="latin-1", low_memory=False))
print(con.execute(open("sql/arrests_by_state.sql").read()).fetchdf().head(15))
PY
```

## Verification

`tests/test_sql.py` runs `arrests_by_state.sql` and the equivalent pandas pipeline over
the same synthetic fixture and asserts **all columns** match: counts, daily rates,
rate change, and shares. Edge cases cover duplicates, missing flags, invalid dates,
the exclusive cutoff, unknown/fallback states, zero baselines, old-only cohorts and
empty input. The test runs in CI without raw LFS data. During development, all SQL
columns were also checked against the committed result table using the exact July
24 CSV (including its Latin-1 encoding).

SQL describes the result and leaves execution planning to the engine. Pandas
`groupby` and joins are also vectorized/set-oriented; they are not inherently
row-by-row imperative loops. The two versions demonstrate different interfaces to
the same relational transformation.
