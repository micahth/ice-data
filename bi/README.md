# Tableau companion

[`ice-geography.twbx`](ice-geography.twbx) is a packaged Tableau workbook containing
the committed annual state panel as a relative CSV source. It contains two bar-chart
worksheets: annual arrests per 100,000 residents and annual arrest records, colored by
region. The initial year is 2025; use the year filter to select **one** year. Summing
annual rates across years does not produce a valid period rate.

Open the workbook in Tableau Desktop or Tableau Public. Region is available as a
dimension for filtering (drag it to Filters and choose Show Filter). The companion
uses ranked-state-style bars rather than claiming a state-to-AOR relationship from
marginal tables. The Python/static dashboards provide the source-derived drill-down.

Rebuild with:

```bash
python bi/build_workbook.py
```

Tests check package integrity, relative data paths, workbook XML, and byte-for-byte
agreement of the embedded CSV with the source. **Native Tableau rendering has not
been verified in this Linux environment.** Publication to Tableau Public requires
opening the workbook in Tableau and signing into your own account; no public
Tableau URL is claimed here.

Records are not unique people or completed removals; apprehension states are not
residence or workplace. The source is the July 24, 2026 DDP export processed by this
project. The workbook contains aggregate data only.
