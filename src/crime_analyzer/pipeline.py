"""End-to-end run: raw tables -> tidy data -> Power BI tables, charts, report.

    python -m crime_analyzer.pipeline          (from src/, or with PYTHONPATH=src)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from crime_analyzer import analysis as A  # noqa: E402
from crime_analyzer.cleaning import impute_missing, load_raw  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "reference" / "districts.csv"
PROCESSED = ROOT / "data" / "processed"
PBI = ROOT / "powerbi" / "data"
FIG = ROOT / "outputs" / "figures"
REPORT = ROOT / "outputs" / "report.md"


def export_powerbi(df: pd.DataFrame, districts: pd.DataFrame) -> None:
    """Star schema: one fact table plus three dimensions."""
    PBI.mkdir(parents=True, exist_ok=True)
    heads = (
        df[["crime_head", "category"]].drop_duplicates().sort_values(["category", "crime_head"])
    )
    heads.insert(0, "crime_head_id", range(1, len(heads) + 1))
    dist = districts.sort_values("district").reset_index(drop=True)
    dist.insert(0, "district_id", range(1, len(dist) + 1))
    years = pd.DataFrame({"year": sorted(df["year"].unique())})

    fact = (
        df.merge(dist[["district_id", "district"]], on="district")
        .merge(heads[["crime_head_id", "crime_head"]], on="crime_head")
        [["year", "district_id", "crime_head_id", "cases", "imputed"]]
    )
    fact.to_csv(PBI / "fact_crime.csv", index=False)
    dist.to_csv(PBI / "dim_district.csv", index=False)
    heads.to_csv(PBI / "dim_crime_head.csv", index=False)
    years.to_csv(PBI / "dim_year.csv", index=False)


def make_figures(df: pd.DataFrame, latest: int) -> list[str]:
    FIG.mkdir(parents=True, exist_ok=True)
    names = []

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(FIG / name, dpi=150)
        plt.close(fig)
        names.append(name)

    trend = A.yearly_trend(df)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(trend["year"], trend["cases"] / 1000, marker="o", color="#2a6f97")
    ax.set(title="Total registered cases, Kerala", xlabel="Year", ylabel="Cases (thousands)")
    ax.grid(alpha=0.3)
    save(fig, "01_yearly_trend.png")

    cat = A.category_trend(df)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    (cat / cat.iloc[0] * 100).plot(ax=ax, marker="o")
    ax.axhline(100, color="grey", lw=0.8, ls="--")
    ax.set(title=f"Category trend (index, {cat.index[0]} = 100)", xlabel="Year", ylabel="Index")
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.3)
    save(fig, "02_category_index.png")

    rank = A.district_ranking(df, latest).sort_values("rate_per_lakh")
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(rank["district"], rank["rate_per_lakh"], color="#2a6f97")
    ax.set(title=f"Crime rate per lakh population by district, {latest}", xlabel="Cases per lakh")
    save(fig, "03_district_rate.png")

    heat = A.district_category_rates(df, latest)
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(heat.values, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(heat.columns)), heat.columns, rotation=25, ha="right", fontsize=8)
    ax.set_yticks(range(len(heat.index)), heat.index, fontsize=8)
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            v = heat.values[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if v > heat.values.max() * 0.6 else "black")
    fig.colorbar(im, ax=ax, label="Cases per lakh")
    ax.set_title(f"District x category crime rate, {latest}")
    save(fig, "04_district_category_heatmap.png")

    growth = A.crime_head_growth(df).sort_values("cagr_pct")
    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = ["#c0392b" if v > 0 else "#2a6f97" for v in growth["cagr_pct"]]
    ax.barh(growth.index, growth["cagr_pct"], color=colors)
    ax.axvline(0, color="grey", lw=0.8)
    ax.set(title="Compound annual growth by crime head", xlabel="CAGR (%)")
    save(fig, "05_crime_head_cagr.png")
    return names


def write_report(df: pd.DataFrame, figures: list[str], sample: bool) -> None:
    years = sorted(df["year"].unique())
    first, latest = years[0], years[-1]
    trend = A.yearly_trend(df)
    rank = A.district_ranking(df, latest)
    growth = A.crime_head_growth(df)
    share = df[df["year"] == latest].groupby("category")["cases"].sum()
    share = (share / share.sum() * 100).sort_values(ascending=False)
    hot = A.hotspots(df, latest).head(10)
    total_cagr = A.cagr(trend.set_index("year")["cases"])
    dip = trend.loc[trend["yoy_pct"].idxmin()]

    lines = ["# Crime Analysis in Kerala: Findings", ""]
    if sample:
        lines += [
            "> **Sample data.** These findings come from the synthetic dataset made by",
            "> `scripts/generate_sample_data.py`, so they show what the pipeline produces,",
            "> not real facts about Kerala. Re-run with the official tables to get real findings.",
            "",
        ]
    lines += [
        f"Coverage: {len(df['district'].unique())} districts, "
        f"{df['crime_head'].nunique()} crime heads, {first} to {latest}. "
        f"Imputed cells: {int(df['imputed'].sum())} of {len(df)}.",
        "",
        "## Overall trend",
        f"- Total cases went from {trend.iloc[0]['cases']:,.0f} in {first} to "
        f"{trend.iloc[-1]['cases']:,.0f} in {latest} (CAGR {total_cagr:+.1f}%).",
        f"- The biggest year-on-year change was {dip['yoy_pct']:+.1f}% in {int(dip['year'])}.",
        "",
        "## Category mix in " + str(latest),
        *[f"- {c}: {v:.1f}% of cases" for c, v in share.items()],
        "",
        "## Fastest-changing crime heads",
        *[f"- {h}: {r.cagr_pct:+.1f}% a year" for h, r in growth.head(3).iterrows()],
        *[f"- {h}: {r.cagr_pct:+.1f}% a year" for h, r in growth.tail(3).iterrows()],
        "",
        f"## Districts by crime rate, {latest}",
        "| Rank | District | Region | Cases | Per lakh | Share of state |",
        "|---:|---|---|---:|---:|---:|",
        *[
            f"| {i + 1} | {r.district} | {r.region} | {r.cases:,.0f} | "
            f"{r.rate_per_lakh:,.0f} | {r.share_pct:.1f}% |"
            for i, r in rank.iterrows()
        ],
        "",
        f"## Hotspots, {latest} (top 10 where the rate is at least 1.5 standard deviations above the average district)",
    ]
    lines += (
        [f"- {r.district}: {r.crime_head} ({r.rate_per_lakh:.1f} per lakh, z = {r.z_score:.1f})"
         for r in hot.itertuples()]
        if len(hot) else ["- None found."]
    )
    lines += ["", "## Charts", *[f"![{f}](figures/{f})" for f in figures], ""]
    lines += [
        "Note: rates use Census 2011 population, the latest official district count. "
        "Population growth since then pushes rates slightly upward over time.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    districts = pd.read_csv(REF)
    df = A.add_rates(impute_missing(load_raw(RAW)), districts)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED / "kerala_crime_tidy.csv", index=False)
    export_powerbi(df[["year", "district", "crime_head", "category", "cases", "imputed"]],
                   districts)
    latest = int(df["year"].max())
    figures = make_figures(df, latest)
    sample = (RAW / "SAMPLE_DATA").exists()
    write_report(df, figures, sample)
    print(f"{len(df)} rows -> {PROCESSED.relative_to(ROOT)}, {PBI.relative_to(ROOT)}, "
          f"{REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
