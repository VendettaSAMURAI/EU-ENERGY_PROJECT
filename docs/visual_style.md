# Visual Style

All charts use `src/viz/style.py`, so every panel shares one theme and a colour always means the same thing. This note records the decisions and how they were checked.

## Theme

Dark only, following the SaaS reference design: page `#0d0d0d`, chart surface `#1a1a19`, recessive gridlines (`#2c2c2a`) and axes (`#383835`), muted tick labels, system sans-serif font. Call `style.apply()` once after `hv.extension("bokeh")` / `pn.extension()`. It sets the Bokeh theme (also inside Panel's dark design) and default options: 2px lines, 8px markers, 2px surface-coloured gaps between heatmap cells and bars.

## Colour has one job per chart

| Job | Used for | Scale |
|---|---|---|
| Identity | energy source, country | categorical, fixed colour per entity |
| Magnitude | demand, generation, shares (heatmaps, map) | sequential, one hue (blue), dark = low |
| Sign around zero | price vs average, residual load surplus/deficit | diverging blue / gray / red, symmetric limits |
| Status | KPI card alerts only | good / warning / serious / critical, always with icon or label |

## Energy source colours

| Source | Colour | Data columns |
|---|---|---|
| Solar | yellow `#c98500` | `solar_mw` |
| Hydro | aqua `#199e70` | `hydro_mw` |
| Wind | blue `#3987e5` | `wind_onshore_mw` + `wind_offshore_mw` |
| Biomass & other renewables | green `#008300` | `biomass_mw` + `other_renewables_mw` |
| Coal | red `#e66767` | `coal_mw` |
| Nuclear | violet `#9085e9` | `nuclear_mw` |
| Gas | orange `#d95926` | `gas_mw` |
| Oil, storage & other | neutral gray `#6b6a65` | `oil_mw` + `other_mw` + `storage_mw` |

The table is also the **stack order, bottom to top**. Renewables sit on the baseline, so the top of the renewable block reads directly as total renewable generation (Q3), and the midday solar bulge (duck curve) rises from the axis.

Why these exact choices:

- **Conventional hues where they exist** (solar yellow, wind blue, hydro aqua, biomass green, gas orange), so readers need the legend less.
- **Colour-blind safety was computed, not eyeballed.** `src/viz/palette_check.py` simulates protanopia and deuteranopia (Machado et al. 2009) and measures the perceptual distance (OKLab ΔE ×100) between colours that touch in a stacked chart. Target ≥ 8 under CVD simulation, ≥ 15 for normal vision. All 40,320 stack orders were tested. With eight distinct hues, no order that keeps renewables and fossils grouped passes: red is too close to orange and magenta, and green too close to aqua.
- **"Other" became a neutral gray** to solve that. It bundles small, mixed sources, so it should recede anyway. With the gray, the order above passes with a worst touching pair of ΔE 8.4 (CVD) and 19.5 (normal vision). Nuclear sits between coal and gas because red and orange cannot touch.

Re-run the checks after any colour or order change:

```bash
python src/viz/palette_check.py --project
```

## Countries

Countries are compared by **position** (axis, ranking, small multiples) or **highlight** (selected country in bright ink `style.HIGHLIGHT`, others muted `style.CONTEXT`), because the hues already mean energy sources. Where one colour per country is unavoidable (e.g. line charts), `style.COUNTRY_COLORS` gives each country a fixed colour that does not change when filters remove other countries. Scatter plots colour at most three countries at once (only three hues stay distinguishable when any two points can be neighbours); otherwise facet by country.

## Marks and text

- Lines 2px, markers 8px with a thin surface ring so overlapping points stay separable.
- One y-axis per chart. Two measures with different units go in two charts, never a dual axis.
- Text uses the ink colours, never the series colour. Legends always shown for two or more series.
- Units in axis titles. Formatters in `style` (`fmt_power`, `fmt_energy`, `fmt_price`, `fmt_pct`) and hover formats (`HOVER_MW`, `HOVER_PRICE`, ...) keep numbers consistent across charts.

## Notes for chart code

- Chart functions take the filtered hourly DataFrame and return a HoloViews object; aggregation lives in separate `*_data` functions so it can be tested (`tests/test_viz.py`).
- Charts that aggregate load across countries take `relative`: absolute GW (summed) for one country, % of each country's own average for several. Otherwise Germany and France dominate any multi-country view.
- pandas 3 stores text as Arrow strings, which HoloViews heatmaps cannot handle. Convert label columns with `.astype(str).astype(object)` before plotting (see `_for_hv` in `src/viz/demand.py`).
- Categorical axes (e.g. weekdays) cannot take custom tick tuples in Bokeh; put the display labels in the data instead.
- Panel links axes that share a dimension name across plots. Charts with different time ranges need `shared_axes=False` or different dimension names.
- Stacked charts reverse their legend with `utils.reverse_legend` (a Bokeh hook), so the legend reads top to bottom like the layers.
- Stacked areas carry their tooltip on one line (the load line, or an invisible line) with `hover_mode="vline"`, so one hover shows every source at that time instead of only the layer under the cursor.
- Shares over a period are energy-weighted (sum of renewable MWh / sum of load MWh), never the mean of hourly percentages, which would over-weight low-demand hours.
- Price axes show the middle 99% of hours (0.5th to 99.5th percentile) so the 2022 crisis spikes (up to almost 3,000 EUR/MWh) do not flatten everything else. The chart title says so; tooltips show exact values.
- Violins need SciPy (kernel density). The shape is estimated from a fixed random sample of 5,000 hours per group (same shape, about 0.5 s instead of 10 s); medians and tooltips use every hour.
- Too many points for a scatter (245k hours, no datashader): `prices.share_price` uses a hexbin density plus a median line per country, which reads better than overlapping dots anyway.
- Charts on one Panel page that share a dimension name (`price`, `time`) get linked axes. That is good when all charts show the same filtered data, but turn it off with `.opts(shared_axes=False)` when they show different selections.
- The map (`countries.country_map`) uses Eurostat GISCO country borders (1:20M, 2020; (c) EuroGeographics), downloaded by `src/data/download_gisco.py` into `data/raw/gisco/`. It is drawn as plain HoloViews polygons in a simple Mercator projection, so no geopandas, geoviews or cartopy is needed. Mainland Europe only; neighbouring countries in neutral gray for orientation. Add GISCO to the README data sources table.
- Ranked charts put countries at numeric y positions with name tick labels. HoloViews cannot overlay flipped (`invert_axes`) dots with unflipped segments.
- Per capita: every `countries` function takes an optional `population` DataFrame (country, year, population). Without it, per-capita metrics are not offered.
- Renewable share "of load" (Q3, rankings, map) and "of generation" (mix bars) can rank countries differently because of net imports. A net importer generates less than it consumes, so its share of generation is higher than its share of load (2022 to 2025: Hungary generates 75% of its load, 16.2% vs 21.7%; Denmark 94%, 75.5% vs 80.6%, which puts it above Austria on generation). Net exporters show the opposite (France generates 114% of its load, 28.5% vs 25.1%). Tooltips and titles name the denominator.
