# Interactive Data Visualization Dashboard

Project work for **Data Visualization Methods (INMAA0105L-01/26f)**, University of Debrecen.

## Team
- Gilbert Mutai
- Aviral Birthare
- <Colleague 2>

## Overview
<One paragraph: what the dashboard explores and why.>

## Analytical Questions
1. <Question 1>
2. <Question 2>
3. <Question 3>

## Data Sources
| Dataset | Source | License | Accessed |
|---------|--------|---------|----------|
| <name>  | <URL>  | <license> | <date> |

## Data Preparation
<Summary of cleaning, merging, derived variables. Details in `docs/`.>

## Project Structure
```
data/
  raw/            original data, never modified
  interim/        intermediate outputs
  processed/      final, dashboard-ready data
notebooks/        exploratory analysis
src/
  data/           download and cleaning scripts
  features/       derived variables and aggregations
  viz/            reusable chart functions
dashboard/        Panel app
docs/             source notes, prep documentation, slides
reports/figures/  exported figures
tests/
```

## Setup
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the Pipeline
```bash
python src/data/make_dataset.py
```

## Running the Dashboard
```bash
panel serve dashboard/app.py --show
```
