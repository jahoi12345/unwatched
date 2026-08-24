"""Figure 5: per-city implied Latino-share slope, from the pooled interaction
model (src/pooled_model.py). Same palette/style as build_figures.py.
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
BLUE = "#2a78d6"
GRAY_GRID = "#c9c7be"

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


def plot_slopes(per_city: dict, order: list, n_per_city: dict, xlabel: str, out_name: str):
    fig, ax = plt.subplots(figsize=(6.6, 3.0 + 0.3 * len(order)))
    y_pos = np.arange(len(order))[::-1]

    for y, city in zip(y_pos, order):
        d = per_city[city]
        color = BLUE if d["p"] < 0.05 else INK_SECONDARY
        ax.plot(d["ci"], [y, y], color=color, linewidth=1.6, solid_capstyle="round")
        ax.scatter([d["coef"]], [y], color=color, s=55, zorder=3, edgecolor="white", linewidth=0.6)

    ax.axvline(0, color=GRAY_GRID, linewidth=1)
    labels = [f"{c}  (n={n_per_city[c]['n']})" for c in order]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel(xlabel)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(length=0)

    path = FIGURES / f"{out_name}.svg"
    fig.savefig(path, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)
    print(f"saved {path}")


def main():
    results = json.loads((HERE / "pooled_results.json").read_text())

    all_cities = sorted(results["per_city_slope"].keys(),
                         key=lambda c: results["per_city_slope"][c]["coef"], reverse=True)
    n_sig = sum(1 for d in results["per_city_slope"].values() if d["p"] < 0.05)
    plot_slopes(
        results["per_city_slope"],
        all_cities,
        results["n_per_city"],
        f"Implied Latino-share coefficient by city, no crime control\n"
        f"(all {len(all_cities)} cities, independent per-city models; {n_sig} individually significant)",
        "fig5_per_city_slopes",
    )

    cc = results["crime_controlled"]
    cc_cities = sorted(cc["per_city_slope"].keys(), key=lambda c: cc["per_city_slope"][c]["coef"], reverse=True)
    attempted = len(cc["cities"])
    plot_slopes(
        cc["per_city_slope"],
        cc_cities,
        cc["n_per_city"],
        f"Implied Latino-share coefficient by city, WITH crime control\n"
        f"({len(cc_cities)} of {attempted} attempted converged; Oakland's effect survives and strengthens)",
        "fig6_per_city_slopes_crime_controlled",
    )


if __name__ == "__main__":
    main()
