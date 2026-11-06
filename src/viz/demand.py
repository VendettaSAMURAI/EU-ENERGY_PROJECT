"""Q1 charts: how does electricity demand vary by hour, weekday and season?

Every chart function takes the (already filtered) hourly DataFrame from
data/processed/electricity_hourly.parquet and returns a HoloViews object, so
the dashboard can rebuild charts when filters change.

Scale (the `relative` argument):
- absolute: load in GW. With several countries the values are summed, which
  answers "how much does this group of countries use".
- relative: each country's load as % of its own average, then averaged over
  countries. This compares the *shape* of demand, so Germany (avg 53 GW) does
  not drown out Denmark (avg 4 GW).
- None (default): absolute for one country, relative for several.

Aggregation helpers (`*_data`) are separate from plotting so they can be
tested and reused (e.g. for KPI cards).
"""

import holoviews as hv
import numpy as np
import pandas as pd

from . import style
from .utils import MONTHS, combine as _combine, for_hv as _for_hv, use_relative as _use_relative

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAYS_SHORT = [d[:3] for d in WEEKDAYS]  # axis labels on heatmaps
PEAK_START, PEAK_END = 8, 20  # matches is_peak in the data contract


def _value_dim(relative, what="Mean load"):
    if relative:
        return hv.Dimension("value", label=f"{what}", unit="% of average")
    return hv.Dimension("value", label=what, unit="GW")


def _scaled_hourly(df, relative):
    """Hourly load per country: GW, or % of that country's mean load."""
    out = df[["country", "timestamp_local", "weekday", "hour", "season", "load_mw"]].copy()
    if relative:
        mean = out.groupby("country", observed=True)["load_mw"].transform("mean")
        out["value"] = 100 * out["load_mw"] / mean
    else:
        out["value"] = out["load_mw"] / 1000
    return out


# -- hour x weekday heatmap ----------------------------------------------------

def hour_weekday_data(df, relative=None):
    """Mean load per weekday and local hour (one row per cell)."""
    relative = _use_relative(df, relative)
    h = _scaled_hourly(df, relative)
    per_country = h.groupby(["country", "weekday", "hour"], observed=True)["value"].mean()
    cells = _combine(per_country.groupby(level=["weekday", "hour"], observed=True), relative)
    cells = cells.reset_index()
    cells["weekday"] = cells["weekday"].astype(str).str[:3]
    return _for_hv(cells, "weekday"), relative


def hour_weekday_heatmap(df, relative=None, title="Typical week: mean load by hour and weekday"):
    """Hour-of-day x weekday heatmap. Shows the daily peak, the lunchtime
    plateau, and how much lower weekend demand is, in one view."""
    cells, relative = hour_weekday_data(df, relative)
    vdim = _value_dim(relative)
    fmt = "{0.0}%" if relative else "{0,0.0} GW"
    return hv.HeatMap(cells, kdims=["hour", "weekday"], vdims=[vdim]).opts(
        title=title,
        cmap=style.SEQUENTIAL,
        colorbar=True,
        clabel=f"{vdim.label} ({vdim.unit})",
        invert_yaxis=True,
        xlabel="Hour of day (local time)",
        ylabel="",
        xticks=[(h, f"{h:02d}") for h in range(0, 24, 3)],
        tools=["hover"],
        hover_tooltips=[("", "@weekday, @hour{00}:00"), (vdim.label, f"@value{fmt}")],
        line_color=style.SURFACE,
        line_width=style.GAP,
    ).redim.values(weekday=WEEKDAYS_SHORT)


# -- calendar heatmap ----------------------------------------------------------

def daily_data(df, relative=None):
    """Daily consumption per local calendar day.

    Daily energy = mean hourly load x number of hours in the day. This equals
    the sum of hourly MWh on complete days, handles 23/25-hour DST days, and
    does not undercount days with missing load (e.g. the Iberian blackout,
    28 April 2025), where a plain sum would show an artificial dip.
    """
    relative = _use_relative(df, relative)
    d = df[["country", "timestamp_local", "load_mw"]].copy()
    d["date"] = d["timestamp_local"].dt.normalize()
    g = d.groupby(["country", "date"], observed=True)["load_mw"]
    energy_gwh = (g.mean() * g.size()) / 1000
    if relative:
        energy_gwh = 100 * energy_gwh / energy_gwh.groupby(level="country", observed=True).transform("mean")
    days = _combine(energy_gwh.groupby(level="date"), relative).rename("value").reset_index()

    days["year"] = days["date"].dt.year
    days["weekday"] = days["date"].dt.day_name().str[:3]
    # Column = week of the year, counted from the Monday on or before 1 January
    jan1 = pd.to_datetime(days["year"].astype(str) + "-01-01")
    first_monday = jan1 - pd.to_timedelta(jan1.dt.day_of_week, unit="D")
    days["week"] = (days["date"] - first_monday).dt.days // 7
    days["label"] = days["date"].dt.strftime("%a %d %b %Y")
    return _for_hv(days, "weekday", "label"), relative


def calendar_heatmap(df, relative=None, title="Daily electricity consumption"):
    """One calendar row per year (weeks x weekdays), shared colour scale.
    Shows seasonality, holidays (Christmas, Easter, August in France) and
    year-to-year changes such as lower demand during the 2022 energy crisis."""
    days, relative = daily_data(df, relative)
    if relative:
        vdim = hv.Dimension("value", label="Consumption", unit="% of average day")
        fmt = "{0.0}%"
    else:
        vdim = hv.Dimension("value", label="Consumption", unit="GWh")
        fmt = "{0,0} GWh"
    clim = (np.nanpercentile(days["value"], 1), np.nanpercentile(days["value"], 99))

    # Month ticks at the week column of each month's first day (approximate
    # to +-1 column across years, which is fine for orientation)
    month_ticks = [((pd.Timestamp(2024, m, 1) - pd.Timestamp(2024, 1, 1)).days // 7, MONTHS[m - 1])
                   for m in range(1, 13)]

    years = sorted(days["year"].unique())
    plots = []
    for i, year in enumerate(years):
        yd = days[days["year"] == year]
        last = i == len(years) - 1
        plots.append(hv.HeatMap(yd, kdims=["week", "weekday"], vdims=[vdim, "label"]).opts(
            title=title if i == 0 else "",
            cmap=style.SEQUENTIAL,
            clim=clim,
            colorbar=last,
            clabel=f"{vdim.label} ({vdim.unit})",
            colorbar_position="bottom",
            invert_yaxis=True,
            ylabel=str(year),
            xlabel="",
            xaxis="bottom" if last else None,
            xticks=month_ticks,
            height=150 + (60 if last else 0) + (30 if i == 0 else 0),
            tools=["hover"],
            hover_tooltips=[("", "@label"), (vdim.label, f"@value{fmt}")],
            line_color=style.SURFACE,
            line_width=1,
        ).redim.values(weekday=WEEKDAYS_SHORT))
    return hv.Layout(plots).cols(1).opts(shared_axes=False)


# -- hour-of-day profiles by season -------------------------------------------

def seasonal_profile_data(df, relative=None):
    """Mean load per season and local hour."""
    relative = _use_relative(df, relative)
    h = _scaled_hourly(df, relative)
    per_country = h.groupby(["country", "season", "hour"], observed=True)["value"].mean()
    prof = _combine(per_country.groupby(level=["season", "hour"], observed=True), relative)
    return _for_hv(prof.reset_index(), "season"), relative


def seasonal_profile(df, relative=None, title="Daily load profile by season"):
    """Average 24-hour load curve for each season, with the weekday peak
    window shaded. Winter evening peaks vs flatter summer days answer when
    demand peaks across the year."""
    prof, relative = seasonal_profile_data(df, relative)
    vdim = _value_dim(relative)
    fmt = "{0.0}%" if relative else "{0,0.0} GW"

    peak = hv.VSpan(PEAK_START, PEAK_END).opts(color=style.TEXT, alpha=0.05, line_width=0)
    peak_label = hv.Text(PEAK_START + 0.2, prof["value"].min(), "Peak hours (weekdays 08 to 20)",
                         halign="left", valign="bottom").opts(text_color=style.TEXT_MUTED, text_font_size="10px")

    curves, ends = [], []
    for season in style.SEASON_ORDER:
        s = prof[prof["season"] == season]
        if s.empty:
            continue
        color = style.SEASON_COLORS[season]
        curves.append(hv.Curve(s, "hour", vdim, label=season).opts(
            color=color,
            tools=["hover"],
            hover_tooltips=[("Season", season), ("Hour", "@hour{00}:00"), (vdim.label, f"@value{fmt}")],
        ))
        end = s.loc[s["hour"].idxmax()]
        ends.append([season, end["hour"], end["value"], color])

    # Direct labels at the line ends (the season colours need a second cue).
    # Curves often converge late in the evening, so push overlapping labels
    # apart to a minimum vertical gap while keeping their order.
    gap = 0.10 * (prof["value"].max() - prof["value"].min())
    ends.sort(key=lambda e: e[2])
    for lower, upper in zip(ends, ends[1:]):
        upper[2] = max(upper[2], lower[2] + gap)
    # Label text stays in ink; a dot in the series colour links label and line
    labels = []
    for season, h, y, color in ends:
        labels.append(hv.Points([(h + 0.45, y)]).opts(color=color, size=7, line_width=0, tools=[]))
        labels.append(hv.Text(h + 0.8, y, season, halign="left").opts(
            text_color=style.TEXT_SECONDARY, text_font_size="11px"))

    return hv.Overlay([peak, peak_label, *curves, *labels]).opts(
        title=title,
        xlabel="Hour of day (local time)",
        ylabel=f"{vdim.label} ({vdim.unit})",
        xlim=(0, 25.5),
        xticks=[(h, f"{h:02d}") for h in range(0, 24, 3)],
        show_legend=True,
        legend_position="top_left",
    )
