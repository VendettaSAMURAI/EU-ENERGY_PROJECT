# European Union Renewable Energy Observatory

Interactive dashboard tracking electricity demand, generation mix, renewables, and prices across European Union member states from 2022 to 2025.

Project work for **Data Visualization Methods (INMAA0105L-01/26f)**, MSc Data Science, University of Debrecen.

## Team
- Gilbert Mutai
- Aviral Birthare
- Venkatachalamoorthy Jagadish

---

## Overview
Europe’s power system is evolving rapidly. The 2022 energy crisis pushed prices to record highs, solar and wind capacity continues to expand, and hours with negative electricity prices have become increasingly common. This dashboard allows you to explore the European renewable energy transition hour by hour from 2022 to 2025—a transformative period spanning the energy crisis, market recovery, and the unprecedented solar boom across renewable and low-carbon resources (including solar, wind, hydro, nuclear, and thermal generation).

To capture the diversity of Europe’s energy landscape, the analysis integrates comprehensive Eurostat datasets for all EU member states alongside granular hourly data for key representative bidding zones and countries, with a special focus on Hungary (our host country).

---

## Analytical Questions
1. **Demand Patterns:** How does electricity demand vary by hour, weekday, and season across Europe, and when do peak loads occur?
2. **Country Comparison:** How do different national power systems (hydro, nuclear, coal, wind, solar) differ in their overall consumption and generation mix?
3. **Renewables Growth:** How has the renewable share of generation grown across Europe from 2022 to 2025, and how effectively does renewable output cover demand?
4. **Price Dynamics:** Do hours with high renewable generation correlate with lower or negative prices, and how does this relationship differ across countries?

*Detailed key findings per question can be found in [docs/insights.md](docs/insights.md).*

---

## Visualizations
Built with the PyViz stack (**Panel** and **Plotly**). Chart types were intentionally selected to directly answer each analytical question rather than for visual variety:

| Question | Charts & Visualizations |
| :--- | :--- |
| **1. Demand** | Hour × weekday heatmap, calendar heatmap, daily profile per season |
| **2. Countries** | Choropleth map, ranked dot and dumbbell chart, generation mix bars per country |
| **3. Renewables** | Stacked generation mix with load, country × month heatmap, duck curve, coverage duration curve |
| **4. Prices** | Violin plots, price duration curve, hexbin of renewable share (or residual load) vs. price, negative-price heatmap |

All charts share a unified dark theme and a consistent color palette per energy source, rigorously checked for color-blind safety ([docs/visual_style.md](docs/visual_style.md)). Detailed documentation on chart functions is available in [docs/charts.md](docs/charts.md).

---

## Data Sources
| Dataset | Source | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| **Hourly / 15-min generation by source & load** (7 countries) | [Energy-Charts API](https://api.energy-charts.info), Fraunhofer ISE (`public_power`) | Energy-Charts terms of use ([energy-charts.info](https://www.energy-charts.info)) | November 2026 |
| **Day-ahead prices** (bidding zones: HU, DE-LU, AT, FR, PL, DK1, DK2) | Energy-Charts API (`price`), data from Bundesnetzagentur / SMARD.de | CC BY 4.0 | November 2026 |
| **Day-ahead prices** (bidding zone: ES) | Energy-Charts API (`price`), market data from EPEX SPOT SE | Private and internal use only; no external/commercial use | November 2026 |
| **Renewable energy share** (all energy uses, annual) | [Eurostat `nrg_ind_ren`](https://ec.europa.eu/eurostat/databrowser/view/nrg_ind_ren/default/table) | Eurostat reuse policy (free reuse with attribution) | October 2026 |
| **Country administrative borders** (1:20M, 2020) | [Eurostat GISCO](https://gisco-services.ec.europa.eu/distribution/v2/countries/) | © EuroGeographics | November 2026 |

*(Planned: Eurostat population metrics (`demo_pjan`) for per-capita consumption analysis).*

Raw data is excluded from Git. Every dataset is automatically downloaded via scripts in `src/data/` to ensure full reproducibility from primary sources.

---

## Data Preparation & Engineering
- **Harmonised Resolution:** Mixed 15-minute and hourly generation, load, and price feeds are resampled to hourly means (for MW power, the hourly mean equals MWh energy).
- **Time Harmonisation:** All timestamps are standardized to UTC (eliminating daylight-saving gaps or duplicates), while local time is preserved for analyzing hour-of-day and weekday behavioral patterns.
- **Complete Calendar:** Each country's dataset contains exactly 35,064 hours, making temporal data gaps explicit.
- **Missing Value Handling:** Short gaps up to 3 hours are linearly interpolated (206 values); extended gaps for decommissioned sources are set to 0 where appropriate (e.g., German nuclear post-April 2023 shutdown); missing load data (54 hours, primarily during the Iberian blackout of April 28, 2025) remains explicitly flagged as missing.
- **Bidding Zones:** Germany uses `DE-LU`; Danish pricing represents the mean of `DK1` and `DK2`. Negative market prices are preserved as genuine economic signals.
- **Derived Features:** Includes 12 distinct generation categories, renewable shares of load and generation, residual load, peak/off-peak indicators, seasons, and weekday flags.
- **Validation:** 14 automated data quality checks are implemented (e.g., verifying zero duplicate timestamps and plausible annual consumption bounds per country).
##############################################################################################################################################################################################################################
Running the Dashboard
Launch the interactive local Panel server:

Bash
panel serve dashboard/app.py --show
---

## Project Structure
```text
data/
  raw/            Original downloads, never modified (git-ignored)
  interim/        Intermediate processed outputs
  processed/      Final, dashboard-ready data (Parquet format)
notebooks/        Exploratory data analysis and prototyping
src/
  data/           Data ingestion and cleaning scripts
  features/       Feature engineering and derived variables
  viz/            Chart generation functions and theme definitions
dashboard/        Panel application script
docs/             Comprehensive documentation (data contract, prep, chart guide, styling, insights)
reports/figures/  Exported report figures
tests/            Automated data validation checks and chart unit tests


##############################################################################################################################################################################################################################
python -m venv venv
venv\Scripts\activate            # macOS / Linux: source venv/bin/activate
pip install -r requirements.txt

Running the Dashboard
Launch the interactive local Panel server:

