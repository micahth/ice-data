-- The caller creates locations(location, era) from one fixed, allowlisted column.
WITH counts AS (
    SELECT location,
           COUNT(*) FILTER (WHERE era = 'old') AS old,
           COUNT(*) FILTER (WHERE era = 'new') AS new
    FROM locations
    GROUP BY location
), rates AS (
    SELECT *, old / $old_days AS old_per_day, new / $new_days AS new_per_day
    FROM counts
)
SELECT *,
       (new_per_day / NULLIF(old_per_day, 0) - 1) * 100 AS change_pct,
       new / NULLIF(SUM(new) OVER (), 0) * 100 AS share_new_pct
FROM rates
ORDER BY new DESC, location;
