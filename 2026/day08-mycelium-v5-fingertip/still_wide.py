"""Hero still: the whole stone hand with the grown mushroom (the animation's last frame is a close-up without the hand).

Blender -b piece.blend --python still_wide.py -- --out ABS.png [--scale 100] [--samples 128] [--lift 3] [--back 12]
Frame 360 (mushroom open, spores falling), the camera on the opening wide shot's line, raised and pulled back so the
cap fits above the finger.
"""
import argparse
import sys

import bpy
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--scale', type=int, default=100)
ap.add_argument('--samples', type=int, default=128)
ap.add_argument('--lift', type=float, default=3.0)     # target raised (cm) over the opening shot's
ap.add_argument('--back', type=float, default=12.0)    # camera pulled back (cm) along the view line
ap.add_argument('--fstop', type=float, default=0.11)
ap.add_argument('--camz', type=float, default=0.0)    # camera lowered (−) / raised (+) on its own, so the cap lands on a darker background
ap.add_argument('--tx', type=float, default=0.0)      # target shifted sideways to centre the hand
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])

sc = bpy.context.scene
sc.frame_set(360)
cam, tgt = bpy.data.objects['PA_Camera'], bpy.data.objects['PA_Target']
for idb in (cam, tgt, cam.data):
    idb.animation_data_clear()

CAM0, TGT0 = Vector((-22.0, -96.0, 10.0)), Vector((-1.2, 0.6, 11.0))
t = TGT0 + Vector((a.tx, 0.0, a.lift))
c = CAM0 + Vector((a.tx, 0.0, a.lift + a.camz))
c = c + (c - t).normalized() * a.back
cam.location, tgt.location = c, t
fwd = (t - c).normalized()
# focus on the raised finger, halfway up
finger = Vector((2.9 * 1.4, 0.0, 15.0))
cam.data.dof.focus_distance = (finger - c).dot(fwd)
cam.data.dof.aperture_fstop = a.fstop

sc.render.resolution_percentage = a.scale
sc.cycles.samples = a.samples
sc.render.filepath = a.out
bpy.ops.render.render(write_still=True)
print('WROTE', a.out, 'focus', round(cam.data.dof.focus_distance, 1))
