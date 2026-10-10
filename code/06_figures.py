#!/usr/bin/env python3
"""Manuscript figures, built from pipeline outputs only.

    Figure 1  Item missingness in the 2024 analytic cohort, by reason (not stated vs NCHS-imputed)
    Figure 2  Early preterm prevalence among records with an item missing vs recorded (2024)
    Figure 3  Baseline AUPRC with 95% bootstrap intervals, both tasks (standard track)

Writes paper/figures/fig{1,2,3}.png (300 dpi) and paper/tables/table_predictors.md.
Figures carry a DRAFT mark unless run with --final (after author verification).

    python code/06_figures.py [--final]
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import pandas as pd  # noqa: E402

from natality_common import PAPER, PROCESSED, TEST_YEAR, load_layout  # noqa: E402

FINAL = "--final" in sys.argv
BLUE, ORANGE = "#2a78d6", "#eb6834"          # validated categorical slots 1-2
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"
FIG = PAPER / "figures"
TAB = PAPER / "tables"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.dpi": 300,
})


def stamp(fig):
    if not FINAL:
        fig.text(0.99, 0.01, "DRAFT", ha="right", va="bottom", fontsize=7, color="#c00000", alpha=0.6)


def labels():
    lay = load_layout()
    lab = dict(zip(lay["name"], lay["label"]))
    return {k: v.split(" (")[0] for k, v in lab.items()}


def fig1(aud, lab):
    d = aud[(aud["year"] == TEST_YEAR) & (aud["population"] == "cohort") & (aud["role"] == "predictor")].copy()
    d["S_pct"], d["I_pct"] = 100 * d["S"] / d["n"], 100 * d["I"] / d["n"]
    d["tot"] = d["S_pct"] + d["I_pct"]
    d = d[d["tot"] >= 0.5].sort_values("tot")
    fig, ax = plt.subplots(figsize=(6.2, 0.22 * len(d) + 0.9))
    y = range(len(d))
    names = [lab.get(f, f) for f in d["field"]]
    ax.barh(y, d["S_pct"], height=0.62, color=BLUE, label="Not stated", edgecolor=SURFACE, linewidth=1)
    ax.barh(y, d["I_pct"], left=d["S_pct"], height=0.62, color=ORANGE, label="Imputed by NCHS (restored to missing)",
            edgecolor=SURFACE, linewidth=1)
    for yi, t in zip(y, d["tot"]):
        ax.text(t + 0.15, yi, f"{t:.1f}%", va="center", fontsize=7.5, color=INK2)
    ax.set_yticks(list(y), names)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel(f"Share of {TEST_YEAR} analytic cohort with the item missing (%)")
    ax.set_xlim(0, d["tot"].max() * 1.15)
    ax.legend(loc="lower right", frameon=False, fontsize=7.5)
    stamp(fig)
    fig.tight_layout()
    fig.savefig(FIG / "fig1.png")
    plt.close(fig)


def fig2(inf, lab):
    d = inf[(inf["year"] == TEST_YEAR) & (inf["task"] == "EPTB") & (inf["n_missing"] >= 1000)].copy()
    lay = load_layout()
    preds = set(lay.loc[lay["role"] == "predictor", "name"])
    d = d[d["field"].isin(preds)].copy()
    d["ratio"] = d["prev_missing"] / d["prev_observed"]
    d = d.sort_values("ratio")
    fig, ax = plt.subplots(figsize=(6.2, 0.19 * len(d) + 0.9))
    y = list(range(len(d)))
    for yi, (_, r) in zip(y, d.iterrows()):
        ax.plot([100 * r["prev_observed"], 100 * r["prev_missing"]], [yi, yi], color=GRID, lw=2, zorder=1)
    ax.scatter(100 * d["prev_observed"], y, s=34, color=BLUE, zorder=3, label="Item recorded",
               edgecolor=SURFACE, linewidth=1.5)
    ax.scatter(100 * d["prev_missing"], y, s=34, color=ORANGE, zorder=3, label="Item missing",
               edgecolor=SURFACE, linewidth=1.5)
    for yi, (_, r) in zip(y, d.iterrows()):
        ax.text(max(100 * r["prev_missing"], 100 * r["prev_observed"]) * 1.08, yi, f"{r['ratio']:.1f}×",
                va="center", fontsize=7.5, color=INK2)
    ax.set_xscale("log")
    ax.set_yticks(y, [lab.get(f, f) for f in d["field"]])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel(f"Early preterm birth prevalence, {TEST_YEAR} cohort (%, log scale)")
    lo = 100 * d[["prev_missing", "prev_observed"]].min().min()
    hi = 100 * d[["prev_missing", "prev_observed"]].max().max()
    xs = [x for x in [1, 1.5, 2, 3, 5, 8, 10, 20, 50] if lo * 0.85 <= x <= hi * 1.6]
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xticks(xs, [f"{x:g}" for x in xs])
    ax.set_xlim(lo * 0.85, hi * 1.6)
    ax.legend(loc="lower right", frameon=False, fontsize=7.5)
    stamp(fig)
    fig.tight_layout()
    fig.savefig(FIG / "fig2.png")
    plt.close(fig)


NAMES = {"B1": "B1 Complete case", "B2": "B2 Mean + indicators", "B3": "B3 Chained equations",
         "B4": "B4 Iterative random forest", "B5": "B5 LightGBM, native missing", "B6": "B6 B5 + agency classes"}


def fig3(res):
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7), sharey=True)
    titles = {"EPTB": "Early preterm birth (<34 weeks)", "VLBW": "Very low birthweight (<1,500 g)"}
    for ax, task in zip(axes, ["EPTB", "VLBW"]):
        d = res[res["task"] == task].sort_values("baseline", ascending=False)
        y = list(range(len(d)))
        ax.hlines(y, d["auprc_lo"], d["auprc_hi"], color=BLUE, lw=2)
        ax.scatter(d["auprc"], y, s=30, color=BLUE, zorder=3, edgecolor=SURFACE, linewidth=1.5)
        prev = d["prevalence"].iloc[0]
        ax.axvline(prev, color=INK2, lw=1, ls=(0, (3, 2)))
        ax.text(prev, -0.75, f" prevalence {100 * prev:.2f}%", fontsize=7, color=INK2, va="center")
        for yi, v in zip(y, d["auprc"]):
            ax.text(v + 0.002, yi + 0.18, f"{v:.3f}", fontsize=7, color=INK2)
        ax.set_yticks(y, [NAMES[b] for b in d["baseline"]])
        ax.grid(axis="y", visible=False)
        ax.set_title(titles[task], fontsize=8.5, color=INK, loc="left")
        ax.set_xlabel("AUPRC, 2024 test year (95% CI)")
        ax.set_xlim(0, d["auprc_hi"].max() * 1.2)
        ax.set_ylim(-1.2, len(d) - 0.5)
    stamp(fig)
    fig.tight_layout()
    fig.savefig(FIG / "fig3.png")
    plt.close(fig)


def table_predictors(aud, lab):
    lay = load_layout()
    p = lay[lay["role"] == "predictor"]
    d = aud[(aud["year"] == TEST_YEAR) & (aud["population"] == "cohort")].set_index("field")
    rows = ["| Field | Description | Not stated (%) | NCHS-imputed (%) | Not applicable (%) |",
            "|---|---|---:|---:|---:|"]
    for _, r in p.iterrows():
        x = d.loc[r["name"]]
        rows.append(f"| `{r['name']}` | {lab.get(r['name'], r['name'])} | {100 * x['S'] / x['n']:.2f} | "
                    f"{100 * x['I'] / x['n']:.2f} | {100 * x['A'] / x['n']:.2f} |")
    (TAB / "table_predictors.md").write_text("\n".join(rows) + "\n")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    aud = pd.read_csv(PROCESSED / "missingness_audit.csv")
    inf = pd.read_csv(PROCESSED / "missingness_vs_outcome.csv")
    res = pd.read_csv(PAPER / "baselines_standard.csv")
    lab = labels()
    fig1(aud, lab)
    fig2(inf, lab)
    fig3(res)
    table_predictors(aud, lab)
    print("wrote", sorted(p.name for p in FIG.glob("*.png")), "and tables/table_predictors.md")


if __name__ == "__main__":
    main()
