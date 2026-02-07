import pandas as pd
from pathlib import Path

def load_price_data(id, type):
    file_path = Path(f"./data/{type}/{id}.csv")
    df = pd.read_csv(file_path)

    df['id'] = id
    df['datum'] = pd.to_datetime(df['datum'])
    return df

data = pd.concat([
    load_price_data("IE00B5BMR087", "depot"),
    load_price_data("IE00BK5BQT80", "depot"),
    load_price_data("LU0908500753", "depot"),
    load_price_data("BTC", "wallet"),
    load_price_data("Sparbrief_ING_231207", "sparbrief")
], ignore_index=True)

all_ids = data['id'].unique()
expanded = []

end_date = pd.Timestamp.today().normalize()

for current_id in all_ids:
    group = data[data['id'] == current_id].copy()

    date_range = pd.date_range(
        start=group['datum'].min(),
        end=end_date,
        freq='D'
    )

    group = (
        group
        .set_index('datum')
        .sort_index()
        .reindex(date_range)
        .rename_axis('datum')
        .reset_index()
    )

    group['id'] = current_id
    group['preis'] = group['preis'].ffill()

    expanded.append(group)

finanzen_prices = pd.concat(expanded, ignore_index=True)
finanzen_prices.to_csv("prices.csv", index=False)
