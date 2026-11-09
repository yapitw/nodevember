"""Render a hero, storyboard, or resumable PNG animation from piece.blend."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
for _lib in (HERE.parents[1]/'lib', HERE.parents[2]/'.agents/skills/procedural-art/scripts'):  # public repo, monorepo
    if (_lib/'proc_blender.py').exists():
        sys.path.insert(0, str(_lib))
        break
import proc_blender as pb

p = argparse.ArgumentParser()
p.add_argument('--hero', action='store_true')
p.add_argument('--storyboard', action='store_true')
p.add_argument('--animation', action='store_true')
p.add_argument('--delivery', action='store_true')
p.add_argument('--width', type=int, default=960)
p.add_argument('--samples', type=int, default=64)
a = p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
if a.delivery:
    a.hero = a.storyboard = a.animation = True
sc = bpy.context.scene
sc.render.resolution_x = sc.render.resolution_y = a.width
sc.render.resolution_percentage = 100
sc.eevee.taa_render_samples = a.samples
sc.render.image_settings.media_type = 'IMAGE'
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGB'
sc.render.image_settings.color_depth = '8'
sc.render.image_settings.compression = 25

if a.hero:
    if a.delivery:
        sc.render.resolution_x = sc.render.resolution_y = 1440
        sc.eevee.taa_render_samples = 128
    (HERE/'checks'/'still-progress.json').write_text(json.dumps({'phase': 'hero'}))
    print(pb.render_still(str(HERE/'render.png'), frame=168, samples=128 if a.delivery else a.samples), flush=True)
if a.storyboard:
    if a.delivery:
        sc.render.resolution_x = sc.render.resolution_y = 624
        sc.eevee.taa_render_samples = 32
    (HERE/'checks'/'storyboard-progress.json').write_text(json.dumps({'phase': 'storyboard'}))
    folder = HERE/'review'
    folder.mkdir(exist_ok=True)
    for f in (1, 25, 49, 73, 97, 121, 145, 168, 192):
        print(pb.render_still(str(folder/f'{f:04}.png'), frame=f, samples=32 if a.delivery else a.samples), flush=True)
if a.animation:
    if a.delivery:
        sc.render.resolution_x = sc.render.resolution_y = 960
        sc.eevee.taa_render_samples = 32
    folder = HERE/'frames'
    folder.mkdir(exist_ok=True)
    manifest = {'blend_sha256': hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
                'resolution': [sc.render.resolution_x, sc.render.resolution_y],
                'samples': sc.eevee.taa_render_samples, 'fps': sc.render.fps,
                'frames': [sc.frame_start, sc.frame_end]}
    manifest_path = HERE/'checks'/'render-manifest.json'
    if any(folder.glob('*.png')):
        if not manifest_path.exists() or json.loads(manifest_path.read_text()) != manifest:
            raise RuntimeError('Existing frames belong to another scene or render configuration')
    manifest_path.write_text(json.dumps(manifest, indent=2))
    # Validate existing files, then let Blender keep its native animation cache.
    for f in range(sc.frame_start, sc.frame_end+1):
        path = folder/f'{f:04}.png'
        if path.exists() and path.stat().st_size > 1000:
            with path.open('rb') as handle:
                handle.seek(-12, 2)
                complete = handle.read() == b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
            if complete:
                continue
        if path.exists():
            path.unlink()
    started = time.monotonic()
    written = []
    def frame_written(scene, *unused):
        f = scene.frame_current
        written.append(f)
        (HERE/'checks'/'render-progress.json').write_text(json.dumps({'frame': f, 'total': sc.frame_end,
             'seconds': round(time.monotonic()-started, 1), 'rendered_this_run': len(written)}))
        print('FRAME_OK', f, flush=True)
    sc.render.filepath = str(folder)+'/'
    sc.render.use_overwrite = False
    sc.render.use_placeholder = True
    bpy.app.handlers.render_write.append(frame_written)
    try:
        bpy.ops.render.render(animation=True)
    finally:
        bpy.app.handlers.render_write.remove(frame_written)
