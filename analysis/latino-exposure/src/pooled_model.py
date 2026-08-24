"""Pools Oakland + the four Phase-5 cities into one tract-level table and runs
a negative-binomial regression with city fixed effects.

Two specifications:
1. All 5 cities, no crime control (El Paso has none; kept for comparability
   across all 5).
2. The 4 cities that now have a crime feed (Oakland, Fresno, Albuquerque,
   Phoenix -- see src/add_crime_controls.py), WITH an annualized crime-rate
   control, to test whether the missing-crime-control explanation for the
   cross-city heterogeneity in spec (1) actually holds up.
"""

import json
import pathlib

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as st

HERE = pathlib.Path(__file__).resolve().parent
DATA_PROCESSED = HERE.parent / "data" / "processed"
REPORT = HERE.parent / "report"

CITY_FILES = {
    "El Paso": "el_paso_tracts_analysis_table.geojson",
    "Fresno": "fresno_tracts_analysis_table.geojson",
    "Phoenix": "phoenix_tracts_analysis_table.geojson",
    "Albuquerque": "albuquerque_tracts_analysis_table.geojson",
    "San Jose": "san_jose_tracts_analysis_table.geojson",
    "Fort Worth": "fort_worth_tracts_analysis_table.geojson",
    "Denver": "denver_tracts_analysis_table.geojson",
    "Sacramento": "sacramento_tracts_analysis_table.geojson",
    "Seattle": "seattle_tracts_analysis_table.geojson",
    "Dallas": "dallas_tracts_analysis_table.geojson",
    "Kansas City": "kansas_city_tracts_analysis_table.geojson",
    "San Diego": "san_diego_tracts_analysis_table.geojson",
    "Columbus": "columbus_tracts_analysis_table.geojson",
    "Charlotte": "charlotte_tracts_analysis_table.geojson",
}

COLS = ["city", "GEOID", "camera_count", "latino_share", "arterial_km_per_km2", "log_income",
        "pop_density_per_km2"]

CITY_FILES_WITH_CRIME = {
    "Fresno": "fresno_tracts_analysis_table.geojson",
    "Phoenix": "phoenix_tracts_analysis_table.geojson",
    "Albuquerque": "albuquerque_tracts_analysis_table.geojson",
    "Fort Worth": "fort_worth_tracts_analysis_table.geojson",
    "Denver": "denver_tracts_analysis_table.geojson",
    "Sacramento": "sacramento_tracts_analysis_table.geojson",
    "Seattle": "seattle_tracts_analysis_table.geojson",
}


def load_pooled() -> pd.DataFrame:
    frames = []

    oak = gpd.read_file(DATA_PROCESSED / "oakland_tracts_analysis_table.geojson")
    oak = oak[oak["B19013_001E"] > 0].copy()
    oak["log_income"] = np.log(oak["B19013_001E"])
    oak["city"] = "Oakland"
    frames.append(oak[COLS])

    for city, fname in CITY_FILES.items():
        gdf = gpd.read_file(DATA_PROCESSED / fname)
        gdf = gdf[gdf["log_income"].notna()].copy()
        frames.append(gdf[COLS])

    pooled = pd.concat(frames, ignore_index=True)
    pooled["pop_density_per_km2_1000"] = pooled["pop_density_per_km2"] / 1000
    return pooled


def load_pooled_with_crime() -> pd.DataFrame:
    """Oakland + the 3 cities with a crime feed (El Paso excluded -- none found)."""
    cols = COLS + ["crime_rate_annual_per_km2_1000"]
    frames = []

    oak = gpd.read_file(DATA_PROCESSED / "oakland_tracts_analysis_table.geojson")
    oak = oak[oak["B19013_001E"] > 0].copy()
    oak["log_income"] = np.log(oak["B19013_001E"])
    oak["city"] = "Oakland"
    frames.append(oak[cols])

    for city, fname in CITY_FILES_WITH_CRIME.items():
        gdf = gpd.read_file(DATA_PROCESSED / fname)
        gdf = gdf[gdf["log_income"].notna()].copy()
        frames.append(gdf[cols])

    pooled = pd.concat(frames, ignore_index=True)
    pooled["pop_density_per_km2_1000"] = pooled["pop_density_per_km2"] / 1000
    return pooled


def per_city_independent_models(pooled: pd.DataFrame, controls: list, weight_col: str | None = None):
    """Fits each city's own NB regression independently, rather than one joint
    interaction model. With 10 cities the joint model (city dummies +
    city-interaction terms, ~24 parameters) stopped converging -- one city
    (Seattle) has a very narrow real-world Latino-share range (0.6%-26%, vs.
    20+ points of spread elsewhere) that made the joint Hessian singular.
    Fitting each city on its own is standard practice for this situation
    (equivalent in spirit to a "multiverse" of site-level regressions) and
    numerically robust, at the cost of not being able to test cross-city
    equality directly in one model.
    """
    out = {}
    for city in sorted(pooled["city"].unique()):
        sub = pooled[pooled["city"] == city]
        X = sm.add_constant(sub[["latino_share"] + controls])
        y = sub["camera_count"]
        m = sm.NegativeBinomial(y, X).fit(disp=False, cov_type="HC1", maxiter=200)
        b, se = m.params["latino_share"], m.bse["latino_share"]
        p10, p90 = sub["latino_share"].quantile(0.1), sub["latino_share"].quantile(0.9)
        out[city] = {
            "coef": float(b), "se": float(se), "p": float(m.pvalues["latino_share"]),
            "ci": [float(b - 1.96 * se), float(b + 1.96 * se)],
            "converged": bool(m.mle_retvals.get("converged", True)),
            "p10": float(p10), "p90": float(p90),
            "implied_p10_p90_effect": float(b * (p90 - p10)),
        }
    return out


def main():
    pooled = load_pooled()
    print("N per city:")
    print(pooled.groupby("city").agg(n=("GEOID", "count"), cameras=("camera_count", "sum"),
                                       latino_mean=("latino_share", "mean")))

    base_controls = ["arterial_km_per_km2", "log_income", "pop_density_per_km2_1000"]

    print("\n--- Attempting joint pooled NB with city fixed effects (Oakland = reference) ---")
    homog_converged = True
    homog_tbl = {}
    try:
        X = sm.add_constant(
            pd.get_dummies(pooled[["latino_share"] + base_controls + ["city"]], columns=["city"],
                           drop_first=True, dtype=float)
        )
        y = pooled["camera_count"]
        model = sm.NegativeBinomial(y, X).fit(disp=False, cov_type="HC1", maxiter=200)
        if model.bse.isna().any() or not model.mle_retvals.get("converged", True):
            raise RuntimeError("did not converge / singular covariance")
        print(model.summary().tables[1])
        homog_tbl = {v: {"coef": float(model.params[v]), "se": float(model.bse[v]),
                          "p": float(model.pvalues[v])} for v in X.columns}
    except Exception as exc:
        homog_converged = False
        print(f"  FAILED: {exc} -- reporting per-city independent models instead (see below).")

    print("\n--- Per-city independent NB models (robust alternative) ---")
    per_city_out = per_city_independent_models(pooled, base_controls)
    for c, d in per_city_out.items():
        print(f"  {c}: coef={d['coef']:.3f}, p={d['p']:.4f}, "
              f"P10-P90 implied effect={d['implied_p10_p90_effect']:.3f}, converged={d['converged']}")

    out = {
        "n_per_city": pooled.groupby("city").agg(
            n=("GEOID", "count"), cameras=("camera_count", "sum"), latino_mean=("latino_share", "mean")
        ).to_dict("index"),
        "pooled_fe_homogeneous_converged": homog_converged,
        "pooled_fe_homogeneous": homog_tbl,
        "per_city_slope": per_city_out,
        "reference_city": sorted(pooled["city"].unique())[0],
    }

    # --- Crime-controlled spec: Oakland + every city with a crime feed ---
    print(f"\n\n=== Crime-controlled models ({len(CITY_FILES_WITH_CRIME) + 1} cities) ===")
    pooled_c = load_pooled_with_crime()
    print(pooled_c.groupby("city").agg(n=("GEOID", "count"), cameras=("camera_count", "sum")))
    cities_c = sorted(pooled_c["city"].unique())

    print("\n--- Attempting joint pooled NB with crime control + city FE ---")
    homog_c_converged = True
    homog_c_tbl = {}
    try:
        Xc_h = sm.add_constant(
            pd.get_dummies(pooled_c[["latino_share"] + base_controls
                                     + ["crime_rate_annual_per_km2_1000", "city"]],
                           columns=["city"], drop_first=True, dtype=float)
        )
        yc = pooled_c["camera_count"]
        model_ch = sm.NegativeBinomial(yc, Xc_h).fit(disp=False, cov_type="HC1", maxiter=200)
        if model_ch.bse.isna().any() or not model_ch.mle_retvals.get("converged", True):
            raise RuntimeError("did not converge / singular covariance")
        print(model_ch.summary().tables[1])
        homog_c_tbl = {v: {"coef": float(model_ch.params[v]), "se": float(model_ch.bse[v]),
                            "p": float(model_ch.pvalues[v])} for v in Xc_h.columns}
    except Exception as exc:
        homog_c_converged = False
        print(f"  FAILED: {exc} -- reporting per-city independent models instead (see below).")

    print("\n--- Per-city independent NB models, WITH crime control ---")
    per_city_out_c = {}
    crime_coefs = {}
    for city in cities_c:
        sub = pooled_c[pooled_c["city"] == city]
        Xc = sm.add_constant(sub[["latino_share"] + base_controls + ["crime_rate_annual_per_km2_1000"]])
        yc = sub["camera_count"]
        try:
            m = sm.NegativeBinomial(yc, Xc).fit(disp=False, cov_type="HC1", maxiter=200)
            if m.bse.isna().any():
                raise RuntimeError("singular covariance")
        except Exception as exc:
            print(f"  {city}: FAILED to converge with crime control ({exc}) -- skipped")
            continue
        b, se = m.params["latino_share"], m.bse["latino_share"]
        p10, p90 = sub["latino_share"].quantile(0.1), sub["latino_share"].quantile(0.9)
        per_city_out_c[city] = {
            "coef": float(b), "se": float(se), "p": float(m.pvalues["latino_share"]),
            "ci": [float(b - 1.96 * se), float(b + 1.96 * se)],
            "implied_p10_p90_effect": float(b * (p90 - p10)),
        }
        crime_coefs[city] = {
            "coef": float(m.params["crime_rate_annual_per_km2_1000"]),
            "se": float(m.bse["crime_rate_annual_per_km2_1000"]),
            "p": float(m.pvalues["crime_rate_annual_per_km2_1000"]),
        }
        print(f"  {city}: latino coef={b:.3f}, p={m.pvalues['latino_share']:.4f}; "
              f"crime coef={crime_coefs[city]['coef']:.3f}, p={crime_coefs[city]['p']:.4f}")

    out["crime_controlled"] = {
        "cities": cities_c,
        "n_per_city": pooled_c.groupby("city").agg(
            n=("GEOID", "count"), cameras=("camera_count", "sum")
        ).to_dict("index"),
        "pooled_homogeneous_converged": homog_c_converged,
        "pooled_homogeneous": homog_c_tbl,
        "per_city_slope": per_city_out_c,
        "per_city_crime_coef": crime_coefs,
        "reference_city": cities_c[0],
    }

    (REPORT / "pooled_results.json").write_text(json.dumps(out, indent=2))
    print(f"\nsaved {REPORT / 'pooled_results.json'}")


if __name__ == "__main__":
    main()
