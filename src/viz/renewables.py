"""Q3 charts: how has the renewable share evolved, and how well does
renewable generation cover demand?

Same conventions as src/viz/demand.py: each chart takes the filtered hourly
DataFrame and returns a HoloViews object; aggregation is in `*_data` helpers.

Renewable = solar, wind, hydro (run-of-river + reservoir), biomass and other
renewables, as `renewable_mw` in the data contract. Pumped storage and
batteries are storage, not renewable generation.
"""

import holoviews as hv
import numpy as np
import pandas as pd

from . import style
from .utils import MONTHS, combine, duration_curve, for_hv, reverse_legend, use_relative

RENEWABLE_LABELS = [style.SOURCE_LABELS[k] for k in style.RENEWABLE_SOURCES]


def _source_frame(df):
    """Hourly MW per display source group (sum of its data columns)."""
    out = df[["country", "timestamp_local", "hour", "season", "load_mw"]].copy()
    for key, cols in style.SOURCE_COLUMNS.items():
        out[key] = df[cols].sum(axis=1)
    return out


def _auto_freq(df):
    """Hourly for up to two weeks, daily up to ~4 months, weekly beyond."""
    span = df["timestamp_local"].max() - df["timestamp_local"].min()
    if span <= pd.Timedelta(days=14):
        return "h"
    if span <= pd.Timedelta(days=120):
        return "D"
    return "W-MON"


# -- generation mix over time ---------------------------------------------------

def generation_mix_data(df, freq=None, as_share=False):
    """Mean generation per source (GW) per time step, summed over countries.

    All seven countries are on Central European Time, so local timestamps
    align across countries and can be summed directly.
    as_share: each source as % of total generation instead of GW.
    """
    freq = freq or _auto_freq(df)
    s = _source_frame(df)
    cols = style.SOURCE_ORDER + ["load_mw"]
    total = s.groupby("timestamp_local")[cols].sum(min_count=1)
    # Mean power over each step = average GW; label steps by their start
    mix = total.resample(freq, label="left", closed="left").mean() / 1000
    mix = mix.rename(columns={"load_mw": "load"})
    if as_share:
        gen = mix[style.SOURCE_ORDER].sum(axis=1)
        mix[style.SOURCE_ORDER] = 100 * mix[style.SOURCE_ORDER].div(gen, axis=0)
    mix["renewable"] = mix[style.RENEWABLE_SOURCES].sum(axis=1)
    mix.index.name = "time"
    return mix.reset_index(), freq


def generation_mix(df, freq=None, as_share=False, title=None):
    """Stacked area of generation by source, renewables at the bottom, with
    load as a dashed line (absolute mode). Where the stack is above the load
    line the countries export; below it they import."""
    mix, freq = generation_mix_data(df, freq, as_share)
    step = {"h": "hourly", "D": "daily", "W-MON": "weekly"}.get(freq, freq)
    unit = "% of generation" if as_share else "GW"
    title = title or f"Generation mix ({step} average)"

    layers = [
        hv.Area(mix, "time", hv.Dimension(key, label=style.SOURCE_LABELS[key], unit=unit),
                label=style.SOURCE_LABELS[key]).opts(color=style.SOURCE_COLORS[key])
        for key in style.SOURCE_ORDER
    ]
    stack = hv.Area.stack(hv.Overlay(layers))

    # One invisible-hover line carries the tooltip for all layers at once
    fmt = "{0.0}%" if as_share else "{0,0.0} GW"
    tips = [("", "@time{%d %b %Y" + (" %H:%M" if freq == "h" else "") + "}")]
    tips += [(style.SOURCE_LABELS[k], f"@{k}{fmt}") for k in reversed(style.SOURCE_ORDER)]
    vdims = ["renewable", *style.SOURCE_ORDER, "load"]
    if as_share:
        tips.insert(1, ("Renewable share", "@renewable{0.0}%"))
        hover_line = hv.Curve(mix, "time", vdims).opts(alpha=0, tools=["hover"], hover_mode="vline")
        overlay = stack * hover_line
    else:
        tips.insert(1, ("Load", "@load{0,0.0} GW"))
        load = hv.Curve(mix, "time", ["load", *vdims[:-1]], label="Load").opts(
            color=style.TEXT, line_dash="dashed", line_width=style.LINE_WIDTH,
            tools=["hover"], hover_mode="vline")
        overlay = stack * load
    overlay = overlay.opts(hv.opts.Curve(hover_tooltips=tips, hover_formatters={"@time": "datetime"}))

    return overlay.opts(
        title=title,
        xlabel="",
        ylabel=f"Generation ({unit})",
        legend_position="right",
        hooks=[reverse_legend],
        **({"ylim": (0, 100)} if as_share else {}),
    )


# -- renewable share heatmap (country x month) -------------------------------

def monthly_share_data(df):
    """Renewable share of load per country and month, energy-weighted:
    sum of renewable MWh / sum of load MWh (not the mean of hourly %)."""
    d = df[["country", "timestamp_local", "renewable_mw", "load_mw"]].copy()
    d["month"] = d["timestamp_local"].dt.to_period("M").dt.to_timestamp()
    m = d.groupby(["country", "month"], observed=True)[["renewable_mw", "load_mw"]].sum().reset_index()
    m["share"] = 100 * m["renewable_mw"] / m["load_mw"].where(m["load_mw"] > 0)
    m["renewable_twh"] = m["renewable_mw"] / 1e6
    first = m["month"].min()
    m["col"] = (m["month"].dt.year - first.year) * 12 + m["month"].dt.month - first.month
    m["month_label"] = m["month"].dt.strftime("%b %Y")
    m["country_name"] = m["country"].astype(str).map(style.COUNTRY_NAMES)
    return for_hv(m, "country", "country_name", "month_label")


def renewable_share_heatmap(df, title="Renewable share of demand by month"):
    """Rows are countries (highest average share on top), columns are months.
    Shows the long-term trend and the seasonal pattern (solar summers, windy
    winters, hydro springs) for all countries in one compact view."""
    m = monthly_share_data(df)
    order = (m.groupby("country_name")["renewable_mw"].sum() / m.groupby("country_name")["load_mw"].sum()) \
        .sort_values(ascending=False).index.tolist()
    first = m["month"].min()
    year_ticks = [(c, str(first.year + (first.month - 1 + c) // 12))
                  for c in sorted(m["col"].unique()) if (first.month - 1 + c) % 12 == 0]
    if len(year_ticks) < 2:  # short range: label months instead
        year_ticks = [(c, MONTHS[(first.month - 1 + c) % 12]) for c in sorted(m["col"].unique())]

    share = hv.Dimension("share", label="Renewable share", unit="% of load")
    return hv.HeatMap(m, kdims=["col", "country_name"], vdims=[share, "month_label", "renewable_twh"]).opts(
        title=title,
        cmap=style.SEQUENTIAL,
        clim=(0, max(100, float(np.nanmax(m["share"])))),
        colorbar=True,
        clabel="Renewable share (% of load)",
        xlabel="",
        ylabel="",
        xticks=year_ticks,
        height=60 + 34 * len(order),
        tools=["hover"],
        hover_tooltips=[("", "@country_name, @month_label"),
                        ("Renewable share", "@share{0.0}% of load"),
                        ("Renewable generation", "@renewable_twh{0.00} TWh")],
    ).redim.values(country_name=order[::-1])


# -- duck curve: renewables vs demand over the day ---------------------------

def daily_coverage_data(df, relative=None):
    """Mean renewable generation per source and mean load, by local hour.

    relative: values as % of each country's own mean load (then averaged), so
    the chart compares how well renewables cover demand, not country size.
    """
    relative = use_relative(df, relative)
    s = _source_frame(df)
    cols = style.RENEWABLE_SOURCES + ["load_mw"]
    if relative:
        mean_load = s.groupby("country", observed=True)["load_mw"].transform("mean")
        s[cols] = 100 * s[cols].div(mean_load, axis=0)
    else:
        s[cols] = s[cols] / 1000
    per_country = s.groupby(["country", "hour"], observed=True)[cols].mean()
    prof = combine(per_country.groupby(level="hour"), relative).reset_index()
    prof = prof.rename(columns={"load_mw": "load"})
    prof["renewable"] = prof[style.RENEWABLE_SOURCES].sum(axis=1)
    prof["residual"] = prof["load"] - prof["renewable"]
    return prof, relative


def daily_coverage(df, relative=None, title="Renewables vs demand over the day"):
    """Average day: renewable sources stacked from the baseline, load on top.
    The gap between them is what other sources and imports must cover; the
    midday solar bulge and the evening ramp form the duck curve."""
    prof, relative = daily_coverage_data(df, relative)
    unit = "% of average load" if relative else "GW"
    fmt = "{0.0}%" if relative else "{0,0.0} GW"

    layers = [
        hv.Area(prof, "hour", hv.Dimension(k, label=style.SOURCE_LABELS[k], unit=unit),
                label=style.SOURCE_LABELS[k]).opts(color=style.SOURCE_COLORS[k])
        for k in style.RENEWABLE_SOURCES
    ]
    stack = hv.Area.stack(hv.Overlay(layers))
    tips = [("Hour", "@hour{00}:00"), ("Load", f"@load{fmt}"), ("Renewables", f"@renewable{fmt}"),
            ("Gap to cover", f"@residual{fmt}")]
    tips += [(style.SOURCE_LABELS[k], f"@{k}{fmt}") for k in reversed(style.RENEWABLE_SOURCES)]
    load = hv.Curve(prof, "hour", ["load", "renewable", "residual", *style.RENEWABLE_SOURCES],
                    label="Load").opts(color=style.TEXT, line_dash="dashed", line_width=style.LINE_WIDTH,
                                       tools=["hover"], hover_mode="vline", hover_tooltips=tips)
    return (stack * load).opts(
        title=title,
        xlabel="Hour of day (local time)",
        ylabel=f"Mean power ({unit})",
        xticks=[(h, f"{h:02d}") for h in range(0, 24, 3)],
        xlim=(0, 23),
        ylim=(0, None),
        legend_position="right",
        hooks=[reverse_legend],
    )


# -- coverage duration curve -------------------------------------------------

def coverage_duration_data(df):
    """For each country: renewable share of load in every hour, sorted from
    highest to lowest. Point (x, y) means: in x% of hours renewables covered
    at least y% of demand."""
    out = duration_curve(df, "renewable_share_load_pct").rename(columns={"value": "share"})
    full = df.groupby("country", observed=True)["renewable_share_load_pct"] \
        .apply(lambda s: 100 * (s.dropna() >= 100).mean())
    out["hours_full"] = out["country"].map(full).astype(float)
    out["country_name"] = out["country"].astype(str).map(style.COUNTRY_NAMES)
    return for_hv(out, "country", "country_name")


def coverage_duration(df, title="How often do renewables cover demand?"):
    """Duration curve of hourly renewable share per country, with the 100%
    line where renewables alone cover all demand. The x-value where a curve
    crosses 100% is the share of hours with full renewable coverage."""
    d = coverage_duration_data(df)
    ref = hv.HLine(100).opts(color=style.TEXT_MUTED, line_dash="dotted", line_width=1)
    ref_label = hv.Text(99, 100, "Renewables cover all demand", halign="right", valign="bottom").opts(
        text_color=style.TEXT_MUTED, text_font_size="10px")
    curves = []
    for code in style.COUNTRY_ORDER:
        c = d[d["country"] == code]
        if c.empty:
            continue
        name = style.COUNTRY_NAMES[code]
        curves.append(hv.Curve(c, "pct_hours", ["share", "hours_full"], label=name).opts(
            color=style.COUNTRY_COLORS[code],
            tools=["hover"],
            hover_tooltips=[("", name),
                            ("", "In @pct_hours{0}% of hours renewables covered"),
                            ("", "at least @share{0}% of demand"),
                            ("Hours fully covered", "@hours_full{0.0}%")],
        ))
    return hv.Overlay([ref, ref_label, *curves]).opts(
        title=title,
        xlabel="Share of hours (%)",
        ylabel="Renewable share of load (%)",
        xlim=(0, 100),
        ylim=(0, None),
        legend_position="right",
    )
