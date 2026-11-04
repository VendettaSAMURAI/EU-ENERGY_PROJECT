"""Checks on data/processed/electricity_hourly.parquet.

Run from the repo root after building the data:
    pytest tests/
"""

from pathlib import Path

import pandas as pd
import pytest

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "electricity_hourly.parquet"

COUNTRIES = {"HU", "DE", "AT", "FR", "ES", "PL", "DK"}
HOURS_2022_2025 = 35064  # 4 years incl. leap year 2024

GENERATION_COLUMNS = [
    "solar_mw", "wind_onshore_mw", "wind_offshore_mw", "hydro_mw", "biomass_mw",
    "other_renewables_mw", "nuclear_mw", "gas_mw", "coal_mw", "oil_mw", "other_mw",
]


@pytest.fixture(scope="module")
def df():
    if not DATA_PATH.exists():
        pytest.skip("processed data not built yet, run the scripts in src/ first")
    return pd.read_parquet(DATA_PATH)


def test_all_countries_present(df):
    assert set(df["country"].unique()) == COUNTRIES


def test_complete_hourly_calendar(df):
    counts = df.groupby("country", observed=True).size()
    assert (counts == HOURS_2022_2025).all()


def test_no_duplicate_hours(df):
    assert not df.duplicated(["country", "timestamp_utc"]).any()


def test_timestamps_are_utc(df):
    assert str(df["timestamp_utc"].dt.tz) == "UTC"


def test_years_in_scope(df):
    assert set(df["year"].unique()) == {2022, 2023, 2024, 2025}


def test_generation_has_no_missing_values(df):
    assert df[GENERATION_COLUMNS].notna().all().all()


def test_generation_is_not_negative(df):
    assert (df[GENERATION_COLUMNS] >= 0).all().all()


def test_load_missing_only_where_flagged(df):
    assert (df["load_mw"].isna() == df["load_missing"]).all()
    assert df["load_missing"].mean() < 0.001


def test_iberian_blackout_left_missing(df):
    blackout = df[(df["country"] == "ES")
                  & (df["timestamp_utc"] >= "2025-04-28 11:00")
                  & (df["timestamp_utc"] <= "2025-04-29 21:00")]
    assert blackout["load_missing"].all()


def test_prices_complete(df):
    assert df["price_eur_mwh"].notna().all()


def test_negative_prices_kept(df):
    assert (df["price_eur_mwh"] < 0).any()
    assert (df["is_negative_price"] == (df["price_eur_mwh"] < 0)).all()


def test_renewable_mw_is_sum_of_parts(df):
    parts = ["solar_mw", "wind_onshore_mw", "wind_offshore_mw", "hydro_mw",
             "biomass_mw", "other_renewables_mw"]
    assert (df[parts].sum(axis=1) - df["renewable_mw"]).abs().max() < 1e-6


def test_annual_load_plausible(df):
    # Annual consumption in TWh, wide bounds around published national figures
    bounds = {"DE": (400, 550), "FR": (380, 500), "ES": (200, 270), "PL": (140, 190),
              "AT": (50, 75), "HU": (35, 50), "DK": (28, 45)}
    annual = df.groupby(["country", "year"], observed=True)["load_mw"].sum() / 1e6
    for (country, year), twh in annual.items():
        low, high = bounds[country]
        assert low <= twh <= high, f"{country} {year}: {twh:.1f} TWh"


def test_peak_definition(df):
    peak = df[df["is_peak"]]
    assert peak["hour"].between(8, 19).all()
    assert not peak["is_weekend"].any()
