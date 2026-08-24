"""Adds an annualized crime-rate control to Fresno, Albuquerque, and Phoenix's
tract tables (El Paso: no feed found, stays without one), and recomputes
Oakland's on the same annualized basis so all four are comparable in the
pooled model. Each city's crime feed covers a different date range (Fresno
2022-01 to 2023-07; Albuquerque a rolling ~6-month window; Phoenix 2015-2025;
Oakland's existing pre-treatment window) -- annualizing (count / years-of-
coverage / km^2) is the only way to put them on one scale, but it means each
city's "crime rate" reflects a different, non-overlapping period. That's a
real limitation, stated in the report, not hidden.
"""

import json
import pathlib
from datetime import datetime, timezone

import geopandas as gpd
from shapely.geometry import Point

HERE = pathlib.Path(__file__).resolve().parent
DATA_RAW = HERE.parent / "data" / "raw"
DATA_PROCESSED = HERE.parent / "data" / "processed"


def ms_to_dt(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def add_point_crime(city_slug: str, crime_path: pathlib.Path, date_field: str) -> None:
    table_path = DATA_PROCESSED / f"{city_slug}_tracts_analysis_table.geojson"
    gdf = gpd.read_file(table_path)

    features = json.loads(crime_path.read_text())
    dates_ms = [f["attributes"][date_field] for f in features if f["attributes"].get(date_field)]
    span_years = (max(dates_ms) - min(dates_ms)) / (1000 * 60 * 60 * 24 * 365.25)
    print(f"{city_slug}: {len(features)} incidents, "
          f"{ms_to_dt(min(dates_ms)):%Y-%m-%d} to {ms_to_dt(max(dates_ms)):%Y-%m-%d} "
          f"({span_years:.2f} years)")

    pts = gpd.GeoDataFrame(
        {"i": range(len(features))},
        geometry=[Point(f["geometry"]["x"], f["geometry"]["y"]) for f in features],
        crs=4326,
    ).to_crs(3310)

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


def add_phoenix_crime() -> None:
    table_path = DATA_PROCESSED / "phoenix_tracts_analysis_table.geojson"
    gdf = gpd.read_file(table_path)

    import csv

    grid_counts: dict[str, int] = {}
    dates = []
    with open(DATA_RAW / "phoenix" / "crime_raw.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            grid = row.get("GRID")
            if grid:
                grid_counts[grid] = grid_counts.get(grid, 0) + 1
            occ = row.get("OCCURRED ON", "")
            if occ:
                dates.append(occ)

    from dateutil import parser as dateparser
    parsed = [dateparser.parse(d) for d in dates[:: max(1, len(dates) // 5000)]]  # sample for speed
    span_years = (max(parsed) - min(parsed)).days / 365.25
    print(f"phoenix: {sum(grid_counts.values())} incidents across {len(grid_counts)} grid cells, "
          f"~{span_years:.2f} years (sampled date range)")

    grid_features = json.loads((DATA_RAW / "phoenix" / "crime_grid.json").read_text())
    grid_rows = []
    for feat in grid_features:
        gnum = feat["attributes"].get("GRID_NUMBER")
        geom = feat.get("geometry")
        if not gnum or not geom or "rings" not in geom:
            continue
        # ArcGIS "rings" don't reliably follow the outer/inner-ring winding
        # convention Shapely expects; build each ring as its own polygon,
        # fix any self-intersections with buffer(0), and union the parts --
        # robust to both holes and genuine multi-part grid cells.
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        parts = []
        for ring in geom["rings"]:
            if len(ring) < 4:
                continue
            p = Polygon(ring)
            if not p.is_valid:
                p = p.buffer(0)
            if not p.is_empty:
                parts.append(p)
        if not parts:
            continue
        poly = unary_union(parts)
        grid_rows.append({"GRID_NUMBER": gnum, "count": grid_counts.get(gnum, 0), "geometry": poly})

    grid_gdf = gpd.GeoDataFrame(grid_rows, crs=4326).to_crs(3310)
    grid_gdf["geometry"] = grid_gdf.geometry.buffer(0)
    grid_gdf["grid_area"] = grid_gdf.geometry.area

    gdf_proj = gdf.to_crs(3310)
    gdf_proj["geometry"] = gdf_proj.geometry.buffer(0)
    tract_crime = []
    for _, tract in gdf_proj.iterrows():
        overlap = grid_gdf[grid_gdf.geometry.intersects(tract.geometry)].copy()
        if len(overlap) == 0:
            tract_crime.append(0.0)
            continue
        try:
            overlap["int_area"] = overlap.geometry.intersection(tract.geometry).area
        except Exception:
            overlap["int_area"] = [
                g.buffer(0).intersection(tract.geometry).area for g in overlap.geometry
            ]
        overlap["frac"] = overlap["int_area"] / overlap["grid_area"].replace(0, float("nan"))
        weighted = (overlap["frac"].fillna(0) * overlap["count"]).sum()
        tract_crime.append(weighted)

    gdf["crime_count_raw"] = tract_crime
    gdf["crime_rate_annual_per_km2_1000"] = (
        gdf["crime_count_raw"] / span_years / gdf["land_area_km2"] / 1000
    )
    gdf.to_file(table_path, driver="GeoJSON")
    print(f"  updated {table_path}")


def add_oakland_crime() -> None:
    table_path = DATA_PROCESSED / "oakland_tracts_analysis_table.geojson"
    gdf = gpd.read_file(table_path)
    span_years = (datetime(2025, 12, 15) - datetime(2023, 1, 1)).days / 365.25
    gdf["crime_rate_annual_per_km2_1000"] = (
        gdf["crime_count_pre_treatment"] / span_years / gdf["land_area_km2"] / 1000
    )
    gdf.to_file(table_path, driver="GeoJSON")
    print(f"oakland: annualized over {span_years:.2f} years -> {table_path}")


if __name__ == "__main__":
    add_oakland_crime()
    add_point_crime("fresno", DATA_RAW / "fresno" / "crime.json", "OccurredOn")
    add_point_crime("albuquerque", DATA_RAW / "albuquerque" / "crime.json", "ReportDateTime")
    add_phoenix_crime()
