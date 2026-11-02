import os
import pandas as pd

def cleaning_of_dataset():
    raw_path = r"EU-ENERGY_PROJECT\data\raw\eurostat\nrg_ind_ren$defaultview_linear_2_0.csv"
    if not os.path.exists(raw_path):
        raw_path = r"C:\Users\Asus\Desktop\DATA VIS PROJECT\EU-ENERGY_PROJECT\data\raw\eurostat\nrg_ind_ren$defaultview_linear_2_0.csv"

    df = pd.read_csv(raw_path)

    coulmns_to_keep = {
        'Geopolitical entity (reporting)': 'country',
        'geo': 'geo_code',
        'TIME_PERIOD': 'year',
        'OBS_VALUE': 'renewable_share_pct',
        'OBS_FLAG': 'data_flag'
    }

    df_clean = df[list(coulmns_to_keep.keys())].rename(columns=coulmns_to_keep)

    # Here we clean the missing values
    df_clean = df_clean.dropna(subset=['renewable_share_pct'])
    df_clean['year'] = df_clean['year'].astype(int)
    df_clean['renewable_share_pct'] = df_clean['renewable_share_pct'].round(3)
    df_clean['data_flag'] = df_clean['data_flag'].fillna('Government')

    # Here Handle Agrregate Data so the flags doesnt look disorted
    aggregates = ['EU27_2020', 'EA19', 'EA20']
    df_clean['is_aggregate'] = df_clean['geo_code'].isin(aggregates)

    # Clean country names
    df_clean['country'] = df_clean['country'].str.replace('*', '', regex=False)
    df_clean['country'] = df_clean['country'].str.strip()

    # Sorting of data
    df_clean = df_clean.sort_values(by=['country','year'])

    # Saving processed Dataset
    output_dir = os.path.join('EU-ENERGY_PROJECT', 'data', 'processed')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'renewable_energy_shares.csv')

    df_clean.to_csv(output_path, index=False)
    print(f"Data set has been succesfully cleaned and saved to our {output_path}")
    print(f"Cleaned dataset shape is {df_clean.shape}")

if __name__ == "__main__":
    cleaning_of_dataset()