import os
import sys
import pandas as pd
import panel as pn

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

pn.extension('plotly', sizing_mode="stretch_width")

data_path = os.path.join('data', 'processed', 'renewable_energy_shares.csv')
if not os.path.exists(data_path):
    data_path = os.path.join('EU-ENERGY_PROJECT', 'data', 'processed', 'renewable_energy_shares.csv')

if os.path.exists(data_path):
    df = pd.read_csv(data_path)
    countries = sorted(df['country'].dropna().unique().tolist())
    years = sorted(df['year'].dropna().unique().tolist())
else:
    df = pd.DataFrame(columns=['country', 'geo_code', 'year', 'renewable_share_pct', 'data_flag', 'is_aggregate'])
    countries = ['Albania', 'France', 'Germany', 'Hungary']
    years = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]

try:
    from src.viz.charts import plot_choropleth_map, plot_line_trend, plot_distribution_boxplot
    CHARTS_READY = True
except (ImportError, AttributeError, ModuleNotFoundError):
    CHARTS_READY = False

country_picker = pn.widgets.MultiChoice(
    name='Select Countries',
    options=countries,
    value=['Germany', 'France', 'Hungary', 'Albania'] if 'Hungary' in countries else countries[:4]
)

year_slider = pn.widgets.DiscreteSlider(
    name='Select Map Target Year',
    options=years,
    value=max(years) if years else 2024
)

@pn.depends(year_slider.param.value)
def map_pane(selected_year):
    if CHARTS_READY:
        return plot_choropleth_map(df, selected_year)
    return pn.pane.Alert(
        f"### Geographic Map View (Placeholder)\n\n"
        f"**Target Year Selected**: {selected_year}\n\n"
        f"*Waiting for plot_choropleth_map(df, year) in src/viz/charts.py*",
        alert_type="info"
    )

@pn.depends(country_picker.param.value)
def trend_pane(selected_countries):
    if not selected_countries:
        return pn.pane.Markdown("### Please select at least one country from the sidebar.")
    if CHARTS_READY:
        return plot_line_trend(df, selected_countries)
    return pn.pane.Alert(
        f"### Country Trends & Comparison (Placeholder)\n\n"
        f"**Selected Countries**: {', '.join(selected_countries)}\n\n"
        f"*Waiting for plot_line_trend(df, countries) in src/viz/charts.py*",
        alert_type="info"
    )

def distribution_pane():
    if CHARTS_READY:
        return plot_distribution_boxplot(df)
    return pn.pane.Alert(
        "### Yearly Distribution & Outliers (Placeholder)\n\n"
        "*Waiting for plot_distribution_boxplot(df) in src/viz/charts.py*",
        alert_type="info"
    )

template = pn.template.FastListTemplate(
    title="European Renewable Energy Interactive Dashboard",
    sidebar=[
        pn.pane.Markdown("## Interactive Filters"),
        country_picker,
        year_slider,
        pn.pane.Markdown("---"),
        pn.pane.Markdown("**Course**: Data Visualization Methods\n**Institution**: University of Debrecen")
    ],
    main=[
        pn.Tabs(
            ("Geographic Map View", pn.Column(map_pane)),
            ("Country Trends & Comparison", pn.Column(trend_pane)),
            ("Yearly Distribution & Outliers", pn.Column(distribution_pane))
        )
    ],
    accent_base_color="#2E7D32",
    header_background="#1B5E20"
)

template.servable()