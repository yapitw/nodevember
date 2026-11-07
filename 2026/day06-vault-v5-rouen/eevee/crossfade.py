"""Close the EEVEE loop: blend the main pass into the one-bay-on alt pass over the last second.

    uv run --with pillow --with numpy python eevee/crossfade.py

frames_alt/ holds frames 271–300 with the nave one bay further forward: identical geometry, and
its frame 301 is exactly frame 1. Frames 271–300 of the output are (1 − φ) · main + φ · alt with
φ = (frame − 270) / 30, so frame 300 is all alt and steps onto frame 1 like any other frame.

The first EEVEE version had to blend across the whole loop (600 frames), because the baked probe
light drifted by about 10 levels per bay; undoing that in a short fade showed as the vault
darkening. prepare_eevee.py now bakes an "endless" nave, and the drift left is about 2 levels,
which a one-second fade hides.
Writes frames_loop/ and loop.mp4.
"""
import os
import shutil
import subprocess

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
N, FADE = 300, 30
MAIN, ALT, OUT = (os.path.join(HERE, d) for d in ("frames", "frames_alt", "frames_loop"))


def weight(f):
    return max(0.0, (f - (N - FADE)) / FADE)   # 0 up to frame 270, 1/30 at 271 … 1 at 300


os.makedirs(OUT, exist_ok=True)
for f in range(1, N + 1):
    name = f"{f:04d}.png"
    w = weight(f)
    if w == 0:
        shutil.copyfile(os.path.join(MAIN, name), os.path.join(OUT, name))
        continue
    a = np.asarray(Image.open(os.path.join(MAIN, name)).convert("RGB"), np.float32)
    b = np.asarray(Image.open(os.path.join(ALT, name)).convert("RGB"), np.float32)
    Image.fromarray(np.clip((1 - w) * a + w * b + 0.5, 0, 255).astype(np.uint8)).save(os.path.join(OUT, name))
print("CROSSFADE_FRAMES", N, "fade", FADE)

enc = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart"]
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", os.path.join(OUT, "%04d.png"),
                *enc, os.path.join(HERE, "loop.mp4")], check=True)
print("MP4", os.path.join(HERE, "loop.mp4"))
