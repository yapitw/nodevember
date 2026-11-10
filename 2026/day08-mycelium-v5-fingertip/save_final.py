"""Final render file: Cycles 128 spp, 1080², PNG frames → piece.blend (+ a copy for a render farm, frames to //frames/).
Blender -b --factory-startup --python save_final.py -- [--farm FARM_SHARE/piece.blend]"""
import runpy
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
sys.argv = [sys.argv[0], '--']
ns = runpy.run_path(str(HERE / 'build.py'), run_name='lib')
ns['build'](samples=128)
import proc_blender as pb

sc = bpy.context.scene
sc.render.resolution_percentage = 100
sc.cycles.samples = 128
sc.render.use_persistent_data = True        # the moss, ground and hand are static: keep their BVH between frames
sc.render.image_settings.media_type = 'IMAGE'
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_depth = '8'
sc.render.filepath = str(HERE / 'frames' / '####')
pb.save(str(HERE / 'piece.blend'))
print('SAVED', HERE / 'piece.blend', sc.name)
if '--farm' in argv:
    farm = Path(argv[argv.index('--farm') + 1])
    farm.parent.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = '//frames/####'
    pb.save(str(farm))
    print('SAVED', farm)
