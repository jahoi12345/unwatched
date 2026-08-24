"""Second batch of crime-data feeds, for the Phase-5b cities (San Jose, Fort
Worth, Denver, Sacramento, Seattle). San Jose has no point-geocoded feed (only
block-range address strings) and is skipped, same as El Paso in batch 1.

- Fort Worth: official ArcGIS point layer (CFW Police Crime Data Points),
  631,346 incidents.
- Denver: official ArcGIS point layer (ODC_CRIME_OFFENSES_P, layer 324),
  375,777 incidents.
- Sacramento: official ArcGIS point layer, but only calendar-year 2025
  (58,484 incidents) -- a single-year snapshot, not a multi-year history.
- Seattle: official Socrata feed (data.seattle.gov, tazs-3rd5), 1.56M
  incidents back to 2008, point lat/lon -- some rows have -1.0 sentinel
  coordinates for unknown location, filtered out.
"""

import json
import pathlib
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
DATA_RAW = HERE.parent / "data" / "raw"
USER_AGENT = "unwatched-latino-exposure-research/0.1 (public-interest research)"


def _get(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def paginated_arcgis_query(base_url: str, out_fields: str, page_size: int = 1000) -> list:
    """resultOffset pagination -- confirmed reliable on these servers (unlike
    Phoenix's Police Crime Grid service in batch 1, which needed ID chunking).
    """
    count_url = f"{base_url}/query?" + urllib.parse.urlencode(
        {"where": "1=1", "returnCountOnly": "true", "f": "json"}
    )
    total = _get(count_url, timeout=30).get("count", 0)

    features = []
    offset = 0
    while True:
        params = {"where": "1=1", "outFields": out_fields, "f": "json",
                  "resultOffset": str(offset), "resultRecordCount": str(page_size)}
        url = f"{base_url}/query?" + urllib.parse.urlencode(params)
        batch = _get(url, timeout=60).get("features", [])
        features.extend(batch)
        if len(features) % (page_size * 20) == 0 or not batch:
            print(f"  fetched {len(features)} / {total}")
        if len(batch) < page_size:
            break
        offset += page_size
    return features


def fetch_fort_worth():
    out_path = DATA_RAW / "fort_worth" / "crime.json"
    if out_path.exists():
        print("fort_worth crime already cached")
        return
    features = paginated_arcgis_query(
        "https://mapit.fortworthtexas.gov/ags/rest/services/CIVIC/Crime_Data/MapServer/0",
        out_fields="OBJECTID,Reported_Date",
    )
    out_path.write_text(json.dumps(features))
    print(f"saved {len(features)} Fort Worth crime records -> {out_path}")


def fetch_denver():
    out_path = DATA_RAW / "denver" / "crime.json"
    if out_path.exists():
        print("denver crime already cached")
        return
    features = paginated_arcgis_query(
        "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/ODC_CRIME_OFFENSES_P/FeatureServer/324",
        out_fields="OBJECTID,REPORTED_DATE,GEO_LAT,GEO_LON",
    )
    out_path.write_text(json.dumps(features))
    print(f"saved {len(features)} Denver crime records -> {out_path}")


def fetch_sacramento():
    out_path = DATA_RAW / "sacramento" / "crime.json"
    if out_path.exists():
        print("sacramento crime already cached")
        return
    features = paginated_arcgis_query(
        "https://services5.arcgis.com/54falWtcpty3V47Z/arcgis/rest/services/Sacramento_Report_Data_2025/FeatureServer/0",
        out_fields="Record_ID,Occurrence_Date_PT",
    )
    out_path.write_text(json.dumps(features))
    print(f"saved {len(features)} Sacramento crime records -> {out_path}")


def fetch_seattle():
    out_path = DATA_RAW / "seattle" / "crime.json"
    if out_path.exists():
        print("seattle crime already cached")
        return
    base = "https://data.seattle.gov/resource/tazs-3rd5.json"
    limit = 50000
    offset = 0
    rows = []
    while True:
        params = {"$select": "report_date_time,latitude,longitude", "$limit": str(limit), "$offset": str(offset)}
        url = base + "?" + urllib.parse.urlencode(params)
        page = _get(url, timeout=60)
        if not isinstance(page, list):
            raise RuntimeError(f"Unexpected Seattle response: {page}")
        rows.extend(page)
        print(f"  fetched {len(rows)} so far")
        if len(page) < limit:
            break
        offset += limit
    out_path.write_text(json.dumps(rows))
    print(f"saved {len(rows)} Seattle crime records -> {out_path}")


if __name__ == "__main__":
    print("=== Fort Worth ===")
    fetch_fort_worth()
    print("=== Denver ===")
    fetch_denver()
    print("=== Sacramento ===")
    fetch_sacramento()
    print("=== Seattle ===")
    fetch_seattle()
