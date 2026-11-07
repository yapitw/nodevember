"""Render resumable PNG frames from color/rouen_color.blend inside Blender.

Afterwards encode color/frames/%04d.png at 30 fps with ffmpeg. Completed PNGs
are retained across restarts; geometry and shader data persist between frames.
"""
import os
import runpy
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
pb = runpy.run_path(os.path.join(HERE, "build.py"))["pb"]


def render():
    sc = bpy.context.scene
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.kernel_optimization_level = "OFF"
    device = pb._use_gpu(sc)
    if device != "CPU":
        for d in prefs.devices:
            d.use = d.type == device
    sc.render.use_persistent_data = True
    sc.render.image_settings.media_type = "IMAGE"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    folder = os.path.join(HERE, "color", "frames")
    os.makedirs(folder, exist_ok=True)
    print("COLOR_RENDER_DEVICE", device, flush=True)
    print("COLOR_RENDER_SETTINGS", sc.render.resolution_x, sc.cycles.samples, flush=True)
    for frame in range(sc.frame_start, sc.frame_end + 1):
        path = os.path.join(folder, f"{frame:04d}.png")
        if os.path.isfile(path) and os.path.getsize(path) > 1024:
            continue
        start = time.monotonic()
        sc.frame_set(frame)
        sc.render.filepath = path
        print("COLOR_FRAME_START", frame, flush=True)
        bpy.ops.render.render(write_still=True)
        assert os.path.isfile(path) and os.path.getsize(path) > 1024
        print("COLOR_FRAME_COMPLETE", frame, round(time.monotonic() - start, 2), flush=True)
    print("COLOR_SEQUENCE_COMPLETE", sc.frame_end - sc.frame_start + 1, flush=True)


if __name__ == "__main__":
    render()
