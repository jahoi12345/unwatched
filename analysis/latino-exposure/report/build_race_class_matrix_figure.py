"""Figure 7: city x demographic-variable matrix of implied P10-P90 effects
(src/multi_city_race_class.py's results) -- the visual counterpart to Table 5,
which is otherwise a 60-row text table with no way to see the cross-city
pattern at a glance.
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
# Diverging pair (polarity: positive vs negative effect), consistent with the
# rest of the report's blue accent; red as the cool/warm opposite pole.
POS = "#2a78d6"
NEG = "#b5302f"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Source Serif Pro", "Georgia", "serif"],
    "text.color": INK,
    "axes.edgecolor": GRAY_GRID,
    "axes.labelcolor": INK,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
    "figure.facecolor": "none",
    "axes.facecolor": "none",
    "savefig.facecolor": "none",
    "svg.fonttype": "none",
})

VAR_LABELS = {
    "latino_share": "Latino\nshare",
    "black_share": "Black\nshare",
    "asian_share": "Asian\nshare",
    "poverty_rate": "Poverty\nrate",
}


def main():
    d = json.loads((HERE / "multi_city_race_class_results.json").read_text())
    per_var = d["per_variable_per_city"]
    cities = sorted(per_var["latino_share"].keys())
    variables = list(VAR_LABELS.keys())

    # Order cities by number of significant effects (most first), then by
    # total |implied effect| as a tiebreak -- puts the "interesting" cities
    # (Oakland, San Diego, Sacramento...) near the top.
    def city_sort_key(c):
        n_sig = sum(1 for v in variables if per_var[v][c]["p"] < 0.05)
        total_abs = sum(abs(per_var[v][c]["implied_p10_p90_effect"]) for v in variables)
        return (-n_sig, -total_abs)

    cities_sorted = sorted(cities, key=city_sort_key)

    fig, ax = plt.subplots(figsize=(6.6, 0.42 * len(cities_sorted) + 1.6))

    max_abs = max(
        abs(per_var[v][c]["implied_p10_p90_effect"]) for v in variables for c in cities
    )

    for yi, city in enumerate(cities_sorted):
        y = len(cities_sorted) - 1 - yi
        for xi, var in enumerate(variables):
            d_cv = per_var[var][city]
            effect = d_cv["implied_p10_p90_effect"]
            sig = d_cv["p"] < 0.05
            color = POS if effect >= 0 else NEG
            size = 40 + 260 * (abs(effect) / max_abs)
            if sig:
                ax.scatter([xi], [y], s=size, color=color, edgecolor="white",
                           linewidth=0.7, zorder=3)
            else:
                ax.scatter([xi], [y], s=size, facecolor="none", edgecolor=color,
                           linewidth=1.1, alpha=0.55, zorder=2)

    ax.set_xlim(-0.6, len(variables) - 0.4)
    ax.set_ylim(-1.15, len(cities_sorted) - 0.2)
    ax.set_xticks(range(len(variables)))
    ax.set_xticklabels([VAR_LABELS[v] for v in variables], fontsize=9)
    ax.set_yticks(range(len(cities_sorted)))
    ax.set_yticklabels(list(reversed(cities_sorted)), fontsize=9)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=GRAY_GRID, linewidth=0.4, alpha=0.5)

    # Legend: significance + sign, built by hand since sizes vary continuously.
    legend_y = -0.75
    ax.scatter([-0.5], [legend_y], s=140, color=POS, edgecolor="white", linewidth=0.7, clip_on=False)
    ax.text(-0.2, legend_y, "positive,\nsignificant", fontsize=7.5, va="center", color=INK_SECONDARY)
    ax.scatter([0.75], [legend_y], s=140, color=NEG, edgecolor="white", linewidth=0.7, clip_on=False)
    ax.text(1.05, legend_y, "negative,\nsignificant", fontsize=7.5, va="center", color=INK_SECONDARY)
    ax.scatter([2.05], [legend_y], s=140, facecolor="none", edgecolor=INK_SECONDARY, linewidth=1.1, alpha=0.55, clip_on=False)
    ax.text(2.35, legend_y, "not significant\n(either sign)", fontsize=7.5, va="center", color=INK_SECONDARY)

    ax.set_title(
        "Implied P10-to-P90 effect by city and demographic variable\n"
        "(dot size = effect magnitude; filled = significant at p<0.05, colored by sign)",
        fontsize=10.5, loc="left", color=INK, pad=12,
    )

    path = FIGURES / "fig7_race_class_matrix.svg"
    fig.savefig(path, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)
    print(f"saved {path}")


if __name__ == "__main__":
    main()
