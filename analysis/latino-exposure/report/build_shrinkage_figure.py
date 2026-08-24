"""Figure 8: the shrinkage plot -- each city's independent (unpooled) Latino-
share estimate next to its hierarchical (partially-pooled) counterpart, with
a line connecting them. This is the standard way to show what a multilevel
model actually does: noisy per-city estimates get pulled toward the
population mean, by an amount proportional to how uncertain they were.
"""

import json
import pathlib

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")

HERE = pathlib.Path(__file__).resolve().parent
FIGURES = HERE / "figures"

INK = "#1c1b17"
INK_SECONDARY = "#52514e"
GRAY_GRID = "#c9c7be"
UNPOOLED = "#9c4221"  # rust -- matches the report's secondary accent
POOLED = "#2a78d6"  # blue -- matches the primary accent


def main():
    # The hierarchical model's Latino-share slope is estimated jointly with
    # Black share, Asian share, and poverty rate as covariates -- so the
    # correct "unpooled" comparison is the per-city model that ALSO includes
    # those covariates (multi_city_race_class.py), not the plain Latino-only
    # spec in pooled_results.json (which would be an apples-to-oranges
    # comparison: different adjustment sets produce different coefficients
    # for reasons that have nothing to do with pooling).
    race_class = json.loads((HERE / "multi_city_race_class_results.json").read_text())
    hier = json.loads((HERE / "hierarchical_results.json").read_text())

    unpooled = race_class["per_variable_per_city"]["latino_share"]
    city_slope = hier["city_slope"]
    pop_mean = hier["population_level"]["b_latino"]["mean"]
    pop_lo = hier["population_level"]["b_latino"]["hdi_3%"]
    pop_hi = hier["population_level"]["b_latino"]["hdi_97%"]

    cities = sorted(city_slope.keys(), key=lambda c: unpooled[c]["coef"], reverse=True)
    y = np.arange(len(cities))[::-1]

    fig, ax = plt.subplots(figsize=(6.8, 0.42 * len(cities) + 1.3))

    ax.axvspan(pop_lo, pop_hi, color=POOLED, alpha=0.08, zorder=0)
    ax.axvline(pop_mean, color=POOLED, linewidth=1.2, linestyle="--", zorder=1)

    for yi, city in zip(y, cities):
        u = unpooled[city]["coef"]
        p = city_slope[city]["mean"]
        p_lo, p_hi = city_slope[city]["hdi_3%"], city_slope[city]["hdi_97%"]
        ax.plot([u, p], [yi, yi], color=GRAY_GRID, linewidth=1.2, zorder=1)
        ax.plot([p_lo, p_hi], [yi, yi], color=POOLED, linewidth=3, alpha=0.35, zorder=2)
        ax.scatter([u], [yi], color=UNPOOLED, s=45, zorder=3, edgecolor="white", linewidth=0.5)
        ax.scatter([p], [yi], color=POOLED, s=45, zorder=4, edgecolor="white", linewidth=0.5)

    ax.axvline(0, color=INK, linewidth=0.8, alpha=0.6, zorder=1)
    ax.set_yticks(y)
    ax.set_yticklabels(cities, fontsize=9)
    ax.set_xlabel("Latino-share coefficient\nrust = per-city (unpooled)   blue = hierarchical (pooled)   "
                  "band = population CI", fontsize=9)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(length=0)

    path = FIGURES / "fig8_shrinkage.svg"
    fig.savefig(path, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)
    print(f"saved {path}")


if __name__ == "__main__":
    main()
