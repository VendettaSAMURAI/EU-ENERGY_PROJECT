# European Union Renewable Energy Dashboard 

Interactive dashboard on electricity demand, generation mix, renewables and prices in seven EU countries, 2022 to 2025.

Project work for **Data Visualization Methods (INMAA0105L-01/26f)**, MSc Data Science, University of Debrecen.

## Team
- Gilbert Mutai
- Aviral Birthare
- Venkatachalamoorthy Jagadish

## Overview
Europe’s power system is changing fast. The 2022 energy crisis pushed prices to record highs, solar and wind capacity keeps growing, and hours with negative prices have become common. This dashboard lets you explore the European renewable energy transition hour by hour, from 2022 to 2025, a period that spans the crisis, the recovery and the solar boom to the all renewable energy resources including thermal , nuclear & wind energy.

To capture the diversity of Europe’s power systems, the analysis uses seven representative countries: Hungary (our host country) and all 27 nations of European union.

## Analytical Questions
1.Demand patterns: How does electricity demand vary by hour, weekday and season across Europe, and when do the peaks occur?
2.Country comparison: How do different power systems (hydro, nuclear, coal, wind, solar) differ in consumption and generation mix?
3.Renewables: How has the renewable share of generation grown across Europe from 2022 to 2025, and how well does renewable output cover demand?
4.Prices: Do hours with high renewable generation have lower or negative prices, and how does this relationship differ between countries?

Key findings per question: [docs/insights.md](docs/insights.md).

## Visualizations
Built with the PyViz stack (** Bokeh**). Chart types were chosen per question, not for variety:

| Question | Charts |
|---|---|
| 1 Demand | hour × weekday heatmap, calendar heatmap, daily profile per season |
| 2 Countries | choropleth map, ranked dot and dumbbell chart, generation mix bars per country |
| 3 Renewables | stacked generation mix with load, country × month heatmap, duck curve, coverage duration curve |
| 4 Prices | violin plots, price duration curve, hexbin of renewable share (or residual load) vs price, negative-price heatmap |

All charts share one dark theme and one colour per energy source, checked for colour-blind safety ([docs/visual_style.md](docs/visual_style.md)). How to use the chart functions: [docs/charts.md](docs/charts.md).

## Data Sources
| Dataset | Source | Licence | Accessed |
|---|---|---|---|
| Hourly / 15-min generation by source and load, 7 countries | [Energy-Charts API](https://api.energy-charts.info), Fraunhofer ISE (`public_power`) | Energy-Charts terms of use, see [energy-charts.info](https://www.energy-charts.info) | November 2026 |
| Day-ahead prices, bidding zones HU, DE-LU, AT, FR, PL, DK1, DK2 | Energy-Charts API (`price`), data from Bundesnetzagentur / SMARD.de | CC BY 4.0 | November 2026 |
| Day-ahead prices, bidding zone ES | Energy-Charts API (`price`), market data from EPEX SPOT SE | Private and internal use only; no external or commercial use (licence note in the API response) | November 2026 |
| Renewable energy share (all energy uses), annual | [Eurostat `nrg_ind_ren`](https://ec.europa.eu/eurostat/databrowser/view/nrg_ind_ren/default/table) | Eurostat reuse policy (free reuse with attribution) | October 2026 |
| Country borders for the map (1:20 million, 2020) | [Eurostat GISCO](https://gisco-services.ec.europa.eu/distribution/v2/countries/) | © EuroGeographics for the administrative boundaries | November 2026 |

Planned: Eurostat population (`demo_pjan`) for per-capita consumption.

Raw data is not stored in Git. Every file is downloaded by a script in `src/data/`, so the dataset can be rebuilt from the sources.

## Data Preparation
- **Harmonised resolution:** generation, load and prices come in mixed 15-minute and hourly resolution; everything is resampled to hourly means (for MW, the hourly mean equals MWh).
- **Time:** all timestamps in UTC (no daylight-saving gaps or duplicates); local time is kept for hour-of-day and weekday patterns.
- **Complete calendar:** each country has exactly 35,064 hours, so gaps are explicit.
- **Missing values:** gaps up to 3 hours interpolated (206 values); long gaps in a generation source set to 0 where the source produced nothing (e.g. German nuclear after the April 2023 shutdown); missing load (54 hours, mostly the Iberian blackout of 28 April 2025) left missing and flagged.
- **Bidding zones:** Germany uses DE-LU; Denmark's price is the mean of DK1 and DK2. Negative prices are kept: they are real.
- **Derived variables:** 12 generation categories, renewable share of load and of generation, residual load, peak/off-peak flag, season, weekday.
- **Validation:** 14 automated checks on the processed data, e.g. no duplicate hours, plausible annual consumption per country.

Details: [docs/data_preparation.md](docs/data_preparation.md). Column definitions: [docs/data_contract.md](docs/data_contract.md).

## Project Structure
```
data/
  raw/            original downloads, never modified (not in Git)
  interim/        intermediate outputs
  processed/      final, dashboard-ready data (Parquet)
notebooks/        exploratory analysis
src/
  data/           download and cleaning scripts
  features/       derived variables
  viz/            chart functions and shared style
dashboard/        Panel app
docs/             data contract, preparation, chart guide, visual style, insights
reports/figures/  exported figures
tests/            data checks and chart tests
```

## Setup
Python 3.12 or 3.13 recommended.
```bash
python -m venv venv
venv\Scripts\activate            # macOS / Linux: source venv/bin/activate
pip install -r requirements.txt
```

## Building the Data
Run from the repo root. The downloads are only needed once.
```bash
python src/data/download_energy_charts.py      # Energy-Charts raw data (60 files, ~100 MB, a few minutes)
python src/data/download_gisco.py              # map borders (1.9 MB)
python src/data/clean_energy_charts.py         # raw -> data/interim/
python src/features/build_features.py          # interim -> data/processed/electricity_hourly.parquet
python src/data/clean_eurostat_renewables.py   # Eurostat -> data/processed/
pytest tests/                                  # data checks and chart tests
```

## Running the Dashboard
```bash
panel serve dashboard/app.py --show
```
