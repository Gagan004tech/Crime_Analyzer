# Power BI Dashboard: Build Guide

The pipeline writes a star schema to `powerbi/data/`. This guide turns it into the
interactive dashboard. Save the finished report as `powerbi/Kerala_Crime_Dashboard.pbix`.

## 1. Load the data

**Get Data → Text/CSV** and load all four files from `powerbi/data/`:

| Table | Grain | Key columns |
|---|---|---|
| `fact_crime` | one row per year × district × crime head | `year`, `district_id`, `crime_head_id`, `cases`, `imputed` |
| `dim_district` | one row per district (14) | `district_id`, `district`, `region`, `population_2011`, `area_sq_km` |
| `dim_crime_head` | one row per crime head (15) | `crime_head_id`, `crime_head`, `category` |
| `dim_year` | one row per year | `year` |

In Power Query, set `cases` to Whole Number, `imputed` to True/False and `year` to Whole Number.

## 2. Model

In **Model view**, create three one-to-many relationships with single-direction filtering:

```
dim_district[district_id]    1 ──► *  fact_crime[district_id]
dim_crime_head[crime_head_id] 1 ──► * fact_crime[crime_head_id]
dim_year[year]               1 ──► *  fact_crime[year]
```

Then:
- Set `dim_district[district]` **Data category → County** and `region` → **State or Province** so map visuals geocode correctly. Add "Kerala, India" to the location if the map misplaces a district.
- Build a hierarchy `Region → District` in `dim_district` and `Category → Crime Head` in `dim_crime_head` for drill-down.
- Hide the ID columns from report view.

## 3. Measures

Create an empty table called `_Measures` (**Enter Data → OK**), then add each measure from
[`measures.dax`](measures.dax). Format `YoY Change %`, `CAGR %`, `Share of …` and `Rate vs State Avg %` as percentages.

## 4. Pages

Use one theme across pages: blue `#2a6f97` for neutral bars, red `#c0392b` for increases.

### Page 1: Overview
| Visual | Fields |
|---|---|
| 4 KPI cards | `Total Cases`, `Crime Rate per Lakh`, `YoY Change %`, `CAGR %` |
| Line chart: yearly trend | X `dim_year[year]`, Y `Total Cases` |
| Donut: category mix | Legend `dim_crime_head[category]`, Values `Total Cases` |
| Filled map: rate by district | Location `dim_district[district]`, colour saturation `Crime Rate per Lakh` |
| Slicers | `dim_year[year]` (between), `dim_district[region]`, `dim_crime_head[category]` |

### Page 2: District Analysis
| Visual | Fields |
|---|---|
| Bar chart sorted by rate | Y `district`, X `Crime Rate per Lakh`; add a constant line for `State Avg Rate per Lakh` |
| Matrix heatmap | Rows `district`, Columns `category`, Values `Crime Rate per Lakh`; **Conditional formatting → Background colour → Gradient** |
| Table: district scorecard | `district`, `Total Cases`, `Crime Rate per Lakh`, `District Rank (Rate)`, `Share of State %`, `YoY Change %` (font colour from `YoY Colour`) |
| Scatter: size vs rate | X `Population`, Y `Crime Rate per Lakh`, Details `district`, Legend `region` |

### Page 3: Category Trends
| Visual | Fields |
|---|---|
| Line chart by category | X `year`, Y `Total Cases`, Legend `category` |
| Bar chart: growth | Y `crime_head`, X `CAGR %`, data colours from `YoY Colour` |
| Decomposition tree | Analyse `Total Cases`, Explain by `region`, `district`, `category`, `crime_head` |
| Ribbon chart | X `year`, Y `Total Cases`, Legend `category`, to show rank changes |

### Page 4: Hotspots (drill-through)
- Add `dim_district[district]` to the **Drill-through** well, so right-clicking a district on any page opens this page for it.
- Table of crime heads with `Crime Rate per Lakh`, `Rate vs State Avg %`, `Hotspot Flag` (icon conditional formatting).
- Line chart of that district's trend against `State Avg Rate per Lakh`.

## 5. Interactivity and finishing

- **Edit interactions**: let the map and the category donut cross-filter every other visual.
- **Bookmarks + buttons**: a "Reset filters" button and a toggle between *Cases* and *Rate per lakh* views.
- **Tooltip page**: a small page with the district's KPI cards and sparkline, set as the report tooltip for the map and bar charts.
- Add a text box in the footer: data source, the years covered, and the `Imputed Cells` count.
- If the data is the synthetic sample, say so in the header.

## Refreshing with new data

Drop new yearly tables into `data/raw/`, re-run `python -m crime_analyzer.pipeline`, then **Home → Refresh** in Power BI.
