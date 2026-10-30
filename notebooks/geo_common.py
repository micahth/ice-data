"""
Shared helpers for the geography / operator analyses (scripts 05 and 06).

External inputs (all public, fetched from GitHub raw/media URLs and cached):
  facilities_latest.parquet  deportationdata/ice-detention-facilities  (facility -> county, CBSA, Metro/Micro)
  list1_2023.xlsx            OMB July-2023 CBSA delineation (via jenniferpeebles/omb_msas_historical_delineation)
  pop/*.json                 Census county population estimates 2020-2025 (GreatTombProductions/county-population)
  gdp.csv                    BEA SAGDP1 real GDP by state 1997-2025 (njl250/JoE-Spring-2026)
  laus_old.json / laus_new.csv  BLS LAUS state unemployment 2020-2024 / 2025-2026 (kmazurek95, dathere)
  fbi_crime.csv              FBI state crime 2010-2024 (CatalinaBedoya1/PlotlyDashboard)
  rtci.csv                   Real-Time Crime Index sample, monthly through Jun 2026 (AH-Datalytics/rtci)
  acs.csv / gaz.txt / pres.csv  county ACS controls, land area, 2024 presidential vote (kmazurek95)
"""
import glob
import json
import os
import re
import subprocess

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CACHE = os.environ.get("GEO_CACHE", os.path.join(HERE, ".cache"))
RESULTS = os.path.join(HERE, "results")
os.makedirs(CACHE, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)

RAW = "https://raw.githubusercontent.com"
MEDIA = "https://media.githubusercontent.com/media"
SOURCES = {
    "facilities_latest.parquet": f"{MEDIA}/deportationdata/ice-detention-facilities/main/data/facilities-latest.parquet",
    "facilities_attributes.parquet": f"{MEDIA}/deportationdata/ice-detention-facilities/main/data/facilities-attributes-cleaned-with-codes.parquet",
    "list1_2023.xlsx": f"{RAW}/jenniferpeebles/omb_msas_historical_delineation/HEAD/data/raw/list1_2023.xlsx",
    "gdp.csv": f"{RAW}/njl250/JoE-Spring-2026/main/SAGDP1_ALL_AREAS_1997_2025.csv",
    "laus_old.json": f"{RAW}/kmazurek95/us-election-county-swing/main/data/raw/bls_laus_states.json",
    "laus_new.csv": f"{RAW}/dathere/bls-laus-stats/HEAD/output/stateUnemployment.csv",
    "fbi_crime.csv": f"{RAW}/CatalinaBedoya1/PlotlyDashboard/main/FinalProject/data/fbi_state_crime-2010-2024.csv",
    "rtci.csv": f"{RAW}/AH-Datalytics/rtci/main/data/Crime_Index_Reported_Crime_Trends_Jan17_Jun26.csv",
    "acs.csv": f"{RAW}/kmazurek95/us-election-county-swing/main/data/raw/acs_demographics.csv",
    "gaz.txt": f"{RAW}/kmazurek95/us-election-county-swing/main/data/raw/gazetteer_counties.txt",
    "pres.csv": f"{RAW}/kmazurek95/us-election-county-swing/main/data/raw/countypres_2000-2024.csv",
}


def fetch(name):
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        print(f"  downloading {name}")
        subprocess.run(["curl", "-sfL", "-o", path, SOURCES[name]], check=True)
    return path


def fetch_pop_shards():
    d = os.path.join(CACHE, "pop")
    os.makedirs(d, exist_ok=True)
    for i in range(256):
        p = os.path.join(d, f"{i:02x}.json")
        if not os.path.exists(p):
            subprocess.run(["curl", "-sfL", "-o", p,
                            f"{RAW}/GreatTombProductions/county-population/main/data/detail/{i:02x}.json"],
                           check=True)
    return d


# ---------------------------------------------------------------------------
# Periods
# ---------------------------------------------------------------------------
CUTOFF = pd.Timestamp("2026-03-11")   # last book-in / book-out in the FOIA release
PERIODS = {
    "Old (2023-2024)": (pd.Timestamp("2023-01-01"), pd.Timestamp("2025-01-01")),
    "New (2025-Mar 2026)": (pd.Timestamp("2025-01-01"), CUTOFF + pd.Timedelta(days=1)),
    "2023": (pd.Timestamp("2023-01-01"), pd.Timestamp("2024-01-01")),
    "2024": (pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01")),
    "2025": (pd.Timestamp("2025-01-01"), pd.Timestamp("2026-01-01")),
    "2026 YTD (to Mar 11)": (pd.Timestamp("2026-01-01"), CUTOFF + pd.Timedelta(days=1)),
}
ANNUAL = ["2023", "2024", "2025", "2026 YTD (to Mar 11)"]
ERAS = ["Old (2023-2024)", "New (2025-Mar 2026)"]

# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------
REGION = {}
for _r, _s in {
    "Northeast": "CT ME MA NH RI VT NJ NY PA",
    "Midwest": "IL IN MI OH WI IA KS MN MO NE ND SD",
    "South": "DE DC FL GA MD NC SC VA WV AL KY MS TN AR LA OK TX",
    "West": "AZ CO ID MT NV NM UT WY AK CA HI OR WA",
}.items():
    for _a in _s.split():
        REGION[_a] = _r
TERRITORY = "Territories/Other"

STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
ABBR_STATE = {v: k for k, v in STATE_ABBR.items()}


def region_of(abbr):
    return REGION.get(abbr, TERRITORY)


# ---------------------------------------------------------------------------
# Operator classification (name / code based; ICE does not publish an operator field)
# ---------------------------------------------------------------------------
CORECIVIC = {
    "ADAMSMS", "STWRTGA", "EAZ", "CCASDCA", "HOUICDF", "STFRCTX", "CCAHUTX", "CCAFLAZ", "LRDICDF", "WEBDCTX",
    "TOORANM", "CIBOCNM", "EDNDCTX", "CCANOOH", "TNWESDF", "OKCIMMC", "OKDBACK", "DILLSAF", "NVSDCNV",
    "CACTYCA", "ELZICDF",
}
GEO = {
    "STCDFTX", "MSVPCPA", "JCRLYTX", "MTGPCTX", "ELVDFTX", "BASILLA", "ADLNTCA", "GLDSACA", "CADESVI",
    "FIPCMGA", "FIPCAGA", "FIPCDGA", "DENICDF", "WCCPBFL", "CSCNWWA", "CACFMES", "RGRNDTX", "DHDFNJ",
    "KRNRCTX", "JENADLA", "POLKCTX", "NRLKCMI", "BIINCCO", "CVANXCA",
}
OTHER_PRIVATE = {  # MTC, LaSalle Corrections, Immigration Centers of America
    "OTRPCNM", "BLBNATX", "IRADFCA", "LAWINCI", "JKPCCLA", "RWCCMLA", "RVRCCLA", "APPSCLA", "PINEPLA",
    "PRLDCTX", "FRMVLVA", "CARDFVA",
}
ICE_TYPES = {"SPC", "STAGING", "HOLD"}
ICE_CODES = {"EROFCB", "EPSSFTX", "BPC", "AFRC"}   # Camp East Montana / El Paso soft-sided, Boston SPC, Artesia FRC
STATE_RUN_CODES = {"FLDSSFS", "LICEPLA"}            # Florida soft-sided (state-run), Louisiana state-run site
ICE_NAME = re.compile(r"HOLD|STAGING|DOCKET|\bSPC\b|^ERO\b|\bF\.?O\.?\b|FIELD OFFICE|DIST\.? ?OFFICE|SUB.?OFFICE|"
                      r"CUST CASE|AROCC|REM OP|ENFORCEMENT AND REMOVAL", re.I)
FED_NAME = re.compile(r"\bCBP\b|GUANTANAMO|CENTRALIZED PROCESSING|\bFCI\b|\bUSP\b|U\.S\. PEN|\bFDC\b|\bMDC\b|\bFMC\b|\bMCC\b|FED(ERAL)?\.? ?DET|\bBOP\b", re.I)
GOV_NAME = re.compile(r"JAIL|COUNTY|\bCO\b\.?|SHERIFF|PARISH|\bDEPT|CORRECTION|DETENTION|JUSTICE|PUBLIC SAFETY|"
                      r"\bCI\b|PENITENT|\bDOC\b", re.I)
OPERATORS = ["ICE", "CoreCivic", "GEO Group", "Other private", "Local/state government", "Federal (BOP/CBP/other)",
             "Unclassified"]


def classify_operator(code, name, type_detailed):
    name = name if isinstance(name, str) else ""
    t = type_detailed.upper() if isinstance(type_detailed, str) else ""
    if code in CORECIVIC or re.search(r"CORE ?CIVIC|\bCCA\b", name, re.I):
        return "CoreCivic", "named CoreCivic/CCA facility"
    if code in GEO:
        return "GEO Group", "named GEO Group facility"
    if code in OTHER_PRIVATE:
        return "Other private", "named MTC/LaSalle/ICA facility"
    if code in STATE_RUN_CODES:
        return "Local/state government", "state-run site hosting ICE detainees"
    if code in ICE_CODES or t in ICE_TYPES or ICE_NAME.search(name):
        return "ICE", "ICE SPC / staging / hold room / ERO site"
    if t == "BOP" or code.startswith("BOP") or FED_NAME.search(name):
        return "Federal (BOP/CBP/other)", "federal prison / detention center"
    if t == "CDF":
        return "Other private", "contract detention facility (private), operator unverified"
    if GOV_NAME.search(name) or t in {"IGSA", "DIGSA", "USMS IGA", "JUVENILE"}:
        return "Local/state government", "county/state jail or IGSA/IGA"
    return "Unclassified", "no operator signal"


# ---------------------------------------------------------------------------
# Population (county -> state / CBSA)
# ---------------------------------------------------------------------------
def load_county_pop():
    rows = []
    for p in glob.glob(os.path.join(fetch_pop_shards(), "*.json")):
        for fips, v in json.load(open(p)).items():
            for y, d in v["yr"].items():
                rows.append((fips.zfill(5), v["s"], int(y), d["p"]))
    cp = pd.DataFrame(rows, columns=["fips", "state_name", "year", "pop"])
    cp["state"] = cp.state_name.map(STATE_ABBR)
    return cp


def load_cbsa_delineation():
    x = pd.read_excel(fetch("list1_2023.xlsx"), header=2, dtype=str).dropna(subset=["FIPS County Code"])
    x = x[x["CBSA Code"].str.fullmatch(r"\d{5}", na=False)]
    x["fips"] = x["FIPS State Code"].str.zfill(2) + x["FIPS County Code"].str.zfill(3)
    x["cbsa_type"] = np.where(x["Metropolitan/Micropolitan Statistical Area"].str.startswith("Metro"),
                              "Metropolitan", "Micropolitan")
    x = x.rename(columns={"CBSA Code": "cbsa_code", "CBSA Title": "cbsa_title"})
    return x[["fips", "cbsa_code", "cbsa_title", "cbsa_type"]].drop_duplicates("fips")


def period_population(cp, by, year_map=None):
    """Population by `by` column(s) for each period label (2026 uses 2025; Old = mean 2023-24)."""
    out = {}
    pivot = cp.groupby(by + ["year"])["pop"].sum().unstack("year")
    for label in PERIODS:
        if label.startswith("Old"):
            out[label] = pivot[[2023, 2024]].mean(axis=1)
        elif label.startswith("New"):
            out[label] = pivot[2025]
        elif label.startswith("2026"):
            out[label] = pivot[2025]
        else:
            out[label] = pivot[int(label)]
    return pd.DataFrame(out)
