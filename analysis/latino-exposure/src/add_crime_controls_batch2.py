"""Adds annualized crime-rate controls to Fort Worth, Denver, Sacramento, and
Seattle's tract tables, same method as add_crime_controls.py (batch 1:
Oakland/Fresno/Albuquerque/Phoenix). Each source has a different schema:
  - Fort Worth: point geometry (x/y) + Reported_Date attribute.
  - Denver: attribute lat/lon (GEO_LAT/GEO_LON) rather than geometry, +
    REPORTED_DATE.
  - Sacramento: point geometry + Occurrence_Date_PT (MM/DD/YYYY HH:MM), only
    calendar-year 2025 (single-year window, not multi-year).
  - Seattle: flat Socrata records with latitude/longitude/report_date_time;
    -1.0 sentinel coordinates (unknown location) are dropped.
"""

import json
import pathlib
from datetime import datetime, timezone

import geopandas as gpd
from dateutil import parser as dateparser
from shapely.geometry import Point

HERE = pathlib.Path(__file__).resolve().parent
DATA_RAW = HERE.parent / "data" / "raw"
DATA_PROCESSED = HERE.parent / "data" / "processed"


def add_point_crime_from_arcgis_geometry(city_slug: str, date_field: str) -> None:
    """Fort Worth, Sacramento: geometry.x/y present on each feature."""
    table_path = DATA_PROCESSED / f"{city_slug}_tracts_analysis_table.geojson"
    gdf = gpd.read_file(table_path)
    features = json.loads((DATA_RAW / city_slug / "crime.json").read_text())

    dates_ms = []
    points = []
    for f in features:
        attrs = f.get("attributes", {})
        geom = f.get("geometry")
        raw_date = attrs.get(date_field)
        if not geom or raw_date is None:
            continue
        if isinstance(raw_date, (int, float)):
            dt = datetime.fromtimestamp(raw_date / 1000, tz=timezone.utc)
        else:
            try:
                dt = dateparser.parse(str(raw_date))
            except Exception:
                continue
        dates_ms.append(dt)
        points.append(Point(geom["x"], geom["y"]))

    span_years = (max(dates_ms) - min(dates_ms)).days / 365.25
    print(f"{city_slug}: {len(points)} geocoded incidents, "
          f"{min(dates_ms):%Y-%m-%d} to {max(dates_ms):%Y-%m-%d} ({span_years:.2f} years)")

    _join_and_save(gdf, points, span_years, table_path)


def add_point_crime_from_attribute_latlon(city_slug: str, date_field: str,
                                            lat_field: str, lon_field: str) -> None:
    """Denver: lat/lon are attributes, not geometry."""
    table_path = DATA_PROCESSED / f"{city_slug}_tracts_analysis_table.geojson"
    gdf = gpd.read_file(table_path)
    features = json.loads((DATA_RAW / city_slug / "crime.json").read_text())

    dates_ms = []
    points = []
    for f in features:
        attrs = f.get("attributes", {})
        raw_date = attrs.get(date_field)
        lat, lon = attrs.get(lat_field), attrs.get(lon_field)
        if raw_date is None or lat is None or lon is None:
            continue
        dt = datetime.fromtimestamp(raw_date / 1000, tz=timezone.utc)
        dates_ms.append(dt)
        points.append(Point(lon, lat))

    span_years = (max(dates_ms) - min(dates_ms)).days / 365.25
    print(f"{city_slug}: {len(points)} geocoded incidents, "
          f"{min(dates_ms):%Y-%m-%d} to {max(dates_ms):%Y-%m-%d} ({span_years:.2f} years)")

    _join_and_save(gdf, points, span_years, table_path)


def add_seattle_crime() -> None:
    """Dataset is documented as 2008-present; a handful of records carry
    clearly wrong dates (e.g. 1975) that would badly distort the annualization
    if not filtered."""
    table_path = DATA_PROCESSED / "seattle_tracts_analysis_table.geojson"
    gdf = gpd.read_file(table_path)
    rows = json.loads((DATA_RAW / "seattle" / "crime.json").read_text())

    floor = datetime(2008, 1, 1, tzinfo=timezone.utc)
    dates_ms = []
    points = []
    for r in rows:
        lat, lon = r.get("latitude"), r.get("longitude")
        raw_date = r.get("report_date_time")
        if not lat or not lon or not raw_date:
            continue
        try:
            lat, lon = float(lat), float(lon)
        except ValueError:
            continue  # e.g. "REDACTED" sentinel for suppressed locations
        if lat == -1.0 or lon == -1.0:
            continue
        dt = dateparser.parse(raw_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt < floor:
            continue
        dates_ms.append(dt)
        points.append(Point(lon, lat))

    span_years = (max(dates_ms) - min(dates_ms)).days / 365.25
    print(f"seattle: {len(points)} geocoded incidents, "
          f"{min(dates_ms):%Y-%m-%d} to {max(dates_ms):%Y-%m-%d} ({span_years:.2f} years)")

    _join_and_save(gdf, points, span_years, table_path)


def _join_and_save(gdf, points, span_years, table_path):
    gdf = gdf.drop(columns=["crime_count_raw", "crime_rate_annual_per_km2_1000"], errors="ignore")
    pts = gpd.GeoDataFrame({"i": range(len(points))}, geometry=points, crs=4326).to_crs(3310)
    gdf_proj = gdf.to_crs(3310)
    joined = gpd.sjoin(pts, gdf_proj[["GEOID", "geometry"]], how="left", predicate="within")
    counts = joined.groupby("GEOID").size().rename("crime_count_raw")

    gdf = gdf.merge(counts, on="GEOID", how="left")
    gdf["crime_count_raw"] = gdf["crime_count_raw"].fillna(0)
    gdf["crime_rate_annual_per_km2_1000"] = (
        gdf["crime_count_raw"] / span_years / gdf["land_area_km2"] / 1000
    )
    gdf.to_file(table_path, driver="GeoJSON")
    print(f"  updated {table_path}")


if __name__ == "__main__":
    add_point_crime_from_arcgis_geometry("fort_worth", "Reported_Date")
    add_point_crime_from_attribute_latlon("denver", "REPORTED_DATE", "GEO_LAT", "GEO_LON")
    add_point_crime_from_arcgis_geometry("sacramento", "Occurrence_Date_PT")
    add_seattle_crime()
