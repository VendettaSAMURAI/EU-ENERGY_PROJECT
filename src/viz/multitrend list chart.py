"""Multi-trend list chart: one line per country, plus a ranked list as the legend.

Run:   python multitrend_list_chart.py
Needs: pip install plotly pandas numpy
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

TREND_MODES = [
    "Renewable share (%)",
    "Change since start of window (pp)",
    "Gap vs. EU-27 average (pp)",
]


def create_multitrend(
    df,
    selected_countries=None,
    trend_mode="Renewable share (%)",
    year_range=None,
    show_eu=True,
    include_controls=True,
):
    raw = df[~df["is_aggregate"]].dropna(subset=["renewable_share_pct"]).copy()
    if year_range:
        raw = raw[raw["year"].between(year_range[0], year_range[1])]

    piv_share = raw.pivot_table(index="year", columns="country", values="renewable_share_pct").sort_index()
    years = piv_share.index.tolist()

    eu_raw = (
        df[df["geo_code"] == "EU27_2020"]
        .groupby("year")["renewable_share_pct"]
        .mean()
        .reindex(years)
    )

    # Compute alternative series
    first_vals = piv_share.apply(lambda s: s.dropna().iloc[0] if s.notna().any() else np.nan)
    piv_delta = piv_share.sub(first_vals, axis=1)
    piv_vs_eu = piv_share.sub(eu_raw, axis=0)

    if trend_mode == "Change since start of window (pp)":
        piv_active = piv_delta
        eu_active = eu_raw - (eu_raw.dropna().iloc[0] if eu_raw.notna().any() else 0)
        y_title = "Change since window start (pp)"
        y_suffix = " pp"
        val_fmt = "%{y:+.2f} pp"
    elif trend_mode == "Gap vs. EU-27 average (pp)":
        piv_active = piv_vs_eu
        eu_active = pd.Series(0.0, index=years)
        y_title = "Gap vs. EU-27 average (pp)"
        y_suffix = " pp"
        val_fmt = "%{y:+.2f} pp"
    else:
        piv_active = piv_share
        eu_active = eu_raw
        y_title = "Renewable share (%)"
        y_suffix = "%"
        val_fmt = "%{y:.2f}%"

    latest = piv_share.apply(lambda s: s.dropna().iloc[-1])
    first = piv_share.apply(lambda s: s.dropna().iloc[0])
    change = latest - first
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

    if selected_countries is not None:
        visible_set = set(selected_countries)
    else:
        visible_set = groups["Top 10"]

    fig = go.Figure()
    for i, c in enumerate(ranked):
        s = piv_active[c]
        is_vis = c in visible_set
        fig.add_trace(go.Scatter(
            x=years,
            y=s.values,
            mode="lines+markers",
            name=f"#{i + 1:<2} {c}  {latest[c]:.1f}%",
            line=dict(color=PALETTE[i % len(PALETTE)], width=2.8 if is_vis else 2.0),
            marker=dict(size=6),
            connectgaps=False,
            legendrank=i + 1,
            visible=is_vis if selected_countries is None else (True if is_vis else "legendonly"),
            customdata=np.stack(
                [[c] * len(s), [i + 1] * len(s), [change[c]] * len(s), [latest[c]] * len(s)],
                axis=-1,
            ),
            hovertemplate=(
                f"<b>%{{customdata[0]}}</b> · %{{x}}<br>"
                f"Value: <b>{val_fmt}</b><br>"
                f"Latest Share: <b>%{{customdata[3]:.2f}}%</b> (Rank #%{{customdata[1]}})<br>"
                f"Period Change: %{{customdata[2]:+.2f}} pp<extra></extra>"
            ),
        ))

    fig.add_trace(go.Scatter(
        x=years,
        y=eu_active.values,
        mode="lines",
        name="EU-27 average",
        visible=show_eu,
        line=dict(color="#F8FAFC", width=3, dash="dash"),
        legendrank=0,
        hovertemplate=f"<b>EU-27 average</b> · %{{x}}<br>{val_fmt}<extra></extra>",
    ))
    eu_flag = [show_eu]

    updatemenus = []
    if include_controls:
        group_buttons = [
            dict(
                label=name,
                method="update",
                args=[{"visible": [c in members for c in ranked] + eu_flag}],
            )
            for name, members in groups.items()
        ]
        mode_buttons = [
            dict(
                label=m_name,
                method="update",
                args=[
                    {
                        "y": [
                            (piv_share if m_name == "Renewable share (%)"
                             else piv_delta if m_name == "Change since start of window (pp)"
                             else piv_vs_eu)[c].values
                            for c in ranked
                        ] + [
                            (eu_raw if m_name == "Renewable share (%)"
                             else (eu_raw - eu_raw.dropna().iloc[0]) if m_name == "Change since start of window (pp)"
                             else pd.Series(0.0, index=years)).values
                        ]
                    },
                    {
                        "yaxis.title.text": m_name,
                        "yaxis.ticksuffix": "%" if m_name == "Renewable share (%)" else " pp",
                    },
                ],
            )
            for m_name in TREND_MODES
        ]
        updatemenus = [
            dict(
                type="buttons", direction="right", x=0.02, y=1.01, xanchor="left", yanchor="bottom",
                bgcolor="#1E293B", bordercolor="#38BDF8", borderwidth=1,
                font=dict(color="#E2E8F0", size=11), pad=dict(t=2, b=2, l=5, r=5),
                buttons=group_buttons,
                active=1,
            ),
            dict(
                type="dropdown", x=0.99, y=1.01, xanchor="right", yanchor="bottom",
                bgcolor="#1E293B", bordercolor="#38BDF8", borderwidth=1,
                font=dict(color="#E2E8F0", size=11),
                buttons=mode_buttons,
            ),
        ]

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(size=12, color="#F8FAFC"),
        title=dict(
            text="<b style='font-size:20px; color:#F8FAFC;'>RENEWABLE SHARE · TRENDS BY COUNTRY</b><br>"
                 f"<span style='font-size:13px; color:#94A3B8;'>{n} countries · ranked by latest share · "
                 f"click legend to toggle, double-click to isolate</span>",
            x=0.02, y=0.97,
        ),
        margin=dict(l=70, r=260, t=125, b=60),
        hovermode="closest",
        xaxis=dict(
            title="Year",
            tickmode="linear",
            dtick=1,
            showgrid=False,
            showspikes=True,
            spikecolor="#38BDF8",
            spikethickness=1,
            rangeslider=dict(visible=include_controls, bgcolor="#0F172A", thickness=0.06),
        ),
        yaxis=dict(
            title=y_title,
            ticksuffix=y_suffix,
            gridcolor="#1E293B",
            zeroline=True,
            zerolinecolor="#475569",
        ),
        legend=dict(
            title=dict(text="<b>Ranked list</b>"),
            bgcolor=PANEL,
            bordercolor=GRID,
            borderwidth=1,
            font=dict(size=11, family="Consolas, 'Courier New', monospace"),
            x=1.01, xanchor="left", y=1, yanchor="top", tracegroupgap=0,
        ),
        updatemenus=updatemenus,
    )
    return fig


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
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]) and sys.argv[1].endswith(".csv"):
        path = sys.argv[1]
        df = pd.read_csv(path)
        return df if "is_aggregate" in df.columns else clean_raw_eurostat(path)

    here = os.path.dirname(os.path.abspath(__file__))
    roots = [
        here, os.getcwd(), os.path.abspath(os.path.join(here, "..")),
        os.path.abspath(os.path.join(here, "..", "..")),
        os.path.abspath(os.path.join(here, "..", "..", "..")),
        os.path.join(os.path.expanduser("~"), "Downloads"),
    ]
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
    raise FileNotFoundError("Dataset not found.")


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