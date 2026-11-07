"""Close the EEVEE loop: blend the main pass into the one-bay-on alt pass across the whole loop.

    uv run --with pillow --with numpy python eevee/crossfade.py

The baked probe light is not exactly periodic with the bay, so frame 300 → 1 of the main
pass jumps (12.6 mean RGB against 3.3 for an ordinary step). frames_alt/ holds the same
frames with the nave one bay further forward: identical geometry, and its frame 301 is
exactly frame 1.

The output is (1 − φ) · main + φ · alt over the whole loop, with φ = (frame − 1) / 300.
The probe light drifts almost linearly as the nave slides (the vault brightens by about 10
levels from frame 1 to 300 in the main pass), and the alt pass carries the same drift one
bay earlier, so the linear blend cancels it: the vault stays within about half a level of
frame 1 all the way round. (A first version faded only over frames 241–300; it undid the
whole drift in under two seconds, which showed as the vault darkening at 8–9.5 s.)
Writes frames_loop/, loop.mp4 and loop_3x.mp4.
"""
import os
import shutil
import subprocess

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
N, FADE = 300, 300
MAIN, ALT, OUT = (os.path.join(HERE, d) for d in ("frames", "frames_alt", "frames_loop"))


def weight(f):
    return (f - 1) / N                   # 0 at frame 1 … 299/300 at frame 300; frame 301 is alt = frame 1


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
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", os.path.join(HERE, "loop.mp4"),
                "-c", "copy", os.path.join(HERE, "loop_3x.mp4")], check=True)
print("MP4", os.path.join(HERE, "loop.mp4"), os.path.join(HERE, "loop_3x.mp4"))
