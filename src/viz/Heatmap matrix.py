"""Heatmap matrix: every European country (rows) x every year (columns).

Run:   python "Heatmap matrix.py"            (opens Heatmap matrix.html)
Needs: pip install plotly pandas numpy
Use the buttons on top to switch between renewable share, year-over-year
change and change since the first reported year.
"""
import os
import sys
import webbrowser

import numpy as np
import pandas as pd
import plotly.graph_objects as go

BG, PANEL, GRID = "#0B1120", "#0F172A", "#334155"


def build_matrices(df):
    raw = df[~df["is_aggregate"]]
    share = raw.pivot_table(index="country", columns="year", values="renewable_share_pct")
    years = sorted(share.columns)
    share = share[years]

    # Highest latest-known share on top
    latest = share.ffill(axis=1).iloc[:, -1]
    order = latest.sort_values(ascending=False).index.tolist()
    share = share.loc[order]

    yoy = share.diff(axis=1)
    first = share.apply(lambda r: r.dropna().iloc[0] if r.notna().any() else np.nan, axis=1)
    since = share.sub(first, axis=0)

    # EU-27 average as an extra top row (shown in the share view only)
    eu = (df[df["geo_code"] == "EU27_2020"].set_index("year")["renewable_share_pct"]
          .reindex(years))
    return share, yoy, since, eu, years


def create_heatmap(df):
    share, yoy, since, eu, years = build_matrices(df)
    rows = ["EU-27 average"] + share.index.tolist()

    def with_eu(m, eu_vals):
        top = pd.DataFrame([eu_vals], index=["EU-27 average"], columns=m.columns)
        return pd.concat([top, m])

    nan_row = pd.Series(np.nan, index=years)
    z_share = with_eu(share, eu.values).values
    z_yoy = with_eu(yoy, nan_row.values).values
    z_since = with_eu(since, nan_row.values).values

    sym_yoy = float(np.nanmax(np.abs(z_yoy))) if np.isfinite(z_yoy).any() else 1.0
    sym_since = float(np.nanmax(np.abs(z_since))) if np.isfinite(z_since).any() else 1.0
    show_text = len(years) <= 20

    views = {
        "Renewable share (%)": dict(
            z=z_share, colorscale="Viridis", zmin=5, zmax=85, title="Share (%)",
            text="%{z:.0f}", hover="Renewable share: <b>%{z:.2f}%</b>"),
        "Year-over-year change (pp)": dict(
            z=z_yoy, colorscale="RdBu", zmin=-sym_yoy, zmax=sym_yoy, title="Change (pp)",
            text="%{z:+.1f}", hover="Change vs previous year: <b>%{z:+.2f} pp</b>"),
        f"Change since {years[0]} (pp)": dict(
            z=z_since, colorscale="RdBu", zmin=-sym_since, zmax=sym_since, title="Change (pp)",
            text="%{z:+.1f}", hover=f"Change since first reported year: <b>%{{z:+.2f}} pp</b>"),
    }
    first_name = next(iter(views))
    v0 = views[first_name]

    def hover_tmpl(body):
        return "<b style='font-size:15px;'>%{y}</b> · %{x}<br>" + body + "<extra></extra>"

    fig = go.Figure(go.Heatmap(
        z=v0["z"], x=[str(y) for y in years], y=rows,
        colorscale=v0["colorscale"], zmin=v0["zmin"], zmax=v0["zmax"],
        xgap=2, ygap=2, hoverongaps=False,
        texttemplate=v0["text"] if show_text else None,
        textfont=dict(size=11, color="#F8FAFC"),
        hovertemplate=hover_tmpl(v0["hover"]),
        colorbar=dict(title=v0["title"], thickness=16, len=0.7, bgcolor=PANEL,
                      bordercolor=GRID, borderwidth=1),
    ))

    buttons = []
    for name, v in views.items():
        args = {
            "z": [v["z"]], "colorscale": [v["colorscale"]],
            "zmin": [v["zmin"]], "zmax": [v["zmax"]],
            "hovertemplate": [hover_tmpl(v["hover"])],
            "colorbar.title.text": [v["title"]],
        }
        if show_text:
            args["texttemplate"] = [v["text"]]
        buttons.append(dict(label=name, method="restyle", args=[args]))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(size=13, color="#F8FAFC"),
        title=dict(
            text="<b style='font-size:21px; color:#F8FAFC;'>RENEWABLE ENERGY SHARE · MATRIX</b><br>"
                 "<span style='font-size:13px; color:#94A3B8;'>Countries ranked by latest share · "
                 "blank cell = not reported · switch the view with the buttons</span>",
            x=0.02, y=0.97),
        margin=dict(l=150, r=30, t=120, b=50),
        xaxis=dict(side="top", showgrid=False, tickfont=dict(size=13)),
        yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(size=12), dtick=1),
        updatemenus=[dict(
            type="buttons", direction="right", x=0.02, y=1.0, xanchor="left", yanchor="bottom",
            bgcolor="#1E293B", bordercolor="#38BDF8", borderwidth=1,
            font=dict(color="#E2E8F0"), pad=dict(t=2, b=2, l=6, r=6), buttons=buttons)],
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
    save_and_open(create_heatmap(load_data()), "Heatmap matrix.html")
