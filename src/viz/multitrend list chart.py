"""Multi-trend list chart: one line per country, plus a ranked list as the legend.

Run:   python "multitrend list chart.py"     (opens multitrend list chart.html)
Needs: pip install plotly pandas numpy
The legend on the right is the ranked list (latest share). Click an entry to
hide/show a line, double-click to isolate it. Buttons pick a group of countries.
"""
import os
import sys
import webbrowser

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative

BG, PANEL, GRID = "#0B1120", "#0F172A", "#334155"
PALETTE = qualitative.Alphabet + qualitative.Light24


def create_multitrend(df):
    raw = df[~df["is_aggregate"]].dropna(subset=["renewable_share_pct"])
    piv = raw.pivot_table(index="year", columns="country", values="renewable_share_pct").sort_index()
    years = piv.index.tolist()

    latest = piv.apply(lambda s: s.dropna().iloc[-1])
    first = piv.apply(lambda s: s.dropna().iloc[0])
    change = (latest - first)
    ranked = latest.sort_values(ascending=False).index.tolist()
    n = len(ranked)

    groups = {
        "Top 5": set(ranked[:5]),
        "Top 10": set(ranked[:10]),
        "All countries": set(ranked),
        "Bottom 10": set(ranked[-10:]),
        "Fastest risers (10)": set(change.sort_values(ascending=False).index[:10]),
        "Biggest decliners (10)": set(change.sort_values().index[:10]),
    }
    default = "Top 10"

    fig = go.Figure()
    for i, c in enumerate(ranked):
        s = piv[c]
        fig.add_trace(go.Scatter(
            x=years, y=s.values, mode="lines+markers", name=f"#{i + 1:<2} {c}  {latest[c]:.1f}%",
            line=dict(color=PALETTE[i % len(PALETTE)], width=2.4),
            marker=dict(size=6), connectgaps=False, legendrank=i + 1,
            visible=c in groups[default],
            customdata=np.stack([[c] * len(s), [i + 1] * len(s),
                                 [change[c]] * len(s)], axis=-1),
            hovertemplate=("<b>%{customdata[0]}</b> · %{x}<br>Share: <b>%{y:.2f}%</b><br>"
                           "Latest rank: #%{customdata[1]}<br>"
                           "Change over period: %{customdata[2]:+.1f} pp<extra></extra>")))

    # EU-27 reference line, always visible
    eu = (df[df["geo_code"] == "EU27_2020"].groupby("year")["renewable_share_pct"].mean()
          .reindex(years))
    fig.add_trace(go.Scatter(
        x=years, y=eu.values, mode="lines", name="EU-27 average",
        line=dict(color="#F8FAFC", width=3, dash="dash"), legendrank=0,
        hovertemplate="<b>EU-27 average</b> · %{x}<br>%{y:.2f}%<extra></extra>"))
    eu_flag = [True]

    buttons = [
        dict(label=name, method="update",
             args=[{"visible": [c in members for c in ranked] + eu_flag}])
        for name, members in groups.items()
    ]

    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(size=13, color="#F8FAFC"),
        title=dict(
            text="<b style='font-size:21px; color:#F8FAFC;'>RENEWABLE SHARE · TRENDS BY COUNTRY</b><br>"
                 f"<span style='font-size:13px; color:#94A3B8;'>{n} countries · list ranked by latest "
                 f"share · click a list entry to hide it, double-click to isolate</span>",
            x=0.02, y=0.97),
        margin=dict(l=70, r=20, t=120, b=60),
        hovermode="closest",
        xaxis=dict(title="Year", tickmode="linear", dtick=1, showgrid=False),
        yaxis=dict(title="Renewable share (%)", ticksuffix="%", gridcolor="#1E293B", rangemode="tozero"),
        legend=dict(title=dict(text="<b>Ranked list</b>"), bgcolor=PANEL, bordercolor=GRID,
                    borderwidth=1, font=dict(size=12, family="Consolas, 'Courier New', monospace"),
                    x=1.01, xanchor="left", y=1, yanchor="top", tracegroupgap=0),
        updatemenus=[dict(
            type="buttons", direction="right", x=0.02, y=1.0, xanchor="left", yanchor="bottom",
            bgcolor="#1E293B", bordercolor="#38BDF8", borderwidth=1, font=dict(color="#E2E8F0"),
            pad=dict(t=2, b=2, l=6, r=6), buttons=buttons,
            active=list(groups).index(default))],
    )
    fig.update_layout(margin=dict(r=260))
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
    save_and_open(create_multitrend(load_data()), "multitrend list chart.html")
