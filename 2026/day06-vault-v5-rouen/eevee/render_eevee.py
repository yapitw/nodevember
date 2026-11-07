"""Render resumable PNG frames from eevee/rouen_eevee.blend.

    Blender -b eevee/rouen_eevee.blend --python eevee/render_eevee.py -- [first last] [--alt]

Pass first > last to walk backwards, so a second process can start from the end of the
loop while the first works from the start; each skips frames that already exist.

--alt renders the "one bay behind" copy into eevee/frames_alt/: the nave and its window
lights sit one bay (6.3 m) further forward than in the main pass. The geometry is the same
(the nave is periodic), but the baked probe light is not exactly periodic, so frame 301 of
this pass equals frame 1 of the main pass. crossfade.py blends the two across the whole loop.
The render farm can't run this driver swap, so it renders rouen_eevee_alt.blend: the same
file saved after use_alt_phase().
"""
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
WRAP = "((frame - 1) / 300 - floor((frame - 1) / 300))"
ALT = "((frame - 1) / 300 - 1)"


def use_alt_phase():
    """Swap the wrapped loop phase for phase − 1 in every driver (nave and window lights)."""
    n = 0
    for ob in bpy.data.objects:
        if ob.animation_data:
            for fc in ob.animation_data.drivers:
                if WRAP in fc.driver.expression:
                    fc.driver.expression = fc.driver.expression.replace(WRAP, ALT)
                    n += 1
    assert n > 1, "no loop drivers found"
    print("EEVEE_ALT_DRIVERS", n, flush=True)


def render():
    sc = bpy.context.scene
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    alt = "--alt" in args
    nums = [a for a in args if a != "--alt"]
    first, last = (int(nums[0]), int(nums[1])) if len(nums) == 2 else (sc.frame_start, sc.frame_end)
    if alt:
        use_alt_phase()
    folder = os.path.join(HERE, "frames_alt" if alt else "frames")
    os.makedirs(folder, exist_ok=True)
    step = 1 if last >= first else -1
    for frame in range(first, last + step, step):
        path = os.path.join(folder, f"{frame:04d}.png")
        if os.path.isfile(path) and os.path.getsize(path) > 1024:
            continue
        start = time.monotonic()
        sc.frame_set(frame)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        assert os.path.isfile(path) and os.path.getsize(path) > 1024
        print("EEVEE_FRAME_COMPLETE", frame, round(time.monotonic() - start, 2), flush=True)
    print("EEVEE_SEQUENCE_COMPLETE", flush=True)


if __name__ == "__main__":
    render()
