"""Q4 charts: do hours with high renewable generation have lower (or
negative) prices, and does this differ by country?

Same conventions as the other chart modules: each function takes the
filtered hourly DataFrame and returns a HoloViews object; aggregation is in
`*_data` helpers.

Prices are day-ahead prices in EUR/MWh per bidding zone (Denmark: mean of
DK1 and DK2, see docs/data_preparation.md). They range from -500 to almost
3,000 EUR/MWh, but 99% of hours lie between about -3 and 525. Charts that
show the price axis cut it at the 0.5th and 99.5th percentile of the
selection so the bulk of the distribution stays readable; the subtitle says
so, and tooltips show exact values. Negative prices are real (oversupply),
not errors.
"""

import holoviews as hv
import numpy as np
import pandas as pd

from . import style
from .utils import MONTHS, duration_curve, for_hv

PRICE = hv.Dimension("price", label="Day-ahead price", unit="EUR/MWh")
CLIP = (0.5, 99.5)  # percentiles for the price axis
FILL = "#5598e7"    # neutral single-hue fill (sequential ramp step) for one-series charts
# Violin shapes come from a kernel density estimate, which is slow on all
# 245k hours (about 10 s). A fixed random sample per group gives the same
# shape in well under a second; medians and tooltips still use every hour.
VIOLIN_SAMPLE = 5000


def _price_range(prices, pad=0.05):
    lo, hi = np.nanpercentile(prices, CLIP)
    span = hi - lo
    return lo - pad * span, hi + pad * span


CLIP_NOTE = "(axis shows middle 99% of hours)"


def _country_order(df):
    """Country codes ordered from cheapest to most expensive median price."""
    med = df.groupby("country", observed=True)["price_eur_mwh"].median().sort_values()
    return [c for c in med.index.astype(str) if c in style.COUNTRY_NAMES]


# -- price distributions ---------------------------------------------------------

def price_summary_data(df, by="country"):
    """Median, mean, interquartile range and share of negative-price hours."""
    g = df.groupby(by, observed=True)["price_eur_mwh"]
    s = pd.DataFrame({
        "median": g.median(),
        "mean": g.mean(),
        "q25": g.quantile(0.25),
        "q75": g.quantile(0.75),
        "negative_pct": df.groupby(by, observed=True)["is_negative_price"].mean() * 100,
        "hours": g.count(),
    }).reset_index()
    return s


def price_distribution(df, by="country", title=None):
    """Violin of hourly prices per country (cheapest median left) or per
    year. Width shows how often each price occurs; the white dot is the
    median. Country is identified by position, so one fill colour is enough.
    by="year" pools the selected countries to show the 2022 crisis and the
    move towards cheap and negative hours since."""
    d = df[[by, "price_eur_mwh"]].dropna().copy()
    if by == "country":
        order = _country_order(df)
        d["group"] = d["country"].astype(str).map(style.COUNTRY_NAMES)
        labels = [style.COUNTRY_NAMES[c] for c in order]
        xlabel = ""
    else:
        d["group"] = d[by].astype(str)
        labels = sorted(d["group"].unique())
        xlabel = by.capitalize()
    d = for_hv(d.rename(columns={"price_eur_mwh": "price"}), "group")
    ylim = _price_range(d["price"])
    # Categorical axes follow row order, so sort rows into the display order
    rank = {g: i for i, g in enumerate(labels)}
    shape = d.sample(frac=1, random_state=0).groupby("group").head(VIOLIN_SAMPLE)
    shape = shape.sort_values("group", key=lambda s: s.map(rank), kind="stable")

    summary = price_summary_data(df, by)
    summary["group"] = (summary[by].astype(str).map(style.COUNTRY_NAMES) if by == "country"
                        else summary[by].astype(str))
    summary = for_hv(summary.sort_values("group", key=lambda s: s.map(rank)), "group")

    title = title or ("Price distribution by country" if by == "country" else "Price distribution by year")
    violin = hv.Violin(shape, kdims=[hv.Dimension("group", label=xlabel or "Country")],
                       vdims=[PRICE.clone(range=ylim)]).opts(
        violin_fill_color=FILL, violin_fill_alpha=0.85, violin_line_color=style.SURFACE,
        inner=None, bandwidth=0.05, cut=0,
    )
    medians = hv.Scatter(summary, "group", ["median", "mean", "q25", "q75", "negative_pct"]).opts(
        color=style.TEXT, size=7, line_color=style.SURFACE, line_width=1.5,
        tools=["hover"],
        hover_tooltips=[("", "@group"), ("Median", "@median{0,0.0} EUR/MWh"),
                        ("Middle 50%", "@q25{0,0} to @q75{0,0} EUR/MWh"),
                        ("Mean", "@mean{0,0.0} EUR/MWh"), ("Negative-price hours", "@negative_pct{0.0}%")],
    )
    zero = hv.HLine(0).opts(color=style.BASELINE, line_width=1)
    return (zero * violin * medians).opts(
        title=f"{title} {CLIP_NOTE}",
        xlabel=xlabel,
        ylabel="Day-ahead price (EUR/MWh)",
        ylim=ylim,
        show_legend=False,
    )


# -- price duration curve ------------------------------------------------------

def price_duration_data(df):
    out = duration_curve(df, "price_eur_mwh").rename(columns={"value": "price"})
    neg = df.groupby("country", observed=True)["is_negative_price"].mean() * 100
    out["negative_pct"] = out["country"].map(neg).astype(float)
    out["country_name"] = out["country"].astype(str).map(style.COUNTRY_NAMES)
    return for_hv(out, "country", "country_name")


def price_duration_curve(df, title="Price duration curve"):
    """Hourly prices per country sorted from highest to lowest. The right
    end below zero is the share of hours with negative prices; a flatter
    curve means more stable prices."""
    d = price_duration_data(df)
    zero = hv.HLine(0).opts(color=style.TEXT_MUTED, line_dash="dotted", line_width=1)
    curves = []
    for code in style.COUNTRY_ORDER:
        c = d[d["country"] == code]
        if c.empty:
            continue
        name = style.COUNTRY_NAMES[code]
        curves.append(hv.Curve(c, "pct_hours", [PRICE, "negative_pct"], label=name).opts(
            color=style.COUNTRY_COLORS[code],
            tools=["hover"],
            hover_tooltips=[("", name), ("", "In @pct_hours{0}% of hours the price was"),
                            ("", "at least @price{0,0.0} EUR/MWh"),
                            ("Negative-price hours", "@negative_pct{0.0}%")],
        ))
    return hv.Overlay([zero, *curves]).opts(
        title=f"{title} {CLIP_NOTE}",
        xlabel="Share of hours (%)",
        ylabel="Day-ahead price (EUR/MWh)",
        xlim=(0, 100),
        ylim=_price_range(df["price_eur_mwh"]),
        legend_position="right",
    )


# -- renewables (or residual load) vs price -----------------------------------

X_OPTIONS = {
    "renewable_share": ("renewable_share_load_pct", "Renewable share of load (%)"),
    "residual_load": ("residual_load_pct", "Residual load (% of country's average load)"),
}
BIN_WIDTH = 5  # percentage points per bin for the median lines


def share_price_data(df, x="renewable_share"):
    """Hourly x/price pairs plus, per country, the median and interquartile
    range of price in BIN_WIDTH-wide bins of x (bins with < 20 hours dropped).

    x="residual_load": load minus wind and solar, as % of the country's mean
    load, so countries of different size share one axis. This is the
    merit-order view: the more demand is left after wind and solar, the more
    expensive plants set the price.
    """
    col, _ = X_OPTIONS[x]
    d = df[["country", "price_eur_mwh", "renewable_share_load_pct", "residual_load_mw", "load_mw"]].copy()
    mean_load = d.groupby("country", observed=True)["load_mw"].transform("mean")
    d["residual_load_pct"] = 100 * d["residual_load_mw"] / mean_load
    pts = d[["country", col, "price_eur_mwh"]].dropna().rename(columns={col: "x", "price_eur_mwh": "price"})

    pts["bin"] = (np.floor(pts["x"] / BIN_WIDTH) * BIN_WIDTH + BIN_WIDTH / 2)
    g = pts.groupby(["country", "bin"], observed=True)["price"]
    lines = pd.DataFrame({"median": g.median(), "q25": g.quantile(0.25), "q75": g.quantile(0.75),
                          "hours": g.count()}).reset_index()
    lines = lines[lines["hours"] >= 20]
    lines["country_name"] = lines["country"].astype(str).map(style.COUNTRY_NAMES)
    return pts, for_hv(lines, "country", "country_name")


def share_price(df, x="renewable_share", title=None):
    """Hexbin density of all selected hours (where most hours fall) with one
    median-price line per country on top. A falling line means hours with
    more renewables are cheaper; a steeper line means a stronger effect."""
    pts, lines = share_price_data(df, x)
    _, xlabel = X_OPTIONS[x]
    title = title or ("Renewable share vs price" if x == "renewable_share" else "Residual load vs price")
    xlim = tuple(np.nanpercentile(pts["x"], CLIP))
    ylim = _price_range(pts["price"])
    inside = pts[pts["x"].between(*xlim) & pts["price"].between(*ylim)]

    density = hv.HexTiles(inside, ["x", "price"]).opts(
        cmap=["#262625", "#303A4A", *style.SEQUENTIAL[:5]],
        gridsize=40, min_count=1, line_width=0, alpha=0.9,
        colorbar=False, tools=[],
    )
    countries = [c for c in style.COUNTRY_ORDER if c in set(lines["country"])]
    single = len(countries) == 1
    layers = [density, hv.HLine(0).opts(color=style.BASELINE, line_width=1)]
    for code in countries:
        c = lines[lines["country"] == code]
        name = style.COUNTRY_NAMES[code]
        color = style.TEXT if single else style.COUNTRY_COLORS[code]
        if single:  # one country: show the spread too
            layers.append(hv.Area(c, "bin", ["q25", "q75"], label="Middle 50% of hours").opts(
                color=style.TEXT, fill_alpha=0.15, line_width=0))
        layers.append(hv.Curve(c, hv.Dimension("bin", label=xlabel),
                               [hv.Dimension("median", label="Median price", unit="EUR/MWh"),
                                "q25", "q75", "hours"], label=name).opts(
            color=color, line_width=style.LINE_WIDTH + (0.5 if single else 0),
            tools=["hover"],
            hover_tooltips=[("", name), (xlabel.split(" (")[0], "@bin{0}%"),
                            ("Median price", "@median{0,0.0} EUR/MWh"),
                            ("Middle 50%", "@q25{0,0} to @q75{0,0} EUR/MWh"), ("Hours", "@hours{0,0}")],
        ))
    return hv.Overlay(layers).opts(
        title=f"{title} (shading: number of hours; lines: median price)",
        xlabel=xlabel,
        ylabel="Day-ahead price (EUR/MWh)",
        xlim=xlim,
        ylim=ylim,
        legend_position="right",
        show_legend=not single,
    )


# -- negative-price frequency --------------------------------------------------

def negative_price_data(df, by="hour"):
    """Share of hours with a negative price per country and hour of day
    (by="hour") or month (by="month")."""
    d = df[["country", "timestamp_local", "hour", "is_negative_price"]].copy()
    if by == "month":
        d["month"] = d["timestamp_local"].dt.to_period("M").dt.to_timestamp()
        first = d["month"].min()
        d["col"] = (d["month"].dt.year - first.year) * 12 + d["month"].dt.month - first.month
        d["col_label"] = d["month"].dt.strftime("%b %Y")
    else:
        d["col"] = d["hour"]
        d["col_label"] = d["hour"].map(lambda h: f"{h:02d}:00")
    g = d.groupby(["country", "col", "col_label"], observed=True)["is_negative_price"]
    out = pd.DataFrame({"negative_pct": g.mean() * 100, "negative_hours": g.sum()}).reset_index()
    out["country_name"] = out["country"].astype(str).map(style.COUNTRY_NAMES)
    return for_hv(out, "country", "country_name", "col_label"), d


def negative_price_heatmap(df, by="hour", title=None):
    """How often prices go negative, per country. by="hour": the midday
    cluster shows it is a solar effect; by="month": the trend since 2022."""
    out, d = negative_price_data(df, by)
    totals = out.groupby("country_name")["negative_hours"].sum().sort_values(ascending=False)
    order = totals.index.tolist()
    if by == "month":
        first = d["month"].min()
        ticks = [(c, str(first.year + (first.month - 1 + c) // 12))
                 for c in sorted(out["col"].unique()) if (first.month - 1 + c) % 12 == 0]
        if len(ticks) < 2:
            ticks = [(c, MONTHS[(first.month - 1 + c) % 12]) for c in sorted(out["col"].unique())]
        xlabel = ""
    else:
        ticks = [(h, f"{h:02d}") for h in range(0, 24, 3)]
        xlabel = "Hour of day (local time)"
    title = title or ("Negative prices by hour of day" if by == "hour" else "Negative prices by month")
    share = hv.Dimension("negative_pct", label="Hours with negative price", unit="%")
    return hv.HeatMap(out, kdims=["col", "country_name"], vdims=[share, "negative_hours", "col_label"]).opts(
        title=title,
        cmap=style.SEQUENTIAL,
        clim=(0, max(1.0, float(out["negative_pct"].max()))),
        colorbar=True,
        clabel="Hours with negative price (%)",
        xlabel=xlabel,
        ylabel="",
        xticks=ticks,
        height=60 + 34 * len(order),
        tools=["hover"],
        hover_tooltips=[("", "@country_name, @col_label"),
                        ("Negative-price hours", "@negative_pct{0.0}% (@negative_hours{0} hours)")],
    ).redim.values(country_name=order[::-1])
