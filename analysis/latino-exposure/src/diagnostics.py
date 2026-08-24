"""Phase 1 descriptives + Moran's I. Phase 2 (models.py) builds the actual
regressions; this is deliberately pre-regression -- raw correlation and spatial
autocorrelation checks that inform how Phase 2 has to be built (e.g. whether
plain OLS/NB standard errors are usable at all).
"""

import pathlib

import geopandas as gpd
import pandas as pd
from esda.moran import Moran
from libpysal.weights import Queen
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
DATA_PROCESSED = HERE.parent / "data" / "processed"


def describe(unit_name: str) -> None:
    gdf = gpd.read_file(DATA_PROCESSED / f"oakland_{unit_name}_analysis_table.geojson")
    gdf = gdf[gdf["latino_share"].notna()].copy()

    print(f"\n=== {unit_name} (n={len(gdf)}) ===")
    print(f"Camera count: total={gdf['camera_count'].sum()}, "
          f"mean/unit={gdf['camera_count'].mean():.2f}, "
          f"units with 0 cameras={ (gdf['camera_count']==0).mean():.1%}")

    pearson_r, pearson_p = stats.pearsonr(gdf["latino_share"], gdf["camera_density_per_km2"])
    spearman_r, spearman_p = stats.spearmanr(gdf["latino_share"], gdf["camera_count"])
    print(f"Raw correlation, Latino share vs camera density/km2: "
          f"Pearson r={pearson_r:.3f} (p={pearson_p:.4f})")
    print(f"Raw correlation, Latino share vs camera count (Spearman, rank-based, "
          f"robust to the count's skew): rho={spearman_r:.3f} (p={spearman_p:.4f})")

    # Split into terciles for an easy-to-read comparison
    gdf["latino_tercile"] = pd.qcut(gdf["latino_share"], 3, labels=["low", "mid", "high"])
    tercile_means = gdf.groupby("latino_tercile", observed=True)["camera_density_per_km2"].mean()
    print("Mean camera density/km2 by Latino-share tercile:")
    print(tercile_means.to_string())

    # Moran's I on camera density -- is it spatially autocorrelated at all,
    # before any regression is run on it?
    gdf_proj = gdf.to_crs(3310)
    w = Queen.from_dataframe(gdf_proj, use_index=False)
    w.transform = "r"
    moran = Moran(gdf["camera_density_per_km2"].values, w)
    print(f"Moran's I on camera density: I={moran.I:.3f}, p={moran.p_sim:.4f} "
          f"({'SIGNIFICANT spatial autocorrelation -- plain OLS/NB SEs will be wrong' if moran.p_sim < 0.05 else 'not significant'})")

    moran_latino = Moran(gdf["latino_share"].values, w)
    print(f"Moran's I on Latino share (sanity check -- demographics should be "
          f"spatially clustered): I={moran_latino.I:.3f}, p={moran_latino.p_sim:.4f}")


if __name__ == "__main__":
    describe("tracts")
    describe("block_groups")
