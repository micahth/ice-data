# Facility ownership / operating changes since the start of Trump's second term

Window: **2025-01-20 → 2026-03-11** (last book-in in the data). Full machine-readable list: [`results/facility_changes.csv`](results/facility_changes.csv) (script `07_facility_changes.py`).

## How to read this list

The ICE data has **no owner or operator field**, so this list has two tiers, and they carry different levels of confidence:

| Tier | Source | Confidence |
|---|---|---|
| **A. Data-observed activity changes** | Facility codes whose book-in history changes after 2025-01-20: first-ever book-ins, near-zero before inauguration, booking stops, or name changes under one code | High that the *activity* changed. A new/stopped code is **not proof** the owner or operator changed. Operator labels come from my name/code rules (see MASTER_RESULTS) |
| **B. Publicly reported ownership/operator events** | My background knowledge of news and company announcements, matched to the data where possible | **Not verified in this run.** Web search was unavailable, so confirm each before publication |

## A. Data-observed changes (summary)

| Change type | Facilities | Notes |
|---|---:|---|
| New since 2025-01-20 (no earlier book-ins) | 111 | Local/state 78+, ICE 14, Federal 11, CoreCivic 5, GEO 2, 1 unclassified. About 166k book-ins |
| Recent start (≤10% of post-inauguration volume came before) | 8 | Mostly hold rooms and jails |
| Stopped booking (>90 days no book-ins, but used after 2025-01-20) | 13 | Mostly NC/TX/SC county jails |
| Name changed under same code | 9 + overlaps | Mostly renames/relabels, often with ICE hold rooms |

### A1. Largest new facility codes (first book-in after inauguration)

| Code | Facility | State | Operator class (inferred) | First book-in | Book-ins to 3/11/26 |
|---|---|---|---|---|---:|
| EROFCB | El Paso – Camp East Montana (Fort Bliss) | TX | ICE (contractor-staffed) | 2025-07-03 | 35,548 |
| EPSSFTX | El Paso Soft-Sided Facility | TX | ICE | 2025-03-10 | 15,734 |
| FLDSSFS | Florida Soft-Sided Facility South ("Alligator Alcatraz") | FL | State of Florida | 2025-09-18* | 13,661 |
| FLBAKCI | Baker CI ("Deportation Depot") | FL | State of Florida | 2025-09-02 | 5,700 |
| NRLKCMI | North Lake Processing Center | MI | GEO Group | 2025-06-16 | 5,590 |
| RSREGVA | Riverside Regional Jail | VA | Local/state | 2025-05-01 | 5,284 |
| FIPCDGA | Folkston D. Ray ICE Processing Center (new code) | GA | GEO Group | 2025-08-05 | 5,275 |
| OKCIMMC | Cimarron Correctional Facility | OK | CoreCivic | 2025-03-03 | 4,283 |
| CACTYCA | California City Detention Facility | CA | CoreCivic | 2025-08-27 | 3,682 |
| URSLATX | Ursula Centralized Processing Center | TX | Federal (CBP) | 2025-06-26 | 3,546 |
| CCANOOH | Northeast Ohio Correctional Center (Youngstown) | OH | CoreCivic | 2025-02-24 | 2,400 |
| IRWINGA | Irwin County Detention Center | GA | Local/private (LaSalle-run historically) | 2025-10-12 | 1,575 |
| INMIAMI | Miami Correctional Facility | IN | State (Indiana DOC) | 2025-10-01 | 1,186 |
| OKDBACK | Diamondback Correctional Facility | OK | CoreCivic | 2026-01-01 | 1,131 |
| BOPPHL / BOPATL / BOPMIM / BOPBER / BOPBRO | BOP facilities (Philadelphia, Atlanta, Miami, Berlin NH, MDC Brooklyn) | multi | Federal (BOP) | Feb–Jun 2025 | 12,700 combined |

\* The data's first book-in for the Everglades site is September 2025, but public reporting says it opened in July 2025 under a different code or before ICE code assignment. Treat the data date as the first *recorded* book-in.

Another 78+ local jails and sheriff's offices appear for the first time, led by Greene Co. MO (4,294), Butler Co. OH (3,396), Walton Co. FL (3,110), Glades Co. FL (2,910), Putnam Co. TN (2,537), TGK Jail Miami FL (2,259), Ste. Genevieve Co. MO (1,774), and Uinta Co. WY (1,613). These generally reflect new or expanded local intergovernmental agreements (IGSAs/287(g)), not changes in who owns the jail.

### A2. Stopped booking

| Code | Facility | State | Last book-in | Book-ins before → after 1/20/25 |
|---|---|---|---|---|
| ALAMCNC | Alamance Co. Detention Center | NC | 2025-11-14 | 3,605 → 3,690 |
| DALCOTX | Dallas Co. Jail (Lew Sterrett) | TX | 2025-12-08 | 4,288 → 1,194 |
| GASTNNC | Gaston Co. Jail | NC | 2025-09-25 | 86 → 69 |
| CBRRSNC | Cabarrus Co. Jail | NC | 2025-09-13 | 89 → 58 |
| YORCOSC | York Co. Detention Center | SC | 2025-08-21 | 55 → 50 |
| BOPGUA | Guaynabo MDC (San Juan) | PR | 2025-02-25 | 572 → 32 |
| Others | Sioux City hold room, Washington Co. MN, Haile ID, Teller Co. CO, Burnet Co. TX, Honolulu hold room, Cobb Co. GA | — | Jan–Dec 2025 | small |

### A3. Recent starts and name changes

- **Recent starts:** LaSalle Co. Regional Detention Center TX (4 → 1,694), Williamsport/Champlain/Alamosa/Helena hold rooms, Monroe Co. FL, Campbell Co. WY, BI Inc. (GEO) Colorado.
- **Name changes under one code:** Central Louisiana ICE Processing Center (Jena; GEO), Baltimore / San Bernardino / Detroit hold rooms, Calhoun Co. MI, Rockingham Co. VA, Geauga Co. OH, Guam hold room, Abraxas Academy PA. Name-only changes are mostly relabels, not ownership changes.

## B. Publicly reported ownership / operator events (NOT verified in this run)

Match to the data in the last column. **Verify against news, SEC filings and ICE contract postings before use.**

| Facility | Reported change | Operator before → after | Seen in data? |
|---|---|---|---|
| California City, CA | CoreCivic reopened an idle prison under a new ICE contract | idle → CoreCivic | Yes, first book-in 2025-08-27 |
| Diamondback (Watonga), OK | CoreCivic idle prison reactivated for ICE | idle → CoreCivic | Yes, 2026-01-01 |
| Cimarron (Cushing), OK | CoreCivic facility activated for ICE | idle/other → CoreCivic | Yes, 2025-03-03 |
| Northeast Ohio Correctional Center (Youngstown) | CoreCivic facility again used for ICE | → CoreCivic | Yes, 2025-02-24 |
| North Lake (Baldwin), MI | GEO Group facility, previously idle, reopened for ICE | idle → GEO | Yes, 2025-06-16 |
| Delaney Hall (Newark), NJ | GEO contract (announced Feb 2025) for ICE processing, reopened/expanded | GEO (changed contract) | Not flagged as new (code existed) |
| Folkston, GA | GEO expansion of the D. Ray ICE Processing Center | GEO (expansion) | Yes, new code 2025-08-05 |
| Camp East Montana (Fort Bliss), TX | Soft-sided tent site on Army land, built and run by a private contractor under an ICE contract | none → federal land / contractor | Yes, 2025-07-03 |
| "Alligator Alcatraz" (Dade-Collier), FL | State-built, State of Florida-run site, with federal reimbursement | none → State of Florida | Yes, as Florida Soft-Sided South |
| Baker CI "Deportation Depot", FL | State prison converted for ICE detainees, State-run | State DOC → State/ICE use | Yes, 2025-09-02 |
| Louisiana "Camp 57" / Angola | State-run site for ICE detainees | none → State of Louisiana | Not confirmed in data |
| Irwin County, GA | Reopened for ICE after earlier closure; ownership/operator not confirmed | closed → reopened | Yes, 2025-10-12 |
| Indiana Miami Correctional Facility | Indiana DOC prison used for ICE | State DOC → State/ICE use | Yes, 2025-10-01 |

Not ownership changes but related: BOP facilities (Philadelphia, Atlanta, Miami, Berlin NH) began holding ICE detainees in Feb–Mar 2025 under federal-to-federal arrangements.

## Caveats

1. Tier A shows *when ICE started or stopped using a facility*, not who owns it.
2. Operator class comes from name/code rules in `geo_common.py`; misclassifications are possible.
3. Tier B is not checked against live sources. Do not cite it as fact until confirmed.
4. The data ends 2026-03-11; later changes are missing, and "stopped booking" may reflect delayed or sparse updates.
