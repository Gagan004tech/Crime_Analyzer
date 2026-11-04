import math

import pandas as pd
import pytest

from crime_analyzer.analysis import cagr
from crime_analyzer.cleaning import (
    impute_missing,
    normalise_crime_head,
    normalise_district,
    tidy_year,
)


@pytest.mark.parametrize(
    "label, expected",
    [
        ("Kochi City", "Ernakulam"),
        (" THIRUVANANTHAPURAM RURAL", "Thiruvananthapuram"),
        ("Calicut", "Kozhikode"),
        ("Railway Police", None),
        ("State Total", None),
    ],
)
def test_normalise_district(label, expected):
    assert normalise_district(label) == expected


def test_unknown_district_raises():
    with pytest.raises(ValueError):
        normalise_district("Atlantis")


@pytest.mark.parametrize(
    "header, expected",
    [
        ("N.D.P.S Act ", "NDPS Act"),
        ("Kidnapping and Abduction", "Kidnapping & Abduction"),
        ("Cyber Crimes", "Cyber Crime"),
    ],
)
def test_normalise_crime_head(header, expected):
    assert normalise_crime_head(header) == expected


def test_tidy_year_merges_city_and_rural():
    raw = pd.DataFrame(
        {"Police District": ["Kochi City", "Ernakulam Rural", "Railway Police"],
         "Theft": [10, 5, 99]}
    )
    out = tidy_year(raw, 2020)
    assert out.to_dict("records") == [
        {"year": 2020, "district": "Ernakulam", "crime_head": "Theft", "cases": 15}
    ]


def test_partial_blank_makes_merged_value_missing():
    raw = pd.DataFrame(
        {"Police District": ["Kochi City", "Ernakulam Rural"], "Theft": [10, None]}
    )
    assert math.isnan(tidy_year(raw, 2020)["cases"].iloc[0])


def test_impute_missing_interpolates_and_flags():
    df = pd.DataFrame(
        {"year": [2016, 2017, 2018], "district": ["Idukki"] * 3,
         "crime_head": ["Theft"] * 3, "cases": [10, None, 30]}
    )
    out = impute_missing(df)
    assert out["cases"].tolist() == [10, 20, 30]
    assert out["imputed"].tolist() == [False, True, False]


def test_cagr():
    s = pd.Series([100, 121], index=[2016, 2018])
    assert cagr(s) == pytest.approx(10.0)
