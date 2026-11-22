"""Heatmap matrix: every European country (rows) x every year (columns).

Run:   python heatmap_matrix.py
Needs: pip install plotly pandas numpy
"""
import os
from pathlib import Path
import sys
import webbrowser

import numpy as np
import pandas as pd
import plotly.graph_objects as go

BG, PANEL, GRID = "#0B1120", "#0F172A", "#1E293B"
ACCENT = "#38BDF8"

# Calibrated mid-luminance dark-UI colorscales so crisp white text stays readable on every cell
SHARE_SCALE = [
    [0.00, "#172554"],  # Deep navy
    [0.25, "#1D4ED8"],  # Royal blue
    [0.50, "#0F766E"],  # Deep teal
    [0.75, "#059669"],  # Rich emerald
    [1.00, "#16A34A"],  # Forest green
]

DIVERGING_SCALE = [
    [0.00, "#BE123C"],  # Deep rose
    [0.25, "#881337"],  # Muted burgundy
    [0.50, "#1E293B"],  # Dark slate (zero midpoint blends with UI)
    [0.75, "#0369A1"],  # Ocean blue
    [1.00, "#0284C7"],  # Clear cyan-blue
]

HEATMAP_VIEWS = [
    "Renewable share (%)",
    "Year-over-year change (pp)",
    "Change since first year (pp)",
    "Gap vs. EU-27 average (pp)",
]


def build_matrices(df, year_range=None, selected_countries=None, only_selected=False, sort_by="latest"):
    raw = df[~df["is_aggregate"]].copy()
    if year_range:
        raw = raw[raw["year"].between(year_range[0], year_range[1])]

    share = raw.pivot_table(index="country", columns="year", values="renewable_share_pct")
    years = sorted(share.columns)
    share = share[years]

    if only_selected and selected_countries:
        keep = [c for c in share.index if c in set(selected_countries)]
        if keep:
            share = share.loc[keep]

    latest = share.ffill(axis=1).iloc[:, -1]
    first = share.apply(lambda r: r.dropna().iloc[0] if r.notna().any() else np.nan, axis=1)
    since = share.sub(first, axis=0)

    if sort_by == "alpha":
        order = sorted(share.index.tolist())
    elif sort_by == "gain":
        gain = latest - first
        order = gain.sort_values(ascending=False).index.tolist()
    else:
        order = latest.sort_values(ascending=False).index.tolist()

    share = share.loc[order]
    since = since.loc[order]
    yoy = share.diff(axis=1)

    eu = (
        df[df["geo_code"] == "EU27_2020"]
        .set_index("year")["renewable_share_pct"]
        .reindex(years)
    )
    vs_eu = share.sub(eu, axis=1)
    return share, yoy, since, vs_eu, eu, years


def create_heatmap(
    df,
    default_view="Renewable share (%)",
    year_range=None,
    selected_countries=None,
    only_selected=False,
    include_controls=True,
):
    share, yoy, since, vs_eu, eu, years = build_matrices(
        df, year_range=year_range, selected_countries=selected_countries, only_selected=only_selected
    )
    selected_set = set(selected_countries or [])

    def format_label(c):
        return f"★ {c}" if c in selected_set else c

    rows = ["EU-27 average"] + [format_label(c) for c in share.index.tolist()]

    def with_eu(m, eu_vals):
        top = pd.DataFrame([eu_vals], index=["EU-27 average"], columns=m.columns)
        return pd.concat([top, m])

    nan_row = pd.Series(np.nan, index=years)
    z_share = with_eu(share, eu.values).values
    z_yoy = with_eu(yoy, nan_row.values).values
    z_since = with_eu(since, nan_row.values).values
    z_vs_eu = with_eu(vs_eu, np.zeros(len(years))).values

    sym_yoy = float(np.nanmax(np.abs(z_yoy))) if np.isfinite(z_yoy).any() else 1.0
    sym_since = float(np.nanmax(np.abs(z_since))) if np.isfinite(z_since).any() else 1.0
    sym_eu = float(np.nanmax(np.abs(z_vs_eu))) if np.isfinite(z_vs_eu).any() else 1.0
    show_text = len(years) <= 22

    views = {
        "Renewable share (%)": dict(
            z=z_share, colorscale=SHARE_SCALE, zmin=5, zmax=85, title="Share (%)",
            text="%{z:.0f}", hover="Renewable share: <b>%{z:.2f}%</b>",
        ),
        "Year-over-year change (pp)": dict(
            z=z_yoy, colorscale=DIVERGING_SCALE, zmin=-sym_yoy, zmax=sym_yoy, title="YoY (pp)",
            text="%{z:+.1f}", hover="Change vs previous year: <b>%{z:+.2f} pp</b>",
        ),
        "Change since first year (pp)": dict(
            z=z_since, colorscale=DIVERGING_SCALE, zmin=-sym_since, zmax=sym_since, title="Total Δ (pp)",
            text="%{z:+.1f}", hover=f"Change since {years[0]}: <b>%{{z:+.2f}} pp</b>",
        ),
        "Gap vs. EU-27 average (pp)": dict(
            z=z_vs_eu, colorscale=DIVERGING_SCALE, zmin=-sym_eu, zmax=sym_eu, title="vs EU-27",
            text="%{z:+.0f}", hover="Gap vs EU-27 average: <b>%{z:+.2f} pp</b>",
        ),
    }

    active_view = default_view if default_view in views else "Renewable share (%)"
    v0 = views[active_view]

    def hover_tmpl(body):
        return "<b style='font-size:15px;'>%{y}</b> · %{x}<br>" + body + "<extra></extra>"

    fig = go.Figure(go.Heatmap(
        z=v0["z"],
        x=[str(y) for y in years],
        y=rows,
        colorscale=v0["colorscale"],
        zmin=v0["zmin"],
        zmax=v0["zmax"],
        xgap=2,
        ygap=2,
        hoverongaps=False,
        texttemplate=v0["text"] if show_text else None,
        textfont=dict(size=10, color="#F8FAFC"),
        hovertemplate=hover_tmpl(v0["hover"]),
        colorbar=dict(
            title=v0["title"], thickness=14, len=0.72, bgcolor=PANEL,
            bordercolor="#334155", borderwidth=1, tickfont=dict(color="#CBD5E1"),
        ),
    ))

    updatemenus = []
    if include_controls:
        view_buttons = []
        for name, v in views.items():
            args = {
                "z": [v["z"]],
                "colorscale": [v["colorscale"]],
                "zmin": [v["zmin"]],
                "zmax": [v["zmax"]],
                "hovertemplate": [hover_tmpl(v["hover"])],
                "colorbar.title.text": [v["title"]],
            }
            if show_text:
                args["texttemplate"] = [v["text"]]
            view_buttons.append(dict(label=name, method="restyle", args=[args]))

        sort_buttons = []
        for s_label, s_key in [
            ("Sort: Highest Latest", "latest"),
            ("Sort: Biggest Gain", "gain"),
            ("Sort: A–Z", "alpha"),
        ]:
            sh_s, _, _, _, eu_s, _ = build_matrices(
                df, year_range=year_range, selected_countries=selected_countries,
                only_selected=only_selected, sort_by=s_key
            )
            r_sorted = ["EU-27 average"] + [format_label(c) for c in sh_s.index.tolist()]
            z_sorted = with_eu(sh_s, eu_s.values).values
            sort_buttons.append(
                dict(
                    label=s_label,
                    method="restyle",
                    args=[{"y": [r_sorted], "z": [z_sorted]}],
                )
            )

        updatemenus = [
            dict(
                type="buttons", direction="right", x=0.0, y=1.055, xanchor="left", yanchor="bottom",
                bgcolor="#1E293B", bordercolor="#334155", borderwidth=1,
                font=dict(color="#E2E8F0", size=11), pad=dict(t=4, b=4, l=8, r=8),
                buttons=view_buttons,
                active=list(views.keys()).index(active_view),
            ),
            dict(
                type="dropdown", x=1.0, y=1.055, xanchor="right", yanchor="bottom",
                bgcolor="#1E293B", bordercolor="#334155", borderwidth=1,
                font=dict(color="#E2E8F0", size=11),
                buttons=sort_buttons,
            ),
        ]

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(size=12, color="#E2E8F0"),
        hoverlabel=dict(
            bgcolor="#0F172A",
            bordercolor="#38BDF8",
            font=dict(color="#F8FAFC", size=13),
        ),
        title=dict(
            text="<b style='font-size:20px; color:#F8FAFC;'>RENEWABLE ENERGY SHARE · MATRIX</b><br>"
                 "<span style='font-size:13px; color:#94A3B8;'>★ = selected country · "
                 "blank cell = not reported · drag box to zoom, double-click to reset</span>",
            x=0.02, y=0.975, yref="container", yanchor="top",
        ),
        margin=dict(l=160, r=30, t=165, b=40),
        xaxis=dict(
            side="top", showgrid=False, tickfont=dict(size=12, color="#CBD5E1"),
            ticklen=6, tickcolor="rgba(0,0,0,0)",
            showspikes=True, spikecolor=ACCENT, spikethickness=1, spikemode="across",
        ),
        yaxis=dict(
            autorange="reversed", showgrid=False, tickfont=dict(size=11, color="#CBD5E1"), dtick=1,
            showspikes=True, spikecolor=ACCENT, spikethickness=1, spikemode="across",
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
    dark_button_fix = """
    <style>
      .updatemenu-button rect,
      .updatemenu-dropdown-button rect,
      .updatemenu-item-rect {
        fill: #1E293B !important;
        stroke: #334155 !important;
      }
      .updatemenu-button:hover rect,
      .updatemenu-dropdown-button:hover rect,
      .updatemenu-item-rect:hover {
        fill: #334155 !important;
        stroke: #38BDF8 !important;
      }
      .updatemenu-button text,
      .updatemenu-dropdown-button text,
      .updatemenu-item-text {
        fill: #F8FAFC !important;
      }
    </style>
    <script>
      document.addEventListener("DOMContentLoaded", function () {
        const lockDarkButtons = () => {
          document.querySelectorAll(
            ".updatemenu-button rect, .updatemenu-dropdown-button rect, .updatemenu-item-rect"
          ).forEach((rect) => {
            const fill = (rect.style.fill || rect.getAttribute("fill") || "").replace(/\\s+/g, "").toLowerCase();
            if (
              fill === "rgb(255,255,255)" ||
              fill === "#ffffff" ||
              fill === "#fff" ||
              fill === "white" ||
              fill === "rgb(244,244,248)" ||
              fill === "#f4f4f8"
            ) {
              rect.style.setProperty("fill", "#334155", "important");
              rect.style.setProperty("stroke", "#38BDF8", "important");
            }
          });
        };

        const observer = new MutationObserver(lockDarkButtons);
        observer.observe(document.body, {
          subtree: true,
          attributes: true,
          attributeFilter: ["style", "fill"],
          childList: true,
        });
        lockDarkButtons();
      });
    </script>
    """
    html = fig.to_html(
        full_html=True,
        default_width="100vw",
        default_height="100vh",
        config={"scrollZoom": True, "responsive": True, "displaylogo": False},
    ).replace(
        "</body>",
        dark_button_fix + "\n</body>",
    ).replace(
        "<body>",
        '<body style="margin:0; padding:0; width:100vw; height:100vh; '
        'background-color:#0B1120; overflow:hidden;">',
    )
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved:", out)
    webbrowser.open(Path(out).as_uri())


if __name__ == "__main__":
    save_and_open(create_heatmap(load_data()), "Heatmap_matrix.html")