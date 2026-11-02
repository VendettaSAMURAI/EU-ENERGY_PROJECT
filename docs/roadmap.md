# Roadmap

Step-by-step plan for the EU Electricity Dashboard. Tick items off as they are done (`[x]`).
Roles: **A** = Data, **B** = Visualization, **C** = Dashboard, **All** = shared. See `CLAUDE.md` for details.

Deadline / presentation date: _TBD_

---

## Phase 0: Decisions and setup
- [ ] **All** Assign names to roles A, B, C
- [x] **All** Confirm countries: HU, DE, AT, FR, ES, PL, DK
- [x] **All** Confirm years: 2022 to 2025
- [ ] **All** Finalise the analytical questions (draft in `CLAUDE.md`)
- [ ] **All** Everyone sets up the environment: `python -m venv venv`, `pip install -r requirements.txt`
- [ ] **C** Create GitHub Project board and Phase 1 issues
- [ ] **A** Register for an ENTSO-E API token (backup source)

## Phase 1: Data contract and acquisition
- [x] **A** Test Energy-Charts API endpoints (load, generation by source, day-ahead prices) for one country
- [ ] **A** Decide bidding zone to country mapping (DE-LU, DK1/DK2) and write it down
- [ ] **All** Write `docs/data_contract.md`: processed file names, columns, dtypes, units, time zone
- [x] **A** Download script for Energy-Charts -> `data/raw/energy_charts/`
- [ ] **A** Download script for Ember yearly/monthly data -> `data/raw/ember/`
- [ ] **A** Download script for Eurostat population -> `data/raw/eurostat/`
- [x] **A** Move the existing Eurostat renewables file into `data/raw/eurostat/`
- [ ] **A** Replace the manual Eurostat renewables download with a script
- [ ] **A** Deliver a rough sample of processed data so B and C can start

## Phase 2: Cleaning and derived variables
- [ ] **A** Convert timestamps to UTC, handle DST gaps/duplicates
- [ ] **A** Resample 15-min and hourly series to one common resolution
- [ ] **A** Harmonise units (MW vs MWh) and aggregate correctly
- [ ] **A** Handle gaps and outliers (keep negative prices, they are real)
- [ ] **A** Derived variables: renewable share, residual load, peak/off-peak flag, season, per-capita consumption
- [ ] **A** Merge sources on country + time, save Parquet to `data/processed/`
- [ ] **A** Document every prep step in `docs/data_preparation.md` (needed for the defense)
- [ ] **A** Basic tests in `tests/` (no duplicate timestamps, expected columns, sensible ranges)

## Phase 3: Visualizations (`src/viz/`)
- [ ] **B** Pick palette and shared styling (dark SaaS theme), one style module used by all charts
- [ ] **B** Q1 Demand patterns: hour x weekday heatmap, calendar heatmap, seasonal hour-of-day profiles
- [ ] **B** Q2 Country comparison: choropleth map, ranked dot/lollipop chart, generation mix per country
- [ ] **B** Q3 Renewables: stacked area/streamgraph of generation mix, renewables vs demand overlay
- [ ] **B** Q4 Prices: violin/ridgeline per country, price duration curve, renewable share vs price scatter
- [ ] **B** Check every chart answers one analytical question; drop any that do not

## Phase 4: Dashboard (`dashboard/app.py`)
- [ ] **C** Layout skeleton: header with KPI cards, sections A to E as tabs or panels
- [ ] **C** KPI cards: total consumption, average price, renewable share, peak-demand period
- [ ] **C** Global filters: country selector, date range, resolution
- [ ] **C** Linked views (`link_selections`): brushing in one chart filters the others
- [ ] **C** Hover tooltips and zoom where useful
- [ ] **C** "About the data" tab with sources and licences
- [ ] **C** Performance check: app loads and filters quickly with full data
- [ ] **C** Stability check: `panel serve dashboard/app.py --show` runs on a clean clone

## Phase 5: Documentation and presentation
- [ ] **All** Update README: overview, questions, data sources table with licences and access dates, how to run
- [ ] **All** Write down key insights per analytical question
- [ ] **All** Slides in `docs/`: dataset, data prep, design decisions, demo flow, insights
- [ ] **All** Each member rehearses their part plus a full demo
- [ ] **All** Final check against `docs/project_brief.md` (minimum requirements and assessment criteria)
