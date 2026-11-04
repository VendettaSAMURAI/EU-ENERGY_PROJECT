# Data Preparation

How the raw data becomes the dataset used in the dashboard, and why each decision was made. Column definitions are in [data_contract.md](data_contract.md).

## Scope

- **Countries:** Hungary, Germany, Austria, France, Spain, Poland, Denmark. Chosen to cover different power systems: hydro (AT), nuclear (FR), coal (PL), wind (DK, DE), solar (ES), and Hungary as our host country.
- **Period:** 2022 to 2025, four full years covering the energy price crisis (2022), the recovery (2023-2024) and continued solar growth with more negative-price hours (2025).

## Pipeline

```
data/raw/energy_charts/*.json        60 files, as downloaded
        │  src/data/clean_energy_charts.py
        ▼
data/interim/generation_hourly.parquet
data/interim/prices_hourly.parquet
        │  src/features/build_features.py
        ▼
data/processed/electricity_hourly.parquet      245,448 rows × 37 columns
        │  tests/test_processed_data.py         14 automated checks
```

Raw files are never modified. Every later file can be rebuilt from them by running the scripts (see the data contract).

## 1. Acquisition

`src/data/download_energy_charts.py` downloads one file per country (or price zone) per year from the Energy-Charts API:

- `public_power`: generation by source and load, 7 countries × 4 years
- `price`: day-ahead prices, 8 bidding zones × 4 years

The free API limits request rates (HTTP 429). The script pauses between requests, waits and retries when rate-limited, skips files that already exist and never saves error responses.

## 2. Cleaning (`src/data/clean_energy_charts.py`)

### Flattening and timestamps
The API returns nested JSON with Unix timestamps. These are converted to UTC datetimes and the yearly files are concatenated per country. Files follow local calendar years (a year starts at 23:00 UTC on 31 December), so they join without overlaps. Working in UTC avoids the daylight-saving problems of local time: in local time one hour per year is duplicated and one is missing.

### Common hourly resolution
The raw data comes in mixed resolutions:

| Data | Resolution |
|---|---|
| Generation and load: DE, AT, HU | 15 minutes |
| Generation and load: DK, FR | hourly |
| Generation and load: ES | hourly in 2022, 15 minutes from 2023 |
| Generation and load: PL | hourly until 2024, 15 minutes in 2025 |
| Day-ahead prices, all zones | hourly until 30 Sep 2025, 15 minutes from 1 Oct 2025 (EU market change) |

Everything is resampled to **hourly means**. For power in MW, the mean over an hour equals the energy in MWh for that hour, so sums over hours stay correct. Hourly resolution is also what the analytical questions need (hour of day, weekday, season).

### Complete calendar
Each country is reindexed to the full list of 35,064 hours, so a missing hour shows up as an explicit gap instead of a silently absent row.

### Missing values
Three rules, applied per column:

| Case | Rule | Count | Reason |
|---|---|---|---|
| Gap of up to 3 hours | Linear interpolation | 206 values | Short reporting gaps; power changes smoothly over a few hours |
| Longer gap in a generation source | Set to 0 | 227,836 values | Energy-Charts leaves a source empty when it produced nothing or was not yet reported (see below) |
| Longer gap in load | Left missing, flagged | 54 hours | Filling would invent demand that did not happen |

Evidence that long empty generation series mean "no production":
- **German nuclear** is empty from **15 April 2023**, the day Germany shut down its last three reactors.
- **French hard coal** is empty for months in 2024 and 2025, when the remaining coal plants were not running.
- **Batteries** (ES, FR) and some Polish categories only start being reported in 2024-2025.
- Sources a country does not have at all (e.g. nuclear in Denmark) are also 0.

Known limitation: French offshore wind is empty until May 2023, although the first offshore farm (Saint-Nazaire) started in late 2022. Setting it to 0 slightly understates French wind in that period. Offshore wind was well below 1% of French generation then.

The 54 hours without load are the **Iberian blackout** on 28-29 April 2025 (35 hours, Spain) and 19 hours of 4 to 6-hour reporting gaps in Denmark and France (0.02% of all hours). They are flagged with `load_missing`.

### Prices
- Germany uses the DE-LU zone (Germany and Luxembourg form one market zone).
- Denmark has two zones, DK1 (West) and DK2 (East). The Denmark price is the **simple mean** of both. A demand-weighted mean would be more precise, but the two zones usually move closely together.
- **Negative prices are kept.** They are real market outcomes when supply exceeds demand (typically sunny or windy hours with low demand) and are central to analytical question 4.
- Prices have no gaps.

## 3. Derived variables (`src/features/build_features.py`)

### Generation categories
The 21 detailed source series are grouped into 12 categories for readable charts (e.g. lignite + hard coal + coal-derived gas = coal). Pumped storage and batteries are kept as a separate **storage** category and are **not** counted as renewable, because they store electricity produced by other sources.

### Renewable share
`renewable_share_load_pct = renewable generation / load`. Renewable = solar, wind, hydro (excluding pumped storage), biomass, geothermal and other renewables.

**Cross-check:** Energy-Charts publishes its own "renewable share of load". Our value is on average 0.2 to 1.7 percentage points lower depending on the country. The difference comes from waste: Energy-Charts counts part of waste incineration as renewable, we count all of it as non-renewable. We chose the simpler, conservative definition.

### Residual load
`load - solar - wind`: the demand that must be covered by controllable sources (fossil, nuclear, hydro, imports). It is the basis of the "duck curve".

### Calendar fields
Hour, weekday, month and season are taken from **local time**, because daily routines follow the local clock. Peak hours follow the standard European power market definition: weekdays 08:00 to 20:00.

## 4. Validation (`tests/test_processed_data.py`)

14 automated checks, including:
- every country has exactly 35,064 hours, no duplicates, UTC timestamps
- no missing generation values, no negative generation
- load is missing only where flagged, and the blackout hours are not filled
- negative prices are present and correctly flagged
- annual consumption per country is within a plausible range of published national figures

Annual consumption from the processed data, for reference:

| Country | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| Germany | 482 TWh | 458 | 466 | 466 |
| France | 444 | 426 | 430 | 435 |
| Spain | 236 | 229 | 232 | 238 |
| Poland | 172 | 166 | 164 | 158 |
| Austria | 62 | 58 | 59 | 59 |
| Hungary | 43 | 42 | 43 | 43 |
| Denmark | 34 | 35 | 37 | 38 |

## 5. Eurostat renewable energy share (`src/data/clean_eurostat_renewables.py`)

Annual renewable share of **all** energy consumption (not only electricity) from Eurostat `nrg_ind_ren`, used as long-term context. Cleaning: keep and rename the relevant columns, convert types, label observation flags (`p` = provisional, empty = final), mark EU aggregates, strip footnote markers from country names, save as Parquet.
