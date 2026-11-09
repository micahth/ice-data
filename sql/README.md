# SQL views

Declarative (SQL) reproductions of selected result tables, as a counterpart to the
imperative pandas pipelines in `notebooks/`. The goal is to show the same analysis
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
con.execute("CREATE VIEW arrests AS SELECT * FROM read_csv_auto('data/arrests-latest 7-24-2026.csv')")
print(con.execute(open("sql/arrests_by_state.sql").read()).fetchdf().head(15))
PY
```

## Verification

`tests/test_sql.py` runs `arrests_by_state.sql` and the equivalent pandas pipeline over
the same synthetic fixture and asserts the per-state counts match, so the SQL and Python
implementations cannot silently diverge. The test runs in CI without the raw LFS data.
