import importlib.util
import inspect
import os
import sys
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# Page Configuration & Apple Dark Theme Styling
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="EU Renewable Energy Observatory",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

# Cards are real Streamlit containers (st.container(key="card-...")); Streamlit adds the
# class "st-key-<key>" to them, which the CSS below styles.
APPLE_PANEL = "#19191A"
USE_MODULE_CHARTS = False   # True = use the charts from src/viz for Trends / Spread / Matrix (map always uses the module)

# If the Streamlit theme was not set (no .streamlit/config.toml), Streamlit paints sliders red.
# In that case recolour them blue with a hue rotation so the app looks right either way.
_prim = (st.get_option("theme.primaryColor") or "").lower()
SLIDER_FIX = "[data-testid='stSlider'] { filter: hue-rotate(211deg) saturate(1.1); }" if _prim in ("", "#ff4b4b") else ""

st.markdown(f"""
<style>
    .stApp {{
        background-color: {APPLE_BG};
        color: {APPLE_TEXT};
        font-family: {APPLE_FONT};
        -webkit-font-smoothing: antialiased;
    }}
    /* ---- top bar with title (spans the whole window, over the sidebar too) ---- */
    header[data-testid="stHeader"] {{
        position: fixed; top: 0; left: 0; right: 0; width: 100%;
        background: #0B0B0C;
        height: 44px;
        border-bottom: 1px solid {APPLE_BORDER};
        z-index: 999990;
        pointer-events: none;
    }}
    header[data-testid="stHeader"] > * {{ pointer-events: auto; }}
    header[data-testid="stHeader"]::after {{
        content: "EU Renewable Energy Observatory";
        position: absolute; left: 24px; top: 50%; transform: translateY(-50%);
        font-size: 14.5px; font-weight: 600; color: {APPLE_TEXT}; pointer-events: none;
    }}
    [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none !important; }}

    /* ---- sidebar ---- */
    [data-testid="stSidebar"] {{
        background-color: #141416;
        border-right: 1px solid {APPLE_BORDER};
    }}
    [data-testid="stSidebar"][aria-expanded="true"] {{ min-width: 309px; max-width: 309px; }}
    [data-testid="stSidebarHeader"] {{ height: 44px; min-height: 44px; padding: 0 12px; margin-bottom: 0; }}
    [data-testid="stSidebarUserContent"] {{ padding: 18px 20px 24px 20px; }}
    [data-testid="stSidebar"] hr {{ border-color: {APPLE_BORDER}; margin: 14px 0; }}
    .side-title {{
        font-size: 11px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase;
        color: {APPLE_MUTED}; margin: 6px 0 10px 0;
    }}
    .side-label {{ font-size: 13.5px; font-weight: 500; color: {APPLE_TEXT}; margin: 2px 0 6px 0; }}
    .side-label b {{ color: {APPLE_BLUE}; font-weight: 500; }}
    [data-testid="stSidebar"] [data-testid="stSliderThumbValue"], [data-testid="stSidebar"] [data-testid="stTickBarMin"], [data-testid="stSidebar"] [data-testid="stTickBarMax"] {{ display: none !important; }}
    div.stElementContainer:has(iframe[height="0"]) {{ display: none; }}
    {SLIDER_FIX}

    /* ---- inputs (dark, consistent, never brown/red) ---- */
    [data-baseweb="select"] > div {{
        background: {APPLE_CARD_ELEVATED} !important;
        border: 1px solid {APPLE_BORDER} !important;
        border-radius: 10px !important;
        color: {APPLE_TEXT} !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="select"] > div {{ background: {APPLE_CARD} !important; }}
    [data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
        min-height: 132px; align-items: flex-start; border-radius: 12px !important; background: #1A1A1C !important;
    }}
    [data-baseweb="tag"] {{
        background: rgba(10, 132, 255, 0.14) !important;
        border: 1px solid rgba(10, 132, 255, 0.55) !important;
        border-radius: 4px !important;
    }}
    [data-baseweb="tag"], [data-baseweb="tag"] span, [data-baseweb="tag"] svg {{ color: {APPLE_BLUE} !important; fill: {APPLE_BLUE} !important; }}
    label[data-baseweb="checkbox"] > span:first-child {{
        background: {APPLE_CARD_ELEVATED} !important; border: 1px solid rgba(255,255,255,0.28) !important; border-radius: 5px !important;
    }}
    label[data-baseweb="checkbox"]:has(input:checked) > span:first-child {{
        background: {APPLE_BLUE} !important; border-color: {APPLE_BLUE} !important;
    }}

    /* ---- buttons ---- */
    [data-testid="stSidebar"] .stButton, [data-testid="stSidebar"] [data-testid="stButton"] {{ width: 100% !important; }}
    div.stButton > button, [data-testid="stSidebar"] button[kind] {{
        border-radius: 980px !important;
        background-color: {APPLE_CARD_ELEVATED};
        color: {APPLE_TEXT};
        border: 1px solid {APPLE_BORDER};
        width: 100% !important;
        min-height: 32px;
        padding: 2px 10px;
        font-weight: 600;
        font-size: 12px;
        transition: transform 0.15s ease;
    }}
    div.stButton > button p {{ font-size: 12px; font-weight: 600; }}
    div.stButton > button:hover {{
        border-color: rgba(255, 255, 255, 0.25);
        transform: translateY(-1px);
    }}
    div.stDownloadButton > button[kind="primary"],
    .st-key-btn_leaders button {{
        background-color: {APPLE_BLUE} !important; color: #FFFFFF !important; border-color: {APPLE_BLUE} !important;
    }}
    .st-key-btn_movers button {{
        background-color: rgba(48, 209, 88, 0.08) !important; color: {APPLE_GREEN} !important;
        border-color: rgba(48, 209, 88, 0.45) !important;
    }}
    .st-key-btn_movers button p {{ color: {APPLE_GREEN} !important; }}

    /* ---- main panel ---- */
    [data-testid="stMainBlockContainer"], .block-container {{
        background: {APPLE_PANEL};
        max-width: none !important;
        margin: 76px 14px 0 24px;
        padding: 16px 16px 40px 16px !important;
        border-radius: 4px;
    }}
    [data-baseweb="tab-list"], [data-testid="stTabs"] [role="tablist"] {{
        gap: 8px;
        background-color: {APPLE_CARD} !important;
        padding: 6px;
        border-radius: 980px;
        border: 1px solid {APPLE_BORDER};
        margin: 0 auto 20px auto !important;
        width: fit-content !important;
        justify-content: center;
    }}
    [data-baseweb="tab-highlight"], [data-baseweb="tab-border"],
    [data-testid="stTabs"] [role="tablist"] > div[aria-hidden="true"] {{ display: none !important; }}
    button[data-baseweb="tab"], [data-testid="stTabs"] button[role="tab"], button[data-testid="stTab"] {{
        border-radius: 980px !important;
        font-weight: 500;
        padding: 6px 18px !important;
        height: auto !important;
        outline: none !important;
        box-shadow: none !important;
        border: none !important;
        background: transparent !important;
    }}
    button[role="tab"] * {{ color: {APPLE_MUTED} !important; font-size: 13px; }}
    button[role="tab"][aria-selected="true"] {{ background-color: {APPLE_CARD_ELEVATED} !important; }}
    button[role="tab"][aria-selected="true"] * {{ color: {APPLE_TEXT} !important; font-weight: 600; }}
    div[class*="st-key-card-"] {{
        background: {APPLE_CARD} !important;
        border: 1px solid {APPLE_BORDER};
        border-radius: 22px;
        padding: 18px 20px;
        box-sizing: border-box;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.42);
        margin-bottom: 16px;
    }}
</style>
""", unsafe_allow_html=True)

# Plotly only re-fits on a window "resize" event. Streamlit does not fire one when the sidebar is
# opened/closed or a tab is shown, so charts kept their old width. This tiny script fires it.
try:
    import streamlit.components.v1 as components
    components.html("""
    <script>
    (function () {
      const p = window.parent, doc = p.document;
      const fire = () => { clearTimeout(p.__panelT); p.__panelT = setTimeout(() => p.dispatchEvent(new p.Event('resize')), 80); };
      if (p.__panelRO) { p.__panelRO.disconnect(); }
      p.__panelRO = new p.ResizeObserver(fire);
      ['[data-testid="stMain"]', '[data-testid="stMainBlockContainer"]', '[data-testid="stSidebar"]'].forEach(sel => {
        const el = doc.querySelector(sel); if (el) p.__panelRO.observe(el);
      });
      if (!p.__panelClick) {
        p.__panelClick = true;
        doc.addEventListener('click', e => {
          if (e.target.closest('[role="tab"], [data-testid="stSidebarCollapseButton"], [data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"]')) {
            setTimeout(fire, 150); setTimeout(fire, 450);
          }
        });
      }
      fire();
    })();
    </script>
    """, height=0)
except Exception:
    pass

# ----------------------------------------------------------------------------
# Path Resolution & Module Loading
# ----------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))

def find_project_paths():
    candidates = [HERE, os.path.dirname(HERE), os.path.dirname(os.path.dirname(HERE))]
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
    if not os.path.isfile(fpath):
        raise FileNotFoundError(f"Visualization module not found: {fpath}")
    spec = importlib.util.spec_from_file_location(mod_name, fpath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load visualization module from: {fpath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module

hmap = mtrend = obox = None
try:
    cmap = load_viz_module("choropleth_map", "choropleth_map.py")
    if USE_MODULE_CHARTS:
        hmap = load_viz_module("heatmap_matrix", "Heatmap matrix.py")
        mtrend = load_viz_module("multitrend_list_chart", "multitrend list chart.py")
        obox = load_viz_module("outlier_box_plot", "Outlier box plot.py")
except Exception as exc:
    st.error(f"Could not load the visualization modules from `{VIZ_DIR}`: {exc}")
    st.stop()

# ----------------------------------------------------------------------------
# Data Loading & Auto-Generation for Cloud Deployment (2016–2025)
# ----------------------------------------------------------------------------
REQUIRED_COLS = {"country", "geo_code", "year", "renewable_share_pct"}
TARGET_LAST_YEAR = 2025

def find_csvs():
    search_dirs = [HERE, PROJECT_ROOT, os.path.join(PROJECT_ROOT, "data"), os.path.join(PROJECT_ROOT, "data", "raw"), os.path.join(PROJECT_ROOT, "data", "processed")]
    found = []
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if fname.lower().endswith(".csv") and "renewable" in fname.lower():
                found.append(os.path.join(d, fname))
    return found

def _normalize(frame):
    frame = frame.copy()
    if "is_aggregate" not in frame.columns:
        frame["is_aggregate"] = frame["geo_code"].astype(str).str.startswith(("EU", "EA"))
    return frame

def _span(frame):
    yrs = pd.to_numeric(frame["year"], errors="coerce").dropna()
    return (int(yrs.max()) if len(yrs) else 0, len(frame))

@st.cache_data
def load_dataset():
    # Collect every candidate dataset and keep the one that reaches the latest year,
    # so an older CSV (e.g. ending in 2023) can never shadow a newer one.
    candidates = []
    if hasattr(cmap, "load_data"):
        try:
            frame = cmap.load_data(extra_roots=[HERE, PROJECT_ROOT, os.path.join(PROJECT_ROOT, "data")])
            if REQUIRED_COLS.issubset(frame.columns):
                candidates.append(_normalize(frame))
        except Exception:
            pass
    for path in find_csvs():
        try:
            frame = pd.read_csv(path)
            if REQUIRED_COLS.issubset(frame.columns):
                candidates.append(_normalize(frame))
        except Exception:
            continue
    if candidates:
        return max(candidates, key=_span), False

    # Fallback Data Generator up to 37 nations and 2016-2025
    rng = np.random.default_rng(7)
    countries = [
        ("Sweden", "SE"), ("Finland", "FI"), ("Latvia", "LV"), ("Denmark", "DK"),
        ("Austria", "AT"), ("Portugal", "PT"), ("Croatia", "HR"), ("Lithuania", "LT"),
        ("Estonia", "EE"), ("Romania", "RO"), ("Spain", "ES"), ("Greece", "EL"),
        ("Slovenia", "SI"), ("Bulgaria", "BG"), ("Germany", "DE"), ("Italy", "IT"),
        ("France", "FR"), ("Slovakia", "SK"), ("Czechia", "CZ"), ("Poland", "PL"),
        ("Hungary", "HU"), ("Netherlands", "NL"), ("Belgium", "BE"), ("Ireland", "IE"),
        ("Luxembourg", "LU"), ("Malta", "MT"), ("Norway", "NO"), ("Iceland", "IS"),
        ("Switzerland", "CH"), ("Montenegro", "ME"), ("Serbia", "RS"), ("Albania", "AL"),
        ("North Macedonia", "MK"), ("Bosnia and Herzegovina", "BA"), ("Turkey", "TR"),
        ("United Kingdom", "UK"), ("Cyprus", "CY")
    ]
    years = list(range(2016, TARGET_LAST_YEAR + 1))
    rows = []
    for idx, (c, code) in enumerate(countries):
        base = 52 - (idx * 1.0)
        for y_i, y in enumerate(years):
            val = max(4.5, round(base + y_i * rng.uniform(0.5, 1.4), 2))
            rows.append({"country": c, "geo_code": code, "year": y, "renewable_share_pct": val, "data_flag": "Demo", "is_aggregate": False})

    for y_i, y in enumerate(years):
        rows.append({"country": "European Union - 27 countries (from 2020)", "geo_code": "EU27_2020", "year": y, "renewable_share_pct": round(17.8 + y_i * 0.75, 2), "data_flag": "Demo", "is_aggregate": True})

    df_generated = pd.DataFrame(rows)
    proc_dir = os.path.join(PROJECT_ROOT, "data", "processed")
    out_csv = os.path.join(proc_dir, "renewable_energy_shares.csv")
    try:
        os.makedirs(proc_dir, exist_ok=True)
        df_generated.to_csv(out_csv, index=False)
    except Exception:
        pass

    return df_generated, True

def fallback_enrich(raw_df):
    non_agg = raw_df[~raw_df["is_aggregate"]].copy().sort_values(["country", "year"])
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

MAP_METRICS = getattr(cmap, "MAP_METRICS", {
    "Renewable Share (%)": {"col": "renewable_share_pct", "suffix": "%"},
    "YoY Change (pp)": {"col": "yoy_change", "suffix": " pp"},
    "Change Since Base (pp)": {"col": "change_since_base", "suffix": " pp"},
    "Gap vs EU-27 (pp)": {"col": "vs_eu_avg", "suffix": " pp"},
})
if USE_MODULE_CHARTS:
    TREND_MODES = getattr(mtrend, "TREND_MODES", ["Absolute Share (%)", "Indexed (Base = 100)", "YoY Change (pp)"])
    HEATMAP_VIEWS = getattr(hmap, "HEATMAP_VIEWS", ["Renewable Share (%)", "YoY Change (pp)", "Gap vs EU-27 (pp)"])
else:
    TREND_MODES = ["Absolute Share (%)", "Indexed (Base = 100)", "YoY Change (pp)"]
    HEATMAP_VIEWS = ["Renewable Share (%)", "YoY Change (pp)", "Change Since Base (pp)", "Gap vs EU-27 (pp)"]

COUNTRIES = sorted(d_all["country"].dropna().unique())
DATA_YEARS = sorted(int(y) for y in d_all["year"].dropna().unique())
YR_FULL = (DATA_YEARS[0], DATA_YEARS[-1])                      # years that actually have data
YEARS = list(range(min(DATA_YEARS[0], 2016), max(DATA_YEARS[-1], TARGET_LAST_YEAR) + 1))  # slider always reaches 2025
LATEST = YEARS[-1]
DEFAULT_SEL = sorted(c for c in ["Germany", "France", "Hungary", "Sweden", "Poland"] if c in COUNTRIES) or COUNTRIES[:5]

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def show_plot(fig, key):
    """Render a Plotly figure full-width; works across Streamlit versions."""
    try:
        st.plotly_chart(fig, width="stretch", key=key, config={"displaylogo": False, "responsive": True})
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, key=key, config={"displaylogo": False, "responsive": True})

def show_table(data, key, **kwargs):
    try:
        st.dataframe(data, width="stretch", key=key, **kwargs)
    except TypeError:
        st.dataframe(data, use_container_width=True, key=key, **kwargs)

def apply_apple_plotly_theme(fig, uirev=None, preserve_geo=False):
    if not isinstance(fig, go.Figure):
        return fig
    layout_kw = dict(
        autosize=True,
        transition=dict(duration=0),
        paper_bgcolor=APPLE_CARD,
        plot_bgcolor=APPLE_CARD,
        font=dict(family=APPLE_FONT, color=APPLE_TEXT, size=13),
        hoverlabel=dict(bgcolor="#2C2C2E", bordercolor="rgba(255,255,255,0.16)", font=dict(family=APPLE_FONT, color=APPLE_TEXT, size=13)),
    )
    if uirev is not None:
        layout_kw["uirevision"] = uirev
    fig.update_layout(**layout_kw)
    if "geo" in fig.layout and not preserve_geo:
        fig.update_geos(bgcolor=APPLE_CARD, lakecolor=APPLE_CARD, oceancolor=APPLE_CARD)
    return fig

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
    if isinstance(fig, go.Figure) and fig.layout.title.text:
        fig.update_layout(title=dict(x=0.5, xanchor="center"))
    return apply_apple_plotly_theme(fig, uirev=uirev, preserve_geo=preserve_geo)

def safe_viz(fn, primary_arg, label, height, **kwargs):
    """call_viz wrapper: never crashes the page, always returns a Figure."""
    try:
        fig = call_viz(fn, primary_arg, **kwargs)
    except Exception as exc:
        return error_fig(f"{label} could not be rendered: {exc}")
    if not isinstance(fig, go.Figure):
        return error_fig(f"{label} did not return a figure.")
    fig.update_layout(height=height)
    return fig

# ----------------------------------------------------------------------------
# Chart Builders
# ----------------------------------------------------------------------------
def error_fig(msg):
    f = go.Figure()
    f.add_annotation(text=msg, showarrow=False, font=dict(size=14, color=APPLE_MUTED, family=APPLE_FONT))
    f.update_layout(template="plotly_dark", paper_bgcolor=APPLE_CARD, plot_bgcolor=APPLE_CARD, height=400,
                    xaxis=dict(visible=False), yaxis=dict(visible=False))
    return f

def build_map_with_target(year, metric_name, selected, target_pct):
    try:
        fig = call_viz(cmap.create_choropleth_map, df, preserve_geo=True, year=year, selected_year=year, metric=metric_name, selected_countries=selected, target_pct=target_pct, include_controls=False, uirev=f"map-{metric_name}")
    except Exception as exc:
        return error_fig(f"Map could not be rendered: {exc}")
    if isinstance(fig, go.Figure):
        sub = d_all[(d_all["year"] == year) & d_all["renewable_share_pct"].notna()]
        met_cnt = int((sub["renewable_share_pct"] >= target_pct).sum()) if target_pct > 0 else 0
        tot_cnt = len(sub)
        title_text = f"<b>EUROPEAN RENEWABLE ENERGY SHARE · {year}</b>"
        if target_pct > 0:
            title_text += f"<br><span style='font-size:12.5px;color:{APPLE_GREEN};font-weight:500;'>Policy Target ({target_pct}%): {met_cnt}/{tot_cnt} nations above target</span>"
        fig.update_layout(title=dict(text=title_text, x=0.5, xanchor="center", font=dict(size=16)), height=820)
        return fig
    return error_fig("Map did not return a figure.")

def build_ranking_bar(year, metric_name, selected, target_pct):
    metric_cfg = MAP_METRICS.get(metric_name, next(iter(MAP_METRICS.values())))
    col = metric_cfg["col"]
    suffix = metric_cfg.get("suffix", "")
    sub = d_all[(d_all["year"] == year) & d_all[col].notna()].sort_values(col, ascending=True)
    if sub.empty:
        return error_fig(f"No {metric_name} data available for {year}.")
    sel_set = set(selected or [])
    colors = [APPLE_AMBER if c in sel_set else (APPLE_BLUE if v >= 0 else APPLE_RED) for c, v in zip(sub["country"], sub[col])]
    target_x = None
    target_label = f"Target {target_pct}%"
    if target_pct > 0 and col == "renewable_share_pct":
        target_x = float(target_pct)
    vmin, vmax = float(sub[col].min()), float(sub[col].max())
    if target_x is not None:
        vmax = max(vmax, target_x)
    span = max(vmax - min(vmin, 0.0), 1.0)
    x_lo, x_hi = (vmin - span * 0.08) if vmin < 0 else 0.0, vmax + span * 0.32
    fig = go.Figure(go.Bar(
        x=sub[col], y=sub["country"], orientation="h",
        marker=dict(color=colors, line=dict(color=APPLE_CARD, width=0.8), cornerradius=6),
        text=[f"{v:+.1f}{suffix}" if vmin < 0 else f"{v:.1f}{suffix}" for v in sub[col]],
        textposition=["inside" if v < 0 else "outside" for v in sub[col]],
        insidetextanchor="end", textfont=dict(size=11, color="#F5F5F7"),
        hovertemplate="<b>%{y}</b> (" + str(year) + ")<br>" + metric_name + ": <b>%{x:.2f}" + suffix + "</b><extra></extra>",
    ))
    if target_x is not None and target_x > 0:
        fig.add_vline(x=target_x, line_dash="dot", line_color=APPLE_GREEN, line_width=2.0, annotation_text=target_label, annotation_position="top right")

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=120, r=40, t=50, b=40),
        height=820,
        title=dict(text=f"<b>Country Ranking · {year}</b>", font=dict(size=15, color=APPLE_TEXT), x=0.5, xanchor="center"),
        xaxis=dict(range=[x_lo, x_hi], showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(showgrid=False)
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
    order = list(mdf["country"])
    fig = go.Figure()
    for _, r in mdf.iterrows():
        c = r["country"]
        is_sel = c in sel_set
        line_col = APPLE_AMBER if is_sel else (APPLE_GREEN if r["delta"] >= 0 else APPLE_RED)
        fig.add_trace(go.Scatter(x=[r["v0"], r["v1"]], y=[c, c], mode="lines", line=dict(color=line_col, width=3.8 if is_sel else 2.0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=mdf["v0"], y=mdf["country"], mode="markers", name=f"Start ({start_yr})", cliponaxis=False,
                             marker=dict(size=9, color=APPLE_CARD, line=dict(color="#8E8E93", width=2.2)),
                             hovertemplate="<b>%{y}</b><br>Start: %{x:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=mdf["v1"], y=mdf["country"], mode="markers+text", name=f"End ({end_yr})", cliponaxis=False,
                             text=[f" {d:+.1f} pp" for d in mdf["delta"]], textposition="middle right", textfont=dict(size=11, color="#E5E5EA"),
                             marker=dict(size=11, color=[APPLE_AMBER if c in sel_set else APPLE_BLUE for c in mdf["country"]]),
                             hovertemplate="<b>%{y}</b><br>End: %{x:.1f}%<extra></extra>"))
    lo = float(min(mdf["v0"].min(), mdf["v1"].min()))
    hi = float(max(mdf["v0"].max(), mdf["v1"].max()))
    fig.update_layout(
        template="plotly_dark", margin=dict(l=150, r=40, t=120, b=60),
        title=dict(text=f"<b>Net Trajectory ({start_yr}–{end_yr})</b>", font=dict(size=16, color=APPLE_TEXT), x=0.5, xanchor="center", y=0.97, yanchor="top"),
        xaxis=dict(title="Renewable Share (%)", ticksuffix="%", range=[max(0, lo - 4), hi + 9], showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(type="category", categoryorder="array", categoryarray=order, tickmode="linear", dtick=1, showgrid=False, automargin=True),
        legend=dict(orientation="h", x=1, xanchor="right", y=1.0, yanchor="bottom", bgcolor="rgba(0,0,0,0)"),
        height=max(650, 24 * len(order) + 170),
    )
    return apply_apple_plotly_theme(fig, uirev=f"movers-{start_yr}-{end_yr}")

# ---- native chart builders for Trends / Matrix / Spread (driven by the Streamlit controls) ----
PALETTE = ["#0A84FF", "#30D158", "#FFD60A", "#FF453A", "#BF5AF2", "#64D2FF", "#FF9F0A", "#AC8E68", "#5E5CE6", "#FF375F"]

def _share_pivot():
    """rows = year, columns = country (aggregates excluded)."""
    return d_all.pivot_table(index="year", columns="country", values="renewable_share_pct", aggfunc="mean").sort_index()

def _eu_series():
    if "eu_avg_pct" in d_all.columns:
        s = d_all.groupby("year")["eu_avg_pct"].first().dropna()
        if not s.empty:
            return s.sort_index()
    eu = df[df["geo_code"].astype(str).str.startswith("EU27")]
    return eu.groupby("year")["renewable_share_pct"].mean().sort_index()

def _chart_title(main, sub=None):
    t = f"<b>{main}</b>"
    if sub:
        t += f"<br><span style='font-size:12px;color:{APPLE_MUTED};font-weight:400;'>{sub}</span>"
    return dict(text=t, x=0.5, xanchor="center", font=dict(size=18, color=APPLE_TEXT))

def build_trend(mode, selected, show_eu, show_target, target_pct, yr_win):
    p = _share_pivot()
    p = p[(p.index >= yr_win[0]) & (p.index <= yr_win[1])]
    eu = _eu_series().reindex(p.index)
    if p.empty:
        return error_fig("No data available for the chosen years.")
    m = mode.lower()
    if "index" in m:
        kind, ytitle = "index", "Index (first year = 100)"
        tf = lambda x: x.div(x.bfill().iloc[0]) * 100
    elif "yoy" in m or "year" in m:
        kind, ytitle = "yoy", "Year-over-year change (pp)"
        tf = lambda x: x.diff()
    else:
        kind, ytitle = "abs", "Renewable share (%)"
        tf = lambda x: x
    latest = p.ffill().iloc[-1].sort_values(ascending=False)
    chosen = [c for c in (selected or []) if c in p.columns]
    note = f"{len(chosen)} selected countries"
    if not chosen:
        chosen = list(latest.head(10).index)
        note = "no countries selected · showing the top 10 by latest share"
    chosen = [c for c in latest.index if c in chosen]          # ranked by latest share
    tp = tf(p)
    fig = go.Figure()
    for i, c in enumerate(chosen):
        fig.add_trace(go.Scatter(
            x=tp.index, y=tp[c], mode="lines+markers", name=f"#{list(latest.index).index(c) + 1} {c}",
            line=dict(color=PALETTE[i % len(PALETTE)], width=2.4), marker=dict(size=5),
            hovertemplate=f"<b>{c}</b> (%{{x}})<br>%{{y:.2f}}<extra></extra>",
        ))
    if show_eu and not eu.dropna().empty:
        te = tf(eu.to_frame("eu"))["eu"]
        fig.add_trace(go.Scatter(x=te.index, y=te, mode="lines", name="EU-27 average",
                                 line=dict(color="#FFFFFF", width=2.4, dash="dash"),
                                 hovertemplate="<b>EU-27 average</b> (%{x})<br>%{y:.2f}<extra></extra>"))
    if show_target and kind == "abs" and target_pct > 0:
        fig.add_hline(y=target_pct, line_dash="dot", line_color=APPLE_GREEN, line_width=2,
                      annotation_text=f"Policy Target ({target_pct}%)", annotation_font_color=APPLE_GREEN)
    if kind == "yoy":
        fig.add_hline(y=0, line_color="rgba(255,255,255,0.25)", line_width=1)
    fig.update_layout(
        template="plotly_dark", height=600, margin=dict(l=70, r=30, t=95, b=60),
        title=_chart_title("RENEWABLE SHARE · TRENDS BY COUNTRY", f"{note} · click a legend entry to hide it, double-click to isolate"),
        xaxis=dict(title="Year", dtick=1, showgrid=False),
        yaxis=dict(title=ytitle, ticksuffix="%" if kind == "abs" else "", showgrid=True, gridcolor="rgba(255,255,255,0.06)", rangemode="normal" if kind != "abs" else "tozero"),
        legend=dict(bgcolor="#0B1426", bordercolor="rgba(10,132,255,0.45)", borderwidth=1, font=dict(size=11)),
    )
    return apply_apple_plotly_theme(fig, uirev=f"trend-{mode}")

def build_heatmap(view, selected, only_selected, yr_win):
    p = _share_pivot()
    p = p[(p.index >= yr_win[0]) & (p.index <= yr_win[1])]
    if p.empty:
        return error_fig("No data available for the chosen years.")
    latest = p.ffill().iloc[-1].sort_values(ascending=False)
    v = view.lower()
    if "yoy" in v or "year" in v:
        z, cbar, fmt, diverging = p.diff(), "YoY (pp)", ".1f", True
    elif "gap" in v:
        z, cbar, fmt, diverging = p.sub(_eu_series().reindex(p.index), axis=0), "Gap vs EU-27 (pp)", ".1f", True
    elif "change" in v or "base" in v:
        z, cbar, fmt, diverging = p - p.bfill().iloc[0], f"Change since {int(p.index[0])} (pp)", ".1f", True
    else:
        z, cbar, fmt, diverging = p, "Share (%)", ".0f", False
    countries = list(latest.index)
    if only_selected:
        countries = [c for c in countries if c in set(selected or [])]
        if not countries:
            return error_fig("Select at least one country to use “Only selected countries”.")
    z = z[countries].T
    sel_set = set(selected or [])
    labels = [f"<b>{c}</b>" if c in sel_set else c for c in countries]
    colorscale = [[0, "#FF453A"], [0.5, "#2C2C2E"], [1, "#30D158"]] if diverging else "Viridis"
    hm = go.Heatmap(
        z=z.values, x=[str(int(y)) for y in z.columns], y=labels, colorscale=colorscale,
        xgap=1, ygap=1, texttemplate=f"%{{z:{fmt}}}", textfont=dict(size=10, color="#FFFFFF"),
        hovertemplate="<b>%{y}</b> (%{x})<br>" + cbar + ": %{z:.2f}<extra></extra>",
        colorbar=dict(title=dict(text=cbar, font=dict(size=13)), bgcolor="#0B1426", bordercolor="rgba(10,132,255,0.45)", borderwidth=1, thickness=14, len=0.6),
        **({"zmid": 0} if diverging else {}),
    )
    fig = go.Figure(hm)
    fig.update_layout(
        template="plotly_dark", height=max(520, 21 * len(countries) + 170), margin=dict(l=160, r=30, t=100, b=30),
        title=_chart_title("RENEWABLE ENERGY SHARE · MATRIX", "Countries ranked by latest share · blank cell = not reported"),
        xaxis=dict(side="top", type="category", showgrid=False),
        yaxis=dict(autorange="reversed", type="category", tickmode="linear", dtick=1, showgrid=False, automargin=True),
    )
    return apply_apple_plotly_theme(fig, uirev=f"heat-{view}-{only_selected}")

def build_box(selected, show_all, yr_win):
    sub = d_all[d_all["renewable_share_pct"].notna() & d_all["year"].between(yr_win[0], yr_win[1])]
    if sub.empty:
        return error_fig("No data available for the chosen years.")
    fig = go.Figure()
    years = sorted(int(y) for y in sub["year"].unique())
    for y in years:
        g = sub[sub["year"] == y]
        fig.add_trace(go.Box(
            y=g["renewable_share_pct"], name=str(y), text=g["country"],
            boxpoints="all" if show_all else "outliers", jitter=0.45, pointpos=0,
            line=dict(color=APPLE_BLUE, width=1.6), fillcolor="rgba(10,132,255,0.18)",
            marker=dict(color="#8E8E93", size=5, opacity=0.7, outliercolor=APPLE_RED),
            hovertemplate="<b>%{text}</b><br>%{y:.1f}%<extra>" + str(y) + "</extra>", showlegend=False,
        ))
    for i, c in enumerate(selected or []):
        g = sub[sub["country"] == c].sort_values("year")
        if g.empty:
            continue
        fig.add_trace(go.Scatter(
            x=[str(int(y)) for y in g["year"]], y=g["renewable_share_pct"], mode="lines+markers", name=c,
            line=dict(color=PALETTE[(i + 2) % len(PALETTE)], width=2), marker=dict(size=8, line=dict(color="#000", width=1)),
            hovertemplate=f"<b>{c}</b> (%{{x}})<br>%{{y:.1f}}%<extra></extra>",
        ))
    fig.update_layout(
        template="plotly_dark", height=600, margin=dict(l=70, r=30, t=95, b=60),
        title=_chart_title("RENEWABLE SHARE · DISTRIBUTION & OUTLIERS BY YEAR", "box = middle 50% of countries · dots beyond the whiskers are outliers · selected countries drawn as lines"),
        xaxis=dict(type="category", title="Year", showgrid=False),
        yaxis=dict(title="Renewable share (%)", ticksuffix="%", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        legend=dict(bgcolor="#0B1426", bordercolor="rgba(10,132,255,0.45)", borderwidth=1),
    )
    return apply_apple_plotly_theme(fig, uirev="box-dist")

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
        gap_val = g["vs_eu_avg"].iloc[-1]
        rows.append({
            "Country": c,
            "Start (%)": round(v0, 2),
            "End (%)": round(v1, 2),
            "Change (pp)": round(v1 - v0, 2),
            "Latest Rank": f"#{int(rank_val)}" if pd.notna(rank_val) else "n/a",
            "Gap vs EU-27 (pp)": round(float(gap_val), 2) if pd.notna(gap_val) else None,
            f"Vs {target_pct}% Target": round(v1 - target_pct, 2),
        })
    cols = ["Country", "Start (%)", "End (%)", "Change (pp)", "Latest Rank", "Gap vs EU-27 (pp)", f"Vs {target_pct}% Target"]
    return pd.DataFrame(rows, columns=cols)

# ----------------------------------------------------------------------------
# Sidebar Controls & State Initialization
# ----------------------------------------------------------------------------
# Widget state lives under the widgets' own keys; button callbacks modify it
# *before* the widgets are re-instantiated, which is the supported pattern.
if "countries" not in st.session_state:
    st.session_state["countries"] = list(DEFAULT_SEL)
else:
    st.session_state["countries"] = [c for c in st.session_state["countries"] if c in COUNTRIES]

# Year / metric / target live in the sidebar AND in a slim bar on the Overview tab, so they are
# still reachable when the sidebar is closed. The two copies are kept in sync by callbacks.
st.session_state.setdefault("year_val", LATEST)
st.session_state.setdefault("year_main", st.session_state["year_val"])
st.session_state.setdefault("metric_val", list(MAP_METRICS.keys())[0])
st.session_state.setdefault("metric_main", st.session_state["metric_val"])
st.session_state.setdefault("target_val", 32)
st.session_state.setdefault("target_main", st.session_state["target_val"])

def _mirror(src_key, dst_key):
    def _cb():
        st.session_state[dst_key] = st.session_state[src_key]
    return _cb

def _set_top_leaders():
    yr = st.session_state.get("year_val", LATEST)
    top = (
        d_all[(d_all["year"] == yr) & d_all["renewable_share_pct"].notna()]
        .sort_values("renewable_share_pct", ascending=False)["country"].head(5).tolist()
    )
    st.session_state["countries"] = top

def _set_v4():
    st.session_state["countries"] = [c for c in ["Hungary", "Poland", "Czechia", "Slovakia"] if c in COUNTRIES]

def _set_top_movers():
    lo, hi = YR_FULL
    sub = d_all[d_all["year"].isin([lo, hi])].pivot(index="country", columns="year", values="renewable_share_pct").dropna()
    if not sub.empty and lo != hi:
        st.session_state["countries"] = (sub[hi] - sub[lo]).sort_values(ascending=False).head(5).index.tolist()

def _clear_all():
    st.session_state["countries"] = []

with st.sidebar:
    st.markdown("<div class='side-title'>Snapshot & Target</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='side-label'>Year (Map & Ranking): <b>{st.session_state.get('year_val', LATEST)}</b></div>", unsafe_allow_html=True)
    year_val = st.slider("Year (Map & Ranking)", min_value=YEARS[0], max_value=YEARS[-1], key="year_val", label_visibility="collapsed", on_change=_mirror("year_val", "year_main"))

    st.markdown("<div class='side-label' style='margin-top:14px;'>Map & Ranking Metric</div>", unsafe_allow_html=True)
    metric_val = st.selectbox("Map & Ranking Metric", options=list(MAP_METRICS.keys()), key="metric_val", label_visibility="collapsed", on_change=_mirror("metric_val", "metric_main"))

    st.markdown(f"<div class='side-label' style='margin-top:14px;'>Policy Target Benchmark (%): <b>{st.session_state.get('target_val', 32)}</b></div>", unsafe_allow_html=True)
    target_val = st.slider("Policy Target Benchmark (%)", min_value=10, max_value=65, key="target_val", label_visibility="collapsed", on_change=_mirror("target_val", "target_main"))

    st.markdown("---")
    st.markdown("<div class='side-title'>Comparison</div>", unsafe_allow_html=True)

    st.markdown("<div class='side-label' style='margin-bottom:6px;'>Selected Countries</div>", unsafe_allow_html=True)
    selected_countries = st.multiselect("Selected Countries", options=COUNTRIES, key="countries", label_visibility="collapsed")

    col1, col2 = st.columns(2)
    with col1:
        st.button("Top 5 Leaders", on_click=_set_top_leaders, key="btn_leaders")
        st.button("Visegrád (V4)", on_click=_set_v4, key="btn_v4")
    with col2:
        st.button("Top 5 Movers", on_click=_set_top_movers, key="btn_movers")
        st.button("Clear All", on_click=_clear_all, key="btn_clear")

    n_nations = int(d_all["country"].nunique())
    st.markdown("---")
    st.markdown("<div class='side-title'>About & Metadata</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='font-size:11.5px;color:{APPLE_MUTED};line-height:1.5;background:{APPLE_CARD_ELEVATED};border:1px solid {APPLE_BORDER};border-radius:12px;padding:12px;'>
        <strong style='color:{APPLE_TEXT};'>EU Renewable Energy Observatory</strong><br><br>
        Interactive visual analytics tracking national renewable energy shares in gross final consumption, annual momentum, and progress against EU policy benchmarks.<br><br>
        <strong style='color:{APPLE_TEXT};'>Source:</strong> Eurostat (<code style='color:{APPLE_BLUE};background:transparent;'>nrg_ind_ren</code>)<br>
        <strong style='color:{APPLE_TEXT};'>Coverage:</strong> {n_nations} nations · {YEARS[0]}–{YEARS[-1]}<br>
        <strong style='color:{APPLE_TEXT};'>Metric:</strong> Share in gross final energy (%)<br>
        <strong style='color:{APPLE_TEXT};'>Course:</strong> Data Visualization Methods<br>
        <strong style='color:{APPLE_TEXT};'>Institution:</strong> University of Debrecen
    </div>
    """, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Main Content (title lives in the top bar, see CSS)
# ----------------------------------------------------------------------------
if IS_DEMO:
    st.warning("Showing **demo data** because `renewable_energy_shares.csv` was not found in the project folder.")
elif DATA_YEARS[-1] < TARGET_LAST_YEAR:
    st.warning(f"The loaded dataset only contains data up to **{DATA_YEARS[-1]}**. Add a CSV that includes {DATA_YEARS[-1] + 1}–{TARGET_LAST_YEAR} to see those years.")

tab_overview, tab_trends, tab_movers, tab_spread, tab_matrix, tab_data = st.tabs(["Overview", "Trends", "Movers", "Spread & Outliers", "Matrix", "Data"])

with tab_overview:
    with st.container(key="card-controls"):
        k1, k2, k3 = st.columns([2, 2, 2], gap="medium")
        k1.slider("Year (Map & Ranking)", min_value=YEARS[0], max_value=YEARS[-1], key="year_main", on_change=_mirror("year_main", "year_val"))
        k2.selectbox("Map & Ranking Metric", options=list(MAP_METRICS.keys()), key="metric_main", on_change=_mirror("metric_main", "metric_val"))
        k3.slider("Policy Target Benchmark (%)", min_value=10, max_value=65, key="target_main", on_change=_mirror("target_main", "target_val"))
    col_map, col_bar = st.columns([2, 1], gap="medium")
    with col_map:
        with st.container(key="card-map"):
            show_plot(build_map_with_target(year_val, metric_val, selected_countries, target_val), "plot_map")
    with col_bar:
        with st.container(key="card-ranking"):
            show_plot(build_ranking_bar(year_val, metric_val, selected_countries, target_val), "plot_ranking")

with tab_trends:
    with st.container(key="card-trend"):
        t_mode = st.selectbox("Trend View Mode", options=TREND_MODES, key="t_mode_sel")
        c1, c2, c3 = st.columns(3)
        s_eu = c1.checkbox("Show EU-27 average line", value=True, key="show_eu")
        s_tgt = c2.checkbox("Show Policy Target line", value=True, key="show_tgt")

        if USE_MODULE_CHARTS:
            fig_trend = safe_viz(
                mtrend.create_multitrend, df, "Trend chart", 600,
                uirev=f"trend-{t_mode}", selected_countries=selected_countries, trend_mode=t_mode,
                year_range=YR_FULL, show_eu=s_eu, include_controls=False,
            )
            if s_tgt and "Absolute" in t_mode and target_val > 0:
                fig_trend.add_hline(y=target_val, line_dash="dot", line_color=APPLE_GREEN, annotation_text=f"Policy Target ({target_val}%)")
        else:
            fig_trend = build_trend(t_mode, selected_countries, s_eu, s_tgt, target_val, YR_FULL)
        show_plot(fig_trend, "plot_trend")

    with st.container(key="card-summary"):
        st.markdown(f"<div style='font-size:15px;font-weight:600;color:{APPLE_TEXT};margin-bottom:8px;'>Selected Countries Summary</div>", unsafe_allow_html=True)
        stats_df = country_stats_table(selected_countries, YR_FULL, target_val)
        show_table(stats_df, "tbl_summary", hide_index=True)

with tab_movers:
    with st.container(key="card-movers"):
        st.markdown(f"<div style='text-align:center;color:{APPLE_MUTED};font-size:13px;margin-bottom:6px;'>Hollow dot = start of window · Filled dot = end of window</div>", unsafe_allow_html=True)
        show_plot(build_movers_dumbbell(YR_FULL, selected_countries), "plot_movers")

with tab_spread:
    with st.container(key="card-spread"):
        show_pts = st.checkbox("Show all countries as dots", value=True, key="show_pts")
        if USE_MODULE_CHARTS:
            fig_box = safe_viz(
                obox.create_outlier_box, df, "Outlier box plot", 600,
                uirev="box-dist", year_range=YR_FULL, selected_countries=selected_countries,
                show_all_points=show_pts, include_controls=False,
            )
        else:
            fig_box = build_box(selected_countries, show_pts, YR_FULL)
        show_plot(fig_box, "plot_box")

with tab_matrix:
    with st.container(key="card-matrix"):
        hm_view = st.selectbox("Matrix View", options=HEATMAP_VIEWS, key="hm_view")
        hm_only = st.checkbox("Only selected countries", value=False, key="hm_only")
        if USE_MODULE_CHARTS:
            fig_heat = safe_viz(
                hmap.create_heatmap, df, "Heatmap", 650,
                uirev=f"heat-{hm_view}", default_view=hm_view, year_range=YR_FULL,
                selected_countries=selected_countries, only_selected=hm_only, include_controls=False,
            )
        else:
            fig_heat = build_heatmap(hm_view, selected_countries, hm_only, YR_FULL)
        show_plot(fig_heat, "plot_heat")

with tab_data:
    with st.container(key="card-data"):
        d_filt = d_all.rename(columns={"renewable_share_pct": "share_pct", "yoy_change": "yoy_pp", "change_since_base": "since_base_pp", "vs_eu_avg": "gap_to_eu27_pp", "eu_avg_pct": "eu27_pct", "year_rank": "rank"})
        keep = [c for c in ["country", "geo_code", "year", "share_pct", "rank", "yoy_pp", "since_base_pp", "eu27_pct", "gap_to_eu27_pp", "data_flag"] if c in d_filt.columns]
        table_df = d_filt[keep].round(2).sort_values(["year", "rank"], ascending=[False, True])

        col_dl, col_filt = st.columns([1, 3])
        with col_dl:
            csv_data = table_df.to_csv(index=False).encode("utf-8")
            st.download_button("Export CSV", data=csv_data, file_name="renewable_share_filtered.csv", mime="text/csv", type="primary", key="dl_csv")

        show_table(table_df, "tbl_data", height=520)
