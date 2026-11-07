"""Small helpers shared by the chart modules."""

import numpy as np
import pandas as pd

DURATION_POINTS = 201  # quantiles per curve; enough for a smooth duration curve

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def for_hv(df, *cols):
    """pandas 3 stores text as Arrow strings, which HoloViews heatmaps cannot
    reshape. Convert label columns to plain Python objects before plotting."""
    for c in cols:
        df[c] = df[c].astype(str).astype(object)
    return df


def use_relative(df, relative):
    """Default scale: absolute for one country, relative for several."""
    return df["country"].nunique() > 1 if relative is None else relative


def combine(grouped, relative):
    """Combine countries: sum absolute values, average relative %."""
    return grouped.mean() if relative else grouped.sum(min_count=1)


def duration_curve(df, column, by="country"):
    """Values of `column` sorted from highest to lowest per group, reduced to
    DURATION_POINTS quantiles. Point (pct_hours, value) means: in pct_hours %
    of hours the value was at least `value`."""
    x = np.linspace(0, 100, DURATION_POINTS)
    rows = []
    for key, g in df.groupby(by, observed=True):
        v = g[column].dropna().to_numpy()
        if v.size:
            rows.append(pd.DataFrame({by: key, "pct_hours": x, "value": np.percentile(v, 100 - x)}))
    return pd.concat(rows, ignore_index=True)


def reverse_legend(plot, element):
    """Bokeh hook: reverse legend entries so a stacked chart's legend reads
    top to bottom in the same order as the layers."""
    for legend in plot.state.legend:
        legend.items = list(reversed(legend.items))
