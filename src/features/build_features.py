"""Build the dashboard-ready hourly dataset from the cleaned interim tables.

Input:  data/interim/generation_hourly.parquet
        data/interim/prices_hourly.parquet
Output: data/processed/electricity_hourly.parquet

Steps:
1. Group the detailed generation sources into categories used in the charts.
2. Merge generation and prices on country and UTC hour.
3. Add derived variables: renewable generation and shares, residual load,
   negative price flag, and calendar fields in local time (hour, weekday,
   month, season, peak/off-peak).

Definitions are documented in docs/data_contract.md.

Run from anywhere:
    python src/features/build_features.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = REPO_ROOT / "data" / "interim"
OUT_PATH = REPO_ROOT / "data" / "processed" / "electricity_hourly.parquet"

COUNTRY_NAMES = {
    "HU": "Hungary",
    "DE": "Germany",
    "AT": "Austria",
    "FR": "France",
    "ES": "Spain",
    "PL": "Poland",
    "DK": "Denmark",
}
TIME_ZONES = {
    "HU": "Europe/Budapest",
    "DE": "Europe/Berlin",
    "AT": "Europe/Vienna",
    "FR": "Europe/Paris",
    "ES": "Europe/Madrid",
    "PL": "Europe/Warsaw",
    "DK": "Europe/Copenhagen",
}

# Generation categories and the detailed sources they combine (MW).
# Pumped storage and batteries are storage, not primary generation, so they
# are kept separate and are not counted as renewable.
CATEGORIES = {
    "solar_mw": ["solar_mw"],
    "wind_onshore_mw": ["wind_onshore_mw"],
    "wind_offshore_mw": ["wind_offshore_mw"],
    "hydro_mw": ["hydro_run_of_river_mw", "hydro_reservoir_mw"],
    "biomass_mw": ["biomass_mw"],
    "other_renewables_mw": ["geothermal_mw", "other_renewables_mw"],
    "nuclear_mw": ["nuclear_mw"],
    "gas_mw": ["fossil_gas_mw"],
    "coal_mw": ["fossil_lignite_mw", "fossil_hard_coal_mw", "fossil_coal_derived_gas_mw"],
    "oil_mw": ["fossil_oil_mw"],
    "other_mw": ["waste_mw", "others_mw"],
    "storage_mw": ["hydro_pumped_storage_mw", "battery_mw"],
}
RENEWABLE = ["solar_mw", "wind_onshore_mw", "wind_offshore_mw", "hydro_mw",
             "biomass_mw", "other_renewables_mw"]
FOSSIL = ["gas_mw", "coal_mw", "oil_mw"]

SEASONS = {12: "Winter", 1: "Winter", 2: "Winter",
           3: "Spring", 4: "Spring", 5: "Spring",
           6: "Summer", 7: "Summer", 8: "Summer",
           9: "Autumn", 10: "Autumn", 11: "Autumn"}

# Standard European power market definition: weekdays 08:00-20:00 local time
PEAK_HOURS = range(8, 20)


def add_generation_categories(gen):
    out = gen[["timestamp_utc", "country", "load_mw"]].copy()
    for category, sources in CATEGORIES.items():
        out[category] = gen[sources].sum(axis=1)

    out["wind_mw"] = out["wind_onshore_mw"] + out["wind_offshore_mw"]
    out["renewable_mw"] = out[RENEWABLE].sum(axis=1)
    out["fossil_mw"] = out[FOSSIL].sum(axis=1)
    out["total_generation_mw"] = out[list(CATEGORIES)].sum(axis=1)

    load = out["load_mw"].where(out["load_mw"] > 0)
    out["renewable_share_load_pct"] = 100 * out["renewable_mw"] / load
    out["renewable_share_generation_pct"] = (
        100 * out["renewable_mw"] / out["total_generation_mw"].replace(0, np.nan)
    )
    out["residual_load_mw"] = out["load_mw"] - out["solar_mw"] - out["wind_mw"]

    flags = ["n_interpolated", "n_zero_filled", "load_missing"]
    out[flags] = gen[flags]
    return out


def add_calendar_fields(df):
    local = pd.Series(pd.NaT, index=df.index, dtype="datetime64[us]")
    for country, tz in TIME_ZONES.items():
        rows = df["country"] == country
        local[rows] = df.loc[rows, "timestamp_utc"].dt.tz_convert(tz).dt.tz_localize(None)

    df["timestamp_local"] = local
    df["year"] = local.dt.year
    df["month"] = local.dt.month
    df["season"] = local.dt.month.map(SEASONS)
    df["weekday"] = local.dt.day_name()
    df["hour"] = local.dt.hour
    df["is_weekend"] = local.dt.dayofweek >= 5
    df["is_peak"] = ~df["is_weekend"] & df["hour"].isin(PEAK_HOURS)
    return df


def main():
    gen = pd.read_parquet(INTERIM_DIR / "generation_hourly.parquet")
    prices = pd.read_parquet(INTERIM_DIR / "prices_hourly.parquet")

    df = add_generation_categories(gen)
    df = df.merge(prices, on=["timestamp_utc", "country"], how="left", validate="one_to_one")
    df["is_negative_price"] = df["price_eur_mwh"] < 0
    df = add_calendar_fields(df)

    df.insert(2, "country_name", df["country"].map(COUNTRY_NAMES))
    df["country"] = df["country"].astype("category")
    df["country_name"] = df["country_name"].astype("category")
    df["season"] = pd.Categorical(df["season"], ["Winter", "Spring", "Summer", "Autumn"])
    df["weekday"] = pd.Categorical(
        df["weekday"],
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    )

    front = ["timestamp_utc", "timestamp_local", "country", "country_name"]
    df = df[front + [c for c in df.columns if c not in front]]
    df = df.sort_values(["country", "timestamp_utc"]).reset_index(drop=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)
    print(f"{OUT_PATH.relative_to(REPO_ROOT)}: {len(df):,} rows, {df.shape[1]} columns")


if __name__ == "__main__":
    main()
