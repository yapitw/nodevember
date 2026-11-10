"""Tutorial figure: the far trunks with and without the sun's light link (Cycles, frame 1, half size).

  Blender -b piece.blend --python tutorial/src/sun_link.py -- OUT_DIR [SAMPLES]
The tutorial figure uses the first render's .blend (SUN_DIR (0.86, -0.22, -0.46), a side sun): under the final
backlight the trunks face the camera in shadow and the difference is only a thin rim.
→ OUT_DIR/_sun_skips.png (as rendered: PA_Sun excludes the PA_SunSkips collection) and _sun_hits.png (link removed).
The .blend is not saved.
"""
import sys

import bpy

argv = sys.argv[sys.argv.index('--') + 1:]
out_dir, spp = argv[0], int(argv[1]) if len(argv) > 1 else 64
sc = bpy.context.scene
sc.frame_set(1)
sc.render.resolution_percentage = 50
sc.cycles.samples = spp
sun = bpy.data.objects['PA_Sun']
for name, coll in (('skips', sun.light_linking.receiver_collection), ('hits', None)):
    sun.light_linking.receiver_collection = coll
    sc.render.filepath = f'{out_dir}/_sun_{name}.png'
    bpy.ops.render.render(write_still=True)
    print('WROTE', sc.render.filepath)
