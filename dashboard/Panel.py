import importlib.util
import inspect
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from io import StringIO

try:
    import panel as pn
except ModuleNotFoundError:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet",
        "panel>=1.4.0", "bokeh>=3.4.0", "plotly>=5.18.0", "pandas>=2.0.0", "numpy>=1.24.0",
    ])
    import panel as pn

import numpy as np
import pandas as pd
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))

def find_project_paths():
    """Locate the project root even if this dashboard file is moved."""
    candidates = [
        HERE,
        os.path.dirname(HERE),
        os.path.dirname(os.path.dirname(HERE)),
    ]
    for root in candidates:
        viz_dir = os.path.join(root, "src", "viz")
        if os.path.isdir(viz_dir) and os.path.isfile(os.path.join(viz_dir, "choropleth_map.py")):
            return os.path.abspath(root), os.path.abspath(viz_dir)
    root = os.path.dirname(HERE)
    return os.path.abspath(root), os.path.abspath(os.path.join(root, "src", "viz"))

PROJECT_ROOT, VIZ_DIR = find_project_paths()
if VIZ_DIR not in sys.path:
    sys.path.insert(0, VIZ_DIR)

def load_viz_module(mod_name, filename):
    fpath = os.path.join(VIZ_DIR, filename)
    spec = importlib.util.spec_from_file_location(mod_name, fpath)
    if not os.path.isfile(fpath):
        raise FileNotFoundError(
            f"Visualization module not found: {fpath}. "
            "Check that the file is inside the project's src/viz folder."
        )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load visualization module from: {fpath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module

cmap = load_viz_module("choropleth_map", "choropleth_map.py")
hmap = load_viz_module("heatmap_matrix", "Heatmap matrix.py")
mtrend = load_viz_module("multitrend_list_chart", "multitrend list chart.py")
obox = load_viz_module("outlier_box_plot", "Outlier box plot.py")

# ----------------------------------------------------------------------------
# Apple Design System Tokens & Scoped Shadow-DOM Stylesheets
# ----------------------------------------------------------------------------
APPLE_BG = "#000000"
APPLE_CARD = "#1C1C1E"
APPLE_CARD_ELEVATED = "#2C2C2E"
APPLE_BORDER = "rgba(255, 255, 255, 0.10)"
APPLE_TEXT = "#F5F5F7"
APPLE_MUTED = "#8E8E93"
APPLE_BLUE = "#0A84FF"
APPLE_GREEN = "#30D158"
APPLE_AMBER = "#FFD60A"
APPLE_RED = "#FF453A"
APPLE_FONT = '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", "Segoe UI", sans-serif'

GLOBAL_CSS = f"""
.pn-busy-container,
.pn-loading::before,
.pn-loading::after {{
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
}}
body, .bk-root {{
    background-color: {APPLE_BG} !important;
    color: {APPLE_TEXT} !important;
    font-family: {APPLE_FONT} !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    letter-spacing: -0.011em;
    overflow-x: hidden;
}}
#header {{
    background: rgba(18, 18, 20, 0.96) !important;
    border-bottom: 1px solid {APPLE_BORDER} !important;
    box-shadow: none !important;
    z-index: 1005 !important;
}}
#header .title,
#header .app-title {{
    font-family: {APPLE_FONT} !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    letter-spacing: -0.015em !important;
    color: {APPLE_TEXT} !important;
    white-space: nowrap !important;
}}
#sidebar {{
    background: rgba(20, 20, 22, 0.98) !important;
    border-right: 1px solid {APPLE_BORDER} !important;
    box-sizing: border-box !important;
    overflow-x: hidden !important;
}}
#main {{
    background-color: {APPLE_BG} !important;
    padding: 16px 24px 24px 24px !important;
    box-sizing: border-box !important;
}}
.apple-bento {{
    background: {APPLE_CARD} !important;
    border: 1px solid {APPLE_BORDER} !important;
    border-radius: 22px !important;
    padding: 18px 20px !important;
    box-sizing: border-box !important;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.42) !important;
    transition: border-color 0.2s ease !important;
}}
.apple-bento:hover {{
    border-color: rgba(255, 255, 255, 0.18) !important;
}}
.tabulator {{
    background-color: {APPLE_CARD} !important;
    border: 1px solid {APPLE_BORDER} !important;
    border-radius: 16px !important;
    overflow: hidden !important;
    font-family: {APPLE_FONT} !important;
}}
"""

WIDGET_CSS = f"""
:host {{
    font-family: {APPLE_FONT} !important;
    color: {APPLE_TEXT} !important;
}}
label, .bk-input-group > label {{
    font-size: 12px !important;
    font-weight: 500 !important;
    color: #D1D1D6 !important;
    margin-bottom: 6px !important;
}}
.bk-slider-value {{
    color: {APPLE_BLUE} !important;
    font-weight: 600 !important;
    font-variant-numeric: tabular-nums !important;
}}
select.bk-input, input.bk-input, .choices__inner {{
    background-color: {APPLE_CARD_ELEVATED} !important;
    color: {APPLE_TEXT} !important;
    border: 1px solid {APPLE_BORDER} !important;
    border-radius: 12px !important;
    font-family: {APPLE_FONT} !important;
    font-size: 12.5px !important;
    box-shadow: none !important;
}}
select.bk-input:focus, input.bk-input:focus, .choices__inner:focus-within {{
    border-color: {APPLE_BLUE} !important;
    box-shadow: 0 0 0 3px rgba(10, 132, 255, 0.22) !important;
}}
.choices__list--dropdown {{
    background-color: {APPLE_CARD_ELEVATED} !important;
    border: 1px solid {APPLE_BORDER} !important;
    border-radius: 12px !important;
    color: {APPLE_TEXT} !important;
}}
.noUi-connect {{
    background: {APPLE_BLUE} !important;
}}
.noUi-handle {{
    border-radius: 50% !important;
    border: 2px solid {APPLE_BLUE} !important;
    background: #FFFFFF !important;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.45) !important;
    cursor: grab !important;
}}
"""

BUTTON_CSS = f"""
:host {{
    width: 100% !important;
}}
.bk-btn {{
    width: 100% !important;
    border-radius: 980px !important;
    font-family: {APPLE_FONT} !important;
    font-weight: 500 !important;
    font-size: 12px !important;
    padding: 6px 10px !important;
    border: 1px solid {APPLE_BORDER} !important;
    transition: transform 0.15s ease, background-color 0.15s ease !important;
}}
.bk-btn:hover {{
    transform: translateY(-1px);
}}
.bk-btn-primary {{
    background: {APPLE_BLUE} !important;
    border-color: {APPLE_BLUE} !important;
    color: #FFFFFF !important;
}}
.bk-btn-success {{
    background: rgba(48, 209, 88, 0.16) !important;
    border-color: rgba(48, 209, 88, 0.38) !important;
    color: {APPLE_GREEN} !important;
}}
.bk-btn-default, .bk-btn-light {{
    background: {APPLE_CARD_ELEVATED} !important;
    color: {APPLE_TEXT} !important;
}}
"""

TABS_CSS = f"""
.bk-tabs-header {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 0 16px 0 !important;
    margin: 0 auto 6px auto !important;
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
}}
.bk-header {{
    background: {APPLE_CARD} !important;
    border: 1px solid {APPLE_BORDER} !important;
    border-radius: 980px !important;
    padding: 4px !important;
    margin: 0 auto !important;
    display: inline-flex !important;
    justify-content: center !important;
    width: fit-content !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35) !important;
}}
.bk-tab {{
    background: transparent !important;
    border: none !important;
    border-radius: 980px !important;
    color: {APPLE_MUTED} !important;
    font-family: {APPLE_FONT} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 7px 18px !important;
    transition: background-color 0.18s ease, color 0.18s ease !important;
}}
.bk-tab:hover {{
    color: {APPLE_TEXT} !important;
}}
.bk-tab.bk-active {{
    background: {APPLE_CARD_ELEVATED} !important;
    color: {APPLE_TEXT} !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4) !important;
}}
"""

pn.extension("plotly", "tabulator", raw_css=[GLOBAL_CSS])
pn.config.busy = False
pn.config.throttled = True

PLOT_CFG = {"displaylogo": False, "responsive": True, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}

NON_REPORTING_EUROPE = [
    "United Kingdom", "Switzerland", "Ukraine", "Belarus", "Russia",
    "Andorra", "Monaco", "San Marino", "Liechtenstein", "Vatican City", "Faroe Islands",
]

# ----------------------------------------------------------------------------
# Data Loading & Enrichment
# ----------------------------------------------------------------------------
def find_csv():
    search_dirs = [
        HERE,
        PROJECT_ROOT,
        os.path.join(PROJECT_ROOT, "data"),
        os.path.join(PROJECT_ROOT, "data", "raw"),
        os.path.join(PROJECT_ROOT, "data", "processed"),
    ]
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if fname.lower().endswith(".csv") and "renewable" in fname.lower():
                return os.path.join(d, fname)
    return None

def load_dataset():
    if hasattr(cmap, "load_data"):
        try:
            df_loaded = cmap.load_data(extra_roots=[HERE, PROJECT_ROOT, os.path.join(PROJECT_ROOT, "data")])
            return df_loaded, False
        except Exception:
            pass
    csv_path = find_csv()
    if csv_path:
        df_loaded = pd.read_csv(csv_path)
        if "is_aggregate" not in df_loaded.columns:
            df_loaded["is_aggregate"] = df_loaded["geo_code"].astype(str).str.startswith(("EU", "EA"))
        return df_loaded, False
    rng = np.random.default_rng(7)
    countries = [
        ("Sweden", "SE"), ("Finland", "FI"), ("Latvia", "LV"), ("Denmark", "DK"),
        ("Austria", "AT"), ("Portugal", "PT"), ("Croatia", "HR"), ("Lithuania", "LT"),
        ("Estonia", "EE"), ("Romania", "RO"), ("Spain", "ES"), ("Greece", "EL"),
        ("Slovenia", "SI"), ("Bulgaria", "BG"), ("Germany", "DE"), ("Italy", "IT"),
        ("France", "FR"), ("Slovakia", "SK"), ("Czechia", "CZ"), ("Poland", "PL"),
        ("Hungary", "HU"), ("Netherlands", "NL"), ("Belgium", "BE"), ("Ireland", "IE"),
        ("Luxembourg", "LU"), ("Malta", "MT"),
    ]
    years = list(range(2015, 2024))
    rows = []
    for idx, (c, code) in enumerate(countries):
        base = 52 - idx * 1.6
        for y_i, y in enumerate(years):
            val = max(4.5, round(base + y_i * rng.uniform(0.5, 1.4), 2))
            rows.append({
                "country": c, "geo_code": code, "year": y,
                "renewable_share_pct": val, "data_flag": "Demo", "is_aggregate": False,
            })
    for y_i, y in enumerate(years):
        rows.append({
            "country": "European Union - 27 countries (from 2020)",
            "geo_code": "EU27_2020", "year": y,
            "renewable_share_pct": round(17.8 + y_i * 0.75, 2),
            "data_flag": "Demo", "is_aggregate": True,
        })
    return pd.DataFrame(rows), True

def fallback_enrich(raw_df):
    non_agg = raw_df[~raw_df["is_aggregate"]].copy()
    non_agg = non_agg.sort_values(["country", "year"])
    min_yr = int(non_agg["year"].min())
    non_agg["yoy_change"] = non_agg.groupby("country")["renewable_share_pct"].diff()
    base_map = non_agg[non_agg["year"] == min_yr].set_index("country")["renewable_share_pct"]
    non_agg["change_since_base"] = non_agg["renewable_share_pct"] - non_agg["country"].map(base_map)
    non_agg["year_rank"] = non_agg.groupby("year")["renewable_share_pct"].rank(ascending=False, method="min")
    eu_map = raw_df[raw_df["geo_code"] == "EU27_2020"].set_index("year")["renewable_share_pct"]
    non_agg["eu_avg_pct"] = non_agg["year"].map(eu_map)
    non_agg["vs_eu_avg"] = non_agg["renewable_share_pct"] - non_agg["eu_avg_pct"]
    return non_agg, min_yr

df, IS_DEMO = load_dataset()
if hasattr(cmap, "enrich_country_metrics"):
    try:
        d_all, MIN_YEAR = cmap.enrich_country_metrics(df)
    except Exception:
        d_all, MIN_YEAR = fallback_enrich(df)
else:
    d_all, MIN_YEAR = fallback_enrich(df)

MAP_METRICS = getattr(
    cmap,
    "MAP_METRICS",
    {
        "Renewable Share (%)": {"col": "renewable_share_pct", "suffix": "%"},
        "YoY Change (pp)": {"col": "yoy_change", "suffix": " pp"},
        "Change Since Base (pp)": {"col": "change_since_base", "suffix": " pp"},
        "Gap vs EU-27 (pp)": {"col": "vs_eu_avg", "suffix": " pp"},
    },
)
TREND_MODES = getattr(mtrend, "TREND_MODES", ["Absolute Share (%)", "Indexed (Base = 100)", "YoY Change (pp)"])
HEATMAP_VIEWS = getattr(hmap, "HEATMAP_VIEWS", ["Renewable Share (%)", "YoY Change (pp)", "Gap vs EU-27 (pp)"])

COUNTRIES = sorted(d_all["country"].dropna().unique())
YEARS = sorted(int(y) for y in d_all["year"].dropna().unique())
LATEST = YEARS[-1]
DEFAULT_SEL = [
    c for c in ["Germany", "France", "Hungary", "Sweden", "Poland"] if c in COUNTRIES
] or COUNTRIES[:5]

# ----------------------------------------------------------------------------
# Apple Plotly Theme Harmonizer
# ----------------------------------------------------------------------------
def apply_apple_plotly_theme(fig, uirev=None, preserve_geo=False):
    if not isinstance(fig, go.Figure):
        return fig
    layout_kw = dict(
        autosize=True,
        transition=dict(duration=0),
        paper_bgcolor=APPLE_CARD,
        plot_bgcolor=APPLE_CARD,
        font=dict(family=APPLE_FONT, color=APPLE_TEXT, size=13),
        hoverlabel=dict(
            bgcolor="#2C2C2E",
            bordercolor="rgba(255,255,255,0.16)",
            font=dict(family=APPLE_FONT, color=APPLE_TEXT, size=13),
        ),
    )
    if uirev is not None:
        layout_kw["uirevision"] = uirev
    fig.update_layout(**layout_kw)
    if "geo" in fig.layout and not preserve_geo:
        fig.update_geos(bgcolor=APPLE_CARD, lakecolor=APPLE_CARD, oceancolor=APPLE_CARD)
    return fig

# ----------------------------------------------------------------------------
# Plot Helper Functions
# ----------------------------------------------------------------------------
def error_fig(msg):
    f = go.Figure()
    f.add_annotation(text=msg, showarrow=False, font=dict(size=14, color=APPLE_MUTED, family=APPLE_FONT))
    f.update_layout(template="plotly_dark", paper_bgcolor=APPLE_CARD, plot_bgcolor=APPLE_CARD)
    return f

def call_viz(fn, primary_arg, uirev=None, preserve_geo=False, **kwargs):
    if uirev is not None:
        kwargs.setdefault("uirev", uirev)
    try:
        sig = inspect.signature(fn)
        accepts_extra = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        accepted = kwargs if accepts_extra else {k: v for k, v in kwargs.items() if k in sig.parameters}
    except (TypeError, ValueError):
        accepted = kwargs
    res = fn(primary_arg, **accepted)
    fig = res.object if hasattr(res, "object") else res
    if isinstance(fig, go.Figure):
        if fig.layout.title.text:
            fig.update_layout(title=dict(x=0.5, xanchor="center"))
    return apply_apple_plotly_theme(fig, uirev=uirev, preserve_geo=preserve_geo)

# ----------------------------------------------------------------------------
# Interactive Companion Charts & Dynamic Analytics
# ----------------------------------------------------------------------------
def build_map_with_target(year, metric_name, selected, target_pct):
    fig = call_viz(
        cmap.create_choropleth_map,
        df,
        preserve_geo=True,
        year=year,
        selected_year=year,
        metric=metric_name,
        selected_countries=selected,
        target_pct=target_pct,
        include_controls=False,
        uirev=f"map-{metric_name}",
    )
    if isinstance(fig, go.Figure):
        sub = d_all[(d_all["year"] == year) & d_all["renewable_share_pct"].notna()]
        met_cnt = int((sub["renewable_share_pct"] >= target_pct).sum()) if target_pct > 0 else 0
        tot_cnt = len(sub)

        title_text = f"<b>EUROPEAN RENEWABLE ENERGY SHARE · {year}</b>"
        if target_pct > 0:
            title_text += (
                f"<br><span style='font-size:12.5px;color:{APPLE_GREEN};font-weight:500;'>"
                f"Policy Target ({target_pct}%): {met_cnt}/{tot_cnt} nations above target</span>"
            )

        fig.update_layout(
            title=dict(text=title_text, x=0.5, xanchor="center", font=dict(size=16)),
        )
    return fig

def build_ranking_bar(year, metric_name, selected, target_pct):
    metric_cfg = MAP_METRICS.get(metric_name, next(iter(MAP_METRICS.values())))
    col = metric_cfg["col"]
    suffix = metric_cfg.get("suffix", "")
    sub = d_all[(d_all["year"] == year) & d_all[col].notna()].sort_values(col, ascending=True)
    if sub.empty:
        return error_fig(f"No {metric_name} data available for {year}.")
    sel_set = set(selected or [])
    colors = [
        APPLE_AMBER if c in sel_set else (APPLE_BLUE if v >= 0 else APPLE_RED)
        for c, v in zip(sub["country"], sub[col])
    ]
    target_x = None
    target_label = f"Target {target_pct}%"
    if target_pct > 0:
        if col == "renewable_share_pct":
            target_x = float(target_pct)
        elif col == "vs_eu_avg" and "eu_avg_pct" in sub.columns and sub["eu_avg_pct"].notna().any():
            eu_val = float(sub["eu_avg_pct"].dropna().iloc[0])
            target_x = max(0.0, float(target_pct) - eu_val)
            target_label = f"Target {target_pct}% (+{target_x:.1f} pp vs EU)"
        elif col == "change_since_base":
            base_shares = sub["renewable_share_pct"] - sub["change_since_base"]
            target_x = max(0.0, float(target_pct - base_shares.mean()))
            target_label = f"Target Gain (+{target_x:.1f} pp)"
        elif col == "yoy_change":
            yrs_left = max(2030 - int(year), 1)
            gap_now = max(0.0, float(target_pct - sub["renewable_share_pct"].mean()))
            target_x = gap_now / yrs_left
            target_label = f"Target Pace (+{target_x:.1f} pp/yr)"
    vmin = float(sub[col].min())
    vmax = float(sub[col].max())
    if target_x is not None:
        vmax = max(vmax, target_x)
    span = max(vmax - min(vmin, 0.0), 1.0)
    x_lo = (vmin - span * 0.08) if vmin < 0 else 0.0
    x_hi = vmax + span * 0.32
    vs_target = sub["renewable_share_pct"] - float(target_pct)
    hover_extra = [f"<br>Vs {target_pct}% Target: <b>{d:+.2f} pp</b>" for d in vs_target]
    fig = go.Figure(go.Bar(
        x=sub[col],
        y=sub["country"],
        orientation="h",
        marker=dict(color=colors, line=dict(color=APPLE_CARD, width=0.8), cornerradius=6),
        text=[f"{v:+.1f}{suffix}" if vmin < 0 else f"{v:.1f}{suffix}" for v in sub[col]],
        textposition=["inside" if v < 0 else "outside" for v in sub[col]],
        insidetextanchor="end",
        textfont=dict(size=12, color="#F5F5F7"),
        customdata=list(zip(sub["country"], hover_extra)),
        hovertemplate=(
            "<b>%{y}</b> (" + str(year) + ")<br>"
            + metric_name + ": <b>%{x:.2f}" + suffix + "</b>"
            "%{customdata[1]}<br><i>Click to toggle selection</i><extra></extra>"
        ),
    ))
    if target_x is not None and target_x > 0:
        fig.add_vline(
            x=target_x,
            line_dash="dot",
            line_color=APPLE_GREEN,
            line_width=2.0,
            annotation_text=target_label,
            annotation_position="top right",
            annotation_y=0.97,
            annotation_yref="paper",
            annotation_font=dict(color=APPLE_GREEN, size=12, family=APPLE_FONT),
            annotation_bgcolor=APPLE_CARD_ELEVATED,
            annotation_bordercolor=APPLE_BORDER,
            annotation_borderwidth=1,
            annotation_borderpad=5,
        )
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=130, r=60, t=55, b=35),
        title=dict(text=f"<b>Country Ranking · {year}</b>", font=dict(size=16, color=APPLE_TEXT), x=0.5, xanchor="center"),
        xaxis=dict(autorange=False, range=[x_lo, x_hi], showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=True, zerolinecolor="rgba(255,255,255,0.18)", tickfont=dict(size=11)),
        yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#D1D1D6")),
        clickmode="event+select",
    )
    return apply_apple_plotly_theme(fig, uirev=f"ranking-{metric_name}-{year}")

def build_movers_dumbbell(yr_win, selected):
    raw = df[~df["is_aggregate"]].dropna(subset=["renewable_share_pct"])
    start_yr, end_yr = int(yr_win[0]), int(yr_win[1])

    df_start = raw[raw["year"] == start_yr].set_index("country")["renewable_share_pct"]
    df_end = raw[raw["year"] == end_yr].set_index("country")["renewable_share_pct"]

    mdf = pd.DataFrame({"v0": df_start, "v1": df_end}).dropna()
    if mdf.empty:
        return error_fig(f"No overlapping country data available between {start_yr} and {end_yr}.")

    mdf["delta"] = mdf["v1"] - mdf["v0"]
    mdf = mdf.sort_values("delta", ascending=True).reset_index()

    sel_set = set(selected or [])
    fig = go.Figure()

    country_order = mdf["country"].tolist()

    for _, r in mdf.iterrows():
        c = r["country"]
        is_sel = c in sel_set
        line_col = APPLE_AMBER if is_sel else (APPLE_GREEN if r["delta"] >= 0 else APPLE_RED)

        fig.add_trace(go.Scatter(
            x=[r["v0"], r["v1"]],
            y=[c, c],
            mode="lines",
            line=dict(color=line_col, width=3.8 if is_sel else 2.0),
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.add_trace(go.Scatter(
        x=mdf["v0"],
        y=mdf["country"],
        mode="markers",
        name=f"Start ({start_yr})",
        customdata=list(zip(mdf["country"], [start_yr] * len(mdf))),
        marker=dict(size=9, color=APPLE_CARD, line=dict(color="#8E8E93", width=2.2)),
        hovertemplate="<b>%{y}</b> · Start (" + str(start_yr) + "): <b>%{x:.2f}%</b><br><i>Click to toggle selection</i><extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=mdf["v1"],
        y=mdf["country"],
        mode="markers+text",
        name=f"End ({end_yr})",
        customdata=list(zip(mdf["country"], [end_yr] * len(mdf))),
        text=[f" {d:+.1f} pp" for d in mdf["delta"]],
        textposition="middle right",
        textfont=dict(size=11, color="#E5E5EA"),
        marker=dict(size=11, color=[APPLE_AMBER if c in sel_set else APPLE_BLUE for c in mdf["country"]]),
        hovertemplate="<b>%{y}</b> · End (" + str(end_yr) + "): <b>%{x:.2f}%</b><br><i>Click to toggle selection</i><extra></extra>",
    ))

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=130, r=60, t=80, b=65),
        title=dict(
            text=f"<b>Net Trajectory ({start_yr}–{end_yr})</b><br><span style='font-size:12px;color:#8E8E93;'>Sorted by Percentage-Point Gain</span>",
            font=dict(size=16, color=APPLE_TEXT),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(title="Renewable Share (%)", ticksuffix="%", gridcolor="rgba(255,255,255,0.06)", tickfont=dict(size=11)),
        yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#D1D1D6"), categoryorder="array", categoryarray=country_order),
        legend=dict(
            orientation="h",
            x=0.5,
            y=-0.22,
            xanchor="center",
            yanchor="top",
            font=dict(size=12),
        ),
        clickmode="event+select",
    )
    return apply_apple_plotly_theme(fig, uirev=f"movers-{start_yr}-{end_yr}")

def country_stats_table(selected, yr_win, target_pct):
    sub = d_all[
        d_all["country"].isin(selected or [])
        & d_all["year"].between(yr_win[0], yr_win[1])
        & d_all["renewable_share_pct"].notna()
    ].sort_values(["country", "year"])
    rows = []
    for c, g in sub.groupby("country"):
        v0, v1 = float(g["renewable_share_pct"].iloc[0]), float(g["renewable_share_pct"].iloc[-1])
        rank_val = g["year_rank"].iloc[-1]
        rows.append({
            "Country": c,
            "Start (%)": round(v0, 2),
            "End (%)": round(v1, 2),
            "Change (pp)": round(v1 - v0, 2),
            "Latest Rank": f"#{int(rank_val)}" if pd.notna(rank_val) else "n/a",
            "Gap vs EU-27 (pp)": round(float(g["vs_eu_avg"].iloc[-1]), 2) if pd.notna(g["vs_eu_avg"].iloc[-1]) else None,
            f"Vs {target_pct}% Target": round(v1 - target_pct, 2),
        })
    return pd.DataFrame(rows)

# ----------------------------------------------------------------------------
# Build Dashboard Factory (Per-Session Safe for Server & Streamlit)
# ----------------------------------------------------------------------------
def build_dashboard():
    SIDEBAR_W = 260
    year_slider = pn.widgets.IntSlider(name="Year (Map & Ranking)", start=YEARS[0], end=YEARS[-1], value=LATEST, step=1, width=SIDEBAR_W, stylesheets=[WIDGET_CSS])
    map_metric = pn.widgets.Select(name="Map & Ranking Metric", options=list(MAP_METRICS.keys()), value=list(MAP_METRICS.keys())[0], width=SIDEBAR_W, stylesheets=[WIDGET_CSS])
    target_slider = pn.widgets.IntSlider(name="Policy Target Benchmark (%)", start=10, end=65, value=32, step=1, width=SIDEBAR_W, stylesheets=[WIDGET_CSS])
    country_picker = pn.widgets.MultiChoice(name="Selected Countries", options=COUNTRIES, value=DEFAULT_SEL, solid=False, width=SIDEBAR_W, stylesheets=[WIDGET_CSS])

    btn_top5 = pn.widgets.Button(name="Top 5 Leaders", button_type="primary", sizing_mode="stretch_width", stylesheets=[BUTTON_CSS])
    btn_movers = pn.widgets.Button(name="Top 5 Movers", button_type="success", sizing_mode="stretch_width", stylesheets=[BUTTON_CSS])
    btn_v4 = pn.widgets.Button(name="Visegrád (V4)", button_type="default", sizing_mode="stretch_width", stylesheets=[BUTTON_CSS])
    btn_clear = pn.widgets.Button(name="Clear All", button_type="light", sizing_mode="stretch_width", stylesheets=[BUTTON_CSS])

    def apply_top5(_):
        yr_now = int(year_slider.value)
        top = (
            d_all[(d_all["year"] == yr_now) & d_all["renewable_share_pct"].notna()]
            .sort_values("renewable_share_pct", ascending=False)["country"]
            .head(5)
            .tolist()
        )
        if top:
            country_picker.value = top

    def apply_top_movers(_):
        lo, hi = YEARS[0], YEARS[-1]
        sub = d_all[d_all["year"].isin([lo, hi])].pivot(index="country", columns="year", values="renewable_share_pct").dropna()
        if not sub.empty and lo != hi:
            deltas = (sub[hi] - sub[lo]).sort_values(ascending=False)
            country_picker.value = deltas.head(5).index.tolist()

    def apply_v4(_):
        v4 = [c for c in ["Hungary", "Poland", "Czechia", "Slovakia"] if c in COUNTRIES]
        if v4:
            country_picker.value = v4

    def apply_clear(_):
        country_picker.value = []

    btn_top5.on_click(apply_top5)
    btn_movers.on_click(apply_top_movers)
    btn_v4.on_click(apply_v4)
    btn_clear.on_click(apply_clear)

    trend_mode = pn.widgets.Select(name="Trend View", options=TREND_MODES, width=200, stylesheets=[WIDGET_CSS])
    show_eu = pn.widgets.Checkbox(name="Show EU-27 average line", value=True, stylesheets=[WIDGET_CSS])
    show_target_trend = pn.widgets.Checkbox(name="Show Policy Target line", value=True, stylesheets=[WIDGET_CSS])
    show_all_pts = pn.widgets.Checkbox(name="Show all countries as dots", value=True, stylesheets=[WIDGET_CSS])
    heat_view = pn.widgets.Select(name="Matrix View", options=HEATMAP_VIEWS, width=200, stylesheets=[WIDGET_CSS])
    heat_only_sel = pn.widgets.Checkbox(name="Only selected countries", value=False, stylesheets=[WIDGET_CSS])

    def on_pick(event):
        data = event.new
        if not data or not data.get("points"):
            return
        pt = data["points"][0]
        name = None
        clicked_year = None
        cd = pt.get("customdata")
        if isinstance(cd, (list, tuple)) and len(cd) >= 2:
            if cd[0] in COUNTRIES:
                name = cd[0]
            if isinstance(cd[1], (int, float)) and int(cd[1]) in YEARS:
                clicked_year = int(cd[1])
        if not name:
            for key in ("customdata", "text", "y", "location"):
                v = pt.get(key)
                if isinstance(v, (list, tuple)) and v:
                    v = v[-1] if v[-1] in COUNTRIES else v[0]
                if v in COUNTRIES:
                    name = v
                    break
        if clicked_year is not None and clicked_year != int(year_slider.value):
            year_slider.value = clicked_year
        if not name:
            return
        cur = list(country_picker.value)
        country_picker.value = [c for c in cur if c != name] if name in cur else cur + [name]

    def make_pane(builder, widgets, height, interactive_pick=False, stretch_card=False, **kw):
        if stretch_card:
            kw.setdefault("sizing_mode", "stretch_both")
            kw.setdefault("styles", {"height": "100%", "min-height": "0", "width": "100%"})
            pane = pn.pane.Plotly(error_fig("Loading…"), config=PLOT_CFG, **kw)
        else:
            kw.setdefault("sizing_mode", "stretch_both")
            kw.setdefault("styles", {"height": f"{height}px", "width": "100%"})
            pane = pn.pane.Plotly(error_fig("Loading…"), height=height, config=PLOT_CFG, **kw)
        def update(*_):
            try:
                pane.object = builder()
            except Exception as exc:
                pane.object = error_fig(f"Could not render chart: {exc}")
        for w in widgets:
            watch_param = "value_throttled" if hasattr(w.param, "value_throttled") else "value"
            w.param.watch(update, watch_param)
        if interactive_pick:
            pane.param.watch(on_pick, "click_data")
        update()
        return pane

    def bento_box(*objects, **kw):
        kw.setdefault("sizing_mode", "stretch_width")
        return pn.Column(*objects, css_classes=["apple-bento"], **kw)

    def sel():
        return list(country_picker.value)

    def yr():
        return (YEARS[0], YEARS[-1])

    map_pane = make_pane(
        lambda: build_map_with_target(int(year_slider.value), map_metric.value, sel(), int(target_slider.value)),
        [year_slider, map_metric, country_picker, target_slider],
        850, interactive_pick=True, stretch_card=True,
    )
    bar_pane = make_pane(
        lambda: build_ranking_bar(int(year_slider.value), map_metric.value, sel(), int(target_slider.value)),
        [year_slider, map_metric, country_picker, target_slider],
        700, interactive_pick=True, stretch_card=True,
    )

    def build_trend_with_target():
        fig = call_viz(
            mtrend.create_multitrend,
            df,
            uirev=f"trend-{trend_mode.value}",
            selected_countries=sel(),
            trend_mode=trend_mode.value,
            year_range=yr(),
            show_eu=show_eu.value,
            include_controls=False,
        )
        if isinstance(fig, go.Figure) and show_target_trend.value and "Absolute" in trend_mode.value and int(target_slider.value) > 0:
            fig.add_hline(
                y=int(target_slider.value),
                line_dash="dot",
                line_color=APPLE_GREEN,
                line_width=1.8,
                annotation_text=f"Policy Target ({int(target_slider.value)}%)",
                annotation_position="top left",
                annotation_font=dict(color=APPLE_GREEN, size=11.5),
            )
        fig.update_layout(margin=dict(l=60, r=40, t=60, b=50), font=dict(size=13))
        return fig

    trend_pane = make_pane(build_trend_with_target, [country_picker, trend_mode, show_eu, show_target_trend, target_slider], 620, interactive_pick=True)
    movers_pane = make_pane(lambda: build_movers_dumbbell(yr(), sel()), [country_picker], 660, interactive_pick=True)
    box_pane = make_pane(
        lambda: call_viz(obox.create_outlier_box, df, uirev="box-dist", year_range=yr(), selected_countries=sel(), show_all_points=show_all_pts.value, include_controls=False),
        [country_picker, show_all_pts], 620, interactive_pick=True,
    )
    heat_pane = make_pane(
        lambda: call_viz(hmap.create_heatmap, df, uirev=f"heat-{heat_view.value}", default_view=heat_view.value, year_range=yr(), selected_countries=sel(), only_selected=heat_only_sel.value, include_controls=False),
        [heat_view, country_picker, heat_only_sel], 660, interactive_pick=True,
    )

    stats_table = pn.widgets.Tabulator(
        country_stats_table(sel(), yr(), int(target_slider.value)),
        show_index=False, disabled=True, theme="midnight", layout="fit_columns", sizing_mode="stretch_width", height=220,
    )
    for _w in (country_picker, target_slider):
        _wp = "value_throttled" if hasattr(_w.param, "value_throttled") else "value"
        _w.param.watch(lambda *_: setattr(stats_table, "value", country_stats_table(sel(), yr(), int(target_slider.value))), _wp)

    only_sel_data = pn.widgets.Checkbox(name="Filter table to selected countries only", value=False, stylesheets=[WIDGET_CSS])

    def build_data_table_df():
        t = d_all.rename(columns={
            "renewable_share_pct": "share_pct",
            "yoy_change": "yoy_pp",
            "change_since_base": "since_base_pp",
            "vs_eu_avg": "gap_to_eu27_pp",
            "eu_avg_pct": "eu27_pct",
            "year_rank": "rank",
        })
        keep = ["country", "geo_code", "year", "share_pct", "rank", "yoy_pp", "since_base_pp", "eu27_pct", "gap_to_eu27_pp", "data_flag"]
        lo, hi = yr()
        out = t[t["year"].between(lo, hi) & t["share_pct"].notna()]
        if only_sel_data.value and sel():
            out = out[out["country"].isin(sel())]
        return out[keep].round(2).sort_values(["year", "rank"], ascending=[False, True])

    data_table = pn.widgets.Tabulator(
        build_data_table_df(),
        show_index=False, disabled=True, theme="midnight", header_filters=True, pagination="local", page_size=15, layout="fit_columns", sizing_mode="stretch_width", height=540,
    )
    for _w in (country_picker, only_sel_data):
        _wp = "value_throttled" if hasattr(_w.param, "value_throttled") else "value"
        _w.param.watch(lambda *_: setattr(data_table, "value", build_data_table_df()), _wp)

    download = pn.widgets.FileDownload(
        callback=lambda: StringIO(data_table.value.to_csv(index=False)),
        filename="renewable_share_filtered.csv",
        label="Export CSV", button_type="primary", width=140, stylesheets=[BUTTON_CSS],
    )

    def note(text):
        return pn.pane.Markdown(f"<div style='text-align:center;color:{APPLE_MUTED};font-size:13px;margin-bottom:6px;'>{text}</div>", sizing_mode="stretch_width")

    overview = pn.Row(
        bento_box(map_pane, sizing_mode="stretch_width", styles={"flex": "2 1 650px", "min-width": "0", "height": "880px", "overflow": "hidden"}),
        bento_box(bar_pane, sizing_mode="stretch_width", styles={"flex": "1 1 350px", "min-width": "0", "height": "880px", "overflow": "hidden"}),
        sizing_mode="stretch_width", styles={"gap": "16px", "flex-wrap": "wrap", "margin-top": "4px"},
    )

    trends = pn.Column(
        bento_box(
            pn.Row(
                pn.Spacer(sizing_mode="stretch_width"),
                trend_mode,
                pn.Spacer(width=16),
                show_eu,
                show_target_trend,
                pn.Spacer(sizing_mode="stretch_width"),
                align="center",
                styles={"gap": "14px", "align-items": "center", "margin-bottom": "6px", "flex-wrap": "wrap"},
            ),
            trend_pane,
        ),
        pn.Spacer(height=12),
        bento_box(
            pn.pane.Markdown(f"<div style='text-align:center;font-size:15px;font-weight:600;color:{APPLE_TEXT};margin-bottom:8px;'>Selected Countries Summary</div>", sizing_mode="stretch_width"),
            stats_table,
        ),
        sizing_mode="stretch_width",
        styles={"margin-top": "4px"},
    )

    movers = bento_box(note("Hollow dot = start of window · Filled dot = end of window · Click any point to select & jump to year"), movers_pane, styles={"margin-top": "4px"})
    spread = bento_box(pn.Row(note("Annual distribution across reporting countries · Gold = selected · Red = 1.5×IQR outliers"), show_all_pts, align="center"), box_pane, styles={"margin-top": "4px"})
    matrix = bento_box(pn.Row(heat_view, heat_only_sel, align="end", styles={"gap": "14px"}), heat_pane, styles={"margin-top": "4px"})
    data = bento_box(pn.Row(note("Filter directly in column headers or export the active view."), only_sel_data, download, align="center", styles={"gap": "12px"}), data_table, styles={"margin-top": "4px"})

    tabs = pn.Tabs(
        ("Overview", overview), ("Trends", trends), ("Movers", movers), ("Spread & Outliers", spread), ("Matrix", matrix), ("Data", data),
        dynamic=True, sizing_mode="stretch_width", stylesheets=[TABS_CSS],
    )

    main = []
    if IS_DEMO:
        main.append(pn.pane.Alert("Showing **demo data** because `renewable_energy_shares.csv` was not found in the project folder.", alert_type="warning", sizing_mode="stretch_width"))
    main.append(tabs)

    preset_grid = pn.GridBox(btn_top5, btn_movers, btn_v4, btn_clear, ncols=2, width=SIDEBAR_W, styles={"gap": "6px", "margin-top": "4px"})

    def sidebar_heading(text):
        return pn.pane.Markdown(f"<div style='font-size:11px;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;color:{APPLE_MUTED};margin:0 0 3px 0;'>{text}</div>", width=SIDEBAR_W, margin=(2, 0, 0, 0))

    sidebar_content = pn.Column(
        sidebar_heading("Snapshot & Target"),
        year_slider, map_metric, target_slider,
        pn.layout.Divider(width=SIDEBAR_W, margin=(8, 0), styles={"border-color": APPLE_BORDER}),
        sidebar_heading("Comparison"),
        country_picker, preset_grid,
        pn.layout.Divider(width=SIDEBAR_W, margin=(10, 0), styles={"border-color": APPLE_BORDER}),
        sidebar_heading("About & Metadata"),
        pn.pane.Markdown(
            f"<div style='width:100%;box-sizing:border-box;font-size:11.5px;color:{APPLE_MUTED};line-height:1.5;"
            f"background:{APPLE_CARD_ELEVATED};border:1px solid {APPLE_BORDER};border-radius:12px;padding:10px;'>"
            f"<div style='color:{APPLE_TEXT};font-weight:600;margin-bottom:4px;'>EU Renewable Energy Observatory</div>"
            f"<div style='margin-bottom:8px;color:#AEAEB2;font-size:11px;'>"
            f"Interactive visual analytics tracking national renewable energy shares in gross final consumption, "
            f"annual momentum, and progress against EU policy benchmarks."
            f"</div>"
            f"<strong style='color:{APPLE_TEXT};'>Source:</strong> Eurostat (<code>nrg_ind_ren</code>)<br>"
            f"<strong style='color:{APPLE_TEXT};'>Coverage:</strong> {len(COUNTRIES)} nations · {YEARS[0]}–{YEARS[-1]}<br>"
            f"<strong style='color:{APPLE_TEXT};'>Metric:</strong> Share in gross final energy (%)<br>"
            f"<strong style='color:{APPLE_TEXT};'>Course:</strong> Data Visualization Methods<br>"
            f"<strong style='color:{APPLE_TEXT};'>Institution:</strong> University of Debrecen"
            f"</div>",
            width=SIDEBAR_W, margin=(2, 0, 0, 0),
        ),
        width=280, styles={"padding": "4px 8px 16px 8px", "box-sizing": "border-box"},
    )

    return pn.template.FastListTemplate(
        title="EU Renewable Energy Observatory",
        header=[], sidebar=[sidebar_content], main=main, theme="dark", theme_toggle=False,
        accent_base_color=APPLE_BLUE, header_background="#121214", sidebar_width=310,
    )

# ----------------------------------------------------------------------------
# Server & Streamlit Cloud Runtime Handler
# ----------------------------------------------------------------------------
def find_free_port(start_port=5006):
    for p in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return 0

def open_in_chrome(url):
    time.sleep(1.3)
    chrome_candidates = [
        "google-chrome", "chrome",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    ]
    for candidate in chrome_candidates:
        exe = shutil.which(candidate) if not os.path.isabs(candidate) else (candidate if os.path.exists(candidate) else None)
        if exe:
            try:
                webbrowser.get(f'"{exe}" %s').open(url)
                return
            except Exception:
                pass
    webbrowser.open(url)

def is_running_in_streamlit():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False

if is_running_in_streamlit():
    import streamlit as st
    import streamlit.components.v1 as components

    st.set_page_config(
        page_title="EU Renewable Energy Observatory",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        """
        <style>
            #MainMenu, header, footer, [data-testid="stToolbar"] {visibility: hidden; height: 0;}
            .block-container {padding: 0 !important; max-width: 100% !important;}
            iframe {border: none !important; width: 100% !important; min-height: 100vh !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    @st.cache_data(show_spinner="Rendering EU Renewable Energy Observatory...")
    def render_embedded_panel_html():
        buf = StringIO()
        dash = build_dashboard()
        dash.save(buf, embed=True)
        return buf.getvalue()

    components.html(render_embedded_panel_html(), height=1050, scrolling=True)

elif __name__ == "__main__":
    PORT = find_free_port(5006)
    URL = f"http://localhost:{PORT}"
    print(f"\nStarting EU Renewable Energy Dashboard on {URL} ...", flush=True)
    threading.Thread(target=open_in_chrome, args=(URL,), daemon=True).start()
    pn.serve(
        build_dashboard,
        port=PORT,
        address="127.0.0.1",
        show=False,
        title="European Renewable Energy Share",
        websocket_origin=[f"localhost:{PORT}", f"127.0.0.1:{PORT}"],
    )
else:
    build_dashboard().servable()
