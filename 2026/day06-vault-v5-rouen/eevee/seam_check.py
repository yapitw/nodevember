"""Step between neighbouring frames of the EEVEE loop, and the seam from frame 300 back to 1.

    uv run --with pillow --with numpy python eevee/seam_check.py [frames_loop]

Checks eevee/frames_loop/ (the cross-faded loop) by default, or the folder given.
Writes eevee/loop_review.json. A loop is seamless when the 300 → 1 step sits inside the
range of ordinary steps. Also compares EEVEE frame 1 with Cycles frame 1 region by region.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
N = 300
FOLDER = sys.argv[1] if len(sys.argv) > 1 else "frames_loop"


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), np.float32)


def frame(i):
    return load(os.path.join(HERE, FOLDER, f"{i:04d}.png"))


steps = {}
prev = frame(1)
first = prev
for i in range(2, N + 1):
    cur = frame(i)
    steps[f"{i - 1}_{i}"] = float(np.abs(cur - prev).mean())
    prev = cur
seam = float(np.abs(first - prev).mean())
vals = np.array(list(steps.values()))

cycles = load(os.path.join(HERE, "..", "color", "frames", "0001.png"))
w = cycles.shape[1] // 3
regions = {"left third": (slice(None), slice(0, w)), "vault (top middle)": (slice(0, w), slice(w, 2 * w)),
           "right third": (slice(None), slice(2 * w, None)), "whole frame": (slice(None), slice(None))}
compare = {name: {"cycles": [round(float(v), 1) for v in cycles[r].mean((0, 1))],
                  "eevee": [round(float(v), 1) for v in first[r].mean((0, 1))]} for name, r in regions.items()}

summary = {"folder": FOLDER, "median_step": float(np.median(vals)), "min": float(vals.min()), "max": float(vals.max()),
           "max_at": max(steps, key=steps.get), "seam_300_1": seam,
           "seam_ratio": seam / float(np.median(vals)), "frame1_mean_rgb_vs_cycles": compare}
json.dump({"summary": summary, "steps": steps}, open(os.path.join(HERE, "loop_review.json"), "w"), indent=1)
print(json.dumps(summary, indent=1))
