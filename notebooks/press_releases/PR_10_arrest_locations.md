# PRESS RELEASE 10 — ICE arrests more than doubled in daily pace; Texas still leads, but San Diego, Virginia and Georgia grew fastest

**Old = 2023-01-01 → 2024-12-31 (731 days) · New = 2025-01-01 → 2026-03-10 (434 days).** Source: `arrests-latest 7-24-2026.csv`, de-duplicated with ICE's `duplicate_drop_row` flag. Script: `notebooks/09_arrest_locations.py`.

- **Overall pace:** ~359 arrests/day (old) → ~909/day (new), about **+153%**. Monthly arrests rose from 8,181 (Nov 2024) to a peak of 39,829 (Dec 2025).
- **Texas** accounts for 25.7% of new-era arrests (101,231), up from 98 to 233 per day (+138%).
- **Fastest-growing states (≥5,000 new-era arrests):** Virginia +413%, Georgia +332%, Pennsylvania +260%, Maryland +260%, Florida +245%.
- **Slowest-growing large states:** New Jersey +61% and New York +64% (both below the national pace; New Jersey and New York arrest totals are essentially flat in absolute terms: 12,141 → 11,612 and 14,440 → 14,074, but the new window is 41% shorter).
- **By area of responsibility (AOR):** San Diego grew **+961%** (2.4 → 25.4/day), followed by Washington +422%, El Paso +364%, Philadelphia +292% and Atlanta +261%. Miami is now the busiest AOR (40,245 arrests, 10.2%).
- **Site-level:** San Diego, CA arrests went from 283 to 5,331 (+2,103% per day); Laredo ("LRD general area") grew ~16×.
- **Who is arrested changed:** share with a criminal conviction fell from 43.0% to 33.1%; share with pending criminal charges rose from 17.4% to 29.0%; "other immigration violators" were about flat (39.7% → 37.9%).

**Caveats:** Counts are arrests by recorded apprehension location, not residence. Many site entries are non-specific "general area" codes. The file contains one record dated 2026-03-11 and one stray 2026-09-17 record; both are excluded as the data effectively end 2026-03-10. March 2026 is a 10-day partial month, and February 2026 (29,661) is lower than January (37,612), which may reflect incomplete recent data or a real slowdown and should not be over-read. All changes are descriptive, not causal.
