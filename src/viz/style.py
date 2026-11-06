"""Shared visual style for every chart in the dashboard.

One place for colours, fonts and number formats, so all panels look like one
product and a colour always means the same thing (solar is the same yellow in
every chart, which linked views depend on).

Usage in a chart function or notebook:

    import holoviews as hv
    from src.viz import style
    hv.extension("bokeh")
    style.apply()                      # once, after hv.extension / pn.extension

    df.hvplot.area(..., color=style.source_cmap(columns))

Design decisions (details for the defense in docs/visual_style.md):
- Dark theme only, matching the SaaS reference design. Colours are the dark-mode
  steps of a validated categorical palette, not light colours flipped.
- Colour encodes one thing per chart: energy source, or country, or magnitude.
- Every categorical order below passes the colour-vision-deficiency checks in
  src/viz/palette_check.py. Run `python src/viz/palette_check.py --project`
  after changing any colour or order.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette_check import oklab, oklab_to_hex  # noqa: E402

# -- surfaces and ink ----------------------------------------------------------

PAGE = "#0d0d0d"            # dashboard background behind the panels
SURFACE = "#1a1a19"         # chart / card background
TEXT = "#f0efec"            # titles, values
TEXT_SECONDARY = "#c3c2b7"  # axis titles, legend labels
TEXT_MUTED = "#898781"      # tick labels, captions
GRID = "#2c2c2a"            # hairline gridlines
BASELINE = "#383835"        # axis lines, zero lines
BORDER = "rgba(255,255,255,0.10)"

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

# -- energy sources (categorical) ----------------------------------------------
# Each source keeps a conventional hue where one exists (solar yellow, wind
# blue, hydro aqua, biomass green, gas orange). "Other" is a deliberate neutral
# gray: it bundles oil, waste, storage output and unclassified sources, so it
# should recede instead of competing with real sources.

SOURCE_COLORS = {
    "solar": "#c98500",    # yellow
    "hydro": "#199e70",    # aqua
    "wind": "#3987e5",     # blue
    "biomass": "#008300",  # green
    "coal": "#e66767",     # red
    "nuclear": "#9085e9",  # violet
    "gas": "#d95926",      # orange
    "other": "#6b6a65",    # neutral gray
}

# Stack order, bottom to top. Renewables sit on the baseline so the top of the
# renewable block reads directly as total renewable generation, and the solar
# midday bulge (duck curve) rises straight from the axis. The order is also
# what makes the palette colour-blind safe: neighbours in this list are the
# colours that touch in a stacked chart (worst pair dE 8.4, target >= 8).
SOURCE_ORDER = ["solar", "hydro", "wind", "biomass", "coal", "nuclear", "gas", "other"]
RENEWABLE_SOURCES = ["solar", "hydro", "wind", "biomass"]

SOURCE_LABELS = {
    "solar": "Solar",
    "hydro": "Hydro",
    "wind": "Wind",
    "biomass": "Biomass & other renewables",
    "coal": "Coal",
    "nuclear": "Nuclear",
    "gas": "Gas",
    "other": "Oil, storage & other",
}

# Columns in electricity_hourly.parquet that make up each display group (MW).
SOURCE_COLUMNS = {
    "solar": ["solar_mw"],
    "hydro": ["hydro_mw"],
    "wind": ["wind_onshore_mw", "wind_offshore_mw"],
    "biomass": ["biomass_mw", "other_renewables_mw"],
    "coal": ["coal_mw"],
    "nuclear": ["nuclear_mw"],
    "gas": ["gas_mw"],
    "other": ["oil_mw", "other_mw", "storage_mw"],
}

# -- countries (categorical) -------------------------------------------------
# Prefer position (axis, small multiples) or highlight over colour for
# countries: the same hues already mean energy sources elsewhere. Use these
# only when a chart really needs one colour per country (e.g. lines). They pass
# for lines/legends; for scatter plots colour at most 3 countries at once (the
# first 3 slots pass all-pairs), otherwise facet by country.

COUNTRY_ORDER = ["HU", "DE", "AT", "FR", "ES", "PL", "DK"]
COUNTRY_COLORS = dict(zip(COUNTRY_ORDER, [
    "#3987e5",  # blue
    "#d95926",  # orange
    "#199e70",  # aqua
    "#c98500",  # yellow
    "#d55181",  # magenta
    "#008300",  # green
    "#9085e9",  # violet
]))
COUNTRY_NAMES = {
    "HU": "Hungary", "DE": "Germany", "AT": "Austria", "FR": "France",
    "ES": "Spain", "PL": "Poland", "DK": "Denmark",
}

# -- seasons (categorical) ---------------------------------------------------
# For hour-of-day profiles by season. Four lines can cross anywhere, so all
# pairs matter: worst pair dE 6.9 under CVD simulation, which is only allowed
# with a second cue, so season charts must label lines directly.
SEASON_ORDER = ["Winter", "Spring", "Summer", "Autumn"]
SEASON_COLORS = dict(zip(SEASON_ORDER, ["#3987e5", "#008300", "#c98500", "#d55181"]))

# Highlight pattern: the selected item in bright ink, everything else muted.
# Neutral on purpose, so it never collides with a source or country hue.
HIGHLIGHT = TEXT
CONTEXT = "#4a4a46"

# -- continuous colour scales ------------------------------------------------
# Sequential (magnitude: demand, generation, share). One hue, blue. On a dark
# surface low values are dark (they recede into the background) and high
# values are light. The darkest step still clears 2:1 against the surface.
SEQUENTIAL = [
    "#184f95", "#1c5cab", "#256abf", "#2a78d6", "#3987e5", "#5598e7",
    "#6da7ec", "#86b6ef", "#9ec5f4", "#b7d3f6", "#cde2fb",
]


def _ramp(a, b, n):
    """n colours from a to b, interpolated in OKLab (perceptually even)."""
    la, lb = oklab(a), oklab(b)
    return [oklab_to_hex([x + (y - x) * t / (n - 1) for x, y in zip(la, lb)]) for t in range(n)]


# Diverging (sign around a meaningful zero: price vs average, residual load
# surplus/deficit). Blue below zero, red above, neutral gray at the midpoint so
# "no difference" reads as nothing. Use with symmetric limits, e.g.
# clim=(-m, m), so the gray sits exactly at zero.
DIVERGING_MID = BASELINE
DIVERGING = _ramp("#86b6ef", DIVERGING_MID, 6)[:-1] + [DIVERGING_MID] + _ramp(DIVERGING_MID, "#e66767", 6)[1:]

# Status (good / warning / serious / critical). Reserved meaning; never use as
# a series colour, and always pair with an icon or label (for KPI cards).
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}

# -- marks -------------------------------------------------------------------

LINE_WIDTH = 2
MARKER_SIZE = 8
GAP = 2               # px of surface between adjacent fills (bars, cells, stacks)
HEIGHT = 320          # default chart height in px

# -- number formats ----------------------------------------------------------


def fmt_power(mw):
    """Power: MW below 1 GW, GW above. 18543 -> '18.5 GW'."""
    return f"{mw / 1000:,.1f} GW" if abs(mw) >= 1000 else f"{mw:,.0f} MW"


def fmt_energy(mwh):
    """Energy: picks MWh / GWh / TWh. 512_340_000 -> '512.3 TWh'."""
    for unit, size in (("TWh", 1e6), ("GWh", 1e3)):
        if abs(mwh) >= size:
            return f"{mwh / size:,.1f} {unit}"
    return f"{mwh:,.0f} MWh"


def fmt_price(eur_mwh):
    return f"{eur_mwh:,.1f} EUR/MWh"


def fmt_pct(pct):
    return f"{pct:.1f}%"


# Bokeh hover formats (use in tooltips, e.g. ("Load", "@load_mw{0,0} MW"))
HOVER_MW = "{0,0} MW"
HOVER_PRICE = "{0,0.0} EUR/MWh"
HOVER_PCT = "{0.0}%"
HOVER_DATETIME = "%a %d %b %Y, %H:%M"

# -- helpers -----------------------------------------------------------------


def source_cmap(keys=None):
    """Colours for a list of source keys, in the same order (for hvplot color=)."""
    return [SOURCE_COLORS[k] for k in (keys or SOURCE_ORDER)]


def country_cmap(codes=None):
    """{code: colour}. Colour follows the country, never its rank, so a
    filter that removes countries does not repaint the remaining ones."""
    return {c: COUNTRY_COLORS[c] for c in (codes or COUNTRY_ORDER)}


# -- theme -------------------------------------------------------------------

BOKEH_THEME_JSON = {
    "attrs": {
        "Plot": {
            "background_fill_color": SURFACE,
            "border_fill_color": SURFACE,
            "outline_line_color": None,
            "min_border_left": 8, "min_border_right": 16,
            "min_border_top": 8, "min_border_bottom": 8,
        },
        "Axis": {
            "axis_line_color": BASELINE,
            "major_tick_line_color": BASELINE,
            "minor_tick_line_color": None,
            "major_label_text_color": TEXT_MUTED,
            "major_label_text_font": FONT,
            "major_label_text_font_size": "11px",
            "axis_label_text_color": TEXT_SECONDARY,
            "axis_label_text_font": FONT,
            "axis_label_text_font_size": "12px",
            "axis_label_text_font_style": "normal",
        },
        "Grid": {"grid_line_color": GRID, "grid_line_width": 1},
        "Title": {
            "text_color": TEXT,
            "text_font": FONT,
            "text_font_size": "14px",
            "text_font_style": "bold",
        },
        "Legend": {
            "background_fill_color": SURFACE,
            "background_fill_alpha": 0.85,
            "border_line_color": None,
            "label_text_color": TEXT_SECONDARY,
            "label_text_font": FONT,
            "label_text_font_size": "11px",
            "title_text_color": TEXT_SECONDARY,
            "title_text_font": FONT,
            "inactive_fill_color": SURFACE,
            "inactive_fill_alpha": 0.7,
        },
        "ColorBar": {
            "background_fill_color": SURFACE,
            "major_label_text_color": TEXT_MUTED,
            "major_label_text_font": FONT,
            "title_text_color": TEXT_SECONDARY,
            "title_text_font": FONT,
            "title_text_font_style": "normal",
            "bar_line_color": None,
            "major_tick_line_color": None,
        },
    }
}


def bokeh_theme():
    from bokeh.themes import Theme
    return Theme(json=BOKEH_THEME_JSON)


def apply():
    """Apply the dashboard style to HoloViews/hvPlot (and Panel if loaded).

    Call once after hv.extension("bokeh") or pn.extension(). Sets the Bokeh
    theme and default options for the element types we use, so chart
    functions only have to set what is specific to them.
    """
    import holoviews as hv

    theme = bokeh_theme()
    hv.renderer("bokeh").theme = theme

    # Panel's dark design ships its own Bokeh theme, which would override ours
    # inside the dashboard; point it at this one instead.
    try:
        from panel.theme import DarkTheme
        DarkTheme.bokeh_theme = theme
    except ImportError:
        pass

    opts = hv.opts
    common = dict(height=HEIGHT, responsive=True, toolbar="above", fontscale=1.0)
    hv.opts.defaults(
        opts.Curve(line_width=LINE_WIDTH, **common),
        opts.Area(line_width=0, fill_alpha=1.0, **common),
        opts.Scatter(size=MARKER_SIZE, line_color=SURFACE, line_width=1, **common),
        opts.Points(size=MARKER_SIZE, line_color=SURFACE, line_width=1, **common),
        # Missing cells (e.g. calendar days outside the year) stay blank; the
        # Bokeh default paints them white, which reads as "highest value"
        opts.HeatMap(line_color=SURFACE, line_width=GAP, cmap=SEQUENTIAL, colorbar=True,
                     clipping_colors={"NaN": "transparent"}, **common),
        opts.Bars(line_color=SURFACE, line_width=GAP, **common),
        opts.Violin(violin_line_color=SURFACE, violin_fill_color=SOURCE_COLORS["wind"], **common),
        opts.Overlay(legend_position="top_left", **common),
    )
