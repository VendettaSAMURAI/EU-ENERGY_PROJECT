"""Clean the raw Energy-Charts downloads into hourly tables.

Input:  data/raw/energy_charts/public_power_<country>_<year>.json
        data/raw/energy_charts/price_<zone>_<year>.json
Output: data/interim/generation_hourly.parquet  (one row per country and hour)
        data/interim/prices_hourly.parquet      (one row per country and hour)

Steps:
1. Flatten the JSON files into tables with UTC timestamps.
2. Resample everything to hourly means. Generation and load are 15-minute
   for some countries and years, prices are 15-minute from October 2025.
   The mean of MW values over an hour equals the energy in MWh for that hour.
3. Reindex to a complete hourly calendar, so missing hours appear as NaN.
4. Fill short gaps (up to MAX_INTERPOLATION_HOURS) by linear interpolation.
5. Longer gaps in a generation source are set to 0. Energy-Charts leaves a
   source empty when it produced nothing or was not reported yet, e.g. German
   nuclear after the shutdown on 15 April 2023, or batteries before they were
   installed. Sources a country does not have at all are also 0.
6. Longer gaps in load stay NaN. The only case is the Iberian blackout on
   28-29 April 2025 (Spain), which should not be filled with invented values.

Run from anywhere:
    python src/data/clean_energy_charts.py
"""

import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw" / "energy_charts"
OUT_DIR = REPO_ROOT / "data" / "interim"

COUNTRIES = ["HU", "DE", "AT", "FR", "ES", "PL", "DK"]
YEARS = [2022, 2023, 2024, 2025]

# Bidding zones per country. Denmark is the mean of its two zones.
PRICE_ZONES = {
    "HU": ["HU"],
    "DE": ["DE-LU"],
    "AT": ["AT"],
    "FR": ["FR"],
    "ES": ["ES"],
    "PL": ["PL"],
    "DK": ["DK1", "DK2"],
}

# Energy-Charts series name -> column name (all values in MW).
# Residual load, cross-border trading and the source's own renewable share of
# generation are not kept; residual load and shares are recomputed later.
SERIES_COLUMNS = {
    "Load": "load_mw",
    "Solar": "solar_mw",
    "Wind onshore": "wind_onshore_mw",
    "Wind offshore": "wind_offshore_mw",
    "Hydro Run-of-River": "hydro_run_of_river_mw",
    "Hydro water reservoir": "hydro_reservoir_mw",
    "Hydro pumped storage": "hydro_pumped_storage_mw",
    "Hydro pumped storage consumption": "hydro_pumped_storage_consumption_mw",
    "Biomass": "biomass_mw",
    "Geothermal": "geothermal_mw",
    "Other renewables": "other_renewables_mw",
    "Nuclear": "nuclear_mw",
    "Fossil gas": "fossil_gas_mw",
    "Fossil brown coal / lignite": "fossil_lignite_mw",
    "Fossil hard coal": "fossil_hard_coal_mw",
    "Fossil oil": "fossil_oil_mw",
    "Fossil coal-derived gas": "fossil_coal_derived_gas_mw",
    "Waste": "waste_mw",
    "Others": "others_mw",
    "Battery": "battery_mw",
    "Battery Consumption": "battery_consumption_mw",
    # Kept only to cross-check our own renewable share calculation
    "Renewable share of load": "ec_renewable_share_of_load_pct",
}
VALUE_COLUMNS = list(SERIES_COLUMNS.values())
# Columns whose long gaps stay NaN; every other column is a generation source
KEEP_MISSING_COLUMNS = ["load_mw", "ec_renewable_share_of_load_pct"]
GENERATION_COLUMNS = [c for c in VALUE_COLUMNS if c not in KEEP_MISSING_COLUMNS]

MAX_INTERPOLATION_HOURS = 3

# The files follow local (CET) calendar years: 2022-01-01 00:00 CET is
# 2021-12-31 23:00 UTC.
HOURS = pd.date_range("2021-12-31 23:00", "2025-12-31 22:00", freq="h", tz="UTC")


def to_hourly(df):
    """Mean of all values within each UTC hour."""
    return df.groupby(df.index.floor("h")).mean()


def read_public_power(country, year):
    path = RAW_DIR / f"public_power_{country.lower()}_{year}.json"
    raw = json.loads(path.read_text())
    index = pd.to_datetime(raw["unix_seconds"], unit="s", utc=True)
    series = {
        SERIES_COLUMNS[p["name"]]: p["data"]
        for p in raw["production_types"]
        if p["name"] in SERIES_COLUMNS
    }
    return pd.DataFrame(series, index=index, dtype="float64")


def read_price(zone, year):
    path = RAW_DIR / f"price_{zone.lower()}_{year}.json"
    raw = json.loads(path.read_text())
    index = pd.to_datetime(raw["unix_seconds"], unit="s", utc=True)
    return pd.Series(raw["price"], index=index, dtype="float64")


def fill_short_gaps(df, columns):
    """Interpolate gaps up to MAX_INTERPOLATION_HOURS; leave longer gaps as NaN."""
    df = df.copy()
    for col in columns:
        missing = df[col].isna()
        run_id = (missing != missing.shift()).cumsum()
        run_length = missing.groupby(run_id).transform("sum")
        short_gap = missing & (run_length <= MAX_INTERPOLATION_HOURS)
        filled = df[col].interpolate(method="time", limit_area="inside")
        df.loc[short_gap, col] = filled[short_gap]
    return df


def clean_generation():
    frames = []
    for country in COUNTRIES:
        df = pd.concat([read_public_power(country, year) for year in YEARS])
        df = df[~df.index.duplicated()].sort_index()
        df = to_hourly(df).reindex(HOURS)
        df.index.name = "timestamp_utc"

        # Sources that never occur for this country are zero, not missing
        for col in VALUE_COLUMNS:
            if col not in df.columns:
                df[col] = 0.0

        was_missing = df[VALUE_COLUMNS].isna()
        df = fill_short_gaps(df, VALUE_COLUMNS)
        df["n_interpolated"] = (was_missing & df[VALUE_COLUMNS].notna()).sum(axis=1)

        still_missing = df[GENERATION_COLUMNS].isna()
        df[GENERATION_COLUMNS] = df[GENERATION_COLUMNS].fillna(0.0)
        df["n_zero_filled"] = still_missing.sum(axis=1)
        df["load_missing"] = df["load_mw"].isna()

        df.insert(0, "country", country)
        flags = ["n_interpolated", "n_zero_filled", "load_missing"]
        frames.append(df[["country", *VALUE_COLUMNS, *flags]])

    return pd.concat(frames).reset_index()


def clean_prices():
    frames = []
    for country, zones in PRICE_ZONES.items():
        zone_prices = []
        for zone in zones:
            s = pd.concat([read_price(zone, year) for year in YEARS])
            s = s[~s.index.duplicated()].sort_index()
            zone_prices.append(to_hourly(s))
        price = pd.concat(zone_prices, axis=1).mean(axis=1).reindex(HOURS)

        df = pd.DataFrame({"price_eur_mwh": price})
        was_missing = df["price_eur_mwh"].isna()
        df = fill_short_gaps(df, ["price_eur_mwh"])
        df["price_interpolated"] = was_missing & df["price_eur_mwh"].notna()
        df.index.name = "timestamp_utc"
        df.insert(0, "country", country)
        frames.append(df)

    return pd.concat(frames).reset_index()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    generation = clean_generation()
    generation.to_parquet(OUT_DIR / "generation_hourly.parquet", index=False)
    print(f"generation_hourly.parquet: {len(generation):,} rows, "
          f"{generation['n_interpolated'].sum():,} values interpolated, "
          f"{generation['n_zero_filled'].sum():,} set to 0, "
          f"{generation['load_missing'].sum():,} hours without load")

    prices = clean_prices()
    prices.to_parquet(OUT_DIR / "prices_hourly.parquet", index=False)
    print(f"prices_hourly.parquet: {len(prices):,} rows, "
          f"{prices['price_interpolated'].sum():,} values interpolated, "
          f"{prices['price_eur_mwh'].isna().sum():,} values left missing")


if __name__ == "__main__":
    main()
