"""Clean the Eurostat renewable energy share dataset (nrg_ind_ren).

Source: Eurostat, "Renewable energy share" (nrg_ind_ren), annual, % of gross
final energy consumption (all energy, not only electricity).

Input:  data/raw/eurostat/nrg_ind_ren$defaultview_linear_2_0.csv
Output: data/processed/renewable_energy_shares.parquet

Run from anywhere:
    python src/data/clean_eurostat_renewables.py
"""

from pathlib import Path

import pandas as pd

# Paths relative to the repo root, so the script runs on every machine
REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = REPO_ROOT / "data" / "raw" / "eurostat" / "nrg_ind_ren$defaultview_linear_2_0.csv"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "renewable_energy_shares.parquet"

# Eurostat observation flags. An empty flag means a normal, final value.
FLAG_LABELS = {"p": "provisional", "e": "estimated", "b": "break in series"}


def cleaning_of_dataset():
    df = pd.read_csv(RAW_PATH)

    columns_to_keep = {
        'Geopolitical entity (reporting)': 'country',
        'geo': 'geo_code',
        'TIME_PERIOD': 'year',
        'OBS_VALUE': 'renewable_share_pct',
        'OBS_FLAG': 'data_flag'
    }

    df_clean = df[list(columns_to_keep.keys())].rename(columns=columns_to_keep)

    # Here we clean the missing values
    df_clean = df_clean.dropna(subset=['renewable_share_pct'])
    df_clean['year'] = df_clean['year'].astype(int)
    df_clean['renewable_share_pct'] = df_clean['renewable_share_pct'].round(3)
    df_clean['data_flag'] = df_clean['data_flag'].map(FLAG_LABELS).fillna('final')

    # Here Handle Agrregate Data so the flags doesnt look disorted
    aggregates = ['EU27_2020', 'EA19', 'EA20']
    df_clean['is_aggregate'] = df_clean['geo_code'].isin(aggregates)

    # Clean country names
    df_clean['country'] = df_clean['country'].str.replace('*', '', regex=False)
    df_clean['country'] = df_clean['country'].str.strip()

    # Sorting of data
    df_clean = df_clean.sort_values(by=['country','year']).reset_index(drop=True)

    # Saving processed Dataset
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(OUTPUT_PATH, index=False)
    print(f"Data set has been succesfully cleaned and saved to our {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(f"Cleaned dataset shape is {df_clean.shape}")


if __name__ == "__main__":
    cleaning_of_dataset()
