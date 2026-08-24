"""Phase 1: spatial join. Builds one analysis table per geography (tract = primary,
block group = robustness) with:
  - camera count (from cameras.json, the OSM/DeFlock ALPR pull)
  - arterial road length in meters (from the Overpass road network pull)
  - pre-treatment crime count (2023-01-01 through 2025-12-15, the day before
    Oakland's Flock-agreement passage -- deliberately excludes post-passage crime
    so the control isn't itself downstream of the thing we're trying to explain)
  - ACS Latino share, income, population (already joined in Phase 0)
  - population density (population / land area)
"""

import json
import pathlib

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

HERE = pathlib.Path(__file__).resolve().parent
DATA_RAW = HERE.parent / "data" / "raw"
DATA_PROCESSED = HERE.parent / "data" / "processed"
CAMERAS_PATH = HERE.parent.parent.parent / "src" / "data" / "generated" / "cameras.json"

# Day before Oakland's Flock-agreement passage (2025-12-16) -- see SCOPE.md Part 2.
PRE_TREATMENT_CUTOFF = "2025-12-15T23:59:59"


def load_cameras() -> gpd.GeoDataFrame:
    cameras = json.loads(CAMERAS_PATH.read_text())["cameras"]
    df = pd.DataFrame(cameras)
    geometry = [Point(lon, lat) for lat, lon in zip(df["lat"], df["lon"])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs=4326)


def load_road_network_lines() -> gpd.GeoDataFrame:
    """Reconstruct arterial way geometries from the raw Overpass node/way dump."""
    raw = json.loads((DATA_RAW / "oakland_road_network.json").read_text())
    nodes = {int(k): v for k, v in raw["nodes"].items()}  # id -> (lat, lon)

    lines = []
    for way in raw["ways"]:
        coords = [(nodes[n][1], nodes[n][0]) for n in way["nodes"] if n in nodes]  # (lon, lat)
        if len(coords) >= 2:
            lines.append({"way_id": way["id"], "geometry": LineString(coords)})

    return gpd.GeoDataFrame(lines, crs=4326)


def load_crime_points(cutoff: str = PRE_TREATMENT_CUTOFF) -> gpd.GeoDataFrame:
    rows = json.loads((DATA_RAW / "oakland_crime_2023_2026.json").read_text())
    geocoded = [r for r in rows if "location" in r and r["datetime"] <= cutoff]
    lons = [r["location"]["coordinates"][0] for r in geocoded]
    lats = [r["location"]["coordinates"][1] for r in geocoded]
    df = pd.DataFrame(geocoded)
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(lons, lats), crs=4326)


def build_analysis_table(geo_path: pathlib.Path, unit_name: str) -> gpd.GeoDataFrame:
    units = gpd.read_file(geo_path)
    units_proj = units.to_crs(3310)  # meters, for length/area math

    cameras = load_cameras().to_crs(3310)
    cam_counts = gpd.sjoin(cameras, units_proj[["GEOID", "geometry"]], how="left", predicate="within")
    cam_per_unit = cam_counts.groupby("GEOID").size().rename("camera_count")

    roads = load_road_network_lines().to_crs(3310)
    road_len_m = {}
    for _, unit in units_proj.iterrows():
        clipped = roads.geometry.intersection(unit.geometry)
        road_len_m[unit["GEOID"]] = clipped.length.sum()
    road_len_series = pd.Series(road_len_m, name="arterial_road_m")

    crime = load_crime_points().to_crs(3310)
    crime_join = gpd.sjoin(crime, units_proj[["GEOID", "geometry"]], how="left", predicate="within")
    crime_per_unit = crime_join.groupby("GEOID").size().rename("crime_count_pre_treatment")

    result = units.merge(cam_per_unit, on="GEOID", how="left")
    result = result.merge(road_len_series.rename_axis("GEOID"), on="GEOID", how="left")
    result = result.merge(crime_per_unit, on="GEOID", how="left")

    result["camera_count"] = result["camera_count"].fillna(0).astype(int)
    result["arterial_road_m"] = result["arterial_road_m"].fillna(0.0)
    result["crime_count_pre_treatment"] = result["crime_count_pre_treatment"].fillna(0).astype(int)

    result["land_area_km2"] = result["ALAND"] / 1_000_000
    result["pop_density_per_km2"] = result["B01003_001E"] / result["land_area_km2"]
    result["camera_density_per_km2"] = result["camera_count"] / result["land_area_km2"]
    result["crime_rate_per_km2"] = result["crime_count_pre_treatment"] / result["land_area_km2"]
    result["arterial_km_per_km2"] = (result["arterial_road_m"] / 1000) / result["land_area_km2"]

    out_path = DATA_PROCESSED / f"oakland_{unit_name}_analysis_table.geojson"
    result.to_file(out_path, driver="GeoJSON")
    print(f"[{unit_name}] {len(result)} units, {result['camera_count'].sum()} cameras total -> {out_path}")
    return result


if __name__ == "__main__":
    build_analysis_table(DATA_PROCESSED / "oakland_tracts_acs.geojson", "tracts")
    build_analysis_table(DATA_PROCESSED / "oakland_block_groups_acs.geojson", "block_groups")
