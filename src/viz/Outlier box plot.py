"""Outlier box plot: spread of renewable share across countries, one box per year.

Run:   python "Outlier box plot.py"          (opens Outlier box plot.html)
Needs: pip install plotly pandas numpy
Outliers use the standard 1.5 x IQR rule and are labelled with the country name.
The button toggles the faint dots for all countries.
"""
import os
import sys
import webbrowser

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale

BG, PANEL, GRID = "#0B1120", "#0F172A", "#334155"


def _rgba(rgb, alpha):
    return rgb.replace("rgb(", "rgba(").replace(")", f", {alpha})")


def find_outliers(g):
    q1, q3 = np.percentile(g["renewable_share_pct"], [25, 75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    out = g[(g["renewable_share_pct"] < lo) | (g["renewable_share_pct"] > hi)]
    return out, (lo, hi)


def create_outlier_box(df):
    d = df[~df["is_aggregate"]].dropna(subset=["renewable_share_pct"])
    years = sorted(d["year"].unique())
    colors = sample_colorscale("Viridis", [0.15 + 0.7 * i / max(len(years) - 1, 1)
                                           for i in range(len(years))])
    rng = np.random.default_rng(0)

    fig = go.Figure()
    out_rows = []
    # 1) one box per year
    for yr, col in zip(years, colors):
        g = d[d["year"] == yr]
        fig.add_trace(go.Box(
            x=[yr] * len(g), y=g["renewable_share_pct"], width=0.55, name=str(yr),
            boxpoints=False, boxmean=True, line=dict(color=col, width=2),
            fillcolor=_rgba(col, 0.35), showlegend=False,
            hoverinfo="y", hoverlabel=dict(bgcolor=PANEL)))
        out, _ = find_outliers(g)
        out_rows.append(out)

    # 2) faint dots for every country (toggled by the button)
    jitter = rng.uniform(-0.22, 0.22, len(d))
    fig.add_trace(go.Scatter(
        x=d["year"] + jitter, y=d["renewable_share_pct"], mode="markers",
        marker=dict(size=6, color="#94A3B8", opacity=0.45), visible=False,
        text=d["country"], showlegend=False,
        hovertemplate="<b>%{text}</b> · %{customdata}<br>%{y:.2f}%<extra></extra>",
        customdata=d["year"]))
    all_idx = len(fig.data) - 1

    # 3) labelled outliers
    out = pd.concat(out_rows) if out_rows else d.iloc[0:0]
    fig.add_trace(go.Scatter(
        x=out["year"], y=out["renewable_share_pct"], mode="markers+text",
        text=out["country"], textposition="middle right",
        textfont=dict(size=11, color="#FCA5A5"),
        marker=dict(size=10, color="#F87171", symbol="diamond",
                    line=dict(color=BG, width=1.2)),
        customdata=out["year"], showlegend=False,
        hovertemplate="<b>%{text}</b> · %{customdata}<br>Outlier: %{y:.2f}%<extra></extra>"))
    out_idx = len(fig.data) - 1

    n_box = len(years)
    vis_outliers = [True] * n_box + [False, True]
    vis_all = [True] * n_box + [True, True]
    assert len(vis_all) == out_idx + 1 and all_idx == n_box

    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(size=13, color="#F8FAFC"),
        title=dict(
            text="<b style='font-size:21px; color:#F8FAFC;'>RENEWABLE SHARE · OUTLIERS BY YEAR</b><br>"
                 f"<span style='font-size:13px; color:#94A3B8;'>Box = middle 50% of countries · "
                 f"line = median · dashed = mean · "
                 f"<b style='color:#F87171;'>◆ outlier ({len(out)} found, 1.5×IQR rule)</b></span>",
            x=0.02, y=0.97),
        margin=dict(l=70, r=30, t=110, b=60),
        xaxis=dict(title="Year", tickmode="linear", dtick=1, showgrid=False,
                   range=[min(years) - 0.8, max(years) + 1.6]),
        yaxis=dict(title="Renewable share (%)", ticksuffix="%", gridcolor="#1E293B",
                   zeroline=False),
        updatemenus=[dict(
            type="buttons", direction="right", x=0.02, y=1.0, xanchor="left", yanchor="bottom",
            bgcolor="#1E293B", bordercolor="#38BDF8", borderwidth=1, font=dict(color="#E2E8F0"),
            pad=dict(t=2, b=2, l=6, r=6),
            buttons=[
                dict(label="Outliers only", method="update", args=[{"visible": vis_outliers}]),
                dict(label="Show all countries", method="update", args=[{"visible": vis_all}]),
            ])],
    )
    return fig


# ----------------------------------------------------------------------------
# Data loading (same logic as choropleth_map.py)
# ----------------------------------------------------------------------------
def find_file(filename, search_roots):
    for root_dir in search_roots:
        if not os.path.exists(root_dir):
            continue
        for root, _, files in os.walk(root_dir):
            if filename in files:
                return os.path.join(root, filename)
    return None


def clean_raw_eurostat(raw_path):
    df_raw = pd.read_csv(raw_path)
    df = df_raw[
        ["Geopolitical entity (reporting)", "geo", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG"]
    ].rename(
        columns={
            "Geopolitical entity (reporting)": "country",
            "geo": "geo_code",
            "TIME_PERIOD": "year",
            "OBS_VALUE": "renewable_share_pct",
            "OBS_FLAG": "data_flag",
        }
    ).dropna(subset=["renewable_share_pct"])
    df["year"] = df["year"].astype(int)
    df["renewable_share_pct"] = df["renewable_share_pct"].round(3)
    df["data_flag"] = df["data_flag"].fillna("Government")
    df["is_aggregate"] = df["geo_code"].isin(["EU27_2020", "EA19", "EA20"])
    df["country"] = df["country"].str.replace("*", "", regex=False).str.strip()
    return df


def load_data():
    """Optional: pass a CSV path as the first argument, otherwise the data is searched for."""
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        path = sys.argv[1]
        df = pd.read_csv(path)
        return df if "is_aggregate" in df.columns else clean_raw_eurostat(path)

    here = os.path.dirname(os.path.abspath(__file__))
    roots = [here, os.getcwd(), os.path.abspath(os.path.join(here, "..")),
             os.path.abspath(os.path.join(here, "..", "..")),
             os.path.abspath(os.path.join(here, "..", "..", "..")),
             os.path.join(os.path.expanduser("~"), "Downloads")]
    processed = find_file("renewable_energy_shares.csv", roots)
    raw = find_file("nrg_ind_ren$defaultview_linear_2_0.csv", roots)
    if processed:
        df = pd.read_csv(processed)
        if 2015 not in df["year"].unique() and raw:
            df_raw = clean_raw_eurostat(raw)
            if 2015 in df_raw["year"].unique():
                df = df_raw
        return df
    if raw:
        return clean_raw_eurostat(raw)
    raise FileNotFoundError(
        "Neither renewable_energy_shares.csv nor the raw Eurostat CSV was found. "
        "Put the file next to this script or run:  python \"<this file>.py\" path/to/data.csv"
    )


def save_and_open(fig, filename):
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    html = fig.to_html(
        full_html=True,
        default_width="100vw",
        default_height="100vh",
        config={"scrollZoom": True, "responsive": True, "displaylogo": False},
    ).replace(
        "<body>",
        '<body style="margin:0; padding:0; width:100vw; height:100vh; '
        'background-color:#0B1120; overflow:hidden;">',
    )
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved:", out)
    webbrowser.open("file://" + out)


if __name__ == "__main__":
    save_and_open(create_outlier_box(load_data()), "Outlier box plot.html")
