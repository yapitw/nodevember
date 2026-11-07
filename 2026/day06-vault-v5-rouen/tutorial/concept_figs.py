"""Concept figures for the Rouen tutorial, computed from build.py's own constants and formulas.

  uv run --with matplotlib --with numpy python tutorial/concept_figs.py

Writes images/arch-profiles.png, images/vault-heightmap.png, images/stone-plan.png, images/elevation.png.
Nothing here is drawn by hand: each curve re-evaluates the expression the node tree builds.
"""
import ast
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "images")

# Read the constants straight from build.py (top-level NAME = number / tuple assignments), without bpy.
C = {}
for node in ast.parse(open(os.path.join(HERE, "..", "build.py")).read()).body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        tgt = node.targets[0]
        try:
            val = ast.literal_eval(node.value)
        except ValueError:
            continue
        if isinstance(tgt, ast.Name):
            C[tgt.id] = val
        elif isinstance(tgt, ast.Tuple) and isinstance(val, tuple):
            for t, v in zip(tgt.elts, val):
                C[t.id] = v
B, W, ZS, H, RHO = C["B"], C["W"], C["ZS"], C["H"], C["RHO"]
NT, NL, BRICK, JOINT = C["NT"], C["NL"], C["BRICK"], C["JOINT"]

plt.rcParams.update({"font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"], "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False})
INK, STONE, OCHRE, RIB = "#2d2a26", "#8d877c", "#c9962b", "#7a7d85"


def P(u):
    """build.py P(): two-centred pointed profile, height above the springing; u = 0 crown, 1 springing."""
    d = u + RHO - 1.0
    return np.sqrt(np.maximum(RHO * RHO - d * d, 0.0)) * H / math.sqrt(2 * RHO - 1)


# ── 1 · one profile, three spans
def arch_profiles():
    fig, ax = plt.subplots(figsize=(9.5, 6.4))
    t = np.linspace(-1, 1, 801)
    diag = math.hypot(W / 2, B / 2)
    for half, label, col, ls in ((W / 2, f"transverse arch: across the nave, half-span {W / 2:g} m", INK, "-"),
                                 (diag, f"diagonal rib: corner to boss, plan length {diag:.2f} m", OCHRE, "-"),
                                 (B / 2, f"wall rib (formeret): along the wall, half-span {B / 2:g} m", RIB, "--")):
        ax.plot(t * half, ZS + P(np.abs(t)), color=col, lw=2.2, ls=ls, label=label)
    ax.axhline(ZS, color="#bbb", lw=1)
    ax.axhline(ZS + H, color="#bbb", lw=1)
    ax.text(-W / 2 - 0.15, ZS + 0.1, f"springing  z = {ZS:g} m", ha="left", va="bottom", color="#666", fontsize=10)
    ax.text(-W / 2 - 0.15, ZS + H + 0.1, f"crown  z = {ZS + H:g} m", ha="left", va="bottom", color="#666", fontsize=10)
    # the two centres of the transverse arch
    sx = W / 2 * (RHO - 1)
    for s in (-1, 1):
        ax.plot([s * sx], [ZS], "o", color=INK, ms=4)
    ax.annotate(f"centres at ±{sx:.3g} m: radius = {RHO:g} × half-span", (sx, ZS), (sx + 0.4, ZS - 1.7),
                arrowprops={"arrowstyle": "-", "color": "#888"}, fontsize=10, color="#555")
    ax.set_xlabel("horizontal distance from the crown (m)")
    ax.set_ylabel("height (m)")
    ax.set_ylim(ZS - 2.4, ZS + H + 1.2)
    ax.set_aspect("equal")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), frameon=False, fontsize=10, ncol=1)
    ax.set_title("One pointed profile P(u), stretched to three spans:\nevery arch of a bay meets at the same crown",
                 loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "arch-profiles.png"), dpi=150)
    plt.close(fig)


# ── 2 · the bay as min(u, v)
def vault_heightmap():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5.4), gridspec_kw={"width_ratios": [1.15, 1]})
    x = np.linspace(-W / 2, W / 2, 441)
    y = np.linspace(-B / 2, B / 2, 253)
    X, Y = np.meshgrid(x, y)
    u, v = np.abs(X) / (W / 2), np.abs(Y) / (B / 2)
    Z = ZS + P(np.minimum(u, v))
    cs = a1.contourf(X, Y, Z, levels=np.linspace(ZS, ZS + H, 16), cmap="YlOrBr_r")
    a1.contour(X, Y, Z, levels=np.linspace(ZS, ZS + H, 16), colors="white", linewidths=0.4)
    for s in (-1, 1):
        a1.plot([-W / 2, W / 2], [-s * B / 2, s * B / 2], color=INK, lw=1.6)
    a1.plot([0], [0], "o", color=INK, ms=6)
    a1.text(0.15, 0.15, "boss", fontsize=10)
    a1.text(0, B / 2 * 0.62, "transverse cell\nz = P(u): height depends on x only", ha="center", fontsize=9.5)
    a1.text(W / 2 * 0.70, 0, "wall\ncell\nz = P(v)", ha="center", va="center", fontsize=9.5)
    a1.set_aspect("equal")
    a1.set_xlabel("x across the nave (m)")
    a1.set_ylabel("y along the nave (m)")
    a1.set_title("Plan of one bay, contours of z = Zs + P(min(u, v))", loc="left", fontsize=12)
    fig.colorbar(cs, ax=a1, shrink=0.8, label="height (m)")
    # section along the diagonal: the groin, where the two barrels meet
    t = np.linspace(0, 1, 300)
    a2.plot(t, ZS + P(t), color=INK, lw=2, label="barrel profile P(u) on x (and P(v) on y)")
    a2.plot(t, ZS + P(np.minimum(t, 0.55)), color=OCHRE, lw=2, ls="--",
            label="walking along x at fixed v = 0.55: past u = v the other barrel is higher")
    a2.axvline(0.55, color="#bbb", lw=1)
    a2.set_xlabel("u = |x| / (W/2)")
    a2.set_ylabel("height (m)")
    a2.set_title("Why min(): P falls as u grows, so min(u, v) picks the higher barrel", loc="left", fontsize=12)
    a2.legend(frameon=False, fontsize=9.5, loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "vault-heightmap.png"), dpi=150)
    plt.close(fig)


# ── 3 · every stone of one bay, in plan
def bricks(n, lateral):
    """Re-run build.py cells(): yields (course, side, half, start, end) per stone in fraction space."""
    span, along = (B / 2, W / 2) if lateral else (W / 2, B / 2)
    theta_top = math.acos((RHO - 1) / RHO)
    out = []
    for side in (-1, 1):
        for half in (-1, 1):
            for c in range(n):
                theta = theta_top * (1 - (c + .5) / n)
                u = RHO * math.cos(theta) - (RHO - 1)
                rl = along * (1 - u)
                if rl < .06:
                    continue                      # "omit slivers fully covered by the diagonal rib"
                p = max(2, round(rl / BRICK))
                odd = c % 2
                trim = odd * .5 / p
                cnt = p + 1 - odd
                for k in range(cnt):
                    f = k / (cnt - 1)
                    frac = trim + f * (1 - 2 * trim)
                    end = (1 - odd) * (f < .001 or f > .999)
                    center = frac + end / p * .25 * (1 if f < .5 else -1)
                    hw = max(.5 * ((1 - end * .5) / p - JOINT / rl), .001)
                    out.append((c, side, half, center - hw, center + hw, end))
    return out, span, along, theta_top


def stone_plan():
    fig, ax = plt.subplots(figsize=(12, 7.4))
    rng = np.random.default_rng(3)
    counts = {}
    for lateral, n, base in ((False, NT, OCHRE), (True, NL, "#b5803a")):
        st, span, along, theta_top = bricks(n, lateral)
        rx = span * RHO
        row_gap = JOINT / (2 * sum(math.hypot(rx * math.sin(theta_top * (i + .5) / 256),
                                              H / math.sqrt(2 * RHO - 1) * RHO * math.cos(theta_top * (i + .5) / 256))
                                   for i in range(256)) * theta_top / 256)
        counts[lateral] = len(st)
        for c, side, half, a0, a1, end in st:
            pts = []
            for a, bpar in ((0, a0), (0, a1), (1, a1), (1, a0)):
                course = c / n + row_gap + a * (1 / n - 2 * row_gap)
                theta = theta_top * (1 - course)
                u = RHO * math.cos(theta) - (RHO - 1)
                # sample the long edges so the stone's groin end follows the diagonal
                pts.append((u, bpar))
            poly = []
            for (u0, b0), (u1, b1) in zip(pts, pts[1:] + pts[:1]):
                for s in np.linspace(0, 1, 6, endpoint=False):
                    uu, bb = u0 + (u1 - u0) * s, b0 + (b1 - b0) * s
                    vv = uu + (1 - uu) * bb
                    cross, al = half * span * uu, side * along * vv
                    poly.append((al, cross) if lateral else (cross, al))
            tone = rng.uniform(.82, 1.0)
            col = np.array(matplotlib.colors.to_rgb(base)) * tone
            ax.add_patch(Polygon(poly, closed=True, fc=col, ec="#5a4630", lw=0.25))
    for s in (-1, 1):
        ax.plot([-W / 2, W / 2], [-s * B / 2, s * B / 2], color="#f0f1f3", lw=7, solid_capstyle="butt")
        ax.plot([-W / 2, W / 2], [-s * B / 2, s * B / 2], color=RIB, lw=1.2)
    ax.plot([0], [0], "o", color="#f0f1f3", ms=13, mec=RIB)
    ax.set_xlim(-W / 2 - .1, W / 2 + .1)
    ax.set_ylim(-B / 2 - .1, B / 2 + .1)
    ax.set_aspect("equal")
    ax.set_xlabel("x across the nave (m)  ·  wall faces at ±5.5")
    ax.set_ylabel("y along the nave (m)  ·  transverse arches at ±3.15")
    ax.set_title(f"Every stone of one bay seen from below, in plan: {counts[False]} in the transverse cells "
                 f"({NT} courses a half), {counts[True]} in the wall cells ({NL})", loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "stone-plan.png"), dpi=150)
    plt.close(fig)
    return counts


# ── 4 · the four storeys of one wall bay
def lancet_outline(w, spring, sill, yc):
    a = np.linspace(math.pi, 2 * math.pi / 3, 40)
    left = [(yc + w / 2 + w * math.cos(t), spring + w * math.sin(t)) for t in a]
    right = [(2 * yc - y, z) for y, z in reversed(left)]
    return [(yc - w / 2, sill)] + left + right + [(yc + w / 2, sill)]


def elevation():
    fig, ax = plt.subplots(figsize=(7.2, 11))
    yc = B / 2
    ax.add_patch(Polygon([(0, 0), (B, 0), (B, ZS + H + 1), (0, ZS + H + 1)], fc="#e8e6e1", ec="none"))
    orders = C["ORDERS"]
    for name, w, spring, sill in (("arcade", C["AR_W"], C["AR_SPRING"], 0.0),
                                  ("false tribune", C["TR_W"], C["TR_SPRING"], C["TR_SILL"]),
                                  ("clerestory", C["CL_W"], C["CL_SPRING"], C["CL_SILL"])):
        for k, (dw, _) in enumerate(orders):
            fc = ["#cfcbc3", "#b8b3a9", "#ffffff"][k]
            ax.add_patch(Polygon(lancet_outline(w + dw, spring, sill, yc), fc=fc, ec=INK, lw=0.8))
        ax.text(B + 0.25, spring, f"{name}\nspring {spring:g} m\nwidth {w:g} m (+0.45, +0.9)", va="center", fontsize=9)
    for i in range(7):
        ax.add_patch(Polygon(lancet_outline(0.46, C["TF_SPRING"], C["TF_SILL"], yc + (i - 3) * 0.6),
                             fc="#6f6a62", ec=INK, lw=0.6))
    ax.text(B + 0.25, (C["TF_SILL"] + C["TF_TOP"]) / 2, "triforium: 7 lancets, 0.46 m", va="center", fontsize=9)
    for z in C["STRINGS"]:
        ax.plot([0, B], [z, z], color=INK, lw=2.2)
    ax.text(-0.25, C["STRINGS"][0], f"string courses {C['STRINGS'][0]:g} / {C['STRINGS'][1]:g}", ha="right",
            va="center", fontsize=9)
    for z, lab in ((ZS, f"vault springs  {ZS:g} m"), (ZS + H, f"crown  {ZS + H:g} m"),
                   (C["TR_SILL"], f"tribune sill  {C['TR_SILL']:g} m"), (C["AR_SPRING"], f"arcade springs  {C['AR_SPRING']:g} m")):
        ax.plot([-0.1, 0.0], [z, z], color=INK, lw=1)
        ax.text(-0.25, z, lab, ha="right", va="center", fontsize=9)
    # the vault's wall rib over the bay
    t = np.linspace(-1, 1, 200)
    ax.plot(yc + t * B / 2, ZS + P(np.abs(t)), color=OCHRE, lw=2.2)
    for yy in (0, B):                                          # pilasters on the bay lines
        ax.add_patch(Polygon([(yy - 0.36, 0), (yy + 0.36, 0), (yy + 0.36, ZS), (yy - 0.36, ZS)], fc="#a39d92", ec=INK,
                             lw=0.6))
    ax.set_xlim(-4.2, B + 3.2)
    ax.set_ylim(-0.5, ZS + H + 1.3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"One wall bay ({B:g} m) seen from the nave: three orders cut per opening", loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "elevation.png"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    arch_profiles()
    vault_heightmap()
    print("stones per bay", stone_plan())
    elevation()
    print("CONCEPT_FIGS_OK")
