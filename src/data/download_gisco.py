"""Download country borders for the dashboard map from Eurostat GISCO.

Source: https://gisco-services.ec.europa.eu/distribution/v2/countries/
File:   CNTR_RG_20M_2020_4326.geojson (country polygons, 1:20 million scale,
        2020 borders, WGS84 lon/lat), about 1.9 MB.
Licence: free reuse with attribution "(c) EuroGeographics for the
        administrative boundaries" (see GISCO copyright notice).

Saved unchanged to data/raw/gisco/. Skipped if the file already exists.

Run from anywhere:
    python src/data/download_gisco.py
"""

from pathlib import Path

import requests

URL = ("https://gisco-services.ec.europa.eu/distribution/v2/countries/geojson/"
       "CNTR_RG_20M_2020_4326.geojson")
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_FILE = REPO_ROOT / "data" / "raw" / "gisco" / "CNTR_RG_20M_2020_4326.geojson"


def main():
    if OUT_FILE.exists():
        print(f"skip  {OUT_FILE.name} (exists)")
        return
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    if "FeatureCollection" not in r.text[:200]:
        raise ValueError("response is not a GeoJSON FeatureCollection")
    OUT_FILE.write_bytes(r.content)
    print(f"saved {OUT_FILE.relative_to(REPO_ROOT)} ({len(r.content) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
