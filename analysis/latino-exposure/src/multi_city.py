"""Phase 5: multi-city expansion. Runs the same acquire -> spatial-join pipeline
used for Oakland against a small batch of additional cities, then pools all of
them into one tract-level table with a city identifier for a fixed-effects model.

Crime data was checked for each new city (Socrata catalog, common domain
guesses, ArcGIS Hub search) and not found within a bounded effort -- per
decision, these cities run WITHOUT a crime-rate control. Oakland keeps its own
crime control in its standalone model (report/index.html); the pooled multi-city
model below omits crime_rate_per_km2 entirely so all five cities use the same
specification.
"""

import json
import math
import pathlib
import time
import urllib.parse
import urllib.request
import zipfile

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

HERE = pathlib.Path(__file__).resolve().parent
DATA_RAW = HERE.parent / "data" / "raw"
DATA_PROCESSED = HERE.parent / "data" / "processed"

USER_AGENT = "unwatched-latino-exposure-research/0.1 (public-interest research)"

CITIES = [
    {"slug": "el_paso", "name": "El Paso", "nominatim": "El Paso, Texas",
     "state_fips": "48", "county_fips": "141", "census_place": "El Paso"},
    {"slug": "fresno", "name": "Fresno", "nominatim": "Fresno, California",
     "state_fips": "06", "county_fips": "019", "census_place": "Fresno"},
    {"slug": "san_jose", "name": "San Jose", "nominatim": "San Jose, California",
     "state_fips": "06", "county_fips": "085", "census_place": "San Jose"},
    {"slug": "fort_worth", "name": "Fort Worth", "nominatim": "Fort Worth, Texas",
     "state_fips": "48", "county_fips": "439", "census_place": "Fort Worth"},
    {"slug": "denver", "name": "Denver", "nominatim": "Denver, Colorado",
     "state_fips": "08", "county_fips": "031", "census_place": "Denver"},
    {"slug": "sacramento", "name": "Sacramento", "nominatim": "Sacramento, California",
     "state_fips": "06", "county_fips": "067", "census_place": "Sacramento"},
    {"slug": "seattle", "name": "Seattle", "nominatim": "Seattle, Washington",
     "state_fips": "53", "county_fips": "033", "census_place": "Seattle"},
    {"slug": "dallas", "name": "Dallas", "nominatim": "Dallas, Texas",
     "state_fips": "48", "county_fips": "113", "census_place": "Dallas"},
    {"slug": "kansas_city", "name": "Kansas City", "nominatim": "Kansas City, Missouri",
     "state_fips": "29", "county_fips": "095", "census_place": "Kansas City"},
    {"slug": "san_diego", "name": "San Diego", "nominatim": "San Diego, California",
     "state_fips": "06", "county_fips": "073", "census_place": "San Diego"},
    {"slug": "columbus", "name": "Columbus", "nominatim": "Columbus, Ohio",
     "state_fips": "39", "county_fips": "049", "census_place": "Columbus"},
    {"slug": "charlotte", "name": "Charlotte", "nominatim": "Charlotte, North Carolina",
     "state_fips": "37", "county_fips": "119", "census_place": "Charlotte"},
    {"slug": "phoenix", "name": "Phoenix", "nominatim": "Phoenix, Arizona",
     "state_fips": "04", "county_fips": "013", "census_place": "Phoenix"},
    {"slug": "albuquerque", "name": "Albuquerque", "nominatim": "Albuquerque, New Mexico",
     "state_fips": "35", "county_fips": "001", "census_place": "Albuquerque"},
]


def fetch_bbox(nominatim_query: str) -> dict:
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(nominatim_query)}&format=json&limit=1"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
    south, north, west, east = map(float, data[0]["boundingbox"])
    return {"south": south, "west": west, "north": north, "east": east}


def fetch_cameras(bbox: dict) -> list:
    query = (
        f'[out:json][timeout:60];\nnode["surveillance:type"="ALPR"]'
        f'({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});\nout body;'
    )
    result = _run_overpass(query, timeout=65)
    return [
        {"id": e["id"], "lat": e["lat"], "lon": e["lon"],
         "manufacturer": e.get("tags", {}).get("manufacturer"),
         "direction": e.get("tags", {}).get("direction"),
         "zone": e.get("tags", {}).get("surveillance:zone")}
        for e in result["elements"]
    ]


OVERPASS_ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]


def _run_overpass(query: str, timeout: int, retries: int = 4) -> dict:
    data = urllib.parse.urlencode({"data": query}).encode()
    last_err = None
    for attempt in range(retries):
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                req = urllib.request.Request(endpoint, data=data, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.load(resp)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"Overpass failed after {retries} retries: {last_err}")


def fetch_road_network(bbox: dict) -> dict:
    highway_types = (
        "motorway|trunk|primary|secondary|tertiary|"
        "motorway_link|trunk_link|primary_link|secondary_link|tertiary_link"
    )
    query = (
        "[out:json][timeout:150];\n"
        f'way["highway"~"^({highway_types})$"]'
        f'({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});\n'
        "(._;>;);\nout skel qt;"
    )
    result = _run_overpass(query, timeout=160)
    nodes = {e["id"]: (e["lat"], e["lon"]) for e in result["elements"] if e["type"] == "node"}
    ways = [e for e in result["elements"] if e["type"] == "way"]
    return {"nodes": nodes, "ways": ways}


def ensure_state_tiger(state_fips: str) -> pathlib.Path:
    tiger_dir = DATA_RAW / "tiger"
    tiger_dir.mkdir(parents=True, exist_ok=True)
    for kind in ["tract", "place"]:
        zip_path = tiger_dir / f"cb_2023_{state_fips}_{kind}_500k.zip"
        if not zip_path.exists():
            url = f"https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_{state_fips}_{kind}_500k.zip"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                zip_path.write_bytes(resp.read())
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tiger_dir)
            print(f"  downloaded {zip_path.name}")
    return tiger_dir


def fetch_acs(state_fips: str, county_fips: str, api_key: str) -> dict:
    variables = ",".join([
        "NAME", "B03002_001E", "B03002_001M", "B03002_012E", "B03002_012M",
        "B19013_001E", "B19013_001M", "B01003_001E",
    ])
    url = (
        f"https://api.census.gov/data/2023/acs/acs5?get={variables}"
        f"&for=tract:*&in=state:{state_fips}%20county:{county_fips}&key={api_key}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    header, *rows = data
    return {"header": header, "rows": rows}


def build_city(city: dict, api_key: str) -> gpd.GeoDataFrame:
    print(f"\n=== {city['name']} ===")
    city_dir = DATA_RAW / city["slug"]
    city_dir.mkdir(parents=True, exist_ok=True)

    bbox_path = city_dir / "bbox.json"
    if bbox_path.exists():
        bbox = json.loads(bbox_path.read_text())
    else:
        bbox = fetch_bbox(city["nominatim"])
        bbox_path.write_text(json.dumps(bbox))
    print(f"  bbox: {bbox}")

    cam_path = city_dir / "cameras.json"
    if not cam_path.exists():
        cameras = fetch_cameras(bbox)
        cam_path.write_text(json.dumps(cameras))
    else:
        cameras = json.loads(cam_path.read_text())
    print(f"  cameras: {len(cameras)}")

    road_path = city_dir / "road_network.json"
    if not road_path.exists():
        roads = fetch_road_network(bbox)
        road_path.write_text(json.dumps(roads))
    else:
        roads = json.loads(road_path.read_text())
    print(f"  road nodes: {len(roads['nodes'])}, ways: {len(roads['ways'])}")

    tiger_dir = ensure_state_tiger(city["state_fips"])

    acs_path = city_dir / "acs_tracts.json"
    if not acs_path.exists():
        acs = fetch_acs(city["state_fips"], city["county_fips"], api_key)
        acs_path.write_text(json.dumps(acs))
    else:
        acs = json.loads(acs_path.read_text())
    print(f"  ACS tracts (county-wide): {len(acs['rows'])}")

    tracts = gpd.read_file(tiger_dir / f"cb_2023_{city['state_fips']}_tract_500k.shp")
    places = gpd.read_file(tiger_dir / f"cb_2023_{city['state_fips']}_place_500k.shp")
    place_row = places[places["NAME"] == city["census_place"]]
    if len(place_row) == 0:
        raise ValueError(f"Could not find Census place {city['census_place']!r} in state {city['state_fips']}")
    place_poly = place_row.geometry.iloc[0]

    tracts_county = tracts[tracts["COUNTYFP"] == city["county_fips"]].copy()
    tracts_proj = tracts_county.to_crs(3310)
    centroids_ll = gpd.GeoSeries(tracts_proj.geometry.centroid, crs=3310).to_crs(4326)
    tracts_county["centroid_lon"] = centroids_ll.x.values
    tracts_county["centroid_lat"] = centroids_ll.y.values
    city_tracts = tracts_county[centroids_ll.within(place_poly).values].copy()
    print(f"  tracts in city: {len(city_tracts)}")

    acs_df = pd.DataFrame(acs["rows"], columns=acs["header"]).drop(columns=["NAME"])
    for c in ["B03002_001E", "B03002_001M", "B03002_012E", "B03002_012M", "B19013_001E", "B19013_001M", "B01003_001E"]:
        acs_df[c] = pd.to_numeric(acs_df[c], errors="coerce")
    acs_df["GEOID"] = acs_df["state"] + acs_df["county"] + acs_df["tract"]

    merged = city_tracts.merge(acs_df, on="GEOID", how="left")
    merged["latino_share"] = merged["B03002_012E"] / merged["B03002_001E"]

    merged_proj = merged.to_crs(3310)

    cam_gdf = gpd.GeoDataFrame(
        cameras, geometry=[Point(c["lon"], c["lat"]) for c in cameras], crs=4326
    ).to_crs(3310)
    cam_join = gpd.sjoin(cam_gdf, merged_proj[["GEOID", "geometry"]], how="left", predicate="within")
    cam_counts = cam_join.groupby("GEOID").size().rename("camera_count")

    road_nodes = {int(k): v for k, v in roads["nodes"].items()}
    lines = []
    for way in roads["ways"]:
        coords = [(road_nodes[n][1], road_nodes[n][0]) for n in way["nodes"] if n in road_nodes]
        if len(coords) >= 2:
            lines.append({"geometry": LineString(coords)})
    roads_gdf = gpd.GeoDataFrame(lines, crs=4326).to_crs(3310)

    road_len = {}
    for _, row in merged_proj.iterrows():
        clipped = roads_gdf.geometry.intersection(row.geometry)
        road_len[row["GEOID"]] = clipped.length.sum()

    result = merged.merge(cam_counts, on="GEOID", how="left")
    result["camera_count"] = result["camera_count"].fillna(0).astype(int)
    result["arterial_road_m"] = result["GEOID"].map(road_len).fillna(0.0)
    result["land_area_km2"] = result["ALAND"] / 1_000_000
    result["pop_density_per_km2"] = result["B01003_001E"] / result["land_area_km2"]
    result["arterial_km_per_km2"] = (result["arterial_road_m"] / 1000) / result["land_area_km2"]
    result["log_income"] = result["B19013_001E"].apply(lambda x: math.log(x) if x and x > 0 else None)
    result["city"] = city["name"]

    out_path = DATA_PROCESSED / f"{city['slug']}_tracts_analysis_table.geojson"
    result.to_file(out_path, driver="GeoJSON")
    print(f"  saved {out_path} ({result['camera_count'].sum()} cameras assigned)")
    return result


def main():
    import os
    api_key = os.environ.get("CENSUS_API_KEY")
    if not api_key:
        raise RuntimeError("Set CENSUS_API_KEY in the environment first.")

    for city in CITIES:
        build_city(city, api_key)
        time.sleep(2)


if __name__ == "__main__":
    main()
