"""Q2 charts: how do the selected countries differ in consumption (total and
per capita) and generation mix?

Same conventions as the other chart modules: each function takes the
filtered hourly DataFrame and returns a HoloViews object; aggregation is in
`country_metrics`, which role C can also use for KPI cards.

Per capita: pass `population`, a DataFrame with columns country, year,
population (Eurostat demo_pjan, delivered by the data pipeline). Without it,
per-capita metrics are simply not offered.

Map borders: Eurostat GISCO countries 1:20M (2020), downloaded by
src/data/download_gisco.py. (c) EuroGeographics for the administrative
boundaries. The map is cropped to mainland Europe, so overseas territories
(e.g. French Guiana, Reunion, Canary Islands) are not shown; they are not in
the electricity data either, which covers the mainland bidding zones.
"""

import json
import math
from functools import lru_cache
from pathlib import Path

import holoviews as hv
import numpy as np
import pandas as pd

from . import style
from .utils import for_hv

REPO_ROOT = Path(__file__).resolve().parents[2]
BORDERS_FILE = REPO_ROOT / "data" / "raw" / "gisco" / "CNTR_RG_20M_2020_4326.geojson"
MAP_BOUNDS = (-11.0, 35.0, 32.0, 60.0)  # lon_min, lat_min, lon_max, lat_max (mainland Europe)
HOURS_PER_YEAR = 8766  # average incl. leap years, to annualise any selection
MAP_HEIGHT = 380       # px of map frame; width follows from the aspect

# metric key -> (label, unit, hover format, higher_is_better for sorting)
METRICS = {
    "consumption_twh": ("Electricity consumption", "TWh per year", "{0,0.0}"),
    "mean_load_gw": ("Average load", "GW", "{0,0.0}"),
    "peak_load_gw": ("Peak load", "GW", "{0,0.0}"),
    "per_capita_mwh": ("Consumption per person", "MWh per year", "{0.00}"),
    "renewable_share": ("Renewable share", "% of load", "{0.0}"),
    "mean_price": ("Average day-ahead price", "EUR/MWh", "{0,0.0}"),
    "negative_pct": ("Hours with negative price", "%", "{0.0}"),
}


# -- metrics ---------------------------------------------------------------------

def _metrics(g):
    hours = len(g)
    load_mwh = g["load_mw"].mean() * hours  # robust to missing hours, like daily_data
    return pd.Series({
        "hours": hours,
        "consumption_twh": load_mwh / 1e6 * HOURS_PER_YEAR / hours,
        "mean_load_gw": g["load_mw"].mean() / 1000,
        "peak_load_gw": g["load_mw"].max() / 1000,
        "renewable_share": 100 * g["renewable_mw"].sum() / g["load_mw"].sum(),
        "mean_price": g["price_eur_mwh"].mean(),
        "negative_pct": 100 * g["is_negative_price"].mean(),
    })


def country_metrics(df, population=None, by_year=False):
    """One row per country (or country and year) with the METRICS columns.

    consumption_twh is annualised (TWh per year) so selections of any length
    compare. renewable_share is energy-weighted (sum renewable / sum load).
    per_capita_mwh is added when `population` is given: annual consumption
    per year divided by that year's population, then averaged over years.
    """
    d = df.assign(country=df["country"].astype(str))  # plain keys, no categorical surprises
    keys = ["country", "year"] if by_year else ["country"]
    m = d.groupby(keys).apply(_metrics, include_groups=False).reset_index()

    if population is not None:
        pop = population[["country", "year", "population"]].assign(country=lambda p: p["country"].astype(str))
        yearly = d.groupby(["country", "year"]).apply(_metrics, include_groups=False).reset_index()
        yearly = yearly.merge(pop, on=["country", "year"], how="left")
        yearly["per_capita_mwh"] = yearly["consumption_twh"] * 1e6 / yearly["population"]
        per_capita = yearly.groupby(keys)["per_capita_mwh"].mean().rename("per_capita_mwh")
        m = m.merge(per_capita.reset_index(), on=keys, how="left")

    m["country_name"] = m["country"].map(style.COUNTRY_NAMES)
    return for_hv(m, "country", "country_name")


def _check_metric(metric, m):
    if metric not in METRICS:
        raise ValueError(f"metric must be one of {list(METRICS)}")
    if metric not in m.columns:
        raise ValueError(f"{metric} needs population data (pass population=...)")


# -- ranked dot / dumbbell chart -----------------------------------------------
# Countries sit at numeric y positions (0 = bottom) with their names as tick
# labels. HoloViews cannot overlay flipped (invert_axes) dots with unflipped
# segments, so nothing is flipped: x is always the metric.

def _ranked_frame(w, value_col):
    w = w.sort_values(value_col).reset_index(drop=True)
    w["pos"] = np.arange(len(w), dtype=float)
    return w, [(i, n) for i, n in enumerate(w["country_name"])]


def _ranking_opts(title, xlabel, yticks, xlim, **extra):
    return dict(title=title, xlabel=xlabel, ylabel="", yticks=yticks, xlim=xlim,
                ylim=(-0.6, len(yticks) - 0.4), height=80 + 42 * len(yticks), show_grid=False, **extra)


def country_ranking(df, metric="renewable_share", population=None, compare_years=False, title=None):
    """Countries ranked by one metric, highest at the top, as dots on thin
    stems (lollipop). compare_years=True draws a dumbbell from the first to
    the last year in the selection instead, showing change and level at once."""
    label, unit, fmt = METRICS[metric]
    xlabel = f"{label} ({unit})"
    x = hv.Dimension("x", label=xlabel)

    if compare_years:
        m = country_metrics(df, population, by_year=True)
        _check_metric(metric, m)
        y0, y1 = int(m["year"].min()), int(m["year"].max())
        if y0 != y1:
            w = m[m["year"].isin([y0, y1])].pivot(index="country_name", columns="year", values=metric)
            w = w.dropna().reset_index()
            w.columns = ["country_name", "start", "end"]
            w["change"] = w["end"] - w["start"]
            w, yticks = _ranked_frame(for_hv(w, "country_name"), "end")
            tips = [("", "@country_name"), (str(y0), f"@start{fmt} {unit}"),
                    (str(y1), f"@end{fmt} {unit}"), ("Change", f"@change{{+0,0.0}} {unit}")]
            stems = hv.Segments(w, ["start", "pos", "end", "pos"]).opts(color=style.BASELINE, line_width=3)
            cols = ["pos", "start", "end", "change", "country_name"]
            first = hv.Scatter(w.assign(x=w["start"]), x, cols, label=str(y0)).opts(
                color=style.CONTEXT, size=11, line_color=style.TEXT_MUTED, line_width=1,
                tools=["hover"], hover_tooltips=tips)
            last = hv.Scatter(w.assign(x=w["end"]), x, cols, label=str(y1)).opts(
                color=style.HIGHLIGHT, size=11, line_color=style.SURFACE, line_width=1.5,
                tools=["hover"], hover_tooltips=tips)
            lo, hi = float(w[["start", "end"]].min().min()), float(w[["start", "end"]].max().max())
            pad = 0.05 * (hi - lo or 1)
            return (stems * first * last).opts(**_ranking_opts(
                title or f"{label}: {y0} vs {y1}", xlabel, yticks, (lo - pad, hi + pad),
                legend_position="bottom_right"))

    m = country_metrics(df, population)
    _check_metric(metric, m)
    m, yticks = _ranked_frame(m, metric)
    m = m.rename(columns={metric: "x"})
    m["zero"] = 0.0
    m["text"] = m["x"].map(lambda v: f"{v:,.1f}")
    tips = [("", "@country_name"), (label, f"@x{fmt} {unit}")]
    stems = hv.Segments(m, ["zero", "pos", "x", "pos"]).opts(color=style.BASELINE, line_width=2)
    dots = hv.Scatter(m, x, ["pos", "country_name"]).opts(
        color=style.HIGHLIGHT, size=12, line_color=style.SURFACE, line_width=1.5,
        tools=["hover"], hover_tooltips=tips)
    labels = hv.Labels(m, ["x", "pos"], "text").opts(
        text_color=style.TEXT_SECONDARY, text_font_size="11px", text_align="left", xoffset=10)
    lo, hi = min(0.0, float(m["x"].min())), float(m["x"].max())
    return (stems * dots * labels).opts(**_ranking_opts(
        title or f"{label} by country", xlabel, yticks, (lo, hi + 0.2 * (hi - lo or 1))))


# -- generation mix per country ------------------------------------------------

def country_mix_data(df):
    """Share of each source group in total generation per country (%)."""
    gen = pd.DataFrame({"country": df["country"].astype(str)})
    for key, cols in style.SOURCE_COLUMNS.items():
        gen[key] = df[cols].sum(axis=1)
    totals = gen.groupby("country")[style.SOURCE_ORDER].sum()
    shares = 100 * totals.div(totals.sum(axis=1), axis=0)
    renew = shares[style.RENEWABLE_SOURCES].sum(axis=1)
    long = shares.reset_index().melt(id_vars="country", var_name="source", value_name="share")
    long["source_label"] = long["source"].map(style.SOURCE_LABELS)
    long["country_name"] = long["country"].map(style.COUNTRY_NAMES)
    long["twh"] = long.apply(lambda r: totals.loc[r["country"], r["source"]] / 1e6, axis=1)
    return for_hv(long, "country", "country_name", "source", "source_label"), renew


def country_mix(df, title="Generation mix by country"):
    """100% horizontal bars, one per country, in the shared source colours and
    stack order (renewables first). Sorted by renewable share, so the fossil
    and nuclear part grows towards the bottom."""
    long, renew = country_mix_data(df)
    order = [style.COUNTRY_NAMES[c] for c in renew.sort_values().index]
    labels = [style.SOURCE_LABELS[k] for k in style.SOURCE_ORDER]
    bars = hv.Bars(long, ["country_name", "source_label"], ["share", "twh"]).opts(
        stacked=True, invert_axes=True,
        cmap=dict(zip(labels, style.source_cmap())),
        line_color=style.SURFACE, line_width=style.GAP,
        tools=["hover"],
        hover_tooltips=[("", "@country_name: @source_label"), ("Share of generation", "@share{0.0}%"),
                        ("Generation", "@twh{0,0.0} TWh")],
        legend_position="right", xlabel="", ylabel="Share of generation (%)",
        title=title, height=80 + 42 * len(order), ylim=(0, 100),
    )
    return bars.redim.values(country_name=order, source_label=labels)


# -- choropleth map --------------------------------------------------------------

def _mercator_y(lat):
    """Web Mercator y in degrees-equivalent, so the map is not squashed."""
    return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


@lru_cache(maxsize=1)
def _borders():
    """Polygon rings per country inside MAP_BOUNDS, as Mercator x/y arrays."""
    if not BORDERS_FILE.exists():
        raise FileNotFoundError(f"{BORDERS_FILE} missing: run python src/data/download_gisco.py")
    gj = json.loads(BORDERS_FILE.read_text(encoding="utf-8"))
    lon0, lat0, lon1, lat1 = MAP_BOUNDS
    shapes = []
    for feat in gj["features"]:
        code = feat["properties"]["CNTR_ID"]
        geom = feat["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            outer = np.asarray(poly[0])
            cx, cy = outer[:, 0].mean(), outer[:, 1].mean()
            if not (lon0 <= cx <= lon1 and lat0 <= cy <= lat1):
                continue  # overseas parts and countries outside the frame
            rings = [np.column_stack([r[:, 0], [_mercator_y(v) for v in r[:, 1]]])
                     for r in (np.asarray(ring) for ring in poly)]
            shapes.append((code, feat["properties"]["NAME_ENGL"], rings[0], rings[1:]))
    return shapes


def country_map(df, metric="renewable_share", population=None, title=None):
    """Choropleth of one metric for the selected countries (sequential blue,
    light = high); other European countries in neutral gray for orientation."""
    label, unit, fmt = METRICS[metric]
    m = country_metrics(df, population)
    _check_metric(metric, m)
    values = dict(zip(m["country"], m[metric]))

    selected, context = [], []
    for code, name, outer, holes in _borders():
        if code in values:
            selected.append({"x": outer[:, 0], "y": outer[:, 1], "holes": [holes],
                             "value": float(values[code]), "name": name})
        else:
            context.append({"x": outer[:, 0], "y": outer[:, 1], "holes": [holes]})

    vdim = hv.Dimension("value", label=label, unit=unit)
    lo = 0.0 if metric not in ("mean_price",) else float(min(values.values())) * 0.9
    base = hv.Polygons(context).opts(color=style.GRID, line_color=style.SURFACE, line_width=0.8, tools=[])
    choro = hv.Polygons(selected, vdims=[vdim, "name"]).opts(
        color="value", cmap=style.SEQUENTIAL, clim=(lo, float(max(values.values()))),
        colorbar=True, clabel=f"{label} ({unit})",
        line_color=style.SURFACE, line_width=1.2,
        tools=["hover"], hover_tooltips=[("", "@name"), (label, f"@value{fmt} {unit}")],
    )
    lon0, lat0, lon1, lat1 = MAP_BOUNDS
    y0, y1 = _mercator_y(lat0), _mercator_y(lat1)
    frame_w = round(MAP_HEIGHT * (lon1 - lon0) / (y1 - y0))
    # Fixed size with the frame's aspect, so the map is never stretched
    # (HoloViews cannot combine a fixed aspect with a responsive width)
    return (base * choro).opts(
        title=title or f"{label} by country",
        xaxis=None, yaxis=None, show_grid=False,
        xlim=(lon0, lon1), ylim=(y0, y1),
        # Outer size = map frame + room for title (about 40 px) and colour bar
        # (about 110 px), so the frame keeps the map's aspect
        responsive=False, height=MAP_HEIGHT + 40, width=frame_w + 110,
    )
