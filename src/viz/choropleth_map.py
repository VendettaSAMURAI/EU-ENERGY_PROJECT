import os
import webbrowser
import numpy as np
import pandas as pd
import plotly.graph_objects as go


NON_REPORTING_EUROPE = [
    "United Kingdom",
    "Switzerland",
    "Ukraine",
    "Belarus",
    "Russia",
    "Andorra",
    "Monaco",
    "San Marino",
    "Liechtenstein",
    "Vatican City",
    "Faroe Islands",
]


def enrich_country_metrics(df):
    df_raw_countries = df[~df["is_aggregate"]].copy().sort_values(["country", "year"])
    min_year = int(df_raw_countries["year"].min())
    all_years = sorted(df_raw_countries["year"].unique())
    all_countries = sorted(df_raw_countries["country"].unique())

    # Map country -> geo_code before expanding grid
    geo_map = (
        df_raw_countries.dropna(subset=["geo_code"])
        .drop_duplicates("country")
        .set_index("country")["geo_code"]
        .to_dict()
    )

    # Merge EU-27 yearly average for comparison
    eu_avg = (
        df[df["geo_code"] == "EU27_2020"][["year", "renewable_share_pct"]]
        .rename(columns={"renewable_share_pct": "eu_avg_pct"})
    )
    df_raw_countries = df_raw_countries.merge(eu_avg, on="year", how="left")

    # Year-over-year change (percentage points)
    df_raw_countries["yoy_change"] = df_raw_countries.groupby("country")["renewable_share_pct"].diff()

    # Total change since earliest available year
    base_year_df = (
        df_raw_countries[df_raw_countries["year"] == min_year][["country", "renewable_share_pct"]]
        .rename(columns={"renewable_share_pct": "base_share"})
    )
    df_raw_countries = df_raw_countries.merge(base_year_df, on="country", how="left")
    df_raw_countries["change_since_base"] = (
        df_raw_countries["renewable_share_pct"] - df_raw_countries["base_share"]
    )

    # Annual ranking among reporting European countries
    df_raw_countries["year_rank"] = (
        df_raw_countries.groupby("year")["renewable_share_pct"]
        .rank(ascending=False, method="min")
        .astype(int)
    )
    df_raw_countries["year_total"] = df_raw_countries.groupby("year")["country"].transform("count")
    df_raw_countries["vs_eu_avg"] = (
        df_raw_countries["renewable_share_pct"] - df_raw_countries["eu_avg_pct"]
    )

    # Build a dense (year x country) grid so every frame has all 37 countries in identical order
    grid = pd.MultiIndex.from_product(
        [all_years, all_countries], names=["year", "country"]
    ).to_frame(index=False)

    df_countries = grid.merge(df_raw_countries, on=["year", "country"], how="left")
    df_countries["geo_code"] = df_countries["country"].map(geo_map)

    # Clean formatted strings for hover tooltip
    df_countries["share_str"] = df_countries["renewable_share_pct"].apply(
        lambda x: f"{x:.2f}%" if pd.notna(x) else "Not Reported"
    )
    df_countries["rank_str"] = df_countries.apply(
        lambda r: f"#{int(r['year_rank'])} of {int(r['year_total'])}"
        if pd.notna(r["year_rank"]) else "N/A",
        axis=1,
    )
    df_countries["vs_eu_str"] = df_countries.apply(
        lambda r: f"{r['vs_eu_avg']:+.2f} pp (EU-27: {r['eu_avg_pct']:.2f}%)"
        if pd.notna(r["vs_eu_avg"]) else "N/A",
        axis=1,
    )
    df_countries["yoy_str"] = df_countries.apply(
        lambda r: f"{r['yoy_change']:+.2f} pp"
        if pd.notna(r["yoy_change"])
        else ("First Reported Year" if pd.notna(r["renewable_share_pct"]) else "N/A"),
        axis=1,
    )
    df_countries["since_base_str"] = df_countries.apply(
        lambda r: f"{r['change_since_base']:+.2f} pp"
        if pd.notna(r["change_since_base"])
        else (f"No {min_year} Baseline" if pd.notna(r["renewable_share_pct"]) else "N/A"),
        axis=1,
    )
    df_countries["status_str"] = df_countries.apply(
        lambda r: str(r["data_flag"])
        if pd.notna(r["renewable_share_pct"])
        else "No Data Reported for This Year",
        axis=1,
    )

    return df_countries.sort_values(["year", "country"]), min_year


def build_header_html(year, eu_val, leader_country, leader_val, count_countries, min_year, max_year):
    eu_text = f"{eu_val:.2f}%" if pd.notna(eu_val) else "N/A"
    return (
        f"<b style='font-size:21px; letter-spacing:0.5px; color:#F8FAFC;'>"
        f"EUROPEAN RENEWABLE ENERGY SHARE · <span style='color:#38BDF8;'>{year}</span></b><br>"
        f"<span style='font-size:13px; color:#94A3B8;'>"
        f"EU-27 Avg: <b style='color:#38BDF8;'>{eu_text}</b>  ·  "
        f"Leader: <b style='color:#4ADE80;'>{leader_country} ({leader_val:.1f}%)</b>  ·  "
        f"Reporting Nations: <b style='color:#E2E8F0;'>{count_countries}</b>  ·  "
        f"<span style='color:#64748B;'>Range {min_year}–{max_year} · Use ← / → Keys or Drag Timeline</span>"
        f"</span>"
    )


def make_data_trace(sub_df, hover_tmpl):
    custom = np.stack(
        [
            sub_df["geo_code"].values,
            sub_df["share_str"].values,
            sub_df["rank_str"].values,
            sub_df["vs_eu_str"].values,
            sub_df["yoy_str"].values,
            sub_df["since_base_str"].values,
            sub_df["status_str"].values,
            sub_df["year"].values,
        ],
        axis=-1,
    )
    return go.Choropleth(
        locations=sub_df["country"],
        locationmode="country names",
        z=sub_df["renewable_share_pct"],
        text=sub_df["country"],
        customdata=custom,
        colorscale="Viridis",
        zmin=5,
        zmax=85,
        marker_line_width=1.3,
        marker_line_color="#0B1120",
        hovertemplate=hover_tmpl,
        colorbar=dict(
            title="Renewable-Share (%)",
            x=0.985,
            y=0.52,
            xanchor="right",
            thickness=16,
            len=0.52,
            ticksuffix="%",
            bgcolor="#0F172A",
            bordercolor="#334155",
            borderwidth=1,
        ),
    )


def create_choropleth_map(df):
    df_countries, min_year = enrich_country_metrics(df)
    all_years = sorted(df_countries["year"].unique())
    max_year = int(all_years[-1])

    # Precompute yearly summary stats from valid rows only
    valid_df = df_countries.dropna(subset=["renewable_share_pct"])
    eu_by_year = df[df["geo_code"] == "EU27_2020"].set_index("year")["renewable_share_pct"].to_dict()
    top_by_year = (
        valid_df.sort_values("renewable_share_pct", ascending=False)
        .groupby("year")
        .first()
        .to_dict("index")
    )
    count_by_year = valid_df.groupby("year")["country"].count().to_dict()

    hover_tmpl = (
        "<b style='font-size:16px;'>%{text}</b> (%{customdata[0]}) — <b>%{customdata[7]}</b><br>"
        "──────────────────────────────<br>"
        "Renewable Share: <b style='color:#38BDF8;'>%{customdata[1]}</b><br>"
        "European Rank: <b>%{customdata[2]}</b><br>"
        "vs. EU-27 Avg: <b>%{customdata[3]}</b><br>"
        "YoY Change: <b>%{customdata[4]}</b><br>"
        f"Change Since {min_year}: <b>%{{customdata[5]}}</b><br>"
        "Data Status: %{customdata[6]}<extra></extra>"
    )

    # Trace 0 (BOTTOM LAYER): All 48 European countries in dark slate (#1E293B)
    # Includes Georgia + all 37 dataset countries + UK, Switzerland, Ukraine, Belarus, Russia, etc.
    all_europe_countries = sorted(
        list(set(df_countries["country"].unique()).union(set(NON_REPORTING_EUROPE)))
    )
    base_trace = go.Choropleth(
        locations=all_europe_countries,
        locationmode="country names",
        z=[1] * len(all_europe_countries),
        colorscale=[[0, "#1E293B"], [1, "#1E293B"]],
        showscale=False,
        marker_line_width=1.3,
        marker_line_color="#0B1120",
        hovertemplate=(
            "<b style='font-size:15px;'>%{location}</b><br>"
            "────────────────────<br>"
            "Status: <span style='color:#94A3B8;'>No Data Reported for Selected Year</span><extra></extra>"
        ),
        name="Europe Base Layer",
    )

    # Trace 1 (TOP LAYER): Initial year colored choropleth
    init_sub = df_countries[df_countries["year"] == min_year]
    init_data_trace = make_data_trace(init_sub, hover_tmpl)

    fig = go.Figure(data=[base_trace, init_data_trace])

    # Build animation frames updating Trace 1 and the dynamic KPI header
    frames = []
    slider_steps = []
    for yr in all_years:
        yr_int = int(yr)
        sub = df_countries[df_countries["year"] == yr_int]
        frames.append(
            go.Frame(
                name=str(yr_int),
                traces=[1],
                data=[make_data_trace(sub, hover_tmpl)],
                layout=go.Layout(
                    title=dict(
                        text=build_header_html(
                            yr_int,
                            eu_by_year.get(yr_int),
                            top_by_year[yr_int]["country"],
                            top_by_year[yr_int]["renewable_share_pct"],
                            count_by_year[yr_int],
                            min_year,
                            max_year,
                        )
                    )
                ),
            )
        )
        slider_steps.append(
            dict(
                method="animate",
                label=str(yr_int),
                args=[
                    [str(yr_int)],
                    {
                        "frame": {"duration": 250, "redraw": True},
                        "mode": "immediate",
                        "fromcurrent": True,
                        "transition": {"duration": 250, "easing": "cubic-in-out"},
                    },
                ],
            )
        )

    fig.frames = frames

    # Natural, balanced widescreen European projection (Kavrayskiy VII) including Georgia
    fig.update_geos(
        scope="world",
        projection_type="kavrayskiy7",
        resolution=50,
        visible=False,
        showland=False,
        showcountries=False,
        showcoastlines=False,
        showocean=False,
        showlakes=False,
        domain=dict(x=[0.0, 1.0], y=[0.0, 1.0]),
        lataxis_range=[34.5, 71.2],
        lonaxis_range=[-24.5, 47.5],
        fitbounds=False,
        bgcolor="#0B1120",
    )

    initial_header = build_header_html(
        min_year,
        eu_by_year.get(min_year),
        top_by_year[min_year]["country"],
        top_by_year[min_year]["renewable_share_pct"],
        count_by_year[min_year],
        min_year,
        max_year,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0B1120",
        plot_bgcolor="#0B1120",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        autosize=True,
        showlegend=False,
        font=dict(size=14, color="#F8FAFC"),
        title=dict(
            text=initial_header,
            x=0.02,
            y=0.97,
            xanchor="left",
            yanchor="top",
        ),
        hoverlabel=dict(
            bgcolor="#0F172A",
            bordercolor="#38BDF8",
            font_size=14,
            font_family="Arial",
            font_color="#F8FAFC",
            align="left",
        ),
        sliders=[
            dict(
                active=0,
                steps=slider_steps,
                x=0.06,
                y=0.025,
                yanchor="bottom",
                len=0.88,
                pad={"t": 6, "b": 6},
                bgcolor="#1E293B",
                activebgcolor="#38BDF8",
                bordercolor="#38BDF8",
                borderwidth=1,
                ticklen=8,
                tickwidth=2,
                tickcolor="#38BDF8",
                font=dict(size=13, color="#E2E8F0"),
                currentvalue=dict(
                    visible=True,
                    prefix="",
                    xanchor="left",
                    offset=8,
                    font=dict(size=15, color="#38BDF8"),
                ),
                transition=dict(duration=250, easing="cubic-in-out"),
            )
        ],
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


if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")

    processed_path = find_file("renewable_energy_shares.csv", [base_dir, downloads_dir])
    raw_path = find_file("nrg_ind_ren$defaultview_linear_2_0.csv", [base_dir, downloads_dir])

    if processed_path:
        df = pd.read_csv(processed_path)
        if 2015 not in df["year"].unique() and raw_path:
            df_raw_clean = clean_raw_eurostat(raw_path)
            if 2015 in df_raw_clean["year"].unique():
                df = df_raw_clean
                df.to_csv(processed_path, index=False)
    elif raw_path:
        df = clean_raw_eurostat(raw_path)
    else:
        raise FileNotFoundError(
            f"Neither renewable_energy_shares.csv nor the raw Eurostat CSV was found inside {base_dir} or {downloads_dir}."
        )

    fig = create_choropleth_map(df)

    output_html = os.path.join(os.path.dirname(__file__), "choropleth_map_fullscreen.html")
    html_str = fig.to_html(
        full_html=True,
        auto_play=False,
        default_width="100vw",
        default_height="100vh",
        config={"scrollZoom": True, "responsive": True, "displayModeBar": False},
    )

    # Enable Left/Right arrow key navigation across years
    interactive_script = """
    <script>
    document.addEventListener('keydown', function(e) {
        const gd = document.querySelector('.plotly-graph-div');
        if (!gd || !gd._transitionData || !gd._transitionData._frames) return;
        const frames = gd._transitionData._frames.map(f => f.name);
        const current = gd.layout.sliders && gd.layout.sliders[0] ? frames[gd.layout.sliders[0].active] : frames[0];
        let idx = frames.indexOf(current);
        if (e.key === 'ArrowRight' && idx < frames.length - 1) idx++;
        else if (e.key === 'ArrowLeft' && idx > 0) idx--;
        else return;
        Plotly.animate(gd, [frames[idx]], {
            frame: {duration: 250, redraw: true},
            mode: 'immediate',
            transition: {duration: 250, easing: 'cubic-in-out'}
        });
    });
    </script>
    </body>
    """

    html_str = html_str.replace(
        "<body>",
        '<body style="margin:0; padding:0; width:100vw; height:100vh; background-color:#0B1120; overflow:hidden;">',
    ).replace("</body>", interactive_script)

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_str)

    webbrowser.open("file://" + os.path.abspath(output_html))