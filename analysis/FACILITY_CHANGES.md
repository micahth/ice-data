# Recorded facility activity changes

`03_facility_changes.py` writes [`results/facility_changes.csv`](results/facility_changes.csv) from deduplicated stint book-ins through March 11, 2026. The comparison date is January 20, 2025; earlier records begin in October 2022, not the facility's lifetime.

| Label | Rule |
|---|---|
| New since January 20, 2025 | No earlier book-ins in the observed extract; at least 25 later book-ins |
| Recent start | First observed book-in on/after July 1, 2024, at least 25 later book-ins, earlier volume below 10% of later volume |
| Stopped booking | At least 25 earlier book-ins and some later activity, but no book-ins during the final 90 days |
| Name change | Multiple recorded names under one code, with different first and last names |

The extract identifies **111 codes first observed after the comparison date** and **13 codes with no final-90-day bookings** under these rules. Labels can overlap. A new code is not proof of a new facility, and inactivity is not proof of closure; code changes, sparse use and reporting delays can produce these patterns.

`operator_class` comes from name/code/type heuristics in `geo_common.py`, not an ICE ownership field or independently verified contract history. No ownership changes, reopenings, named contractor events or public-news claims are inferred from these activity counts. The table retains recorded facility names; alias matches to names used in news coverage have not been established.
