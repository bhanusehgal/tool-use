"""Generate the README / VISUAL_GUIDE charts as SVG, in a light and a dark version.

GitHub picks the right one with <picture> + prefers-color-scheme.
Numbers are copied from EVALUATION.md (each chart names its source results folder).

Usage:  pip install -r requirements-docs.txt
        py docs/make_charts.py            -> docs/images/*-light.svg and *-dark.svg
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

OUT = Path(__file__).parent / "images"

# Validated default palette (dataviz reference instance). Slots 1-3 validate for all pairs in both modes.
THEMES = {
    "light": {"series": ["#2a78d6", "#eb6834", "#1baf7a"], "ink": "#0b0b0b", "ink2": "#52514e",
              "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7", "gap": "#ffffff"},
    "dark": {"series": ["#3987e5", "#d95926", "#199e70"], "ink": "#ffffff", "ink2": "#c3c2b7",
             "muted": "#898781", "grid": "#2c2c2a", "axis": "#383835", "gap": "#0d1117"},
}

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"],
    "font.size": 10,
    "svg.fonttype": "path",  # text as outlines: renders identically everywhere
})


def bar(ax, x, h, w, color, radius_px=4):
    """A bar drawn as ONE path: flat baseline, ~4px rounded top corners.
    Call AFTER the axis limits are set: the radius is converted from pixels to data units."""
    if h <= 0:
        return
    (x0, y0), (x1, y1) = ax.transData.transform([(0, 0), (1, 1)])
    rx = min(radius_px / (x1 - x0), w / 2)
    ry = min(radius_px / (y1 - y0), h)
    verts = [(x, 0), (x, h - ry), (x, h), (x + rx, h), (x + w - rx, h), (x + w, h), (x + w, h - ry), (x + w, 0), (x, 0)]
    codes = [MPath.MOVETO, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CURVE3, MPath.CURVE3,
             MPath.LINETO, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, linewidth=0))


def style(ax, t, ymax, ylabel=None, yfmt=None):
    ax.set_ylim(0, ymax)
    ax.set_facecolor("none")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["axis"])
    ax.tick_params(colors=t["muted"], length=0, labelsize=9)
    ax.yaxis.grid(True, color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    for label in ax.get_xticklabels():
        label.set_color(t["ink2"])
    if ylabel:
        ax.set_ylabel(ylabel, color=t["muted"], fontsize=9)
    if yfmt:
        ax.yaxis.set_major_formatter(yfmt)


def title(fig, t, text, sub):
    fig.text(0.02, 0.965, text, color=t["ink"], fontsize=13, fontweight="bold", va="top")
    fig.text(0.02, 0.905, sub, color=t["ink2"], fontsize=9.5, va="top")


def legend(fig, t, names, colors, y=0.835):
    x = 0.02
    for name, color in zip(names, colors):
        fig.patches.append(FancyBboxPatch((x, y - 0.012), 0.012, 0.024, boxstyle="round,pad=0,rounding_size=0.003",
                                          transform=fig.transFigure, facecolor=color, linewidth=0))
        fig.text(x + 0.018, y, name, color=t["ink2"], fontsize=9, va="center")
        x += 0.018 + 0.0085 * len(name) + 0.04


def grouped(ax, t, groups, series, values, labels, ymax, width=0.32, gap=0.03):
    """values[s][g]; None = not applicable (drawn as a 'n/a' note)."""
    n = len(series)
    style(ax, t, ymax)
    ax.set_xlim(-0.6, len(groups) - 0.4)
    for g in range(len(groups)):
        start = g - (n * width + (n - 1) * gap) / 2
        for s in range(n):
            v = values[s][g]
            x = start + s * (width + gap)
            if v is None:
                ax.text(x + width / 2, ymax * 0.02, "n/a", ha="center", va="bottom", color=t["muted"], fontsize=8)
                continue
            bar(ax, x, v, width, t["series"][s])
            ax.text(x + width / 2, v + ymax * 0.015, labels[s][g], ha="center", va="bottom",
                    color=t["ink2"], fontsize=8.5)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups)


def save(fig, name, mode):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}-{mode}.svg", transparent=True)
    plt.close(fig)


# ── Charts ───────────────────────────────────────────────────────────────────

def chart_ablation(mode):
    """Source: evals/results/2026-10-03_230935 (ablation) + 2026-10-04_012024 (3 repeats for 'all')."""
    t = THEMES[mode]
    fig = plt.figure(figsize=(9, 4.6))
    title(fig, t, "Stage 4: what each fix contributed",
          "Questions passed out of 14 · Qwen 2.5 7B · each fix switched on alone, then all together")
    legend(fig, t, ["Stage 1: our own JSON protocol", "Stage 2: built-in tool calling"], t["series"][:2])
    ax = fig.add_axes([0.06, 0.12, 0.92, 0.64])
    groups = ["baseline", "+ stemming", "+ prompt rules", "+ better errors", "+ JSON mode", "all fixes\n(3 repeats)"]
    s1 = [9, 10, 11, 10, 10, 11]
    s2 = [10, 11, 13, None, None, 13.33]
    grouped(ax, t, groups, ["s1", "s2"], [s1, s2],
            [[f"{v:g}" for v in s1], ["10", "11", "13", "", "", "13.3"]], ymax=14)
    ax.set_yticks([0, 7, 14])
    save(fig, "ablation", mode)


def chart_stage1_vs_stage2(mode):
    """Source: evals/results/2026-10-03_225345 (stage 3 baseline, 14 cases, re-graded)."""
    t = THEMES[mode]
    fig = plt.figure(figsize=(9, 4.0))
    title(fig, t, "Stages 1–2: our own protocol vs built-in tool calling",
          "Same model, tools and 14 questions · stage 3 baseline, before any fixes")
    legend(fig, t, ["Stage 1: our own JSON protocol", "Stage 2: built-in tool calling"], t["series"][:2])
    metrics = [("Questions passed (of 14)", [9, 10], 14, "{:g}"), ("Format (parse) errors", [22, 0], 25, "{:g}"),
               ("Model calls per question", [3.3, 2.3], 4, "{:.1f}"), ("Seconds per question", [26.1, 10.5], 30, "{:.1f}")]
    for i, (name, vals, ymax, fmt) in enumerate(metrics):
        ax = fig.add_axes([0.04 + i * 0.245, 0.1, 0.2, 0.58])
        style(ax, t, ymax)
        ax.set_xlim(-0.25, 1.25)
        for s, v in enumerate(vals):
            bar(ax, s * 0.55, v, 0.45, t["series"][s])
            ax.text(s * 0.55 + 0.225, v + ymax * 0.02, fmt.format(v), ha="center", va="bottom", color=t["ink2"], fontsize=9)
        ax.set_xlim(-0.25, 1.25)
        ax.set_xticks([])
        ax.set_yticks([0, ymax])
        ax.set_title(name, color=t["ink2"], fontsize=9, loc="left")
    save(fig, "stage1_vs_stage2", mode)


def chart_retrieval(mode):
    """Source: evals/results/retrieval_2026-10-04_013142.md and 2026-10-04_022720 (agent runs)."""
    t = THEMES[mode]
    fig = plt.figure(figsize=(9, 4.4))
    title(fig, t, "Stage 5: keyword vs semantic (embedding) search",
          "Left: retrieval benchmark, 22 queries, no LLM · Right: the agent end to end (stage 2, document questions)")
    legend(fig, t, ["Queries using the docs' own words", "Paraphrased queries (\"PTO\", \"pay rise\")"], t["series"][:2])
    ax = fig.add_axes([0.06, 0.12, 0.6, 0.62])
    groups = ["keyword", "keyword\n+ stemming", "semantic", "hybrid"]
    exact, para = [100, 100, 100, 100], [50, 58, 92, 67]
    grouped(ax, t, groups, ["e", "p"], [exact, para], [[f"{v}%" for v in exact], [f"{v}%" for v in para]],
            ymax=110, width=0.34)
    ax.set_yticks([0, 50, 100])
    ax.set_yticklabels(["0%", "50%", "100%"])
    ax.set_title("Answer line in the top 3 results", color=t["ink2"], fontsize=9, loc="left")

    ax2 = fig.add_axes([0.74, 0.12, 0.24, 0.62])
    style(ax2, t, 7.7)
    ax2.set_xlim(-0.6, 2.6)
    for i, (name, v) in enumerate([("keyword", 3), ("semantic", 7), ("hybrid", 7)]):
        bar(ax2, i - 0.2, v, 0.4, t["series"][2])  # its own colour: a different measure from the left panel
        ax2.text(i, v + 0.15, f"{v}/7", ha="center", va="bottom", color=t["ink2"], fontsize=9)
    ax2.set_xticks(range(3))
    ax2.set_xticklabels(["keyword", "semantic", "hybrid"])
    ax2.set_xlim(-0.6, 2.6)
    ax2.set_yticks([0, 7])
    ax2.set_title("Agent: document questions passed", color=t["ink2"], fontsize=9, loc="left")
    save(fig, "retrieval", mode)


def chart_memory(mode):
    """Source: evals/results/2026-10-04_084809 (60 conversations) + 2026-10-04_092346 (summary, low trigger)."""
    t = THEMES[mode]
    fig = plt.figure(figsize=(9, 4.0))
    title(fig, t, "Stage 6: conversation memory strategies",
          "6 multi-turn conversations × 2 runs · Qwen 2.5 7B · two separate measures, two panels")
    names = ["none", "full", "window\n(2 turns)", "trim", "summary"]
    passed = [2, 10, 8, 10, 10]
    tokens = [5322, 8403, 7616, 7664, 8030]
    ax = fig.add_axes([0.06, 0.13, 0.42, 0.6])
    style(ax, t, 13.2)
    ax.set_xlim(-0.6, 4.6)
    for i, v in enumerate(passed):
        bar(ax, i - 0.2, v, 0.4, t["series"][0])
        ax.text(i, v + 0.25, f"{v}/12", ha="center", va="bottom", color=t["ink2"], fontsize=9)
    ax.set_xticks(range(5)); ax.set_xticklabels(names); ax.set_xlim(-0.6, 4.6); ax.set_yticks([0, 6, 12])
    ax.set_title("Conversations answered correctly", color=t["ink2"], fontsize=9, loc="left")

    ax2 = fig.add_axes([0.56, 0.13, 0.42, 0.6])
    style(ax2, t, 9500)
    ax2.set_xlim(-0.6, 4.6)
    for i, v in enumerate(tokens):
        bar(ax2, i - 0.2, v, 0.4, t["series"][2])
        ax2.text(i, v + 180, f"{v / 1000:.1f}k", ha="center", va="bottom", color=t["ink2"], fontsize=9)
    ax2.set_xticks(range(5)); ax2.set_xticklabels(names); ax2.set_xlim(-0.6, 4.6)
    ax2.set_yticks([0, 4000, 8000]); ax2.set_yticklabels(["0", "4k", "8k"])
    ax2.set_title("Input tokens for the 4-turn conversation", color=t["ink2"], fontsize=9, loc="left")
    save(fig, "memory", mode)


def chart_framework(mode):
    """Source: evals/results/2026-10-04_103205 (72 runs)."""
    t = THEMES[mode]
    fig = plt.figure(figsize=(9, 4.0))
    title(fig, t, "Stage 7: hand-built loop vs framework (LangChain create_agent)",
          "Questions passed out of 18 · same tools, prompt, retrieval and model")
    legend(fig, t, ["Hand-built loop (~319 lines)", "Framework (~127 lines)"], t["series"][:2])
    ax = fig.add_axes([0.06, 0.12, 0.92, 0.62])
    grouped(ax, t, ["no fixes", "all fixes + semantic search"], ["h", "f"], [[12, 16], [12, 16]],
            [["12", "16"], ["12", "16"]], ymax=19.8, width=0.25, gap=0.03)
    ax.set_yticks([0, 9, 18])
    save(fig, "framework", mode)


if __name__ == "__main__":
    for m in THEMES:
        chart_ablation(m)
        chart_stage1_vs_stage2(m)
        chart_retrieval(m)
        chart_memory(m)
        chart_framework(m)
    print("Wrote:", ", ".join(sorted(p.name for p in OUT.glob("*.svg"))))
