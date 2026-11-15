"""Open a single chart in the browser, with the same settings as the gallery.

Run from anywhere:
    python src/viz/preview.py                   # list the available charts
    python src/viz/preview.py country_map       # open one chart
    python src/viz/preview.py country_map --save map.html   # save instead of opening

As in the gallery, Spain is left out of the price charts unless --all-prices
is given (its price data is licensed for private and internal use only).
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import holoviews as hv  # noqa: E402
import pandas as pd  # noqa: E402
import panel as pn  # noqa: E402

from src.viz import countries, demand, prices, renewables, style  # noqa: E402

RESTRICTED_PRICE_COUNTRIES = ["ES"]


def _hu(df):
    return df[df.country == "HU"]


def _de(df):
    return df[df.country == "DE"]


def _y25(df):
    return df[df.year == 2025]


def _de_week(df):
    de = _de(df)
    return de[(de.timestamp_local >= "2024-06-03") & (de.timestamp_local < "2024-06-10")]


def _de_summer(df):
    de = _de(df)
    return de[de.season == "Summer"]


# Chart name -> function(all data, price data) returning the chart
CHARTS = {
    # Q1 Demand
    "hour_weekday_heatmap": lambda df, pdf: demand.hour_weekday_heatmap(
        _hu(df), title="Hungary: mean load by hour and weekday"),
    "calendar_heatmap": lambda df, pdf: demand.calendar_heatmap(
        _hu(df), title="Hungary: daily electricity consumption"),
    "seasonal_profile": lambda df, pdf: demand.seasonal_profile(
        df, title="All countries: daily load profile by season"),
    # Q2 Countries
    "country_map": lambda df, pdf: countries.country_map(df),
    "country_ranking": lambda df, pdf: countries.country_ranking(df, "consumption_twh"),
    "renewable_share_2022_vs_2025": lambda df, pdf: countries.country_ranking(df, compare_years=True),
    "country_mix": lambda df, pdf: countries.country_mix(df),
    # Q3 Renewables
    "generation_mix_week": lambda df, pdf: renewables.generation_mix(
        _de_week(df), title="Germany, 3 to 9 June 2024: generation mix and load (hourly)"),
    "generation_mix_share": lambda df, pdf: renewables.generation_mix(
        df, as_share=True, title="All countries: generation mix as share (weekly)"),
    "renewable_share_heatmap": lambda df, pdf: renewables.renewable_share_heatmap(df),
    "daily_coverage": lambda df, pdf: renewables.daily_coverage(
        _de_summer(df), title="Germany, summer: renewables vs demand"),
    "coverage_duration": lambda df, pdf: renewables.coverage_duration(
        _y25(df), title="2025: how often do renewables cover demand?"),
    # Q4 Prices
    "price_distribution": lambda df, pdf: prices.price_distribution(
        _y25(pdf), title="2025: price distribution by country"),
    "price_distribution_by_year": lambda df, pdf: prices.price_distribution(pdf, by="year"),
    "share_price_germany": lambda df, pdf: prices.share_price(
        _y25(_de(df)), title="Germany 2025: renewable share vs price"),
    "share_price": lambda df, pdf: prices.share_price(
        _y25(pdf), title="2025: renewable share vs price"),
    "residual_load_price": lambda df, pdf: prices.share_price(
        _y25(pdf), x="residual_load", title="2025: residual load vs price"),
    "price_duration_curve": lambda df, pdf: prices.price_duration_curve(
        _y25(pdf), title="2025: price duration curve"),
    "negative_price_heatmap": lambda df, pdf: prices.negative_price_heatmap(
        _y25(pdf), title="2025: negative prices by hour of day"),
    "negative_price_by_month": lambda df, pdf: prices.negative_price_heatmap(pdf, by="month"),
}


def main():
    parser = argparse.ArgumentParser(description="Open a single chart in the browser.")
    parser.add_argument("chart", nargs="?", help="chart name (run without arguments to list them)")
    parser.add_argument("--save", metavar="FILE", help="save the chart as an HTML file instead of opening it")
    parser.add_argument("--all-prices", action="store_true",
                        help="include Spain in the price charts (local use only)")
    args = parser.parse_args()

    if args.chart not in CHARTS:
        if args.chart:
            print(f"Unknown chart: {args.chart}\n")
        print("Available charts:")
        for name in CHARTS:
            print(f"  {name}")
        sys.exit(0 if args.chart is None else 1)

    pn.extension(theme="dark", raw_css=[f"body {{ background: {style.PAGE}; }}"])
    hv.extension("bokeh")
    style.apply()

    df = pd.read_parquet(REPO_ROOT / "data" / "processed" / "electricity_hourly.parquet")
    pdf = df if args.all_prices else df[~df.country.isin(RESTRICTED_PRICE_COUNTRIES)]

    chart = pn.panel(CHARTS[args.chart](df, pdf))
    page = pn.Column(chart, styles={"background": style.PAGE, "padding": "16px"},
                     sizing_mode="stretch_width")
    if args.save:
        page.save(args.save, title=args.chart, resources="inline")
        print(f"saved {args.save}")
    else:
        page.show(title=args.chart)


if __name__ == "__main__":
    main()
