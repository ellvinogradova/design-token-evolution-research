#!/usr/bin/env python3
"""Day 6: generate the paper's comparative figures.
Static print/markdown figures, not an interactive web chart -- so the
dataviz skill's interaction/hover guidance doesn't apply, but its color
and mark-spec guidance does: validated categorical palette (design-token-
evolution-research/references borrowed from the skill's default palette,
see scripts/../dataviz skill palette.md), fixed color per phase across
every figure (Before=blue slot1, After=green slot2, Proposed=magenta
slot3), thin bars with a surface gap, direct value labels at bar tips,
recessive hairline gridlines, legend present for 2+ series.
"""
import json
import glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "paper" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

# Validated categorical palette (light mode), from the dataviz skill's
# reference palette.md -- fixed semantic mapping used across every figure.
BEFORE = "#2a78d6"   # slot 1, blue
AFTER = "#008300"    # slot 2, green
PROPOSED = "#e87ba4" # slot 3, magenta
GRID = "#d9d8d3"     # recessive hairline
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"

plt.rcParams.update({
    "font.size": 11,
    "text.color": TEXT,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT_SECONDARY,
    "xtick.color": TEXT_SECONDARY,
    "ytick.color": TEXT_SECONDARY,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.family": "sans-serif",
})


def load_all():
    systems = []
    for f in sorted(glob.glob(str(RESULTS / "tokens_*.json"))):
        systems.append(json.loads(Path(f).read_text()))
    return systems


def short_name(system_name: str) -> str:
    return {
        "Ant Design": "Ant Design",
        "Fluent UI": "Fluent UI",
        "Carbon Design System": "Carbon",
        "Material Design / MUI": "MUI",
        "Shopify Polaris": "Polaris",
    }.get(system_name, system_name)


def bar_with_label(ax, x, height, color, width, label=None):
    bars = ax.bar(x, height, width=width, color=color, label=label, zorder=3)
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + max(height) * 0.015 if height else 0,
                 f"{int(h)}", ha="center", va="bottom", fontsize=9, color=TEXT)
    return bars


def fig1_token_counts(systems):
    fig, ax = plt.subplots(figsize=(9, 5))
    names = [short_name(s["system"]) for s in systems]
    before = [s["before"]["total_tokens"] for s in systems]
    after = [s["after"]["total_tokens"] for s in systems]

    x = range(len(names))
    w = 0.32
    bar_with_label(ax, [i - w / 2 for i in x], before, BEFORE, w, "Before")
    bar_with_label(ax, [i + w / 2 for i in x], after, AFTER, w, "After")

    ax.set_xticks(list(x))
    ax.set_xticklabels(names)
    ax.set_ylabel("Total tokens extracted")
    ax.set_title("Figure 1. Token count before vs. after each system's audited transition", loc="left", fontsize=12, color=TEXT, pad=45)
    ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.01, 1, 0.2),
              ncol=2, mode="expand", borderaxespad=0)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig1_token_counts.png", dpi=200)
    plt.close(fig)


def fig2_objective_subscore(systems):
    scores = json.loads((RESULTS / "objective_subscores.json").read_text())
    proposals = {
        "ant-design": 3,
        "carbon": 3,
    }
    fig, ax = plt.subplots(figsize=(9, 5))
    names = [short_name(s["system"]) for s in scores]
    before = [s["before"]["objective_subscore"] for s in scores]
    after = [s["after"]["objective_subscore"] for s in scores]
    proposed = [proposals.get(s["slug"], None) for s in scores]

    x = list(range(len(names)))
    w = 0.26
    bar_with_label(ax, [i - w for i in x], before, BEFORE, w, "Before")
    bar_with_label(ax, [i for i in x], after, AFTER, w, "After")
    # proposed bars only where applicable
    px = [i + w for i, p in zip(x, proposed) if p is not None]
    ph = [p for p in proposed if p is not None]
    if px:
        bar_with_label(ax, px, ph, PROPOSED, w, "After + augmentation proposal")

    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("Objective sub-score (0–4)")
    ax.set_ylim(0, 4.6)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.set_title("Figure 2. Objective accessibility sub-score (DTCG + 3 WCAG-cited categories)", loc="left", fontsize=12, color=TEXT, pad=45)
    ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.01, 1, 0.2),
              ncol=3, mode="expand", borderaxespad=0)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig2_objective_subscore.png", dpi=200)
    plt.close(fig)


def fig3_migration_cost(systems):
    fig, ax = plt.subplots(figsize=(9, 5))
    names = [short_name(s["system"]) for s in systems]
    removed = [s["diff"]["removed_count"] for s in systems]
    added = [s["diff"]["added_count"] for s in systems]

    x = range(len(names))
    w = 0.32
    bar_with_label(ax, [i - w / 2 for i in x], removed, "#eb6834", w, "Removed")
    bar_with_label(ax, [i + w / 2 for i in x], added, AFTER, w, "Added")

    ax.set_xticks(list(x))
    ax.set_xticklabels(names)
    ax.set_ylabel("Token count")
    ax.set_title("Figure 3. Migration-cost surface: tokens removed vs. added per transition", loc="left", fontsize=12, color=TEXT, pad=45)
    ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.01, 1, 0.2),
              ncol=2, mode="expand", borderaxespad=0)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig3_migration_cost.png", dpi=200)
    plt.close(fig)


def main():
    systems = load_all()
    fig1_token_counts(systems)
    fig2_objective_subscore(systems)
    fig3_migration_cost(systems)
    print("Wrote fig1_token_counts.png, fig2_objective_subscore.png, fig3_migration_cost.png to", FIGURES)


if __name__ == "__main__":
    main()
