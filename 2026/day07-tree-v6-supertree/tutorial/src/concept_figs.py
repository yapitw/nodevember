"""Concept figures for the Supertree tutorial, computed with the same formulas as build.py.

  uv run --with matplotlib python tutorial/src/concept_figs.py

Writes tutorial/images/crown-section.png (side section of tree 01) and
tutorial/images/rib-module-plan.png (two neighbouring rib modules, unrolled).
"""
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "images"
H, R, RIBS = 40.0, 18.5, 32          # tree 01: Height, Crown Radius, Ribs
r = H * .0625                         # trunk radius
INK, VIOLET, STEEL, LEAF, CAP = "#2b2d33", "#a23ad6", "#5a3040", "#4d8a3c", "#3b4250"
plt.rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]


def clamp(x):
    return min(1., max(0., x))


def profile(u):
    """PA_CrownProfile: (radius, z) for profile parameter u."""
    inner = clamp(u / .65)
    outer = clamp((u - .65) / .395)
    theta = inner * math.pi * .5
    neck, bowl = r * 1.09, R * .56
    radius = neck + (bowl - neck) * (1 - math.cos(theta)) + R * .49 * outer
    z = H * (.65 + .25 * math.sin(theta) + .065 * outer ** 1.35)
    return radius, z


def frange(a, b, n):
    return [a + (b - a) * k / (n - 1) for k in range(n)]


def section():
    fig, ax = plt.subplots(figsize=(10, 9), dpi=150)
    # trunk shell, core cone, balcony, planter rim
    for s in (-1, 1):
        ax.fill([0, s * r, s * r, 0], [0, 0, H * .63, H * .63], color=LEAF, alpha=.35, lw=0)
        zc, d = H * .61, H * .36
        ax.fill([0, s * r * .83, s * r * 1.25, 0], [zc - d / 2, zc - d / 2, zc + d / 2, zc + d / 2],
                color=CAP, alpha=.55, lw=0)
        ax.plot([s * r * 1.9], [H * .58], "o", color="#c0507a", ms=5)
    # dark cap: cylinder + three discs
    for level, rad, thick in ((.94, .55, H * .075), (.905, .60, .28), (.935, .575, .24), (.978, .59, .30)):
        ax.fill([-R * rad, R * rad, R * rad, -R * rad],
                [H * level - thick / 2] * 2 + [H * level + thick / 2] * 2, color=CAP, alpha=.8, lw=0)
    # luminous skin: u .0125 → .65, radius × .96, z + .12
    us = frange(.0125, .65, 80)
    for s in (-1, 1):
        ax.plot([s * profile(u)[0] * .96 for u in us], [profile(u)[1] + .12 for u in us], color=VIOLET, lw=5,
                solid_capstyle="round", label="light skin (×0.96)" if s > 0 else None)
    # the profile itself, 0 → 1.045, and the frame offset (× 1.018, −0.17)
    us = frange(0, 1.045, 160)
    ax.plot([profile(u)[0] for u in us], [profile(u)[1] for u in us], color="#888", lw=1, ls="--",
            label="profile R(u), Z(u)")
    us = frange(0, .63, 60)
    for s in (-1, 1):
        ax.plot([s * profile(u)[0] * 1.018 for u in us], [profile(u)[1] - .17 for u in us], color=STEEL, lw=2.2,
                label="main rib, u 0 → 0.63 (×1.018)" if s > 0 else None)
    # module stations (u values from PA_RibModule; shift = −0.012 for module A)
    stations = {"a": .63, "l0": .723, "r0": .762, "lt": .793, "l1": .863, "r1": .937, "mt / nt": .972,
                "g1 · Y": .995, "tips": 1.045}
    for name, u in stations.items():
        x, z = profile(u)
        x, z = x * 1.018, z - .17
        ax.plot([x], [z], "o", color=STEEL, ms=4.5)
    ax.text(17.2, 34.4, "rib-module stations\nu 0.63 → 1.045 (dots)", fontsize=8.5, color=STEEL, ha="center")
    # dimensions
    nx, nz = profile(0)
    bx, bz = profile(.65)
    tx, tz = profile(1.045)
    ax.annotate(f"neck  1.09 r = {nx:.2f} m\nz = 0.65 h = {nz:.0f} m", (nx, nz), xytext=(40, -32),
                textcoords="offset points", fontsize=9, arrowprops=dict(arrowstyle="-", color=INK, lw=.6))
    ax.annotate(f"bowl rim  0.56 R = {bx:.2f} m\nz = 0.90 h = {bz:.0f} m\n(u = 0.65, end of the quarter ellipse)",
                (bx, bz), xytext=(30, -78), textcoords="offset points", fontsize=9,
                arrowprops=dict(arrowstyle="-", color=INK, lw=.6))
    ax.annotate(f"branch tips  1.05 R = {tx:.2f} m\nz = 0.965 h = {tz:.1f} m", (tx, tz), xytext=(-150, 30),
                textcoords="offset points", fontsize=9, arrowprops=dict(arrowstyle="-", color=INK, lw=.6))
    ax.text(-R * .3, H * .3, "planted trunk\nr = 0.0625 h", fontsize=9, color="#2f5c24", ha="center")
    ax.text(-R * .3, H * .985 + 1.2, "dark cap: one cylinder + three discs", fontsize=9, color=CAP, ha="center")
    ax.text(-r * 1.9 - .5, H * .58 - 2.6, "balcony 0.58 h", fontsize=8.5, color="#c0507a", ha="right")
    ax.set_aspect("equal")
    ax.set_xlim(-21, 22.5)
    ax.set_ylim(0, 44)
    ax.set_xlabel("distance from the trunk axis (m)")
    ax.set_ylabel("height (m)")
    ax.set_title("Tree 01 in section: Height 40 m, Crown Radius 18.5 m", fontsize=12, loc="left")
    ax.grid(alpha=.2)
    ax.legend(loc="lower right", fontsize=8.5, frameon=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "crown-section.png")
    plt.close(fig)


def module(side, shift, rib):
    """Station positions of one PA_RibModule, unrolled: x = radius, y = arc length along the ring."""
    def pt(u0, du, phase):
        u = u0 + shift * du
        rad = profile(u)[0] * 1.018
        ang = (side * phase + rib) * math.tau / RIBS
        return rad, rad * ang
    P = dict(a=pt(.63, 0, 0), l0=pt(.735, 1, -.24), lt=pt(.805, 1, -.24), l1=pt(.875, 1, -.24),
             l2=pt(1.045, 0, -.24), r0=pt(.75, -1, .24), rt=pt(.805, 1, .24), r1=pt(.925, -1, .24),
             nt=pt(.96, -1, .24), r2=pt(1.045, 0, .24), f=pt(.875, 1, -.04), mt=pt(.96, -1, -.04),
             g1=pt(.995, 0, -.04), Y=pt(.995, 0, .46), Yt=pt(1.045, 0, .42))
    rails = [("a", "l0"), ("l0", "lt"), ("lt", "l1"), ("l1", "l2"), ("a", "r0"), ("r0", "rt"), ("rt", "r1"),
             ("r1", "nt"), ("nt", "r2")]
    brackets = [("l1", "f"), ("f", "mt"), ("mt", "g1"), ("r1", "Y"), ("Y", "Yt")]
    ties = [("lt", "rt"), ("mt", "nt")]
    return P, rails, brackets, ties


def plan():
    fig, ax = plt.subplots(figsize=(12, 5.6), dpi=150)
    for rib, (side, shift, tag) in enumerate(((1, -.012, "A"), (-1, .012, "B"))):
        P, rails, brackets, ties = module(side, shift, rib)
        rx = [profile(u)[0] * 1.018 for u in frange(.45, .63, 20)]
        ry = [x * rib * math.tau / RIBS for x in rx]
        ax.plot(rx, ry, color=STEEL, lw=5, solid_capstyle="round", label="main rib (0.140)" if rib == 0 else None)
        for group, lw, col, lab in ((rails, 3.6, STEEL, "long rails (0.120)"),
                                    (brackets, 2.4, "#c0507a", "L bracket + Y fork (0.085)"),
                                    (ties, 1.4, "#3b5fc4", "short ties (0.055)")):
            for a, b in group:
                ax.plot([P[a][0], P[b][0]], [P[a][1], P[b][1]], color=col, lw=lw, solid_capstyle="round",
                        label=lab if (rib == 0 and (a, b) == group[0]) else None)
        for name, (x, y) in P.items():
            ax.plot([x], [y], "o", color=INK, ms=2.5)
            if rib == 0:
                ax.annotate(name, (x, y), xytext=(3, 4), textcoords="offset points", fontsize=8, color=INK)
        ax.text(P["a"][0] - .4, P["a"][1], f"module {tag}\nrib {rib}", ha="right", va="center", fontsize=9.5)
    ax.set_aspect("equal")
    ax.set_xlabel("distance from the trunk axis (m)")
    ax.set_ylabel("arc length around the crown (m)")
    ax.set_title("Two neighbouring rib modules, unrolled (tree 01; one rib step = 11.25°)", fontsize=12, loc="left")
    ax.grid(alpha=.2)
    ax.legend(loc="upper left", fontsize=8.5, frameon=False, ncol=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "rib-module-plan.png")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    section()
    plan()
    print("CONCEPT_FIGS_OK", OUT)
