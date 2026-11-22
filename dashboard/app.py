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

st.markdown(f"""
<style>
    .stApp {{
        background-color: {APPLE_BG};
        color: {APPLE_TEXT};
        font-family: {APPLE_FONT};
    }}
    [data-testid="stSidebar"] {{
        background-color: #141416;
        border-right: 1px solid {APPLE_BORDER};
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: {APPLE_CARD};
        padding: 6px;
        border-radius: 980px;
        border: 1px solid {APPLE_BORDER};
        margin-bottom: 20px;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 980px;
        color: {APPLE_MUTED};
        font-weight: 500;
        padding: 6px 18px;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {APPLE_CARD_ELEVATED} !important;
        color: {APPLE_TEXT} !important;
        font-weight: 600;
    }}
    div.stButton > button {{
        border-radius: 980px;
        background-color: {APPLE_CARD_ELEVATED};
        color: {APPLE_TEXT};
        border: 1px solid {APPLE_BORDER};
        width: 100%;
        font-weight: 500;
        font-size: 12px;
        transition: transform 0.15s ease;
    }}
    div.stButton > button:hover {{
        border-color: rgba(255, 255, 255, 0.25);
        transform: translateY(-1px);
    }}
    div.stButton > button[kind="primary"] {{
        background-color: {APPLE_BLUE};
        color: #FFFFFF;
        border-color: {APPLE_BLUE};
    }}
</style>
""", unsafe_allow_html=True)

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
    spec = importlib.util.spec_from_file_location(mod_name, fpath)
    if not os.path.isfile(fpath):
        raise FileNotFoundError(f"Visualization module not found: {fpath}")
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
# Data Loading & Auto-Generation for Cloud Deployment
# ----------------------------------------------------------------------------
def find_csv():
    search_dirs = [HERE, PROJECT_ROOT, os.path.join(PROJECT_ROOT, "data"), os.path.join(PROJECT_ROOT, "data", "raw"), os.path.join(PROJECT_ROOT, "data", "processed")]
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if fname.lower().endswith(".csv") and "renewable" in fname.lower():
                return os.path.join(d, fname)
    return None

@st.cache_data
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

    # Fallback Data Generator for Streamlit Cloud & Offline Environments
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
            rows.append({"country": c, "geo_code": code, "year": y, "renewable_share_pct": val, "data_flag": "Demo", "is_aggregate": False})
            
    for y_i, y in enumerate(years):
        rows.append({"country": "European Union - 27 countries (from 2020)", "geo_code": "EU27_2020", "year": y, "renewable_share_pct": round(17.8 + y_i * 0.75, 2), "data_flag": "Demo", "is_aggregate": True})
        
    df_generated = pd.DataFrame(rows)
    proc_dir = os.path.join(PROJECT_ROOT, "data", "processed")
    os.makedirs(proc_dir, exist_ok=True)
    out_csv = os.path.join(proc_dir, "renewable_energy_shares.csv")
    try:
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
TREND_MODES = getattr(mtrend, "TREND_MODES", ["Absolute Share (%)", "Indexed (Base = 100)", "YoY Change (pp)"])
HEATMAP_VIEWS = getattr(hmap, "HEATMAP_VIEWS", ["Renewable Share (%)", "YoY Change (pp)", "Gap vs EU-27 (pp)"])

COUNTRIES = sorted(d_all["country"].dropna().unique())
YEARS = sorted(int(y) for y in d_all["year"].dropna().unique())
LATEST = YEARS[-1]
DEFAULT_SEL = [c for c in ["Germany", "France", "Hungary", "Sweden", "Poland"] if c in COUNTRIES] or COUNTRIES[:5]

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

# ----------------------------------------------------------------------------
# Chart Builders
# ----------------------------------------------------------------------------
def error_fig(msg):
    f = go.Figure()
    f.add_annotation(text=msg, showarrow=False, font=dict(size=14, color=APPLE_MUTED, family=APPLE_FONT))
    f.update_layout(template="plotly_dark", paper_bgcolor=APPLE_CARD, plot_bgcolor=APPLE_CARD)
    return f

def build_map_with_target(year, metric_name, selected, target_pct):
    fig = call_viz(cmap.create_choropleth_map, df, preserve_geo=True, year=year, selected_year=year, metric=metric_name, selected_countries=selected, target_pct=target_pct, include_controls=False, uirev=f"map-{metric_name}")
    if isinstance(fig, go.Figure):
        sub = d_all[(d_all["year"] == year) & d_all["renewable_share_pct"].notna()]
        met_cnt = int((sub["renewable_share_pct"] >= target_pct).sum()) if target_pct > 0 else 0
        tot_cnt = len(sub)
        title_text = f"<b>EUROPEAN RENEWABLE ENERGY SHARE · {year}</b>"
        if target_pct > 0:
            title_text += f"<br><span style='font-size:12.5px;color:{APPLE_GREEN};font-weight:500;'>Policy Target ({target_pct}%): {met_cnt}/{tot_cnt} nations above target</span>"
        fig.update_layout(title=dict(text=title_text, x=0.5, xanchor="center", font=dict(size=16)), height=820)
    return fig

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
    fig = go.Figure()
    for _, r in mdf.iterrows():
        c = r["country"]
        is_sel = c in sel_set
        line_col = APPLE_AMBER if is_sel else (APPLE_GREEN if r["delta"] >= 0 else APPLE_RED)
        fig.add_trace(go.Scatter(x=[r["v0"], r["v1"]], y=[c, c], mode="lines", line=dict(color=line_col, width=3.8 if is_sel else 2.0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=mdf["v0"], y=mdf["country"], mode="markers", name=f"Start ({start_yr})", marker=dict(size=9, color=APPLE_CARD, line=dict(color="#8E8E93", width=2.2))))
    fig.add_trace(go.Scatter(x=mdf["v1"], y=mdf["country"], mode="markers+text", name=f"End ({end_yr})", text=[f" {d:+.1f} pp" for d in mdf["delta"]], textposition="middle right", textfont=dict(size=11, color="#E5E5EA"), marker=dict(size=11, color=[APPLE_AMBER if c in sel_set else APPLE_BLUE for c in mdf["country"]])))
    fig.update_layout(template="plotly_dark", margin=dict(l=130, r=60, t=60, b=50), title=dict(text=f"<b>Net Trajectory ({start_yr}–{end_yr})</b>", font=dict(size=16, color=APPLE_TEXT), x=0.5), xaxis=dict(title="Renewable Share (%)", ticksuffix="%"), yaxis=dict(showgrid=False), height=650)
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
# Sidebar Controls & State Initialization
# ----------------------------------------------------------------------------
if "countries" not in st.session_state:
    st.session_state["countries"] = DEFAULT_SEL

with st.sidebar:
    st.markdown(f"<div style='font-size:11px;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;color:{APPLE_MUTED};margin-bottom:6px;'>Snapshot & Target</div>", unsafe_allow_html=True)
    year_val = st.slider("Year (Map & Ranking)", min_value=YEARS[0], max_value=YEARS[-1], value=LATEST)
    metric_val = st.selectbox("Map & Ranking Metric", options=list(MAP_METRICS.keys()))
    target_val = st.slider("Policy Target Benchmark (%)", min_value=10, max_value=65, value=32)
    
    st.markdown("---")
    st.markdown(f"<div style='font-size:11px;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;color:{APPLE_MUTED};margin-bottom:6px;'>Comparison</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Top 5 Leaders"):
            top = d_all[(d_all["year"] == year_val) & d_all["renewable_share_pct"].notna()].sort_values("renewable_share_pct", ascending=False)["country"].head(5).tolist()
            st.session_state["countries"] = top
            st.rerun()
        if st.button("Visegrád (V4)"):
            st.session_state["countries"] = [c for c in ["Hungary", "Poland", "Czechia", "Slovakia"] if c in COUNTRIES]
            st.rerun()
    with col2:
        if st.button("Top 5 Movers"):
            lo, hi = YEARS[0], YEARS[-1]
            sub = d_all[d_all["year"].isin([lo, hi])].pivot(index="country", columns="year", values="renewable_share_pct").dropna()
            if not sub.empty and lo != hi:
                st.session_state["countries"] = (sub[hi] - sub[lo]).sort_values(ascending=False).head(5).index.tolist()
                st.rerun()
        if st.button("Clear All"):
            st.session_state["countries"] = []
            st.rerun()

    selected_countries = st.multiselect("Selected Countries", options=COUNTRIES, default=st.session_state["countries"])
    st.session_state["countries"] = selected_countries

    st.markdown("---")
    st.markdown(f"""
    <div style='font-size:11.5px;color:{APPLE_MUTED};line-height:1.5;background:{APPLE_CARD_ELEVATED};border:1px solid {APPLE_BORDER};border-radius:12px;padding:12px;'>
        <strong style='color:{APPLE_TEXT};'>EU Renewable Energy Observatory</strong><br><br>
        <strong>Source:</strong> Eurostat (<code>nrg_ind_ren</code>)<br>
        <strong>Coverage:</strong> {len(COUNTRIES)} nations · {YEARS[0]}–{YEARS[-1]}<br>
        <strong>Institution:</strong> University of Debrecen
    </div>
    """, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Main Content & Tabs
# ----------------------------------------------------------------------------
if IS_DEMO:
    st.warning("Showing **demo data** because `renewable_energy_shares.csv` was not found in the project folder.")

tab_overview, tab_trends, tab_movers, tab_spread, tab_matrix, tab_data = st.tabs(["Overview", "Trends", "Movers", "Spread & Outliers", "Matrix", "Data"])

with tab_overview:
    col_map, col_bar = st.columns([2, 1], gap="medium")
    with col_map:
        st.markdown(f"<div style='background:{APPLE_CARD};border:1px solid {APPLE_BORDER};border-radius:22px;padding:18px;'>", unsafe_allow_html=True)
        fig_map = build_map_with_target(year_val, metric_val, selected_countries, target_val)
        st.plotly_chart(fig_map, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_bar:
        st.markdown(f"<div style='background:{APPLE_CARD};border:1px solid {APPLE_BORDER};border-radius:22px;padding:18px;'>", unsafe_allow_html=True)
        fig_bar = build_ranking_bar(year_val, metric_val, selected_countries, target_val)
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

with tab_trends:
    st.markdown(f"<div style='background:{APPLE_CARD};border:1px solid {APPLE_BORDER};border-radius:22px;padding:18px;'>", unsafe_allow_html=True)
    t_mode = st.selectbox("Trend View Mode", options=TREND_MODES, key="t_mode_sel")
    c1, c2, c3 = st.columns(3)
    s_eu = c1.checkbox("Show EU-27 average line", value=True)
    s_tgt = c2.checkbox("Show Policy Target line", value=True)
    
    fig_trend = call_viz(mtrend.create_multitrend, df, uirev=f"trend-{t_mode}", selected_countries=selected_countries, trend_mode=t_mode, year_range=(YEARS[0], YEARS[-1]), show_eu=s_eu, include_controls=False)
    if isinstance(fig_trend, go.Figure) and s_tgt and "Absolute" in t_mode and target_val > 0:
        fig_trend.add_hline(y=target_val, line_dash="dot", line_color=APPLE_GREEN, annotation_text=f"Policy Target ({target_val}%)")
    fig_trend.update_layout(height=600)
    st.plotly_chart(fig_trend, use_container_width=True)
    
    st.markdown("---")
    st.markdown(f"<div style='font-size:15px;font-weight:600;color:{APPLE_TEXT};margin-bottom:8px;'>Selected Countries Summary</div>", unsafe_allow_html=True)
    stats_df = country_stats_table(selected_countries, (YEARS[0], YEARS[-1]), target_val)
    st.dataframe(stats_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab_movers:
    st.markdown(f"<div style='background:{APPLE_CARD};border:1px solid {APPLE_BORDER};border-radius:22px;padding:18px;'>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center;color:{APPLE_MUTED};font-size:13px;margin-bottom:6px;'>Hollow dot = start of window · Filled dot = end of window</div>", unsafe_allow_html=True)
    fig_movers = build_movers_dumbbell((YEARS[0], YEARS[-1]), selected_countries)
    st.plotly_chart(fig_movers, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab_spread:
    st.markdown(f"<div style='background:{APPLE_CARD};border:1px solid {APPLE_BORDER};border-radius:22px;padding:18px;'>", unsafe_allow_html=True)
    show_pts = st.checkbox("Show all countries as dots", value=True)
    fig_box = call_viz(obox.create_outlier_box, df, uirev="box-dist", year_range=(YEARS[0], YEARS[-1]), selected_countries=selected_countries, show_all_points=show_pts, include_controls=False)
    fig_box.update_layout(height=600)
    st.plotly_chart(fig_box, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab_matrix:
    st.markdown(f"<div style='background:{APPLE_CARD};border:1px solid {APPLE_BORDER};border-radius:22px;padding:18px;'>", unsafe_allow_html=True)
    hm_view = st.selectbox("Matrix View", options=HEATMAP_VIEWS)
    hm_only = st.checkbox("Only selected countries", value=False)
    fig_heat = call_viz(hmap.create_heatmap, df, uirev=f"heat-{hm_view}", default_view=hm_view, year_range=(YEARS[0], YEARS[-1]), selected_countries=selected_countries, only_selected=hm_only, include_controls=False)
    fig_heat.update_layout(height=650)
    st.plotly_chart(fig_heat, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab_data:
    st.markdown(f"<div style='background:{APPLE_CARD};border:1px solid {APPLE_BORDER};border-radius:22px;padding:18px;'>", unsafe_allow_html=True)
    d_filt = d_all.rename(columns={"renewable_share_pct": "share_pct", "yoy_change": "yoy_pp", "change_since_base": "since_base_pp", "vs_eu_avg": "gap_to_eu27_pp", "eu_avg_pct": "eu27_pct", "year_rank": "rank"})
    keep = ["country", "geo_code", "year", "share_pct", "rank", "yoy_pp", "since_base_pp", "eu27_pct", "gap_to_eu27_pp", "data_flag"]
    table_df = d_filt[keep].round(2).sort_values(["year", "rank"], ascending=[False, True])
    
    col_dl, col_filt = st.columns([1, 3])
    with col_dl:
        csv_data = table_df.to_csv(index=False).encode("utf-8")
        st.download_button("Export CSV", data=csv_data, file_name="renewable_share_filtered.csv", mime="text/csv", type="primary")
    
    st.dataframe(table_df, use_container_width=True, height=520)
    st.markdown("</div>", unsafe_allow_html=True)
