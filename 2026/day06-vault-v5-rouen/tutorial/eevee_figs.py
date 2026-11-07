"""Figures for the EEVEE chapter of the tutorial.

    uv run --with matplotlib --with numpy --with pillow python tutorial/eevee_figs.py

Run from the piece folder after eevee/crossfade.py. Writes
  images/cycles-vs-eevee.jpg   Cycles frame 1 beside the EEVEE loop's frame 1
  images/eevee-blend.png       vault brightness per frame: main pass, alt pass, the blended loop
"""
import os

import matplotlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PIECE = os.path.dirname(HERE)
EEVEE = os.path.join(PIECE, "eevee")
OUT = os.path.join(HERE, "images")
N = 300

# Reference categorical palette, slots 1–3 (validated: CVD ΔE 9.2, aqua carries direct labels).
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def side_by_side():
    a = Image.open(os.path.join(PIECE, "color", "frames", "0001.png")).convert("RGB")
    b = Image.open(os.path.join(EEVEE, "frames_loop", "0001.png")).convert("RGB")
    c = Image.new("RGB", (2 * a.width + 12, a.height), "white")
    c.paste(a, (0, 0))
    c.paste(b, (a.width + 12, 0))
    d = ImageDraw.Draw(c)
    font = ImageFont.load_default(size=40)
    for x, text in ((30, "Cycles · 256 samples · 53 s a frame"), (a.width + 42, "EEVEE · 128 samples · 28 s a frame")):
        box = d.textbbox((x, 30), text, font=font)
        d.rectangle((box[0] - 14, box[1] - 10, box[2] + 14, box[3] + 10), fill=(0, 0, 0))
        d.text((x, 30), text, fill=(255, 255, 255), font=font)
    c.resize((c.width // 2, c.height // 2), Image.LANCZOS).save(os.path.join(OUT, "cycles-vs-eevee.jpg"), quality=90)


def vault(folder, f):
    a = np.asarray(Image.open(os.path.join(EEVEE, folder, f"{f:04d}.png")).convert("L"), np.float32)
    return float(a[:360, 360:720].mean())   # the top-middle ninth: the vault just ahead of the camera


def blend_chart():
    frames = np.arange(1, N + 1)
    main = np.array([vault("frames", f) for f in frames])
    alt = np.array([vault("frames_alt", f) for f in frames])
    loop = np.array([vault("frames_loop", f) for f in frames])

    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.plot(frames, main, color=BLUE, lw=2, label="main pass: probes baked at phase 0")
    ax.plot(frames, alt, color=ORANGE, lw=2, ls=(0, (5, 3)), label="alt pass: nave one bay further on")
    ax.plot(frames, loop, color=AQUA, lw=2.5, label="loop = (1 − φ)·main + φ·alt")
    # The seam: where each curve goes next after frame 300.
    ax.annotate("", xy=(N + 9, main[0]), xytext=(N + 9, main[-1]),
                arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.5))
    ax.text(N + 14, (main[0] + main[-1]) / 2, f"main jumps back\n{main[-1] - main[0]:.1f} levels\nat the seam",
            color=INK2, fontsize=8, va="center")
    for y, text, col in ((main[150] + 1.2, "main", INK), (alt[150] - 2.2, "alt", INK), (loop[150] + 1.0, "loop", INK)):
        ax.text(150, y, text, color=col, fontsize=9, ha="center", fontweight="bold")
    ax.set_xlim(1, N + 60)
    ax.set_xticks([1, 75, 150, 225, 300])
    ax.set_xlabel("frame", color=INK2)
    ax.set_ylabel("vault brightness (mean of 0–255)", color=INK2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.legend(loc="upper left", frameon=False, fontsize=8, labelcolor=INK)
    ax.set_title("The baked light drifts as the nave slides; blending with the pass one bay on cancels it",
                 color=INK, fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "eevee-blend.png"), facecolor=SURFACE)
    print("vault: main %.1f→%.1f, alt %.1f→%.1f, loop %.1f–%.1f" %
          (main[0], main[-1], alt[0], alt[-1], loop.min(), loop.max()))


if __name__ == "__main__":
    side_by_side()
    blend_chart()
