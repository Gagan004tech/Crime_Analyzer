"""Load the raw yearly crime tables and reshape them into one tidy table:
year | district | crime_head | cases
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# Police-district labels (and common spellings) -> revenue district
DISTRICT_ALIASES = {
    "thiruvananthapuram": "Thiruvananthapuram",
    "trivandrum": "Thiruvananthapuram",
    "tvm": "Thiruvananthapuram",
    "kollam": "Kollam",
    "quilon": "Kollam",
    "pathanamthitta": "Pathanamthitta",
    "alappuzha": "Alappuzha",
    "alleppey": "Alappuzha",
    "kottayam": "Kottayam",
    "idukki": "Idukki",
    "ernakulam": "Ernakulam",
    "kochi": "Ernakulam",
    "cochin": "Ernakulam",
    "thrissur": "Thrissur",
    "trichur": "Thrissur",
    "palakkad": "Palakkad",
    "palghat": "Palakkad",
    "malappuram": "Malappuram",
    "kozhikode": "Kozhikode",
    "calicut": "Kozhikode",
    "wayanad": "Wayanad",
    "kannur": "Kannur",
    "cannanore": "Kannur",
    "kasaragod": "Kasaragod",
    "kasargod": "Kasaragod",
}

# Rows in the source tables that are not districts
NON_DISTRICT_PATTERN = re.compile(r"railway|total|crime branch|state", re.I)

# Normalised header -> canonical crime head
CRIME_HEAD_ALIASES = {
    "murder": "Murder",
    "attempt to murder": "Attempt to Murder",
    "rape": "Rape",
    "molestation": "Molestation",
    "cruelty by husband relatives": "Cruelty by Husband/Relatives",
    "cruelty by husband or relatives": "Cruelty by Husband/Relatives",
    "kidnapping abduction": "Kidnapping & Abduction",
    "kidnapping and abduction": "Kidnapping & Abduction",
    "robbery": "Robbery",
    "burglary": "Burglary",
    "theft": "Theft",
    "cheating": "Cheating",
    "riots": "Riots",
    "hurt": "Hurt",
    "cyber crime": "Cyber Crime",
    "cyber crimes": "Cyber Crime",
    "ndps act": "NDPS Act",
    "abkari act": "Abkari Act",
}

CRIME_CATEGORY = {
    "Murder": "Violent Crime",
    "Attempt to Murder": "Violent Crime",
    "Hurt": "Violent Crime",
    "Riots": "Violent Crime",
    "Kidnapping & Abduction": "Violent Crime",
    "Rape": "Crimes Against Women",
    "Molestation": "Crimes Against Women",
    "Cruelty by Husband/Relatives": "Crimes Against Women",
    "Robbery": "Property Crime",
    "Burglary": "Property Crime",
    "Theft": "Property Crime",
    "Cheating": "Economic & Cyber Crime",
    "Cyber Crime": "Economic & Cyber Crime",
    "NDPS Act": "Special & Local Laws",
    "Abkari Act": "Special & Local Laws",
}


def _norm(text: str) -> str:
    text = str(text).lower().replace(".", "")  # "N.D.P.S" -> "ndps"
    return re.sub(r"[^a-z]+", " ", text).strip()


def normalise_district(label: str) -> str | None:
    """Map a police-district label to its revenue district, or None to drop it."""
    if NON_DISTRICT_PATTERN.search(str(label)):
        return None
    key = _norm(label)
    for alias, district in DISTRICT_ALIASES.items():
        if key == alias or key.startswith(alias + " "):
            return district
    raise ValueError(f"Unknown district label: {label!r}")


def normalise_crime_head(header: str) -> str:
    key = _norm(header)
    if key not in CRIME_HEAD_ALIASES:
        raise ValueError(f"Unknown crime head: {header!r}")
    return CRIME_HEAD_ALIASES[key]


def tidy_year(raw: pd.DataFrame, year: int) -> pd.DataFrame:
    """Turn one wide yearly table into long format, merged to revenue districts."""
    first = raw.columns[0]
    df = raw.rename(columns={first: "label"})
    df["district"] = df["label"].map(normalise_district)
    df = df.dropna(subset=["district"]).drop(columns="label")
    long = df.melt(id_vars="district", var_name="crime_head", value_name="cases")
    long["crime_head"] = long["crime_head"].map(normalise_crime_head)
    long["cases"] = pd.to_numeric(long["cases"], errors="coerce")
    long["year"] = year
    # If any police-district part of a revenue district is blank, the merged
    # value is unknown (NaN) rather than a silently understated partial sum.
    return long.groupby(["year", "district", "crime_head"], as_index=False)[
        "cases"
    ].agg(lambda s: s.sum() if s.notna().all() else float("nan"))


def load_raw(raw_dir: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(raw_dir.glob("crime_*.csv")):
        year = int(re.search(r"(\d{4})", path.stem).group(1))
        frames.append(tidy_year(pd.read_csv(path), year))
    if not frames:
        raise FileNotFoundError(f"No crime_<year>.csv files in {raw_dir}")
    df = pd.concat(frames, ignore_index=True)
    df["category"] = df["crime_head"].map(CRIME_CATEGORY)
    return df


def impute_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Fill isolated gaps by linear interpolation within each district/head series.

    Adds an `imputed` flag so the dashboard can show which values were filled.
    """
    df = df.sort_values(["district", "crime_head", "year"]).copy()
    df["imputed"] = df["cases"].isna()
    df["cases"] = (
        df.groupby(["district", "crime_head"])["cases"]
        .transform(lambda s: s.interpolate(limit_direction="both"))
        .round()
        .astype(int)
    )
    return df.reset_index(drop=True)
