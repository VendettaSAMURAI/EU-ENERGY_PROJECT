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

    # Build a dense (year x country) grid so every frame has all countries in identical order
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
        f"<b style='font-size:19px; letter-spacing:0.5px; color:#F8FAFC;'>"
        f"EUROPEAN RENEWABLE ENERGY SHARE · <span style='color:#38BDF8;'>{year}</span></b><br>"
        f"<span style='font-size:12px; color:#94A3B8;'>"
        f"EU-27 Avg: <b style='color:#38BDF8;'>{eu_text}</b>  ·  "
        f"Leader: <b style='color:#4ADE80;'>{leader_country} ({leader_val:.1f}%)</b>  ·  "
        f"Reporting Nations: <b style='color:#E2E8F0;'>{count_countries}</b>"
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
            thickness=15,
            len=0.5,
            ticksuffix="%",
            bgcolor="#0F172A",
            bordercolor="#334155",
            borderwidth=1,
        ),
    )


def create_choropleth_map(df, year=None, selected_year=None, metric=None, selected_countries=None, target_pct=None, include_controls=True, uirev=None):
    df_countries, min_year = enrich_country_metrics(df)
    all_years = sorted(df_countries["year"].unique())
    max_year = int(all_years[-1])

    target_year = int(year or selected_year or max_year)
    if target_year not in all_years:
        target_year = max_year

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
        "vs. EU-27 Avg: <b style='color:#38BDF8;'>%{customdata[3]}</b><br>"
        "YoY Change: <b>%{customdata[4]}</b><br>"
        f"Change Since {min_year}: <b>%{{customdata[5]}}</b><br>"
        "Data Status: %{customdata[6]}<extra></extra>"
    )

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

    sub = df_countries[df_countries["year"] == target_year]
    data_trace = make_data_trace(sub, hover_tmpl)

    fig = go.Figure(data=[base_trace, data_trace])

    # Build animation frames & slider steps for standalone runner support
    frames = []
    slider_steps = []
    for yr in all_years:
        yr_int = int(yr)
        frame_sub = df_countries[df_countries["year"] == yr_int]
        frames.append(
            go.Frame(
                name=str(yr_int),
                traces=[1],
                data=[make_data_trace(frame_sub, hover_tmpl)],
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

    initial_header = build_header_html(
        target_year,
        eu_by_year.get(target_year),
        top_by_year[target_year]["country"],
        top_by_year[target_year]["renewable_share_pct"],
        count_by_year[target_year],
        min_year,
        max_year,
    )

    # Dynamic unique uirevision bound to year/metric to flush stale hover caches
    active_uirev = uirev if uirev else f"map-year-{target_year}"

    layout_kwargs = dict(
        template="plotly_dark",
        paper_bgcolor="#1C1C1E",
        plot_bgcolor="#1C1C1E",
        margin={"r": 20, "t": 75, "l": 20, "b": 80},  # Balanced margins to fit map and slider without squishing
        autosize=True,
        showlegend=False,
        uirevision=active_uirev,
        font=dict(size=13, color="#F8FAFC"),
        title=dict(
            text=initial_header,
            x=0.02,
            y=0.96,
            xanchor="left",
            yanchor="top",
        ),
        hoverlabel=dict(
            bgcolor="#2C2C2E",
            bordercolor="#38BDF8",
            font_size=13,
            font_family="Arial",
            font_color="#F8FAFC",
            align="left",
        ),
    )

    if include_controls:
        active_step_idx = all_years.index(target_year) if target_year in all_years else 0
        layout_kwargs["sliders"] = [
            dict(
                active=active_step_idx,
                steps=slider_steps,
                x=0.05,
                y=-0.08,  # Perfectly placed right below the map area inside the bottom margin
                yanchor="top",
                len=0.90,
                pad={"t": 10, "b": 10},
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
        ]

    fig.update_layout(**layout_kwargs)

    # Configured with clean Mercator scaling so Europe fills the container naturally like your reference screenshot
    fig.update_geos(
        scope="europe",
        projection_type="mercator",
        center=dict(lat=51.5, lon=10.0),
        projection_scale=2.35,  # Adjusted scale to match your reference layout proportions perfectly
        resolution=50,
        visible=False,
        showland=False,
        showcountries=False,
        showcoastlines=False,
        showocean=False,
        showlakes=False,
        bgcolor="#1C1C1E",
    )

    return fig


def load_data(extra_roots=None):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    search_roots = [base_dir, downloads_dir]
    if extra_roots:
        search_roots.extend(extra_roots)

    processed_path = find_file("renewable_energy_shares.csv", search_roots)
    raw_path = find_file("nrg_ind_ren$defaultview_linear_2_0.csv", search_roots)

    if processed_path:
        df = pd.read_csv(processed_path)
        if 2015 not in df["year"].unique() and raw_path:
            df_raw_clean = clean_raw_eurostat(raw_path)
            if 2015 in df_raw_clean["year"].unique():
                df = df_raw_clean
                df.to_csv(processed_path, index=False)
        return df
    elif raw_path:
        return clean_raw_eurostat(raw_path)
    else:
        raise FileNotFoundError(
            f"Neither renewable_energy_shares.csv nor the raw Eurostat CSV was found."
        )


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