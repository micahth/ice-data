"""Alternative SQL implementation of the arrest cohort and published aggregates."""
import os
from pathlib import Path

import duckdb

from arrest_common import ARREST_DAYS, ARREST_END, ARREST_SPLIT, ARREST_START
from data_common import CSV_INPUTS, REPO

SQL = Path(__file__).resolve().parent / "sql"


def aggregate_arrests(connection):
    """Aggregate a registered raw_arrests relation, keeping record-level data local."""
    connection.execute((SQL / "clean_arrests.sql").read_text(), {
        "start_date": ARREST_START.to_pydatetime(), "split_date": ARREST_SPLIT.to_pydatetime(),
        "end_date": ARREST_END.to_pydatetime(),
    })
    count = connection.execute("SELECT COUNT(*) FROM cleaned_arrests").fetchone()[0]
    if not count:
        raise ValueError("SQL arrest cohort is empty; check the input and observation window")
    tables = {}
    for location in ("state", "aor", "landmark"):
        connection.execute(
            f"CREATE OR REPLACE TEMP VIEW locations AS SELECT {location} AS location, era FROM cleaned_arrests"
        )
        table = connection.execute((SQL / "arrest_locations.sql").read_text(), {
            "old_days": ARREST_DAYS["old"], "new_days": ARREST_DAYS["new"],
        }).df().rename(columns={"location": location})
        tables[f"arrests_by_{location}"] = table
    tables["arrest_summary"] = connection.execute("""
        SELECT era, COUNT(*) AS arrests,
               CASE WHEN era = 'old' THEN $old_days ELSE $new_days END AS days,
               arrests / days AS arrests_per_day
        FROM cleaned_arrests GROUP BY era ORDER BY era
    """, {"old_days": ARREST_DAYS["old"], "new_days": ARREST_DAYS["new"]}).df()
    tables["arrest_criminality"] = connection.execute("""
        PIVOT cleaned_arrests ON criminality USING COUNT(*) GROUP BY era ORDER BY era
    """).df()
    tables["monthly_arrests"] = connection.execute("""
        WITH months AS (
            SELECT month FROM GENERATE_SERIES(
                CAST($start_date AS TIMESTAMP),
                DATE_TRUNC('month', CAST($end_date AS TIMESTAMP) - INTERVAL 1 DAY),
                INTERVAL 1 MONTH
            ) AS series(month)
        )
        SELECT STRFTIME(month, '%Y-%m') AS month, COUNT(arrest_date) AS arrests,
               DATE_DIFF('day', month, LEAST(month + INTERVAL 1 MONTH, CAST($end_date AS TIMESTAMP))) AS days_observed,
               month = DATE_TRUNC('month', CAST($end_date AS TIMESTAMP)) AS partial_month
        FROM months LEFT JOIN cleaned_arrests
          ON DATE_TRUNC('month', arrest_date) = month
        GROUP BY month ORDER BY month
    """, {"start_date": ARREST_START.to_pydatetime(), "end_date": ARREST_END.to_pydatetime()}).df()
    return tables


def run_sql(output_directory):
    with duckdb.connect() as connection:
        downloaded = os.environ.get("ICE_DATA_DIR")
        if downloaded:
            connection.read_parquet(str(Path(downloaded) / "arrests-latest.parquet")).create_view("raw_arrests")
        else:
            source = REPO / "data" / CSV_INPUTS["arrests"][0]
            with source.open("rb") as stream:
                if stream.read(42).startswith(b"version https://git-lfs.github.com/spec/v1"):
                    raise ValueError(f"{source.name} is an LFS pointer; hydrate this input or set ICE_DATA_DIR")
            connection.execute("""
                CREATE TEMP TABLE raw_arrests AS
                SELECT apprehension_date, duplicate_drop_row,
                       apprehension_state_filled_in, apprehension_state_original,
                       apprehension_aor, apprehension_site_landmark, apprehension_criminality
                FROM read_csv($source, all_varchar = true, encoding = 'latin-1',
                              nullstr = $null_values)
            """, {"source": str(source), "null_values": [
                "", "NA", "N/A", "NaN", "nan", "NULL", "null", "None", "<NA>",
                "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "1.#IND",
                "1.#QNAN", "-NaN", "-nan",
            ]})
        tables = aggregate_arrests(connection)
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(output_directory / f"{name}.csv", index=False)
    print(f"SQL cohort: {tables['arrest_summary'].arrests.sum():,} arrest records; wrote {len(tables)} tables")
