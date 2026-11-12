# Chart Guide

How to use the chart functions in `src/viz/` in the Panel dashboard. Design decisions (colours, chart choices) are in [visual_style.md](visual_style.md); data columns are in [data_contract.md](data_contract.md).

## Quick start

```python
import sys
from pathlib import Path

import holoviews as hv
import pandas as pd
import panel as pn

ROOT = Path(__file__).resolve().parents[1]      # repo root, from dashboard/app.py
sys.path.insert(0, str(ROOT))
from src.viz import countries, demand, prices, renewables, style

pn.extension(theme="dark")
hv.extension("bokeh")
style.apply()                                     # once, after the extensions

df = pd.read_parquet(ROOT / "data/processed/electricity_hourly.parquet")

country = pn.widgets.MultiChoice(name="Countries", options=style.COUNTRY_ORDER, value=["HU"])
years = pn.widgets.IntRangeSlider(name="Years", start=2022, end=2025, value=(2022, 2025))

def selection(codes, yrs):
    return df[df["country"].isin(codes) & df["year"].between(*yrs)]

heatmap = pn.bind(lambda c, y: demand.hour_weekday_heatmap(selection(c, y)), country, years)
pn.Column(pn.Row(country, years), heatmap).servable()
```

Then run `panel serve dashboard/app.py --show`.

## Conventions (all chart functions)

- **Input:** the hourly DataFrame from `electricity_hourly.parquet`, already filtered by the dashboard (countries, date range, season, ...). Charts never filter by themselves.
- **Output:** a HoloViews object, ready for `pn.pane.HoloViews` or `pn.bind`. Every chart has hover tooltips; zoom and pan come from the Bokeh toolbar.
- **`title=`** overrides the default title on every chart.
- **`relative=`** (charts that aggregate load across countries): `None` (default) shows GW for one country and "% of each country's average" for several, so Germany does not drown out Denmark. Force with `True` / `False`.
- **`*_data` functions** return the aggregated table behind a chart. Use them for KPI cards and tables instead of recomputing.
- **Speed:** every chart renders in under 0.6 s on the full data (4 years, 7 countries), so it is fine to rebuild them on every filter change.
- **Linked axes:** Panel links axes that share a dimension name across plots (e.g. all price charts share `price`). That is what you want when all charts show the same selection. If two charts on one page show different selections, add `.opts(shared_axes=False)` to one of them.
- **Colours** follow the entity, never its rank: a filter that removes countries does not repaint the others.

## Q1: When is demand high? (`demand`)

| Function | Shows | Options |
|---|---|---|
| `hour_weekday_heatmap(df)` | Mean load for each weekday × hour: daily peak, weekend dip | `relative` |
| `calendar_heatmap(df)` | One calendar row per year, one cell per day, shared colour scale: seasons, holidays, year-to-year change | `relative` |
| `seasonal_profile(df)` | Average 24-hour load curve per season, weekday peak window (08 to 20) shaded | `relative` |

Data helpers: `hour_weekday_data`, `daily_data`, `seasonal_profile_data`.

## Q2: How do countries differ? (`countries`)

| Function | Shows | Options |
|---|---|---|
| `country_map(df)` | Choropleth of the selected countries, neighbours in gray | `metric` (below), `population` |
| `country_ranking(df)` | Countries ranked by one metric, dots on stems | `metric`, `population`, `compare_years=True` for a first-vs-last-year dumbbell |
| `country_mix(df)` | 100% bar per country: generation mix in the shared source colours | |
| `country_metrics(df)` | Table, one row per country (or `by_year=True`) | `population` |

`metric` is one of: `consumption_twh` (TWh per year, annualised so any date range compares), `mean_load_gw`, `peak_load_gw`, `renewable_share` (% of load, energy-weighted), `mean_price`, `negative_pct`, and `per_capita_mwh` (only with `population`).

**Per capita:** pass `population=` a DataFrame with columns `country`, `year`, `population`. Until the Eurostat population data exists, leave it out; asking for `per_capita_mwh` without it raises a clear error.

**Map borders:** run `python src/data/download_gisco.py` once (1.9 MB into `data/raw/gisco/`). The map has a fixed size (about 540 × 420 px) so it is never stretched.

`country_metrics` is the natural source for the KPI cards (total consumption, average price, renewable share, peak load).

## Q3: Renewables and demand (`renewables`)

| Function | Shows | Options |
|---|---|---|
| `generation_mix(df)` | Stacked generation by source with load as a dashed line; above the line = exports | `freq` (`"h"`, `"D"`, `"W-MON"`; default picks by date range), `as_share=True` for % of generation |
| `renewable_share_heatmap(df)` | Countries × months, renewable share of load | |
| `daily_coverage(df)` | Duck curve: average day, renewables stacked, load on top, gap = residual load | `relative` |
| `coverage_duration(df)` | Share of hours in which renewables covered at least X% of demand, per country | |

Data helpers: `generation_mix_data`, `monthly_share_data`, `daily_coverage_data`, `coverage_duration_data`.

Tip: `daily_coverage` is most telling with a season filter (`df[df.season == "Summer"]`).

## Q4: Renewables and prices (`prices`)

| Function | Shows | Options |
|---|---|---|
| `price_distribution(df)` | Violin of hourly prices per country (cheapest median left), median dot with summary on hover | `by="year"` pools countries per year |
| `price_duration_curve(df)` | Prices sorted high to low per country; the part below zero = negative-price hours | |
| `share_price(df)` | Hexbin of all hours + median price line per country | `x="renewable_share"` or `x="residual_load"` (merit-order view) |
| `negative_price_heatmap(df)` | Share of negative-price hours per country | `by="hour"` (midday solar effect) or `by="month"` (trend) |

Data helpers: `price_summary_data`, `price_duration_data`, `share_price_data`, `negative_price_data`.

Price axes show the middle 99% of hours (0.5th to 99.5th percentile), stated in the chart title; tooltips show exact values.

## Linked selection (`link_selections`)

The charts above aggregate the data (heatmaps, profiles, hexbins), so brushing in them cannot map back to individual hours. For linked brushing, build a sampled hourly scatter on the same DataFrame and let `hv.link_selections` filter the dashboard from it, for example:

```python
sample = df.sample(20_000, random_state=0)
scatter = hv.Points(sample, ["renewable_share_load_pct", "price_eur_mwh"]).opts(
    color=style.TEXT_MUTED, size=3, alpha=0.3, tools=["box_select", "lasso_select"])
ls = hv.link_selections.instance()
linked = ls(scatter)
# ls.filter(df) returns the selected rows; pass them to the chart functions:
mix = pn.bind(lambda _: renewables.generation_mix(ls.filter(df)), ls.param.selection_expr)
```

## Styling helpers (`style`)

- `style.apply()`: theme and defaults; call once.
- `style.PAGE`, `SURFACE`, `TEXT`, `TEXT_SECONDARY`, `TEXT_MUTED`, `GRID`, `BORDER`: colours for Panel cards and CSS.
- `style.STATUS` (`good`, `warning`, `serious`, `critical`): KPI card alerts only, always with an icon or label.
- `style.fmt_power`, `fmt_energy`, `fmt_price`, `fmt_pct`: number formats for KPI cards (e.g. `fmt_energy(512_340_000)` gives `'512.3 TWh'`).
- `style.SOURCE_COLORS`, `COUNTRY_COLORS`, `HIGHLIGHT`, `CONTEXT`: if the dashboard needs its own legend chips.

## Requirements and checks

- `pip install -r requirements.txt` (SciPy is needed for the violins).
- `pytest tests/` runs the data checks and 61 chart tests (synthetic data, no download needed; the map test is skipped until the borders are downloaded).
- `python src/viz/palette_check.py --project` re-checks the colour palettes after any colour change.
