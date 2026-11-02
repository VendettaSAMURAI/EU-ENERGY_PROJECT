"""Download raw electricity data from the Energy-Charts API (Fraunhofer ISE).

Source: https://api.energy-charts.info (free, no API key)

Downloads, per year:
- public_power: generation by source + load, per country (15-minute resolution)
- price: day-ahead prices, per bidding zone (hourly, 15-minute from Oct 2025)

Each API response is saved unchanged as JSON in data/raw/energy_charts/.
Files that already exist are skipped, so the script can be re-run safely.

Run from the repo root:
    python src/data/download_energy_charts.py
"""

import json
import time
from pathlib import Path

import requests

BASE_URL = "https://api.energy-charts.info"
OUT_DIR = Path("data/raw/energy_charts")

YEARS = [2022, 2023, 2024, 2025]
COUNTRIES = ["hu", "de", "at", "fr", "es", "pl", "dk"]
# Bidding zones for prices. Germany shares DE-LU with Luxembourg;
# Denmark has two zones (DK1 West, DK2 East), averaged later in cleaning.
PRICE_ZONES = ["HU", "DE-LU", "AT", "FR", "ES", "PL", "DK1", "DK2"]

PAUSE_SECONDS = 5   # be polite to a free API
TIMEOUT_SECONDS = 120
MAX_RETRIES = 5
RATE_LIMIT_WAIT = 60  # seconds to wait after a 429 if the API gives no Retry-After


def fetch(endpoint, params):
    """GET an endpoint and return the parsed JSON, retrying on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=TIMEOUT_SECONDS)
            if r.status_code == 429:
                # Rate limited: wait as long as the API asks, then retry
                retry_after = r.headers.get("Retry-After", "")
                wait = int(retry_after) if retry_after.isdigit() else RATE_LIMIT_WAIT * attempt
                print(f"    rate limited, waiting {wait}s (attempt {attempt})")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"    attempt {attempt} failed: {e}")
            time.sleep(PAUSE_SECONDS * attempt * 2)
    return None


def download(endpoint, key_param, key, year, required_field):
    """Download one year for one country/zone and save it as JSON."""
    out_file = OUT_DIR / f"{endpoint}_{key.lower()}_{year}.json"
    if out_file.exists():
        print(f"  skip  {out_file.name} (exists)")
        return

    params = {key_param: key, "start": f"{year}-01-01", "end": f"{year}-12-31"}
    data = fetch(endpoint, params)

    # Only save responses that contain real data, never error messages
    if not data or required_field not in data or not data.get("unix_seconds"):
        print(f"  FAIL  {out_file.name}: no usable data returned")
        return

    out_file.write_text(json.dumps(data))
    print(f"  saved {out_file.name} ({len(data['unix_seconds'])} timestamps)")
    time.sleep(PAUSE_SECONDS)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Generation and load (public_power):")
    for country in COUNTRIES:
        for year in YEARS:
            download("public_power", "country", country, year, "production_types")

    print("Day-ahead prices (price):")
    for zone in PRICE_ZONES:
        for year in YEARS:
            download("price", "bzn", zone, year, "price")


if __name__ == "__main__":
    main()
