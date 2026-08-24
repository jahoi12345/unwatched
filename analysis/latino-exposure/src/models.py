"""Phase 2: regression models.

1. Negative binomial baseline: camera_count ~ latino_share + controls.
2. Attenuation-bias correction for latino_share's known ACS measurement error
   (regression dilution / reliability-ratio method), since Phase 0 established
   the raw estimates are noisy enough that plain OLS/NB understates any real
   coefficient.
3. Moran's I on baseline residuals -- decides whether (4) is necessary.
4. Spatial lag / spatial error models (spreg) if residual autocorrelation is present.
5. GWR (mgwr) as an exploratory robustness layer.

Primary geography: tracts. Block groups run in parallel as the noisier robustness
check (see SCOPE.md's Phase 0 status on ACS MOE).
"""

import json
import pathlib

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
from esda.moran import Moran
from libpysal.weights import Queen

HERE = pathlib.Path(__file__).resolve().parent
DATA_PROCESSED = HERE.parent / "data" / "processed"
REPORT_DATA = HERE.parent / "report" / "data"

CONTROLS = ["arterial_km_per_km2", "log_income", "pop_density_per_km2_1000", "crime_rate_per_km2_1000"]


def load_model_frame(unit_name: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(DATA_PROCESSED / f"oakland_{unit_name}_analysis_table.geojson")
    gdf = gdf[gdf["B19013_001E"] > 0].copy()  # drops Census's -666666666 "not available" sentinel
    gdf["log_income"] = np.log(gdf["B19013_001E"])
    gdf["pop_density_per_km2_1000"] = gdf["pop_density_per_km2"] / 1000
    gdf["crime_rate_per_km2_1000"] = gdf["crime_rate_per_km2"] / 1000
    return gdf.reset_index(drop=True)


def fit_negative_binomial(gdf: gpd.GeoDataFrame):
    X = sm.add_constant(gdf[["latino_share"] + CONTROLS])
    y = gdf["camera_count"]
    model = sm.NegativeBinomial(y, X)
    return model.fit(disp=False, cov_type="HC1")


def attenuation_correction(gdf: gpd.GeoDataFrame, naive_coef: float) -> dict:
    """Reliability-ratio (regression dilution) correction for classical measurement
    error in latino_share. lambda = Var(true X) / Var(observed X); Var(true X) is
    approximated as Var(observed X) - mean(measurement variance), where measurement
    variance per unit is (moe90 / 1.645)^2 (converting the Census 90%-CI half-width
    to a standard error). corrected_coef = naive_coef / lambda.

    This is the standard first-order fix for regression dilution (Fuller 1987,
    Carroll et al. "Measurement Error in Nonlinear Models") -- appropriate here as
    a magnitude-of-bias check, not a replacement for a full errors-in-variables
    model (e.g. SIMEX), which is future work.
    """
    se = gdf["latino_share_moe90"] / 1.645
    mean_measurement_var = (se**2).mean()
    var_observed = gdf["latino_share"].var()
    var_true_approx = max(var_observed - mean_measurement_var, 1e-9)
    reliability = var_true_approx / var_observed
    return {
        "reliability_ratio": reliability,
        "naive_coef": naive_coef,
        "corrected_coef": naive_coef / reliability,
        "mean_measurement_variance": mean_measurement_var,
        "var_observed": var_observed,
    }


def moran_on_residuals(gdf: gpd.GeoDataFrame, residuals: np.ndarray) -> Moran:
    gdf_proj = gdf.to_crs(3310)
    w = Queen.from_dataframe(gdf_proj, use_index=False)
    w.transform = "r"
    return Moran(residuals, w)


def fit_spatial_models(gdf: gpd.GeoDataFrame) -> dict:
    from spreg import GM_Error_Het, GM_Lag

    gdf_proj = gdf.to_crs(3310)
    w = Queen.from_dataframe(gdf_proj, use_index=False)
    w.transform = "r"

    y = np.log1p(gdf["camera_count"].values).reshape(-1, 1)
    X = gdf[["latino_share"] + CONTROLS].values

    lag_model = GM_Lag(y, X, w=w, name_y="log1p_camera_count", name_x=["latino_share"] + CONTROLS)
    error_model = GM_Error_Het(y, X, w=w, name_y="log1p_camera_count", name_x=["latino_share"] + CONTROLS)
    return {"lag": lag_model, "error": error_model}


def fit_gwr(gdf: gpd.GeoDataFrame) -> dict:
    from mgwr.gwr import GWR
    from mgwr.sel_bw import Sel_BW

    gdf_proj = gdf.to_crs(3310)
    coords = list(zip(gdf_proj.geometry.centroid.x, gdf_proj.geometry.centroid.y))
    y = np.log1p(gdf["camera_count"].values).reshape(-1, 1)
    X = gdf[["latino_share"] + CONTROLS].values

    bw = Sel_BW(coords, y, X).search()
    gwr_model = GWR(coords, y, X, bw)
    results = gwr_model.fit()
    return {"bandwidth": bw, "results": results}


def run(unit_name: str) -> dict:
    print(f"\n{'='*70}\n{unit_name.upper()}\n{'='*70}")
    gdf = load_model_frame(unit_name)
    print(f"n = {len(gdf)} (after dropping units with no ACS income data)")

    nb = fit_negative_binomial(gdf)
    print("\n--- Negative binomial baseline ---")
    print(nb.summary().tables[1])

    latino_coef = nb.params["latino_share"]
    latino_p = nb.pvalues["latino_share"]
    correction = attenuation_correction(gdf, latino_coef)
    print(f"\n--- Attenuation correction for latino_share ---")
    print(f"Reliability ratio: {correction['reliability_ratio']:.3f}")
    print(f"Naive coefficient: {correction['naive_coef']:.4f} (p={latino_p:.4f})")
    print(f"Attenuation-corrected coefficient: {correction['corrected_coef']:.4f}  "
          f"(note: correction rescales the point estimate, not the p-value/SE, "
          f"which is a genuine limitation of this first-order method)")

    resid = gdf["camera_count"].values - nb.predict(sm.add_constant(gdf[["latino_share"] + CONTROLS]))
    moran = moran_on_residuals(gdf, resid)
    print(f"\n--- Moran's I on NB residuals ---")
    print(f"I = {moran.I:.3f}, p = {moran.p_sim:.4f} "
          f"({'spatial models needed' if moran.p_sim < 0.05 else 'plain NB SEs likely adequate'})")

    spatial = fit_spatial_models(gdf)
    print(f"\n--- Spatial lag model (GM_Lag) ---")
    lag = spatial["lag"]
    lag_latino_idx = lag.name_x.index("latino_share")
    print(f"latino_share coef: {lag.betas[lag_latino_idx][0]:.4f}, "
          f"z = {lag.z_stat[lag_latino_idx][0]:.3f}, p = {lag.z_stat[lag_latino_idx][1]:.4f}")

    print(f"\n--- Spatial error model (GM_Error_Het) ---")
    err = spatial["error"]
    err_latino_idx = err.name_x.index("latino_share")
    print(f"latino_share coef: {err.betas[err_latino_idx][0]:.4f}, "
          f"z = {err.z_stat[err_latino_idx][0]:.3f}, p = {err.z_stat[err_latino_idx][1]:.4f}")

    gwr = None
    if unit_name == "tracts":  # GWR is the most exploratory piece; run once, on the primary geography
        print(f"\n--- GWR ---")
        gwr = fit_gwr(gdf)
        gwr_latino_idx = 1  # constant, latino_share, controls...
        local_coefs = gwr["results"].params[:, gwr_latino_idx]
        print(f"Optimal bandwidth: {gwr['bandwidth']:.1f}")
        print(f"Local latino_share coefficient range: [{local_coefs.min():.4f}, {local_coefs.max():.4f}], "
              f"mean = {local_coefs.mean():.4f}")

    return {
        "unit_name": unit_name,
        "gdf": gdf,
        "nb": nb,
        "attenuation": correction,
        "moran_residuals": moran,
        "spatial": spatial,
        "gwr": gwr,
    }


if __name__ == "__main__":
    tract_results = run("tracts")
    bg_results = run("block_groups")
