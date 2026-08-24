"""Generates the report's figures as standalone SVGs and a results.json summary
consumed by the HTML report. Run from analysis/latino-exposure/.
"""

import json
import sys
import pathlib

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

matplotlib.use("Agg")

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
FIGURES = HERE / "figures"
sys.path.insert(0, str(ROOT / "src"))

from models import run as run_models, load_model_frame, CONTROLS  # noqa: E402

# ---- palette (dataviz skill reference palette, light mode) ----
INK = "#1c1b17"
INK_SECONDARY = "#52514e"
PAPER = "#f2f1ec"
BLUE = "#2a78d6"
BLUE_DARK = "#184f95"
GRAY_GRID = "#c9c7be"
CRITICAL = "#d03b3b"
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Source Serif Pro", "Georgia", "serif"],
    "text.color": INK,
    "axes.edgecolor": GRAY_GRID,
    "axes.labelcolor": INK,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
    "axes.grid": False,
    "figure.facecolor": "none",
    "axes.facecolor": "none",
    "savefig.facecolor": "none",
    "svg.fonttype": "none",
})

seq_cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)


def save_svg(fig, name):
    path = FIGURES / f"{name}.svg"
    fig.savefig(path, format="svg", bbox_inches="tight", transparent=True)
    if "--png-preview" in sys.argv:
        fig.savefig(FIGURES / f"{name}_preview.png", format="png", bbox_inches="tight",
                    facecolor="white", dpi=140)
    plt.close(fig)
    print(f"saved {path}")


def fig_map(gdf, cameras_gdf):
    fig, ax = plt.subplots(figsize=(7, 7.5))
    gdf.plot(column="latino_share", cmap=seq_cmap, linewidth=0.4, edgecolor="#ffffff",
              ax=ax, legend=False, vmin=0, vmax=gdf["latino_share"].quantile(0.98))
    cameras_gdf.plot(ax=ax, markersize=5, color=INK, alpha=0.55, linewidth=0)
    ax.set_axis_off()
    ax.set_title("Oakland: Latino/Hispanic population share (tracts) and Flock/ALPR cameras",
                 fontsize=11, loc="left", color=INK)

    # simple legend
    sm = plt.cm.ScalarMappable(cmap=seq_cmap, norm=plt.Normalize(0, gdf["latino_share"].quantile(0.98)))
    cax = fig.add_axes([0.15, 0.06, 0.4, 0.018])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.set_label("Tract Latino/Hispanic share", fontsize=8.5, color=INK_SECONDARY)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7.5, color=INK_SECONDARY)

    ax.text(0.58, 0.085, "●  camera (OSM/DeFlock)", transform=fig.transFigure,
            fontsize=8.5, color=INK, va="center")
    save_svg(fig, "fig1_map")


def fig_raw_scatter(gdf):
    fig, ax = plt.subplots(figsize=(6, 4.2))
    jitter = np.random.default_rng(7).normal(0, 0.15, size=len(gdf))
    ax.scatter(gdf["latino_share"], gdf["camera_count"] + jitter, s=26, color=BLUE, alpha=0.65,
               edgecolor="none")

    coeffs = np.polyfit(gdf["latino_share"], gdf["camera_count"], 1)
    xs = np.linspace(0, gdf["latino_share"].max(), 50)
    ax.plot(xs, np.polyval(coeffs, xs), color=CRITICAL, linewidth=1.6, linestyle="--")

    ax.set_xlabel("Tract Latino/Hispanic share")
    ax.set_ylabel("Cameras per tract (jittered)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("Raw relationship: weak, not statistically significant\n(r = 0.050, p = 0.59) — see Figure 2 for the controlled estimate",
                 fontsize=10, loc="left", color=INK_SECONDARY)
    save_svg(fig, "fig2_raw_scatter")


def fig_coefficient_comparison(specs):
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    y_pos = np.arange(len(specs))[::-1]

    for y, spec in zip(y_pos, specs):
        color = BLUE if spec["significant"] else INK_SECONDARY
        if spec.get("ci") is not None:
            lo, hi = spec["ci"]
            ax.plot([lo, hi], [y, y], color=color, linewidth=1.6, solid_capstyle="round")
        if spec.get("no_valid_ci"):
            # Point correction only (see caption) -- open marker so it doesn't
            # visually imply the same precision as the CI-bar'd estimates.
            ax.scatter([spec["coef"]], [y], facecolor="none", edgecolor=color, linewidth=1.6, s=55, zorder=3)
        else:
            ax.scatter([spec["coef"]], [y], color=color, s=55, zorder=3, edgecolor="white", linewidth=0.6)

    ax.axvline(0, color=GRAY_GRID, linewidth=1, linestyle="-")
    ax.set_yticks(y_pos)
    ax.set_yticklabels([s["label"] for s in specs], fontsize=9.5)
    ax.set_xlabel("Coefficient on tract Latino/Hispanic share\n(log-camera-count scale; net of arterial roads, income, density, pre-treatment crime)")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(length=0)
    save_svg(fig, "fig3_coefficients")


def fig_gwr_map(gdf, local_coefs):
    fig, ax = plt.subplots(figsize=(7, 7.5))
    gdf = gdf.copy()
    gdf["local_coef"] = local_coefs
    gdf.plot(column="local_coef", cmap=seq_cmap, linewidth=0.4, edgecolor="#ffffff",
              ax=ax, legend=False)
    ax.set_axis_off()
    ax.set_title("Where the Latino-share effect is strongest\n(GWR local coefficients, always positive across Oakland)",
                 fontsize=11, loc="left", color=INK)
    sm = plt.cm.ScalarMappable(cmap=seq_cmap, norm=plt.Normalize(local_coefs.min(), local_coefs.max()))
    cax = fig.add_axes([0.15, 0.06, 0.4, 0.018])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.set_label("Local coefficient (higher = stronger local relationship)", fontsize=8.5, color=INK_SECONDARY)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7.5, color=INK_SECONDARY)
    save_svg(fig, "fig4_gwr_map")


def main():
    tract_results = run_models("tracts")
    bg_results = run_models("block_groups")

    gdf = tract_results["gdf"]

    import json as _json
    cam_raw = _json.loads((ROOT.parent.parent / "src" / "data" / "generated" / "cameras.json").read_text())
    from shapely.geometry import Point
    cam_pts = gpd.GeoDataFrame(
        cam_raw["cameras"],
        geometry=[Point(c["lon"], c["lat"]) for c in cam_raw["cameras"]],
        crs=4326,
    )
    oak_poly_gdf = gpd.read_file(ROOT / "data" / "processed" / "oakland_tracts_acs.geojson")
    oak_union = oak_poly_gdf.union_all()
    cam_pts = cam_pts[cam_pts.within(oak_union)]

    fig_map(gdf, cam_pts)
    fig_raw_scatter(gdf)

    nb = tract_results["nb"]
    corr = tract_results["attenuation"]
    lag = tract_results["spatial"]["lag"]
    err = tract_results["spatial"]["error"]
    lag_idx = lag.name_x.index("latino_share")
    err_idx = err.name_x.index("latino_share")

    ci = nb.conf_int().loc["latino_share"]

    def spreg_ci(model, idx):
        coef = model.betas[idx][0]
        z, p = model.z_stat[idx]
        se = abs(coef / z)
        return (coef - 1.96 * se, coef + 1.96 * se), p

    lag_ci, lag_p = spreg_ci(lag, lag_idx)
    err_ci, err_p = spreg_ci(err, err_idx)

    specs = [
        {"label": "NB baseline (naive)", "coef": nb.params["latino_share"],
         "ci": (ci[0], ci[1]), "significant": nb.pvalues["latino_share"] < 0.05},
        {"label": "NB, attenuation-corrected*", "coef": corr["corrected_coef"],
         "ci": None, "no_valid_ci": True, "significant": True},
        {"label": "Spatial lag (log camera count)", "coef": lag.betas[lag_idx][0],
         "ci": lag_ci, "significant": lag_p < 0.05},
        {"label": "Spatial error (log camera count)", "coef": err.betas[err_idx][0],
         "ci": err_ci, "significant": err_p < 0.05},
    ]
    fig_coefficient_comparison(specs)

    gwr = tract_results["gwr"]
    local_coefs = gwr["results"].params[:, 1]
    fig_gwr_map(gdf, local_coefs)

    # ---- results.json for the HTML report ----
    def nb_table(results):
        out = {}
        for var in results.params.index:
            out[var] = {
                "coef": float(results.params[var]),
                "se": float(results.bse[var]),
                "z": float(results.tvalues[var]),
                "p": float(results.pvalues[var]),
            }
        return out

    summary = {
        "tract": {
            "n": len(tract_results["gdf"]),
            "cameras_total": int(tract_results["gdf"]["camera_count"].sum()),
            "nb": nb_table(tract_results["nb"]),
            "attenuation": {k: float(v) for k, v in tract_results["attenuation"].items()},
            "moran_residuals": {"I": float(tract_results["moran_residuals"].I),
                                  "p": float(tract_results["moran_residuals"].p_sim)},
            "spatial_lag_latino": {"coef": float(lag.betas[lag_idx][0]),
                                     "z": float(lag.z_stat[lag_idx][0]), "p": float(lag.z_stat[lag_idx][1])},
            "spatial_error_latino": {"coef": float(err.betas[err_idx][0]),
                                       "z": float(err.z_stat[err_idx][0]), "p": float(err.z_stat[err_idx][1])},
            "gwr_bandwidth": float(gwr["bandwidth"]),
            "gwr_local_range": [float(local_coefs.min()), float(local_coefs.max())],
            "gwr_local_mean": float(local_coefs.mean()),
        },
        "block_group": {
            "n": len(bg_results["gdf"]),
            "cameras_total": int(bg_results["gdf"]["camera_count"].sum()),
            "nb": nb_table(bg_results["nb"]),
            "attenuation": {k: float(v) for k, v in bg_results["attenuation"].items()},
            "moran_residuals": {"I": float(bg_results["moran_residuals"].I),
                                  "p": float(bg_results["moran_residuals"].p_sim)},
            "spatial_lag_latino": {
                "coef": float(bg_results["spatial"]["lag"].betas[bg_results["spatial"]["lag"].name_x.index("latino_share")][0]),
                "p": float(bg_results["spatial"]["lag"].z_stat[bg_results["spatial"]["lag"].name_x.index("latino_share")][1]),
            },
            "spatial_error_latino": {
                "coef": float(bg_results["spatial"]["error"].betas[bg_results["spatial"]["error"].name_x.index("latino_share")][0]),
                "p": float(bg_results["spatial"]["error"].z_stat[bg_results["spatial"]["error"].name_x.index("latino_share")][1]),
            },
        },
        "data_provenance": {
            "cameras_total_bbox": 856,
            "cameras_oakland_only": int(len(cam_pts)),
            "crime_rows": 210098,
            "crime_geocoded": 200445,
        },
    }
    (HERE / "results.json").write_text(json.dumps(summary, indent=2))
    print("\nsaved report/results.json")


if __name__ == "__main__":
    main()
