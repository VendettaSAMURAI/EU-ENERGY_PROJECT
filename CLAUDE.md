# Project Context: EU Electricity Dashboard

Official assignment brief: `docs/project_brief.md`. Read it and check all design and implementation decisions against it.
Step-by-step plan and progress: `docs/roadmap.md`. Check it at the start of each session and tick items off as they are done.

## Course
- **Data Visualization Methods (INMAA0105L-01/26f)**, MSc Data Science, University of Debrecen
- Group project, 3 students (Gilbert Mutai + 2 colleagues)
- Repo: github.com/gilbert-mutai/Data-Visualization-Project (default branch: `master`)

## Assignment requirements
Build an interactive dashboard on a freely chosen dataset. It must:
- contain several types of meaningful visualizations, chosen to fit the data and the analytical questions
- include interactive features: filtering, searching, selection, hover, zooming, linked views
- let users examine the data from different perspectives
- use at least one library listed on PyViz.org
- NOT rely only on bar, line and pie charts
- clearly cite the data source

Assessment criteria: Data Preparation, Design Process (clarity of analytical questions, coherence, consistent design), Quality of Visualizations, Analytical Capabilities, Technical Implementation, Presentation/Defense (each student explains data prep, design decisions, demo, key insights).

## Concept
EU electricity dashboard: demand, generation mix, renewables and prices across selected EU countries. Visual design inspired by "Energy Optimization SaaS Dashboard" by Merve Avşar (Dribbble): dark/clean SaaS style, KPI cards on top, panels below.

## Dashboard sections
A. **Overview / KPI cards**: total consumption (GWh/TWh), average price (EUR/MWh), renewable share (%), peak-demand period. KPI cards are a header, not counted as visualizations.
B. **Consumption trends**: demand over time, daily/monthly/seasonal patterns, peak vs off-peak.
C. **Country comparison**: EU member states, consumption ranking, per-capita consumption, map.
D. **Renewable energy**: wind, solar, hydro and other sources, renewable share over time, renewables vs demand.
E. **Electricity prices**: hourly/daily trends, country comparison, relationship between renewables, demand and prices.

## Analytical questions (draft)
1. How does electricity demand vary by hour, weekday and season, and when are the peaks?
2. How do the selected countries differ in consumption (total and per capita) and generation mix?
3. How has the renewable share evolved, and how well does renewable generation cover demand?
4. Do hours with high renewable generation have lower (or negative) prices, and does this differ by country?

## Visualization plan (avoid relying on bar/line/pie)
- B: hour x weekday heatmap, calendar heatmap, hour-of-day profiles by season
- C: choropleth (renewable share or per-capita consumption), ranked dot/lollipop chart
- D: stacked area or streamgraph of generation mix, renewables vs demand overlay ("duck curve")
- E: price distributions (violin/ridgeline) per country, price duration curve, scatter of renewable share vs price with linked brushing
- Linked views: selecting countries/time ranges filters all panels

## Data sources
| Source | Content | Access |
|---|---|---|
| Energy-Charts API (Fraunhofer ISE), api.energy-charts.info | Hourly/15-min generation by source, load, day-ahead prices per country/bidding zone | Free, no key (primary source) |
| ENTSO-E Transparency Platform | Same, official EU source | Free account + API token (requested); use `entsoe-py` |
| Ember | Monthly/yearly generation, demand, emissions per country | Free CSV, CC BY 4.0 |
| Eurostat | Population per country (per-capita figures) | Free API/CSV |

Scope (decided 2026-10-22): 7 countries, Hungary (HU), Germany (DE), Austria (AT), France (FR), Spain (ES), Poland (PL), Denmark (DK); 4 full years, 2022 to 2025 (energy crisis, recovery, solar growth). Denmark has two price zones (DK1 West, DK2 East): use the simple hourly mean of DK1 and DK2 prices as the Denmark price (document in prep notes).

Raw data layout: `data/raw/<source>/...` (e.g. `data/raw/energy_charts/`, `data/raw/ember/`, `data/raw/eurostat/`). Download scripts in `src/data/` so raw data is reproducible.

## Known data prep work
- Timestamps: convert to UTC, handle DST transitions (missing/duplicate hours), align to local time only for hour-of-day analysis.
- Resolution: Energy-Charts generation/load is mixed (DE, AT, HU 15-minute; DK, FR hourly; ES 15-minute from 2023, PL from 2025), day-ahead prices are hourly until 1 Oct 2025 and 15-minute after. Resample everything to hourly (mean of MW values).
- Bidding zones vs countries: e.g. DE-LU is one zone, Denmark has DK1/DK2, Italy has several zones. Decide a mapping and document it.
- Units: MW (power) vs MWh (energy); aggregate correctly when summing over time.
- Gaps and outliers in load/generation series; negative prices are real, not errors.
- Derived variables: renewable share, residual load (demand minus wind and solar), peak/off-peak flag, season, per-capita consumption.
- Combine sources on country + time; save processed outputs as Parquet in `data/processed/`.

## Tech stack
- Python, pandas, numpy, pyarrow, requests
- **Panel + hvPlot/HoloViews + Bokeh** (PyViz stack); HoloViews `link_selections` for linked views
- Likely additions: geopandas, geoviews (map), entsoe-py
- Run the app: `panel serve dashboard/app.py --show`

## Repo structure
```
data/raw/        original data, never modified
data/interim/    intermediate outputs
data/processed/  final, dashboard-ready data (Parquet)
notebooks/       exploration only, numbered (01_explore.ipynb)
src/data/        download and cleaning scripts (raw -> processed)
src/features/    derived variables, aggregations
src/viz/         reusable chart functions
dashboard/       Panel app (thin: layout + interactivity, imports from src/viz)
docs/            data source notes, data contract, prep documentation, slides
reports/figures/ exported figures
tests/
```

## Conventions
- `data/raw/` is immutable; `processed/` must be reproducible from raw via scripts.
- Shared logic in `src/`, not notebooks.
- One branch per task, merged into `master` via pull request reviewed by a teammate.
- GitHub Issues + Project board for task tracking.

## Team organisation (split by layer)
| Role | Owns | Defends in presentation |
|---|---|---|
| A: Data | Download scripts, cleaning, time/zone/unit harmonisation, derived variables, `data/processed/`, prep docs | Data Preparation |
| B: Visualization | Chart functions in `src/viz/`, chart choices, palette, consistent styling | Quality of Visualizations |
| C: Dashboard | Panel layout (SaaS-style design), KPI cards, widgets, filters, linked views, stability, README | Analytical Capabilities + Technical Implementation |

Design Process and the final presentation are shared. (Assign names to roles.)

To avoid B and C waiting on A:
1. Agree a **data contract** first (`docs/data_contract.md`): processed file names, columns, dtypes, units, time zone.
2. A delivers a rough sample of processed data early so B and C can build against it.

## Next steps
1. ~~Confirm countries and years with the team.~~ Done: 7 countries, 2022 to 2025.
2. Test Energy-Charts API endpoints; register for ENTSO-E token in parallel.
3. Write `docs/data_contract.md`.
4. Write download scripts and the cleaning pipeline.
5. Update README (concept, questions, data sources table).
6. Create GitHub issues for Phase 1.

## Working preferences (for Claude)
- Concise, peer-level, informal communication.
- In hands-on work: give commands one at a time and wait for confirmation.
- Explain the "why" behind decisions, not just the steps.
- Do not use em dashes in any writing.