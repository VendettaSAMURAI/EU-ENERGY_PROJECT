"""Build a gallery page with every chart, grouped by analytical question.

Output: reports/figures/chart_gallery.html (standalone, opens in any browser,
fully interactive: hover, zoom, pan). Useful for reviewing the charts before
the dashboard exists, and as a backup for the presentation.

Run from anywhere:
    python src/viz/gallery.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import holoviews as hv  # noqa: E402
import pandas as pd  # noqa: E402
import panel as pn  # noqa: E402

from src.viz import countries, demand, prices, renewables, style  # noqa: E402

OUT = REPO_ROOT / "reports" / "figures" / "chart_gallery.html"


def section(title, text, *rows):
    header = pn.pane.Markdown(f"## {title}\n{text}", styles={"color": style.TEXT}, margin=(24, 10, 4, 10))
    return pn.Column(header, *rows, sizing_mode="stretch_width")


def solo(chart):
    # Each gallery chart shows its own selection, so do not link axes
    return chart.opts(shared_axes=False)


def main():
    pn.extension(theme="dark")
    hv.extension("bokeh")
    style.apply()

    df = pd.read_parquet(REPO_ROOT / "data" / "processed" / "electricity_hourly.parquet")
    hu, de = df[df.country == "HU"], df[df.country == "DE"]
    y25 = df[df.year == 2025]
    de_week = de[(de.timestamp_local >= "2024-06-03") & (de.timestamp_local < "2024-06-10")]

    q1 = section(
        "Q1: How does demand vary by hour, weekday and season?",
        "Hungary in GW; all seven countries as % of each country's average.",
        pn.Row(solo(demand.hour_weekday_heatmap(hu, title="Hungary: mean load by hour and weekday")),
               solo(demand.seasonal_profile(df, title="All countries: daily load profile by season"))),
        solo(demand.calendar_heatmap(hu, title="Hungary: daily electricity consumption")),
    )
    q2 = section(
        "Q2: How do the countries differ?",
        "Averages over 2022 to 2025. Per capita follows once population data is available.",
        pn.Row(solo(countries.country_map(df)), solo(countries.country_ranking(df, "consumption_twh"))),
        pn.Row(solo(countries.country_ranking(df, compare_years=True)), solo(countries.country_mix(df))),
    )
    q3 = section(
        "Q3: How has the renewable share evolved, and does it cover demand?",
        "",
        solo(renewables.generation_mix(de_week, title="Germany, 3 to 9 June 2024: generation mix and load (hourly)")),
        solo(renewables.generation_mix(df, as_share=True, title="All countries: generation mix as share (weekly)")),
        solo(renewables.renewable_share_heatmap(df)),
        pn.Row(solo(renewables.daily_coverage(de[de.season == "Summer"], title="Germany, summer: renewables vs demand")),
               solo(renewables.coverage_duration(y25, title="2025: how often do renewables cover demand?"))),
    )
    q4 = section(
        "Q4: Do hours with more renewables have lower prices?",
        "",
        pn.Row(solo(prices.price_distribution(y25, title="2025: price distribution by country")),
               solo(prices.price_distribution(df, by="year"))),
        pn.Row(solo(prices.share_price(de[de.year == 2025], title="Germany 2025: renewable share vs price")),
               solo(prices.share_price(y25, title="2025: renewable share vs price"))),
        pn.Row(solo(prices.share_price(y25, x="residual_load", title="2025: residual load vs price")),
               solo(prices.price_duration_curve(y25, title="2025: price duration curve"))),
        solo(prices.negative_price_heatmap(y25, title="2025: negative prices by hour of day")),
        solo(prices.negative_price_heatmap(df, by="month")),
    )

    intro = pn.pane.Markdown(
        "# EU Electricity Dashboard: chart gallery\n"
        "Every chart from `src/viz/`, built on `data/processed/electricity_hourly.parquet`. "
        "Hover for values; use the toolbar to zoom and pan. Data: Energy-Charts (Fraunhofer ISE), "
        "Eurostat GISCO (© EuroGeographics).",
        styles={"color": style.TEXT}, margin=(10, 10),
    )
    page = pn.Column(intro, q1, q2, q3, q4, sizing_mode="stretch_width",
                     styles={"background": style.PAGE, "padding": "16px"})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    page.save(OUT, title="Chart gallery", resources="inline")
    print(f"saved {OUT.relative_to(REPO_ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
