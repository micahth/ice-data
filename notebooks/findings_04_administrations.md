# Analysis #4 — Administration Comparison
## ICE Detention Data, 2019–2026

---

## What We Measured

| Metric | Description |
|---|---|
| Arrests per month | Number of ICE arrests recorded per calendar month |
| Median detention length | Median days detained for released detainees |
| Release rate | % of detainees with a recorded book-out date |
| Criminality mix | Share of detainees by criminal history category |

---

## Summary Table

| Administration | Arrests/month | Median detention (days) | Release rate | % No criminal record |
|---|---|---|---|---|
| Obama 2nd | — | — | — | — |
| Trump 1st | — | — | — | — |
| Biden | 11,361 | 33 | 99.6% | 66% |
| Trump 2nd | 24,710 | 26 | 93.2% | 37% |

---

## Key Findings

### 1. Arrests nearly doubled from Biden to Trump 2nd
Monthly arrests went from **11,361 under Biden** to **24,710 under Trump 2nd** —
a 118% increase. This is the single largest measurable shift between administrations
in this dataset.

### 2. Detention length fell slightly
Median detention dropped from **33 days (Biden) to 26 days (Trump 2nd)**.
This is counterintuitive given the surge in arrests, but may reflect faster
processing of straightforward cases at the border.

### 3. Release rate declined
The share of detainees with a recorded release dropped from **99.6% to 93.2%**.
The 6.4 percentage point drop means a larger share of detainees remain in custody
with no recorded book-out — either still detained or missing from records.

### 4. Criminality mix shifted sharply
Under Biden, **66% of detainees had no criminal record** ("Other Immigration Violator").
Under Trump 2nd that fell to **37%**, while pending criminal charges surged from
**9% to 28%**. Convicted criminals rose from 25% to 34%.

---

## Caveats

### Data coverage
- The arrests file appears to begin around **2018–2019**. Obama 2nd and Trump 1st
  rows in the summary table show `NaN` for arrests/month because the file does not
  cover those years. Do not compare those administrations on arrest volume.

### Detention stays file coverage
- Obama 2nd and Trump 1st have only **10 and 191 records** respectively in the
  detention stays file. These are statistically meaningless. All administration
  comparisons should be restricted to **Biden vs. Trump 2nd**.

### Implausible detention lengths
- Obama 2nd median: 3,817 days. Trump 1st median: 1,176 days. These are artifacts
  of a small number of very old open cases still appearing in the file — not true
  detention lengths. Disregard them.

### Censored records
- 2.7% of records have no book-out date. They are counted as "not released" in the
  release rate calculation. This slightly understates the true release rate.

### "Pending criminal charges" category
- The surge in pending charges under Trump 2nd (9% → 28%) could reflect a genuine
  policy shift toward arresting people with open cases, or it could reflect a change
  in how ICE classifies detainees at book-in. Cannot be determined from this data alone.

### Causation
- All findings are descriptive. Changes between administrations reflect policy,
  enforcement priorities, migration patterns, and data collection practices.
  This analysis cannot isolate any single cause.

---

## Figures Produced

| File | Description |
|---|---|
| `admin_monthly_arrests.png` | Monthly arrest counts with administration shading |
| `admin_detention_length.png` | Monthly mean and median detention length |
| `admin_release_rate.png` | Monthly release rate over time |
| `admin_criminality_mix.png` | Stacked area — criminality mix by month |
| `admin_summary_bars.png` | 4-panel bar chart comparing administrations |

---

## Suggested Headlines

- *"ICE arrests more than doubled in Trump's second term"*
- *"Share of ICE detainees with no criminal record fell from 66% to 37%"*
- *"Release rate from ICE detention dropped 6 points under Trump 2nd"*

---

*Data source: ICE detention stays and arrests files, extracted 7/24/2026.
Analysis by: [your name]. Code: `notebooks/analysis_04_administrations.py`*