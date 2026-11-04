# Data Contract

This describes the dashboard-ready datasets in `data/processed/`. Visualization and dashboard code should rely only on the columns listed here. If a column needs to change, update this file in the same pull request.

## How to build

From the repo root, with the virtual environment active:

```bash
python src/data/download_energy_charts.py      # raw data, only needed once
python src/data/clean_energy_charts.py         # raw -> data/interim/
python src/features/build_features.py          # interim -> data/processed/
python src/data/clean_eurostat_renewables.py   # Eurostat -> data/processed/
pytest tests/                                   # checks on the processed data
```

---

## `electricity_hourly.parquet`

One row per **country and hour**. 7 countries × 35,064 hours (2022-01-01 to 2025-12-31, local calendar years) = 245,448 rows.

**Source:** Energy-Charts API, Fraunhofer ISE (api.energy-charts.info), public net electricity generation, load and day-ahead prices.

### Keys and time

| Column | Type | Description |
|---|---|---|
| `timestamp_utc` | datetime (UTC) | Start of the hour in UTC. Use this for joins and time series. |
| `timestamp_local` | datetime (no tz) | Start of the hour in the country's local time. Use this for hour-of-day and weekday patterns. |
| `country` | category | ISO code: `HU`, `DE`, `AT`, `FR`, `ES`, `PL`, `DK` |
| `country_name` | category | Full country name |
| `year`, `month` | int | Local calendar year and month |
| `season` | category | Winter (Dec-Feb), Spring (Mar-May), Summer (Jun-Aug), Autumn (Sep-Nov) |
| `weekday` | category | Monday to Sunday (ordered) |
| `hour` | int | Local hour of day, 0 to 23 |
| `is_weekend` | bool | Saturday or Sunday |
| `is_peak` | bool | Weekday 08:00 to 20:00 local time (standard European power market peak) |

### Demand

| Column | Unit | Description |
|---|---|---|
| `load_mw` | MW | Electricity demand (load), hourly mean. Missing only where `load_missing` is true. |
| `residual_load_mw` | MW | `load_mw` minus solar and wind generation |

### Generation by category

All values are hourly mean power in MW. Because each row is one hour, summing MW over rows gives MWh (divide by 10^6 for TWh).

| Column | Contains |
|---|---|
| `solar_mw` | Solar |
| `wind_onshore_mw` | Onshore wind |
| `wind_offshore_mw` | Offshore wind (DE, DK, FR only) |
| `wind_mw` | Onshore + offshore wind |
| `hydro_mw` | Run-of-river + reservoir hydro (excludes pumped storage) |
| `biomass_mw` | Biomass |
| `other_renewables_mw` | Geothermal + other renewables |
| `nuclear_mw` | Nuclear |
| `gas_mw` | Fossil gas |
| `coal_mw` | Lignite + hard coal + coal-derived gas |
| `oil_mw` | Fossil oil |
| `other_mw` | Waste + others |
| `storage_mw` | Pumped storage + battery discharge |
| `renewable_mw` | Solar + wind + hydro + biomass + other renewables |
| `fossil_mw` | Gas + coal + oil |
| `total_generation_mw` | Sum of all categories above (excluding the `wind_mw`, `renewable_mw`, `fossil_mw` subtotals) |

### Shares

| Column | Unit | Description |
|---|---|---|
| `renewable_share_load_pct` | % | `renewable_mw / load_mw × 100`. Can exceed 100 when a country exports renewable power (e.g. Denmark on windy days). |
| `renewable_share_generation_pct` | % | `renewable_mw / total_generation_mw × 100` |

### Prices

| Column | Unit | Description |
|---|---|---|
| `price_eur_mwh` | EUR/MWh | Day-ahead price, hourly mean. Germany uses the DE-LU zone; Denmark is the mean of DK1 and DK2. Negative values are real. |
| `is_negative_price` | bool | `price_eur_mwh < 0` |

### Data quality flags

| Column | Type | Description |
|---|---|---|
| `load_missing` | bool | No load data for this hour (54 hours in total, 35 of them the Iberian blackout) |
| `n_interpolated` | int | Number of values in this row filled by interpolation (gaps of up to 3 hours) |
| `n_zero_filled` | int | Number of generation sources set to 0 because the source reported no value |
| `price_interpolated` | bool | Price filled by interpolation (currently never) |

### Rules for using this data

- Filter out `load_missing` rows when averaging or summing load and shares.
- Use `timestamp_local` (or `hour`, `weekday`) for daily and weekly patterns, `timestamp_utc` for everything else.
- Average power: take the mean of the `_mw` columns. Energy: sum the `_mw` columns over hours.

---

## `renewable_energy_shares.parquet`

One row per **country and year**, 2016 to 2025, 38 countries plus EU aggregates.

**Source:** Eurostat, `nrg_ind_ren` (renewable share of gross final energy consumption, all energy uses, not only electricity).

| Column | Type | Description |
|---|---|---|
| `country` | str | Country name |
| `geo_code` | str | Eurostat country code (note: Greece is `EL`) |
| `year` | int | Year |
| `renewable_share_pct` | float | Renewable share of gross final energy consumption, % |
| `data_flag` | str | `final` or `provisional` |
| `is_aggregate` | bool | True for EU/euro area totals |
