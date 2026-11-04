"""Trend and pattern metrics computed from the tidy crime table."""

from __future__ import annotations

import pandas as pd

PER_LAKH = 100_000


def add_rates(df: pd.DataFrame, districts: pd.DataFrame) -> pd.DataFrame:
    out = df.merge(districts[["district", "region", "population_2011"]], on="district")
    out["rate_per_lakh"] = out["cases"] / out["population_2011"] * PER_LAKH
    return out


def yearly_trend(df: pd.DataFrame) -> pd.DataFrame:
    t = df.groupby("year", as_index=False)["cases"].sum()
    t["yoy_pct"] = t["cases"].pct_change() * 100
    return t


def category_trend(df: pd.DataFrame) -> pd.DataFrame:
    return df.pivot_table(index="year", columns="category", values="cases", aggfunc="sum")


def cagr(series_by_year: pd.Series) -> float:
    first, last = series_by_year.iloc[0], series_by_year.iloc[-1]
    n = series_by_year.index[-1] - series_by_year.index[0]
    return ((last / first) ** (1 / n) - 1) * 100 if first > 0 and n > 0 else float("nan")


def crime_head_growth(df: pd.DataFrame) -> pd.DataFrame:
    by = df.pivot_table(index="year", columns="crime_head", values="cases", aggfunc="sum")
    first, last = by.index.min(), by.index.max()
    out = pd.DataFrame(
        {
            f"cases_{first}": by.loc[first],
            f"cases_{last}": by.loc[last],
            "cagr_pct": by.apply(cagr),
        }
    )
    return out.sort_values("cagr_pct", ascending=False)


def district_ranking(df: pd.DataFrame, year: int) -> pd.DataFrame:
    d = df[df["year"] == year].groupby(["district", "region"], as_index=False).agg(
        cases=("cases", "sum"), population=("population_2011", "first")
    )
    d["rate_per_lakh"] = d["cases"] / d["population"] * PER_LAKH
    d["share_pct"] = d["cases"] / d["cases"].sum() * 100
    return d.sort_values("rate_per_lakh", ascending=False).reset_index(drop=True)


def district_category_rates(df: pd.DataFrame, year: int) -> pd.DataFrame:
    d = df[df["year"] == year]
    return d.pivot_table(
        index="district", columns="category", values="rate_per_lakh", aggfunc="sum"
    )


def hotspots(df: pd.DataFrame, year: int, z: float = 1.5) -> pd.DataFrame:
    """District/crime-head pairs whose rate is unusually high versus other districts."""
    d = df[df["year"] == year].copy()
    grp = d.groupby("crime_head")["rate_per_lakh"]
    d["z_score"] = (d["rate_per_lakh"] - grp.transform("mean")) / grp.transform("std")
    cols = ["district", "crime_head", "category", "cases", "rate_per_lakh", "z_score"]
    return d.loc[d["z_score"] >= z, cols].sort_values("z_score", ascending=False)
