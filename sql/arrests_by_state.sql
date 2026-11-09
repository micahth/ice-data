-- Arrest records per day by apprehension state: old era (CY2023-2024) vs.
-- new era (2025-01-01 through 2026-03-10). This is the declarative (SQL)
-- expression of the pandas pipeline in notebooks/09_arrest_locations.py and
-- reproduces notebooks/results/arrests_by_state.csv. The equivalence of the two
-- implementations is cross-checked in tests/test_sql.py.
--
-- Expects a table or view named `arrests` holding the raw DDP arrest columns, e.g.:
--   CREATE VIEW arrests AS
--   SELECT * FROM read_csv_auto('data/arrests-latest 7-24-2026.csv');
--
-- Window lengths mirror arrest_common.ARREST_DAYS:
--   old = (2025-01-01) - (2023-01-01) = 731 days
--   new = (2026-03-11) - (2025-01-01) = 434 days   (end date is exclusive)
WITH cleaned AS (
    SELECT
        -- Prefer the filled-in state, fall back to the original, then 'Unknown'
        -- (matches .fillna(...).fillna('Unknown') in the pandas version).
        COALESCE(
            NULLIF(apprehension_state_filled_in, ''),
            NULLIF(apprehension_state_original, ''),
            'Unknown'
        ) AS state,
        CASE
            WHEN TRY_CAST(apprehension_date AS DATE) < DATE '2025-01-01'
            THEN 'old' ELSE 'new'
        END AS era
    FROM arrests
    WHERE NOT COALESCE(duplicate_drop_row, FALSE)               -- drop flagged duplicate records
      AND TRY_CAST(apprehension_date AS DATE) >= DATE '2023-01-01'
      AND TRY_CAST(apprehension_date AS DATE) <  DATE '2026-03-11'
),
by_state AS (
    SELECT
        state,
        COUNT(*) FILTER (WHERE era = 'old') AS old,
        COUNT(*) FILTER (WHERE era = 'new') AS new
    FROM cleaned
    GROUP BY state
)
SELECT
    state,
    old,
    new,
    old / 731.0 AS old_per_day,
    new / 434.0 AS new_per_day,
    CASE WHEN old > 0
         THEN (new / 434.0) / (old / 731.0) * 100 - 100
    END AS change_pct,
    new * 100.0 / SUM(new) OVER () AS share_new_pct
FROM by_state
ORDER BY new DESC;
