"""Pulls geocoded crime/incident feeds found for Fresno, Albuquerque, and
Phoenix (El Paso: no accessible geocoded feed found after a real search --
web search, ArcGIS Hub search, ArcGIS org search, direct portal fetch -- so
El Paso stays without a crime control).

- Fresno: City_of_Fresno_Crime_Data_View FeatureServer, point geometry with
  Lat/Lon fields directly. Data only spans 2022-01 to 2023-07 (a real
  limitation -- stale relative to the camera snapshot -- noted in the report).
- Albuquerque: cabq Incidents MapServer, point geometry (state-plane, wkid
  2903 -- reprojected via outSR=4326). Only ~6 months of data (2026-02 to
  2026-08), a rolling recent window, not a multi-year history like Oakland's.
- Phoenix: crime-data CSV (block addresses + a police GRID code, not lat/lon)
  joined to the Police Crime Grid polygon service by GRID_NUMBER, since no
  point-level geocoding is published.
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


def paginated_query(base_url: str, out_fields: str = "*", out_sr: int | None = None,
                     page_size: int = 2000) -> list:
    """resultOffset pagination is unreliable on some ArcGIS Server instances
    (silently returns an empty/short second page) -- object-ID chunking is
    the robust way to page a query regardless of server version."""
    id_params = {"where": "1=1", "returnIdsOnly": "true", "f": "json"}
    id_url = f"{base_url}/query?" + urllib.parse.urlencode(id_params)
    all_ids = _get(id_url).get("objectIds", [])
    id_field = "OBJECTID"

    features = []
    for i in range(0, len(all_ids), page_size):
        chunk = all_ids[i:i + page_size]
        params = {
            "where": f"{id_field} IN ({','.join(map(str, chunk))})",
            "outFields": out_fields, "f": "json",
        }
        if out_sr:
            params["outSR"] = str(out_sr)
        url = f"{base_url}/query?" + urllib.parse.urlencode(params)
        batch = _get(url, timeout=60).get("features", [])
        features.extend(batch)
        print(f"  fetched {len(features)} / {len(all_ids)} so far")
    return features


def fetch_fresno():
    out_path = DATA_RAW / "fresno" / "crime.json"
    if out_path.exists():
        print("fresno crime already cached")
        return
    features = paginated_query(
        "https://services6.arcgis.com/Gs01XZPFhKUG8tKU/arcgis/rest/services/City_of_Fresno_Crime_Data_View/FeatureServer/0"
    )
    out_path.write_text(json.dumps(features))
    print(f"saved {len(features)} Fresno crime records -> {out_path}")


def fetch_albuquerque():
    out_path = DATA_RAW / "albuquerque" / "crime.json"
    if out_path.exists():
        print("albuquerque crime already cached")
        return
    features = paginated_query(
        "https://coageo.cabq.gov/cabqgeo/rest/services/Incidents/MapServer/0",
        out_fields="OBJECTID,ReportDateTime,IncidentType", out_sr=4326,
    )
    out_path.write_text(json.dumps(features))
    print(f"saved {len(features)} Albuquerque crime records -> {out_path}")


def fetch_phoenix_grid():
    out_path = DATA_RAW / "phoenix" / "crime_grid.json"
    if out_path.exists():
        print("phoenix grid already cached")
        return
    # Native SR is AZ State Plane Central (intl feet) -- request 4326 explicitly,
    # since the layer metadata's "sourceSpatialReference": 4326 is misleading and
    # does NOT match what an unparameterized query actually returns.
    features = paginated_query(
        "https://maps.phoenix.gov/pub/rest/services/Public/PoliceCrimeGrid/MapServer/0",
        out_sr=4326,
    )
    out_path.write_text(json.dumps(features))
    print(f"saved {len(features)} Phoenix grid cells -> {out_path}")


if __name__ == "__main__":
    print("=== Fresno ===")
    fetch_fresno()
    print("=== Albuquerque ===")
    fetch_albuquerque()
    print("=== Phoenix grid ===")
    fetch_phoenix_grid()
