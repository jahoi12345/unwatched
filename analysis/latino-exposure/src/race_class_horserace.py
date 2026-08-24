"""Follow-up to Phase 2: is the Latino-share effect specific to that group, or
does it reflect Black/other-nonwhite composition generally, or class (poverty)
rather than race at all? Adds White/Black/Asian shares (non-Hispanic) and a
poverty-rate variable to the tract-level model and runs the race-vs-class
comparison directly.

Race-share regressors are Latino, Black-non-Hispanic, Asian-non-Hispanic, with
White-non-Hispanic as the omitted reference category (all four are mutually
exclusive and, with the smaller "other/two-or-more races" residual, exhaustive --
including all four plus a constant would be perfectly collinear).
"""

import json
import pathlib

import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = pathlib.Path(__file__).resolve().parent
DATA_RAW = HERE.parent / "data" / "raw"

from models import load_model_frame, CONTROLS  # noqa: E402


def load_race_poverty():
    d = json.loads((DATA_RAW / "alameda_acs_tracts_race_poverty.json").read_text())
    df = pd.DataFrame(d["rows"], columns=d["header"]).drop(columns=["NAME"])
    numeric_cols = [c for c in df.columns if c not in ("state", "county", "tract")]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["GEOID"] = df["state"] + df["county"] + df["tract"]
    return df


def main():
    gdf = load_model_frame("tracts")
    race = load_race_poverty()
    merged = gdf.merge(race, on="GEOID", how="left", suffixes=("", "_rp"))

    total = merged["B03002_001E_rp"] if "B03002_001E_rp" in merged else merged["B03002_001E"]
    merged["white_share"] = merged["B03002_003E"] / total
    merged["black_share"] = merged["B03002_004E"] / total
    merged["asian_share"] = merged["B03002_006E"] / total
    merged["poverty_rate"] = merged["B17001_002E"] / merged["B17001_001E"]

    print(f"n = {len(merged)}")
    print("\n--- Raw correlations with camera density (per km2) ---")
    for var, label in [
        ("latino_share", "Latino share"),
        ("black_share", "Black share (non-Hispanic)"),
        ("asian_share", "Asian share (non-Hispanic)"),
        ("white_share", "White share (non-Hispanic, reference group)"),
        ("poverty_rate", "Poverty rate"),
        ("B19013_001E", "Median household income"),
    ]:
        sub = merged[[var, "camera_density_per_km2"]].dropna()
        r = np.corrcoef(sub[var], sub["camera_density_per_km2"])[0, 1]
        print(f"  {label}: r = {r:.3f} (n={len(sub)})")

    print("\n--- Model A: race shares only (no income/poverty) ---")
    varsA = ["latino_share", "black_share", "asian_share"] + [c for c in CONTROLS if c != "log_income"]
    dfA = merged.dropna(subset=varsA + ["camera_count"])
    XA = sm.add_constant(dfA[varsA])
    modelA = sm.NegativeBinomial(dfA["camera_count"], XA).fit(disp=False, cov_type="HC1")
    print(modelA.summary().tables[1])

    print("\n--- Model B: race shares + poverty rate (the race-vs-class horse race) ---")
    varsB = ["latino_share", "black_share", "asian_share", "poverty_rate"] + [c for c in CONTROLS if c != "log_income"]
    dfB = merged.dropna(subset=varsB + ["camera_count"])
    XB = sm.add_constant(dfB[varsB])
    modelB = sm.NegativeBinomial(dfB["camera_count"], XB).fit(disp=False, cov_type="HC1")
    print(modelB.summary().tables[1])

    print("\n--- Model C: poverty rate only, no race terms at all (does class alone explain it?) ---")
    varsC = ["poverty_rate"] + [c for c in CONTROLS if c != "log_income"]
    dfC = merged.dropna(subset=varsC + ["camera_count"])
    XC = sm.add_constant(dfC[varsC])
    modelC = sm.NegativeBinomial(dfC["camera_count"], XC).fit(disp=False, cov_type="HC1")
    print(modelC.summary().tables[1])

    from statsmodels.stats.outliers_influence import variance_inflation_factor
    print("\n--- VIF, Model B ---")
    for i, col in enumerate(XB.columns):
        if col == "const":
            continue
        print(f"  {col}: {variance_inflation_factor(XB.values, i):.2f}")

    descriptives = {
        v: {"mean": float(merged[v].mean()), "std": float(merged[v].std())}
        for v in ["latino_share", "black_share", "asian_share", "white_share"]
    }

    def model_table(results):
        return {
            var: {
                "coef": float(results.params[var]),
                "se": float(results.bse[var]),
                "p": float(results.pvalues[var]),
            }
            for var in results.params.index
        }

    correlations = {}
    for var in ["latino_share", "black_share", "asian_share", "white_share", "poverty_rate", "B19013_001E"]:
        sub = merged[[var, "camera_density_per_km2"]].dropna()
        correlations[var] = float(np.corrcoef(sub[var], sub["camera_density_per_km2"])[0, 1])

    out = {
        "n": len(merged),
        "correlations": correlations,
        "descriptives": descriptives,
        "model_a_race_only": model_table(modelA),
        "model_b_race_and_poverty": model_table(modelB),
        "model_c_poverty_only": model_table(modelC),
    }
    out_path = HERE.parent / "report" / "race_class_results.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nsaved {out_path}")

    return {"modelA": modelA, "modelB": modelB, "modelC": modelC, "merged": merged}


if __name__ == "__main__":
    main()
