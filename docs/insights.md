# Key Insights

Findings per analytical question, with the chart that shows each one. All numbers are computed from `data/processed/electricity_hourly.parquet` (7 countries, 2022 to 2025) with the functions in `src/viz/`, so they can be reproduced and re-checked live in the dashboard. "Relative" means each country scaled to % of its own average, so small and large countries count equally.

## Q1: How does demand vary by hour, weekday and season?

- **Weekends are about 13% lower than weekdays** (relative, all countries: 90% vs 104% of average load). *Hour × weekday heatmap.*
- **The daily peak is in the early evening, around 18:00 local time, in every season.** In winter it reaches 124% of average load, in summer only 102%. The low point is at 03:00 to 04:00 (75% to 92%). *Season profile.*
- **France has by far the most seasonal demand:** its winter load averages 1.46 times its summer load, against 1.17 for Germany and 1.20 for Hungary. *Season profile with one country selected.*
- **The lowest-demand days are spring Sundays and holidays, not Christmas,** e.g. Easter Sunday (20 April 2025) and Whit Sunday (28 May 2023, 19 May 2024): little heating, little cooling and no working day. *Calendar heatmap.*

## Q2: How do the countries differ?

- **Size:** Germany uses about 468 TWh a year and France 434, against Austria 59, Hungary 43 and Denmark 36 (annual averages 2022 to 2025). *Ranking by consumption.*
- **Renewable share of load, 2022 → 2025:** Hungary 11.6% → 21.3%, Poland 18.1% → 29.0%, France 22.8% → 30.6%, Germany 48.4% → 54.6%, Spain 49.4% → 60.0%, Denmark 73.4% → 76.0%. Austria peaked at 91.2% in 2024 and fell back to 73.9% in 2025. The largest relative growth is in the countries that started lowest. *Dumbbell chart (`compare_years=True`).*
- **Very different systems:** Denmark runs mainly on wind, Austria on hydro, France on nuclear, Poland on coal, Hungary on nuclear and gas. *Generation mix by country.*
- **Imports matter for comparisons.** Hungary generates only about 75% of the electricity it uses and Denmark about 94%, while France generates 114% and Spain 109% (net exporters). That is why "renewable share of load" and "of generation" can rank countries differently (Hungary: 16.2% of load vs 21.7% of generation). The charts always name the denominator.

## Q3: How has the renewable share evolved, and does it cover demand?

- **Across all seven countries, renewables grew from 37.4% to 43.8% of generation (2022 → 2025); solar alone from 8.1% to 12.6%.** *Generation mix as share.*
- **Hours in which renewables alone covered all demand, 2022 → 2025:** Austria 7.8% → 22.1%, Germany 0.2% → 5.6%, Hungary 0% → 1.7%, Spain 0% → 0.9%; Denmark stable at about 25%; France and Poland 0% in both years. *Coverage duration curve.*
- **The duck curve:** on an average summer day, solar pushes renewables close to load at midday, and the gap opens again in the evening as the sun sets and demand peaks around 18:00. *Duck curve (`daily_coverage`) with a summer filter.*
- **Seasons differ by system** (renewable share of load, 2022 to 2025): Denmark (wind) is highest in winter (81.5% vs 68.3% in summer); Austria (hydro) in summer (96.6% vs 59.1% in winter); Hungary (solar) more than doubles from winter to summer (9.3% → 23.0%); Spain peaks in spring (65.2%). Germany stays almost flat at 52% to 55%, because winter wind and summer solar offset each other. *Renewable share heatmap (country × month).*

## Q4: Do hours with more renewables have lower prices?

Spain is left out of this question: its day-ahead prices (EPEX SPOT via Energy-Charts) are licensed for private and internal use only, including derived figures, and this repository is public. All price figures below cover the other six countries.

- **Yes, in every country.** The correlation between hourly renewable share and price in 2025 is negative everywhere: Germany −0.82, Poland −0.69, France −0.64, Austria −0.61, Hungary −0.59, Denmark −0.47.
- **Germany 2025:** the median price falls from about 165 EUR/MWh in hours with ~12% renewables to 74 at ~72%, 4 at ~92%, and about zero above 100%. *Renewable share vs price, Germany selected.*
- **France reaches very low prices at much lower renewable shares:** 92 EUR/MWh at ~22%, 15 at ~42%, 3 at ~52%. Likely reason: nuclear already covers most of the remaining demand, so little expensive generation is needed.
- **Denmark reacts least:** its median price only falls from about 107 to 68 EUR/MWh across the whole range and does not reach zero. A likely reason (not shown in our data) is its strong interconnection with neighbouring markets, which absorbs surplus wind power.
- **Residual load explains prices even better** (load minus wind and solar, correlation with price +0.58 in Denmark to +0.87 in Germany): the more demand is left for controllable plants, the more expensive plants set the price (merit order). *`share_price(x="residual_load")`.*
- **Negative prices are a solar effect and growing fast.** Share of hours with negative prices, 2022 → 2025: Germany 0.8% → 6.6%, France 0% → 5.9%, Austria 0% → 4.3%. In 2025 they cluster at midday (on average 20% of all 13:00 hours across the six countries, 27% in Germany) and in late spring and early summer; the highest month was June 2025 in Germany with 20% of hours. *Negative-price heatmaps.*
- **Price level:** the median price fell from 207 EUR/MWh in 2022 (energy crisis) to 100 in 2023 and 80 in 2024, then rose slightly to 95 in 2025. *Price distribution by year.*
