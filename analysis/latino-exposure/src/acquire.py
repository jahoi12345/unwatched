"""Phase 0 data acquisition for the Latino-exposure / Flock camera analysis.

Pulls, into data/raw/ and data/processed/:
  - Oakland block-group boundaries (Census TIGER cartographic boundary files)
  - Oakland arterial road network (OSM Overpass, same query as ingest/src/sources/overpass.ts)
  - Oakland crime incidents, 2023-01-01 through 2026-08-01 (Oakland CrimeWatch open data)

Does NOT pull ACS demographic/income tables -- that needs a Census API key,
which requires the user to sign up (see SCOPE.md "Open questions"). Re-run
acquire_acs() once CENSUS_API_KEY is set.
"""

import json
import os
import pathlib
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
RAW = HERE.parent / "data" / "raw"
PROCESSED = HERE.parent / "data" / "processed"
CAMERAS_PATH = HERE.parent.parent.parent / "src" / "data" / "generated" / "cameras.json"

USER_AGENT = "unwatched-latino-exposure-research/0.1 (public-interest research)"


def _get_oakland_bbox() -> dict:
    return json.loads(CAMERAS_PATH.read_text())["bbox"]


def acquire_block_group_boundaries() -> None:
    """Oakland block-group polygons, via Census cartographic boundary file + place clip."""
    import zipfile

    import geopandas as gpd

    tiger_dir = RAW / "tiger"
    tiger_dir.mkdir(parents=True, exist_ok=True)

    bg_zip = tiger_dir / "cb_2023_06_bg_500k.zip"
    place_zip = tiger_dir / "cb_2023_06_place_500k.zip"
    for zip_path, url in [
        (bg_zip, "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_06_bg_500k.zip"),
        (place_zip, "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_06_place_500k.zip"),
    ]:
        if not zip_path.exists():
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                zip_path.write_bytes(resp.read())
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tiger_dir)

    bg = gpd.read_file(tiger_dir / "cb_2023_06_bg_500k.shp")
    places = gpd.read_file(tiger_dir / "cb_2023_06_place_500k.shp")

    oak_poly = places[places["NAME"] == "Oakland"].geometry.iloc[0]
    bg_alameda = bg[bg["COUNTYFP"] == "001"].copy()

    bg_proj = bg_alameda.to_crs(3310)
    centroids_ll = gpd.GeoSeries(bg_proj.geometry.centroid, crs=3310).to_crs(4326)
    bg_alameda["centroid_lon"] = centroids_ll.x.values
    bg_alameda["centroid_lat"] = centroids_ll.y.values

    oak_bg = bg_alameda[centroids_ll.within(oak_poly).values].copy()

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED / "oakland_block_groups.geojson"
    out_path.unlink(missing_ok=True)
    oak_bg[["GEOID", "NAME", "ALAND", "AWATER", "centroid_lon", "centroid_lat", "geometry"]].to_file(
        out_path, driver="GeoJSON"
    )
    print(f"[boundaries] {len(oak_bg)} Oakland block groups -> {out_path}")


def acquire_road_network() -> None:
    bbox = _get_oakland_bbox()
    highway_types = (
        "motorway|trunk|primary|secondary|tertiary|"
        "motorway_link|trunk_link|primary_link|secondary_link|tertiary_link"
    )
    query = (
        "[out:json][timeout:120];\n"
        f'way["highway"~"^({highway_types})$"]'
        f"({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});\n"
        "(._;>;);\nout skel qt;"
    )
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter", data=data, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=130) as resp:
        result = json.load(resp)

    els = result["elements"]
    nodes = {e["id"]: (e["lat"], e["lon"]) for e in els if e["type"] == "node"}
    ways = [e for e in els if e["type"] == "way"]

    RAW.mkdir(parents=True, exist_ok=True)
    out_path = RAW / "oakland_road_network.json"
    out_path.write_text(json.dumps({"nodes": nodes, "ways": ways}))
    print(f"[roads] {len(nodes)} nodes, {len(ways)} arterial ways -> {out_path}")


def acquire_crime_data(start="2023-01-01T00:00:00", end="2026-08-01T00:00:00") -> None:
    """Oakland CrimeWatch geocoded incidents (dataset ppgh-7dqv), paginated."""
    base = "https://data.oaklandca.gov/resource/ppgh-7dqv.json"
    where = f"datetime >= '{start}' AND datetime <= '{end}'"
    limit = 50000
    offset = 0
    rows = []
    while True:
        params = {"$where": where, "$order": "datetime", "$limit": str(limit), "$offset": str(offset)}
        url = base + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            page = json.load(resp)
        rows.extend(page)
        print(f"[crime] fetched {len(rows)} rows so far (offset {offset})")
        if len(page) < limit:
            break
        offset += limit

    RAW.mkdir(parents=True, exist_ok=True)
    out_path = RAW / "oakland_crime_2023_2026.json"
    out_path.write_text(json.dumps(rows))
    with_loc = sum(1 for r in rows if "location" in r)
    print(f"[crime] {len(rows)} total rows, {with_loc} geocoded -> {out_path}")


def acquire_acs(api_key: str | None = None) -> None:
    """ACS 5-year block-group data: Hispanic/Latino share (B03002), median household
    income (B19013), population (B01003). Needs a free Census API key -- see
    https://api.census.gov/data/key_signup.html. Set CENSUS_API_KEY in the
    environment, or pass api_key directly, then re-run this function.
    """
    api_key = api_key or os.environ.get("CENSUS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No Census API key found. Get a free key at "
            "https://api.census.gov/data/key_signup.html, then set CENSUS_API_KEY "
            "in the environment and re-run acquire_acs()."
        )

    variables = ",".join(
        [
            "NAME",
            "B03002_001E",  # total population (race/ethnicity universe)
            "B03002_001M",  # ^ margin of error
            "B03002_012E",  # Hispanic or Latino (of any race)
            "B03002_012M",  # ^ margin of error
            "B19013_001E",  # median household income
            "B19013_001M",  # ^ margin of error
            "B01003_001E",  # total population
        ]
    )
    url = (
        "https://api.census.gov/data/2023/acs/acs5"
        f"?get={variables}&for=block%20group:*&in=state:06%20county:001%20tract:*&key={api_key}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)

    header, *body = data
    RAW.mkdir(parents=True, exist_ok=True)
    out_path = RAW / "alameda_acs_block_groups.json"
    out_path.write_text(json.dumps({"header": header, "rows": body}))
    print(f"[acs] {len(body)} Alameda County block groups -> {out_path}")


if __name__ == "__main__":
    acquire_block_group_boundaries()
    acquire_road_network()
    acquire_crime_data()
    try:
        acquire_acs()
    except RuntimeError as exc:
        print(f"[acs] SKIPPED: {exc}")
