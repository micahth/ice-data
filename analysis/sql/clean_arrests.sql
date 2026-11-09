CREATE TEMP TABLE cleaned_arrests AS
WITH parsed AS (
    SELECT
        TRY_CAST(apprehension_date AS TIMESTAMP) AS arrest_date,
        COALESCE(CAST(duplicate_drop_row AS BOOLEAN), FALSE) AS is_duplicate,
        COALESCE(apprehension_state_filled_in, apprehension_state_original, 'Unknown') AS state,
        COALESCE(apprehension_aor, 'Unknown') AS aor,
        COALESCE(UPPER(TRIM(apprehension_site_landmark)), 'Unknown') AS landmark,
        COALESCE(apprehension_criminality, 'Unknown') AS criminality
    FROM raw_arrests
)
SELECT
    arrest_date, state, aor, landmark, criminality,
    CASE WHEN arrest_date < $split_date THEN 'old' ELSE 'new' END AS era
FROM parsed
WHERE NOT is_duplicate
  AND arrest_date >= $start_date
  AND arrest_date < $end_date;
