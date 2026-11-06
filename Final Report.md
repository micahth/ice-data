# Final Report

## Review scope and overall assessment

Reviewed every Markdown document and `codebook.txt`, plus the analysis scripts, generated-result references, and GitHub Actions workflow. The press releases are generally readable and do a good job labeling descriptive analyses and flagging several important limitations. The main concerns are reproducibility, a duration measure described as a full detention stay when it is actually a facility stint, and a workflow configured for a notebook that is not in this repository.

The numerical findings below are interesting claims reported by the project documents; they could not be independently recalculated in this checkout because the CSV inputs and result tables are Git LFS pointers rather than hydrated files.

## Arrest-location analysis (`notebooks/09_arrest_locations.py`, PR 10)

Run on the hydrated `arrests-latest 7-24-2026.csv` (705,286 rows after dropping `duplicate_drop_row`). Old = 2023–2024 (731 days); new = 2025-01-01 to 2026-03-10 (434 days). Outputs: `notebooks/results/arrests_by_{state,aor,landmark}.csv`; press release `notebooks/press_releases/PR_10_arrest_locations.md`.

- Daily arrests rose from ~359 to ~909 (+153%); monthly arrests peaked at 39,829 in Dec 2025.
- Texas holds 25.7% of new-era arrests (+138% per day). Fastest-growing states: Virginia +413%, Georgia +332%, Pennsylvania/Maryland +260%, Florida +245%. New York (+64%) and New Jersey (+61%) lagged.
- By AOR, San Diego grew +961% (2.4 → 25.4/day), Washington +422%, El Paso +364%. Miami is now the largest AOR.
- Share of arrestees with a criminal conviction fell from 43.0% to 33.1%, while pending-charge cases rose from 17.4% to 29.0%.
- Data-quality notes: the file contains one stray 2026-09-17 record and one partial-day 2026-03-11 record (both excluded); data effectively end 2026-03-10, so March 2026 is partial. February 2026 (29,661) is below January (37,612), which could reflect incomplete recent data. Many landmarks are non-specific "general area" codes. Location is arrest location, not residence; findings are descriptive only.
- The existing `notebooks/eda.py` was also run (figures written to `notebooks/figures/`); its field-office section produced no output because the detention-stays sheet has no AOR column, and its arrests section only plots monthly totals.

## Arrest-rate regressions (`notebooks/10_arrest_regressions.py`, PR 11)

State × year panel (2023–2025, 50 states), arrests per 100k by apprehension state against changes in real GDP, unemployment and violent/property crime (RTCI, FBI check). Same controls, year fixed effects and state-clustered SEs as `06_geo_regressions.py`, plus Benjamini–Hochberg q-values.

- Mean state arrest rate: 37.5 (2023), 26.7 (2024), 73.1 (2025) per 100k.
- 7 of 48 regression coefficients and 7 of 100 correlations were nominally significant (p<.05), roughly chance level. No regression coefficient has q<.10; one correlation does (old-era arrest rate vs GDP growth, r = 0.27), and it disappears with controls.
- Old-era controlled models show opposite-signed nominal crime associations (violent +1.1, p = 0.03; property −1.0, p = 0.05, per +10 arrests/100k). Neither replicates in 2025 or in FBI-based checks.
- No evidence of an association with GDP growth or unemployment change. Crime fell almost everywhere in 2025, so there is little differential variation to explain.
- Limits: tiny samples (one year in the new era), arrest location rather than residence, concentration in a few states, and the FBI check omits the lagged-outcome control. Exploratory only; not causal.

## Interesting findings reported by the analysis

- The reported national average daily population rises from about 33.6k in 2023–24 to 55.1k in 2025–March 2026; the reported rate rises from about 9.9 to 16.1 per 100,000 residents.
- Rural/non-CBSA facilities are reported at 78.4 detainees per 100,000 residents, compared with 10.9 in metropolitan counties. These are facility locations divided by local population, not a measure of how many local residents are detained.
- Louisiana is reported at 163.1 per 100,000, and the Midwest has the largest reported regional increase (+318%). Small local populations and large facilities can make these per-resident facility rates extreme.
- Local/state facilities are reported to have grown from 2.2k to 7.8k ADP; the documents estimate that GEO and CoreCivic together hold 56% of the newer-period ADP. Operator labels are inferred, not provided by ICE.
- The correlation and regression documents characterize associations with economic and crime outcomes as weak or unstable, and explicitly caution against causal interpretation and over-reading multiple comparisons.
- The facility-change analysis identifies 111 facility codes first appearing after January 20, 2025, and 13 that stopped booking. It correctly distinguishes observed activity changes from unverified ownership/operator claims.

## Findings and changes made

1. **Duration was mislabeled as full detention-stay length.** `05_geo_detention_analysis.py` calculates duration as the difference between each stint's facility book-in and book-out. It excludes stints without a book-out date. A person transferred between facilities can therefore contribute several shorter stints, rather than one full stay. Updated the relevant summary and press-release labels to say “completed facility stint,” clarified the selection caveat, and renamed the generated summary fields to `mean_stint_days` and `median_stint_days`.
2. **The EDA workflow targeted an absent notebook.** The workflow referenced `notebooks/01_eda.ipynb`, which is not tracked, although the available analysis entry point is `notebooks/eda.py`. It also watched the nonexistent notebook path and attempted notebook/HTML conversion. Updated and renamed the workflow to run the available script, trigger on its script and data inputs, and upload the generated figures.
3. **The administration comparison is not reproducible from this repository.** `findings_04_administrations.md` names `notebooks/analysis_04_administrations.py`, which is absent, and retains the placeholder `[your name]`. Its administration-level counts and comparisons could not be checked against an analysis script here.
4. **The data extraction date and analysis cutoff need to be explained together.** Source filenames say `7-24-2026`, while the geographic analysis explicitly sets its event cutoff to March 11, 2026. These may represent the extraction date and last included event date respectively, but that distinction should be stated and the actual maximum source dates verified after LFS files are hydrated.
5. **Some claims need stronger publication framing.** The correlations script screens up to 500 outcome × detention measure × group × era combinations before filtering unusable samples, while the original press release said about 40 comparisons. The 2025 state-level regressions also have small samples. Updated the correlation document to state the screening scale and exploratory status; any portfolio-facing p-values should be adjusted for multiple testing or clearly labeled exploratory. Tier B facility ownership/operator events are explicitly unverified and should remain unpublished as factual claims until sourced.
6. **Unequal windows made a raw count sound like a decline.** The old period is 24 months and the new period is 15 months. The original “unique people fell” statement compared 539k with 455k without accounting for those unequal windows. Updated the press releases to label these as period totals and avoid calling them a decline.
7. **Facility rates could be mistaken for resident detention rates.** A state's facility ADP divided by state population measures detention at facilities in that state, including people from elsewhere. Updated the PR 1–3 headlines/notes and master finding to make this facility-location interpretation explicit.
8. **Portfolio orientation is missing.** There is no top-level README describing the research question, data provenance, setup, entry points, generated artifacts, or limitations. The copied `codebook.txt` identifies its source and CC-0 license, but project-specific citation and provenance for the additional data inputs are spread across code rather than summarized for readers.

## Validation performed

- Python syntax compilation passed for the notebooks scripts after the code changes. The updated GitHub Actions YAML parses, and `git diff --check` passes.
- A data-range and output-schema audit was attempted but could not read the CSVs: tracked data and result CSVs are Git LFS pointer files in this checkout. For example, the detention-stints sheet 1 pointer declares an 821,880,386-byte object. The source-dependent analyses, figure regeneration, and numerical consistency checks therefore could not be run here.
- The repository contains no automated test suite. Recommended data-dependent checks are listed below.

## Recommended tests before publication

- Hydrate the LFS data, rerun the analysis scripts in documented order, and compare regenerated tables and figures with the claims in all press releases and `MASTER_RESULTS.md`.
- Add tests for interval overlap and boundary dates, duplicate-stint exclusion, negative/invalid durations, missing book-outs, and the cutoff applied to open recent stints.
- Check that facility ADP aggregates reconcile to national ADP, state totals reconcile to region totals, and operator/area classifications do not silently drop facilities. Include unmapped geography and unclassified operators in the reconciliation.
- Verify the population denominators and the handling of the partial 2026 period; test that the annualization uses the actual number of days in each window.
- For the regressions, assert expected sample sizes and missingness by outcome, independently verify state-clustered standard errors, and report a multiple-comparison adjustment or explicitly designate p-values as exploratory.
- Add a reproducibility check that every documented script, input, result, and figure path exists, including the administration comparison.

## Suggestions to prepare the repository for a data-science portfolio

- Add a concise README with a project overview, research questions, data provenance/citations, environment setup, one-command reproduction instructions, figures, and a plain-language limitations section.
- Restore and document the missing administration-analysis code, remove the author placeholder, and make its period definitions and filters explicit.
- Add a source manifest with dataset URLs, release/extraction dates, event-date coverage, licenses, checksums, and retrieval instructions. Explain why the July 2026-named extracts are analyzed only through March 11.
- Keep large raw inputs in LFS or an external data store, but provide a small, clearly labeled fixture for CI so tests run without downloading multi-gigabyte data. Ensure the fixture contains no unnecessary person-level identifiers.
- Add focused automated tests and a reproducible environment lock file; make CI run syntax, data-contract, and small-fixture checks in addition to the EDA workflow.
- Separate source data, derived results, and presentation assets clearly; describe which outputs are generated and avoid making stale generated CSVs appear authoritative.
- Add citations beside sensitive or news-based facility claims, and provide a methods note on the inferred operator labels, small-area denominators, censoring/selection, and limits of causal inference.
- Keep reports concise and consolidated: use `MASTER_RESULTS.md` as the technical index and link the press releases from it; identify the codebook as third-party documentation rather than project-authored analysis.
