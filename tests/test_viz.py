"""Tests for chart functions in src/viz/ on small synthetic data.

These do not need data/processed/, so they run on a clean clone. They check
the aggregation maths with known answers and that every chart renders to a
Bokeh model without errors.
"""

import sys
from pathlib import Path

import holoviews as hv
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.viz import countries, demand, palette_check, prices, renewables, style  # noqa: E402

hv.extension("bokeh")
style.apply()

# Fixed share of load for each generation column in the synthetic data.
# Renewables (solar 0.1 + wind 0.2 + 0.1 + hydro 0.1 + biomass 0.05 + 0.05) = 60%
GEN_SHARES = {
    "solar_mw": 0.10, "wind_onshore_mw": 0.20, "wind_offshore_mw": 0.10, "hydro_mw": 0.10,
    "biomass_mw": 0.05, "other_renewables_mw": 0.05, "coal_mw": 0.15, "nuclear_mw": 0.10,
    "gas_mw": 0.10, "oil_mw": 0.01, "other_mw": 0.02, "storage_mw": 0.02,
}
RENEWABLE_COLS = ["solar_mw", "wind_onshore_mw", "wind_offshore_mw", "hydro_mw",
                  "biomass_mw", "other_renewables_mw"]


def make_hourly(countries=("HU", "DE"), start="2024-01-01", days=21, base=None):
    """Hourly rows shaped like electricity_hourly.parquet (only the columns used)."""
    base = base or {"HU": 5000.0, "DE": 50000.0}
    frames = []
    for c in countries:
        t = pd.date_range(start, periods=24 * days, freq="h")
        # Daily shape: higher during the day; weekends 20% lower
        shape = 1 + 0.2 * np.sin((t.hour - 6) / 24 * 2 * np.pi)
        shape = shape * np.where(t.day_of_week >= 5, 0.8, 1.0)
        frames.append(pd.DataFrame({
            "country": c,
            "timestamp_local": t,
            "weekday": pd.Categorical(t.day_name(), demand.WEEKDAYS),
            "hour": t.hour,
            "season": pd.Categorical(["Winter"] * len(t), style.SEASON_ORDER),
            "load_mw": base[c] * shape,
        }))
    df = pd.concat(frames, ignore_index=True)
    for col, share in GEN_SHARES.items():
        df[col] = share * df["load_mw"]
    df["renewable_mw"] = df[RENEWABLE_COLS].sum(axis=1)
    df["renewable_share_load_pct"] = 100 * df["renewable_mw"] / df["load_mw"]
    df["residual_load_mw"] = df["load_mw"] - df["solar_mw"] - df["wind_onshore_mw"] - df["wind_offshore_mw"]
    df["year"] = df["timestamp_local"].dt.year
    # Price: 100 EUR/MWh minus a midday dip that goes negative at noon
    df["price_eur_mwh"] = 100 - 120 * np.clip(np.cos((df["hour"] - 12) / 24 * 2 * np.pi), 0, None) ** 4
    df["is_negative_price"] = df["price_eur_mwh"] < 0
    return df


def test_relative_is_auto_for_several_countries():
    one = make_hourly(countries=("HU",))
    two = make_hourly()
    assert demand.hour_weekday_data(one)[1] is False
    assert demand.hour_weekday_data(two)[1] is True


def test_relative_scale_averages_to_100():
    cells, _ = demand.hour_weekday_data(make_hourly(), relative=True)
    # Synthetic weeks are complete, so the mean over all cells is the overall mean
    assert cells["value"].mean() == pytest.approx(100, rel=1e-6)


def test_absolute_sums_countries_in_gw():
    df = make_hourly()
    cells, _ = demand.hour_weekday_data(df, relative=False)
    expected = df.groupby("timestamp_local")["load_mw"].sum().mean() / 1000
    assert cells["value"].mean() == pytest.approx(expected, rel=1e-6)


def test_daily_energy_not_undercounted_by_missing_hours():
    df = make_hourly(countries=("HU",), days=3)
    full, _ = demand.daily_data(df, relative=False)
    df.loc[df["timestamp_local"].between("2024-01-02 10:00", "2024-01-02 15:00"), "load_mw"] = np.nan
    gap, _ = demand.daily_data(df, relative=False)
    # 6 missing peak hours: mean x hours stays within 10% of the true value,
    # while a plain sum would lose a quarter of the day
    true, plain_sum = full["value"].iloc[1], full["value"].iloc[1] * 18 / 24
    assert gap["value"].iloc[1] == pytest.approx(true, rel=0.10)
    assert abs(gap["value"].iloc[1] - true) < abs(plain_sum - true) / 2
    # A complete day equals the plain sum of hourly MWh
    day0 = df[df["timestamp_local"].dt.day == 1]["load_mw"].sum() / 1000
    assert full["value"].iloc[0] == pytest.approx(day0)


def test_calendar_week_columns():
    days, _ = demand.daily_data(make_hourly(countries=("HU",), days=14))
    # 2024-01-01 is a Monday: first week is column 0, 8 January is column 1
    assert days.loc[days["date"] == "2024-01-01", "week"].item() == 0
    assert days.loc[days["date"] == "2024-01-08", "week"].item() == 1


@pytest.mark.parametrize("chart", [
    demand.hour_weekday_heatmap,
    demand.calendar_heatmap,
    demand.seasonal_profile,
])
@pytest.mark.parametrize("countries", [("HU",), ("HU", "DE")])
def test_charts_render(chart, countries):
    obj = chart(make_hourly(countries=countries))
    hv.render(obj, backend="bokeh")


def test_project_palettes_pass():
    assert palette_check.check_project()


# -- Q3 renewables -------------------------------------------------------------

def test_mix_auto_frequency():
    assert renewables.generation_mix_data(make_hourly(days=7))[1] == "h"
    assert renewables.generation_mix_data(make_hourly(days=60))[1] == "D"
    assert renewables.generation_mix_data(make_hourly(days=200))[1] == "W-MON"


def test_mix_sums_countries_and_shares_add_to_100():
    df = make_hourly(days=7)
    mix, _ = renewables.generation_mix_data(df, freq="h")
    expected_load = df.groupby("timestamp_local")["load_mw"].sum().to_numpy() / 1000
    assert np.allclose(mix["load"], expected_load)
    share, _ = renewables.generation_mix_data(df, freq="D", as_share=True)
    assert np.allclose(share[style.SOURCE_ORDER].sum(axis=1), 100)
    # 60% of load is renewable; total generation is 100% of load here
    assert np.allclose(share["renewable"], 60)


def test_monthly_share_is_energy_weighted():
    m = renewables.monthly_share_data(make_hourly(days=60))
    assert np.allclose(m["share"], 60)


def test_daily_coverage_relative_and_residual():
    prof, relative = renewables.daily_coverage_data(make_hourly())
    assert relative is True
    assert np.allclose(prof["renewable"], 0.6 * prof["load"])
    assert np.allclose(prof["residual"], prof["load"] - prof["renewable"])


def test_coverage_duration_is_sorted_descending():
    df = make_hourly(countries=("HU",))
    df["renewable_share_load_pct"] = np.linspace(0, 150, len(df))
    d = renewables.coverage_duration_data(df)
    assert d["share"].is_monotonic_decreasing
    # One third of hours (100 to 150) are fully covered
    assert d["hours_full"].iloc[0] == pytest.approx(100 / 3, abs=0.5)


@pytest.mark.parametrize("chart", [
    lambda df: renewables.generation_mix(df),
    lambda df: renewables.generation_mix(df, as_share=True),
    renewables.renewable_share_heatmap,
    renewables.daily_coverage,
    renewables.coverage_duration,
])
@pytest.mark.parametrize("countries", [("HU",), ("HU", "DE")])
def test_renewable_charts_render(chart, countries):
    hv.render(chart(make_hourly(countries=countries)), backend="bokeh")


# -- Q4 prices -------------------------------------------------------------------

def test_negative_prices_cluster_at_midday():
    out, _ = prices.negative_price_data(make_hourly(countries=("HU",)), by="hour")
    by_hour = out.set_index("col")["negative_pct"]
    assert by_hour[12] == 100 and by_hour[0] == 0


def test_price_summary_negative_share():
    df = make_hourly(countries=("HU",))
    s = prices.price_summary_data(df)
    assert s["negative_pct"].iloc[0] == pytest.approx(100 * df["is_negative_price"].mean())
    assert s["median"].iloc[0] == pytest.approx(df["price_eur_mwh"].median())


def test_price_duration_sorted_and_ends_negative():
    d = prices.price_duration_data(make_hourly(countries=("HU",)))
    assert d["price"].is_monotonic_decreasing
    assert d["price"].iloc[-1] < 0 < d["price"].iloc[0]


def test_share_price_bins_drop_sparse_and_follow_price():
    df = make_hourly(countries=("HU",), days=60)
    # Make renewable share follow the price dip: more renewables, lower price
    df["renewable_share_load_pct"] = 100 - df["price_eur_mwh"]
    pts, lines = prices.share_price_data(df)
    assert len(pts) == len(df)
    assert (lines["hours"] >= 20).all()
    assert lines.sort_values("bin")["median"].is_monotonic_decreasing


def test_residual_load_is_relative_to_mean_load():
    pts, _ = prices.share_price_data(make_hourly(), x="residual_load")
    # Residual = 60% of load here (load minus 40% wind and solar)
    assert pts["x"].mean() == pytest.approx(60, rel=0.01)


@pytest.mark.parametrize("chart", [
    prices.price_distribution,
    lambda df: prices.price_distribution(df, by="year"),
    prices.price_duration_curve,
    prices.share_price,
    lambda df: prices.share_price(df, x="residual_load"),
    prices.negative_price_heatmap,
    lambda df: prices.negative_price_heatmap(df, by="month"),
])
@pytest.mark.parametrize("countries", [("HU",), ("HU", "DE")])
def test_price_charts_render(chart, countries):
    hv.render(chart(make_hourly(countries=countries, days=60)), backend="bokeh")


# -- Q2 countries ----------------------------------------------------------------

POP = pd.DataFrame({"country": ["HU", "DE"], "year": [2024, 2024], "population": [10e6, 80e6]})


def test_country_metrics_annualise_consumption():
    df = make_hourly(days=21)
    m = countries.country_metrics(df).set_index("country")
    # Annualised TWh = mean MW x hours per year / 1e6, independent of selection length
    expected = df.groupby("country")["load_mw"].mean() * countries.HOURS_PER_YEAR / 1e6
    assert np.allclose(m.loc[["HU", "DE"], "consumption_twh"], expected[["HU", "DE"]])
    assert np.allclose(m["renewable_share"], 60)


def test_per_capita_only_with_population():
    df = make_hourly(days=21)
    assert "per_capita_mwh" not in countries.country_metrics(df).columns
    m = countries.country_metrics(df, POP).set_index("country")
    assert m.loc["HU", "per_capita_mwh"] == pytest.approx(m.loc["HU", "consumption_twh"] * 1e6 / 10e6)
    with pytest.raises(ValueError, match="population"):
        countries.country_ranking(df, "per_capita_mwh")


def test_country_mix_shares_add_to_100():
    long, renew = countries.country_mix_data(make_hourly())
    assert np.allclose(long.groupby("country")["share"].sum(), 100)
    assert np.allclose(renew, 60)


@pytest.mark.parametrize("chart", [
    countries.country_ranking,
    lambda df: countries.country_ranking(df, "consumption_twh"),
    lambda df: countries.country_ranking(df, "per_capita_mwh", population=POP),
    lambda df: countries.country_ranking(df, compare_years=True),
    countries.country_mix,
])
@pytest.mark.parametrize("countries_", [("HU",), ("HU", "DE")])
def test_country_charts_render(chart, countries_):
    hv.render(chart(make_hourly(countries=countries_)), backend="bokeh")


def test_dumbbell_compares_first_and_last_year():
    df = make_hourly(start="2023-12-20", days=21)  # spans 2023 and 2024
    hv.render(countries.country_ranking(df, compare_years=True), backend="bokeh")


@pytest.mark.skipif(not countries.BORDERS_FILE.exists(), reason="run src/data/download_gisco.py first")
def test_country_map_renders():
    fig = hv.render(countries.country_map(make_hourly()), backend="bokeh")
    assert fig.height == countries.MAP_HEIGHT + 40
