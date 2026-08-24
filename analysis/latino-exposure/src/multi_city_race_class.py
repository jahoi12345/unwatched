"""Extends the Oakland-only race/class horse race (src/race_class_horserace.py)
to the four Phase-5 cities: does "Latino share, not race/class generally"
replicate elsewhere, or was that itself an Oakland-specific pattern?

Pooled NB with city fixed effects, all 5 cities (no crime control, so El Paso
stays in -- consistent with the Part-7 no-crime spec, not the crime-controlled
one), plus per-city implied slopes via the delta method for each of
Latino/Black/Asian share and poverty rate.
"""

import json
import pathlib

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as st

HERE = pathlib.Path(__file__).resolve().parent
DATA_RAW = HERE.parent / "data" / "raw"
DATA_PROCESSED = HERE.parent / "data" / "processed"
REPORT = HERE.parent / "report"

CITY_SLUGS = {
    "Oakland": None,  # handled specially: race_class_horserace.py already built this
    "El Paso": "el_paso",
    "Fresno": "fresno",
    "Phoenix": "phoenix",
    "Albuquerque": "albuquerque",
    "San Jose": "san_jose",
    "Fort Worth": "fort_worth",
    "Denver": "denver",
    "Sacramento": "sacramento",
    "Seattle": "seattle",
    "Dallas": "dallas",
    "Kansas City": "kansas_city",
    "San Diego": "san_diego",
    "Columbus": "columbus",
    "Charlotte": "charlotte",
}

ACS_COLS = ["B03002_001E", "B03002_003E", "B03002_004E", "B03002_006E", "B03002_012E",
            "B17001_001E", "B17001_002E"]


def load_city(city: str) -> pd.DataFrame:
    if city == "Oakland":
        from race_class_horserace import load_race_poverty
        from models import load_model_frame

        gdf = load_model_frame("tracts")
        race = load_race_poverty()
        merged = gdf.merge(race, on="GEOID", how="left", suffixes=("", "_rp"))
        total = merged["B03002_001E_rp"] if "B03002_001E_rp" in merged else merged["B03002_001E"]
    else:
        slug = CITY_SLUGS[city]
        gdf = gpd.read_file(DATA_PROCESSED / f"{slug}_tracts_analysis_table.geojson")
        acs = json.loads((DATA_RAW / slug / "acs_race_poverty.json").read_text())
        race = pd.DataFrame(acs["rows"], columns=acs["header"]).drop(columns=["NAME"])
        for c in ACS_COLS:
            race[c] = pd.to_numeric(race[c], errors="coerce")
        race["GEOID"] = race["state"] + race["county"] + race["tract"]
        # gdf already has B03002_001E/B03002_012E from multi_city.py's own ACS
        # pull (used for latino_share) -- drop the duplicates from this second
        # fetch to avoid a _x/_y suffix collision on merge.
        race = race.drop(columns=["B03002_001E", "B03002_001M", "B03002_012E", "B03002_012M"])
        merged = gdf.merge(race, on="GEOID", how="left")
        total = merged["B03002_001E"]

    merged["black_share"] = merged["B03002_004E"] / total
    merged["asian_share"] = merged["B03002_006E"] / total
    merged["white_share"] = merged["B03002_003E"] / total
    merged["poverty_rate"] = merged["B17001_002E"] / merged["B17001_001E"]
    merged["city"] = city
    keep = ["city", "GEOID", "camera_count", "latino_share", "black_share", "asian_share",
            "white_share", "poverty_rate", "arterial_km_per_km2", "log_income",
            "pop_density_per_km2"]
    return merged[keep].copy()


def main():
    frames = [load_city(c) for c in CITY_SLUGS]
    pooled = pd.concat(frames, ignore_index=True)
    pooled = pooled.dropna(subset=["latino_share", "black_share", "asian_share", "poverty_rate",
                                    "log_income", "camera_count"])
    pooled["pop_density_per_km2_1000"] = pooled["pop_density_per_km2"] / 1000

    print("N per city:")
    print(pooled.groupby("city").agg(n=("GEOID", "count"), cameras=("camera_count", "sum")))

    base_vars = ["arterial_km_per_km2", "log_income", "pop_density_per_km2_1000"]
    demo_vars = ["latino_share", "black_share", "asian_share", "poverty_rate"]

    # Joint pooled model (one shared slope per variable + city fixed effects)
    # is attempted for reference, but at 10 cities the equivalent joint
    # interaction model (needed for per-city slopes) stopped converging --
    # same issue as pooled_model.py (Seattle's narrow demographic ranges make
    # the Hessian singular). Per-city independent models (below) are the
    # robust approach used for the actual per-city results.
    homog_converged = True
    homog_tbl = {}
    try:
        dummies = pd.get_dummies(pooled["city"], prefix="city", drop_first=True, dtype=float)
        X = pd.concat([pooled[demo_vars + base_vars], dummies], axis=1)
        X = sm.add_constant(X)
        y = pooled["camera_count"]
        model = sm.NegativeBinomial(y, X).fit(disp=False, cov_type="HC1", maxiter=200)
        if model.bse.isna().any() or not model.mle_retvals.get("converged", True):
            raise RuntimeError("did not converge / singular covariance")
        print("\n--- Pooled NB, race + poverty + city FE (homogeneous slopes) ---")
        print(model.summary().tables[1])
        homog_tbl = {v: {"coef": float(model.params[v]), "se": float(model.bse[v]),
                          "p": float(model.pvalues[v])} for v in X.columns}
    except Exception as exc:
        homog_converged = False
        print(f"\n--- Pooled NB, race + poverty + city FE: FAILED ({exc}) ---")

    print("\n--- Per-city independent models, all 4 demographic variables together ---")
    per_var_city = {var: {} for var in demo_vars}
    for city in sorted(pooled["city"].unique()):
        sub = pooled[pooled["city"] == city]
        Xc = sm.add_constant(sub[demo_vars + base_vars])
        yc = sub["camera_count"]
        m = sm.NegativeBinomial(yc, Xc).fit(disp=False, cov_type="HC1", maxiter=200)
        print(f"\n{city} (n={len(sub)}):")
        for var in demo_vars:
            b, se, p = m.params[var], m.bse[var], m.pvalues[var]
            p10, p90 = sub[var].quantile(0.1), sub[var].quantile(0.9)
            per_var_city[var][city] = {
                "coef": float(b), "se": float(se), "p": float(p),
                "p10": float(p10), "p90": float(p90),
                "implied_p10_p90_effect": float(b * (p90 - p10)),
            }
            print(f"  {var}: coef={b:.3f}, p={p:.4f}, "
                  f"P10-P90 implied effect={b * (p90 - p10):.3f}")

    out = {
        "n_per_city": pooled.groupby("city").agg(n=("GEOID", "count"), cameras=("camera_count", "sum")).to_dict("index"),
        "pooled_homogeneous_converged": homog_converged,
        "pooled_homogeneous": homog_tbl,
        "per_variable_per_city": per_var_city,
        "reference_city": sorted(pooled["city"].unique())[0],
    }
    (REPORT / "multi_city_race_class_results.json").write_text(json.dumps(out, indent=2))
    print(f"\nsaved {REPORT / 'multi_city_race_class_results.json'}")


if __name__ == "__main__":
    main()
