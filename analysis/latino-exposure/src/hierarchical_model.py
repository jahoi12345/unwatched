"""Bayesian hierarchical (multilevel) negative-binomial model, replacing the
ad hoc choice between "one pooled slope for all 15 cities" (which failed to
converge for the Latino-only spec, and even when it converged for the
race/class spec gave no per-city detail) and "15 completely separate
per-city regressions" (numerically robust but throws away the fact that
these are all draws from a population of cities, and lets small/noisy
cities like Seattle produce wild, unstable point estimates).

Structure: tracts nested in cities. Latino share gets a random intercept AND
random slope by city (partial pooling -- each city's slope is an estimate
informed by its own data AND pulled toward the population mean, with the
pull strength determined by how much the data actually support a
city-specific deviation). Black share, Asian share, poverty rate, and the
controls are fixed (population-level) effects only -- with just 15 cities,
giving every one of the four demographic variables its own random slope
would ask a 15-group dataset to identify a high-dimensional covariance
structure it can't realistically support; Latino share is the one that
matters most for this project's central question, so it's the one that gets
the full hierarchical treatment.

Random intercept and random slope are modeled as independent (not a
correlated 2D normal via LKJ) -- again a deliberate simplification given only
15 groups, where a full covariance estimate would be poorly identified.
"""

import json
import pathlib

import arviz as az
import numpy as np
import pandas as pd
import pymc as pm

HERE = pathlib.Path(__file__).resolve().parent
REPORT = HERE.parent / "report"

import sys
sys.path.insert(0, str(HERE))
from multi_city_race_class import CITY_SLUGS, load_city  # noqa: E402


def load_all_cities() -> pd.DataFrame:
    frames = [load_city(c) for c in CITY_SLUGS]
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["latino_share", "black_share", "asian_share", "poverty_rate",
                            "log_income", "camera_count", "arterial_km_per_km2",
                            "pop_density_per_km2"])
    df["pop_density_per_km2_1000"] = df["pop_density_per_km2"] / 1000
    return df.reset_index(drop=True)


def build_and_sample(df: pd.DataFrame):
    cities = sorted(df["city"].unique())
    city_idx_map = {c: i for i, c in enumerate(cities)}
    city_idx = df["city"].map(city_idx_map).values
    n_cities = len(cities)

    latino = df["latino_share"].values
    black = df["black_share"].values
    asian = df["asian_share"].values
    poverty = df["poverty_rate"].values
    arterial = df["arterial_km_per_km2"].values
    log_income = df["log_income"].values
    density = df["pop_density_per_km2_1000"].values
    y = df["camera_count"].values

    coords = {"city": cities, "obs": np.arange(len(df))}

    with pm.Model(coords=coords) as model:
        # Population-level (fixed) effects
        a = pm.Normal("a", 0, 5)
        b_latino = pm.Normal("b_latino", 0, 2)  # population mean Latino-share slope
        b_black = pm.Normal("b_black", 0, 2)
        b_asian = pm.Normal("b_asian", 0, 2)
        b_poverty = pm.Normal("b_poverty", 0, 2)
        b_arterial = pm.Normal("b_arterial", 0, 2)
        b_income = pm.Normal("b_income", 0, 2)
        b_density = pm.Normal("b_density", 0, 2)

        # Random intercept and random Latino-share slope by city (independent,
        # non-centered parameterization for sampling efficiency)
        sigma_a_city = pm.HalfNormal("sigma_a_city", 2)
        a_city_raw = pm.Normal("a_city_raw", 0, 1, dims="city")
        a_city = pm.Deterministic("a_city", a_city_raw * sigma_a_city, dims="city")

        sigma_b_city = pm.HalfNormal("sigma_b_city", 2)
        b_latino_city_raw = pm.Normal("b_latino_city_raw", 0, 1, dims="city")
        b_latino_city = pm.Deterministic("b_latino_city", b_latino_city_raw * sigma_b_city, dims="city")

        # Per-city total Latino-share slope (population mean + city deviation)
        city_slope = pm.Deterministic("city_slope", b_latino + b_latino_city, dims="city")

        eta = (
            a + a_city[city_idx]
            + city_slope[city_idx] * latino
            + b_black * black + b_asian * asian + b_poverty * poverty
            + b_arterial * arterial + b_income * log_income + b_density * density
        )
        mu = pm.math.exp(eta)
        alpha = pm.HalfNormal("alpha", 5)

        pm.NegativeBinomial("y", mu=mu, alpha=alpha, observed=y, dims="obs")

        trace = pm.sample(1500, tune=1500, chains=4, target_accept=0.95,
                           random_seed=42, progressbar=True)

    return model, trace, cities


def main():
    df = load_all_cities()
    print("N per city:")
    print(df.groupby("city").size())

    model, trace, cities = build_and_sample(df)

    summary = az.summary(trace, ci_prob=0.94, ci_kind="hdi", var_names=[
        "a", "b_latino", "b_black", "b_asian", "b_poverty",
        "b_arterial", "b_income", "b_density",
        "sigma_a_city", "sigma_b_city", "alpha",
    ])
    print(summary)

    max_rhat = summary["r_hat"].max()
    min_ess = summary["ess_bulk"].min()
    n_divergent = int(trace.sample_stats["diverging"].sum())
    print(f"\nmax r_hat: {max_rhat:.3f}, min ess_bulk: {min_ess:.0f}, divergences: {n_divergent}")

    city_slope_summary = az.summary(trace, ci_prob=0.94, ci_kind="hdi", var_names=["city_slope"])
    city_slope_summary.index = cities

    out = {
        "n_total": len(df),
        "n_cities": len(cities),
        "diagnostics": {
            "max_rhat": float(max_rhat),
            "min_ess_bulk": float(min_ess),
            "n_divergent": n_divergent,
        },
        "population_level": {
            var: {
                "mean": float(summary.loc[var, "mean"]),
                "sd": float(summary.loc[var, "sd"]),
                "hdi_3%": float(summary.loc[var, "hdi94_lb"]),
                "hdi_97%": float(summary.loc[var, "hdi94_ub"]),
            }
            for var in ["a", "b_latino", "b_black", "b_asian", "b_poverty",
                        "b_arterial", "b_income", "b_density",
                        "sigma_a_city", "sigma_b_city", "alpha"]
        },
        "city_slope": {
            city: {
                "mean": float(city_slope_summary.loc[city, "mean"]),
                "sd": float(city_slope_summary.loc[city, "sd"]),
                "hdi_3%": float(city_slope_summary.loc[city, "hdi94_lb"]),
                "hdi_97%": float(city_slope_summary.loc[city, "hdi94_ub"]),
            }
            for city in cities
        },
    }
    (REPORT / "hierarchical_results.json").write_text(json.dumps(out, indent=2))
    print(f"\nsaved {REPORT / 'hierarchical_results.json'}")

    trace.to_netcdf(str(HERE.parent / "data" / "processed" / "hierarchical_trace.nc"))
    print("saved trace")


if __name__ == "__main__":
    main()
