"""Clay pass (Workbench) for motion approval: flat greys per material, half resolution.
Blender -b --factory-startup --python clay.py  → clay/clay.blend, then render_frames.sh clay/clay.blend 24"""
import runpy
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.argv = [sys.argv[0], '--']
ns = runpy.run_path(str(HERE / 'build.py'), run_name='lib')
ns['build']()
import proc_blender as pb

sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light, sh.studio_light = 'STUDIO', 'Default'
sh.color_type = 'MATERIAL'
sh.show_cavity, sh.cavity_type = True, 'BOTH'
sh.show_shadows, sh.show_specular_highlight = True, False
sh.shadow_intensity = 0.35
sh.use_dof = True
sh.background_type = 'WORLD'
sc.world.color = (0.35, 0.35, 0.35)
grey = {'PA_Ground': 0.32, 'PA_Needle': 0.45, 'PA_Moss': 0.55, 'PA_Hypha': 0.97, 'PA_Cap': 0.85, 'PA_Gill': 0.95,
        'PA_Stem': 0.80, 'PA_Felt': 0.97, 'PA_Spore': 1.0, 'PA_Bark': 0.25, 'PA_Foliage': 0.45,
        'PA_Shade': 0.2, 'PA_Stone': 0.62}
for name, v in grey.items():
    bpy.data.materials[name].diffuse_color = (v, v, v * 0.97, 1)
sc.render.resolution_percentage = 50
sc.render.image_settings.media_type = 'IMAGE'
sc.render.image_settings.file_format = 'PNG'
pb.save(str(HERE / 'clay' / 'clay.blend'))
print('SAVED clay')
