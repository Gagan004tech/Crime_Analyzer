# Crime Analysis in Kerala

**Data Analyst (Academic Project) · Kerala, India**

- Analyzed district-wise crime data to uncover trends and category-wise crime patterns.
- Built an interactive Power BI dashboard to support data-driven decision making.

This repository contains the full workflow: a Python pipeline that cleans the raw
district tables and computes trends, rates and hotspots, and the model, DAX measures
and page design for the Power BI dashboard.

> **About the data in this repo.** `data/raw/` holds a **synthetic sample** made by
> `scripts/generate_sample_data.py`. It copies the layout and quirks of the official
> tables but the numbers are invented. Use the real tables (see
> [Using the official data](#using-the-official-data)) before quoting any finding.

## What the analysis covers

- **14 districts**, **15 crime heads** in 5 categories (Violent, Crimes Against Women,
  Property, Economic & Cyber, Special & Local Laws), 2016–2023.
- **Trends:** yearly totals, year-on-year change, compound annual growth by crime head.
- **Rates:** cases per lakh population (Census 2011), so large and small districts compare fairly.
- **Patterns:** district × category heatmap, category share, and hotspots: district and
  crime-head pairs whose rate is at least 1.5 standard deviations above the average district.

Generated outputs:
- [`outputs/report.md`](outputs/report.md): findings with tables and charts
- `outputs/figures/`: trend, category index, district rate, heatmap and growth charts
- `data/processed/kerala_crime_tidy.csv`: one tidy table for any further analysis
- `powerbi/data/`: star-schema CSVs for the dashboard

## Project layout

```
data/
  raw/                 yearly district tables, crime_<year>.csv (sample by default)
  reference/           districts.csv: region, Census 2011 population, area
  processed/           tidy output of the pipeline
scripts/
  generate_sample_data.py
src/crime_analyzer/
  cleaning.py          wide tables -> tidy rows; merges City/Rural police districts,
                       drops non-district rows, standardises crime-head names, fills gaps
  analysis.py          rates, trends, CAGR, rankings, hotspots
  pipeline.py          runs everything and writes the outputs
powerbi/
  README.md            step-by-step dashboard build (model, pages, interactions)
  measures.dax         DAX measures
  data/                fact_crime, dim_district, dim_crime_head, dim_year
tests/                 unit tests for cleaning and metrics
```

## Running it

```bash
pip install -r requirements.txt
```

```bash
python scripts/generate_sample_data.py
```

```bash
PYTHONPATH=src python -m crime_analyzer.pipeline
```

```bash
python -m pytest
```

Then build the dashboard by following [`powerbi/README.md`](powerbi/README.md).

## Dashboard

Four pages, all driven by year, region and category slicers:

1. **Overview:** KPI cards (total cases, rate per lakh, YoY %, CAGR %), yearly trend, category mix, district map.
2. **District Analysis:** districts ranked by rate against the state average, district × category heatmap, scorecard table.
3. **Category Trends:** category lines, crime-head growth, decomposition tree.
4. **Hotspots:** drill-through from any district to see which crime heads sit above the state average.

## Data cleaning

The official tables need several fixes before they can be compared across years:

| Issue | Handling |
|---|---|
| Police districts split into City and Rural (e.g. Kochi City + Ernakulam Rural) | Merged into the 14 revenue districts so they match the population data |
| Rows that aren't districts (Railway Police, State Total) | Dropped, so state totals are not double counted |
| Crime-head names spelled differently across years | Mapped to one standard name |
| Old district names (Trivandrum, Calicut, Palghat…) | Mapped to current names |
| Blank cells | Linear interpolation within the district's own series, flagged `imputed = True` |

## Using the official data

District-wise crime statistics are published by Kerala Police
(keralapolice.gov.in → Crime Statistics) and by NCRB in *Crime in India*.

1. Save each year's district table as `data/raw/crime_<year>.csv`, with police districts
   as rows and crime heads as columns (the first column holds the district name).
2. Delete the sample files and `data/raw/SAMPLE_DATA` (this removes the sample warning from the report).
3. If a crime head or district label is new, add it to the alias maps in
   `src/crime_analyzer/cleaning.py`. Unknown labels raise an error instead of being dropped silently.
4. Re-run the pipeline and refresh Power BI.

## Tools

Python (pandas, matplotlib), Power BI (Power Query, DAX), pytest.
