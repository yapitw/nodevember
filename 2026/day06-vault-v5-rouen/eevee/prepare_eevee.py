"""Make eevee/rouen_eevee.blend: the Cycles colour scene switched to EEVEE.

Run on the colour render copy (the nave already split into a moving object and a still one):

    Blender -b color/rouen_color.blend --python eevee/prepare_eevee.py

Indoor bounce light comes from one baked Light Probe Volume, parented to the moving nave
object, so the baked light slides with the stone it was baked on. That only loops if the baked
light repeats bay by bay. Three things broke that in the first version (bake drift over one bay:
10 mean RGB at half size, against 0.8 for an ordinary frame step):

- two volumes of different resolution met at y ≈ 50 m, with a visible step in the light;
- surfels at density 4 did not fit the 6.3 m bay, so the light beat with a ~6-bay period;
- the rear closure and the west wall (stationary, at fixed distances from the camera) left a
  world-fixed gradient in the bake, which turned into drift once the bake slid with the nave.

So the bake uses one long uniform volume (cells of B/6 along the nave), surfel density 16, and
an "endless" nave during the bake only: the end walls are removed, copies of the nave run on
before and behind, a long floor runs under them, and the fill reaches far behind the camera.
Everything is put back before saving. Drift over one bay fell to 2.3. At 1080² and 128 samples,
before the fade, the 300 → 1 seam measured 4.9 against 3.0 for an ordinary step (at the earlier
48° view).
"""
import math
import os

import bmesh
import bpy
from mathutils import Euler, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = 128
B = 6.3            # bay length (build.py)
NAVE_BAYS = 23     # bays K0..K1 in build.py
FILL_BOOST = 2.85  # × PA_Fill's Cycles energy
WINDOW_BOOST = 2.8 # × the clerestory lights' Cycles energy
INDIRECT = 1.5     # scene-wide indirect light intensity
# The EEVEE view looks 10° higher than the Cycles one (pitch 58° instead of 48°, same place, yaw
# and lens). The west wall stands still while the nave slides into it, and the vault's section
# changes through each bay, so the junction moved every frame and read as clipping at the far
# end. At 58° the whole west wall stays out of frame.
CAM_PITCH, CAM_YAW, CAM_LENS = 58.0, 32.0, 22.0


def probe_volume(name, parent, centre, size, res):
    data = bpy.data.lightprobes.new(name, "VOLUME")
    ob = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = centre
    ob.scale = [s / 2 for s in size]  # a probe volume spans -1..1 in its own space
    data.resolution_x, data.resolution_y, data.resolution_z = res
    for attr, value in (("bake_samples", 2048), ("surfel_density", 16), ("capture_world", True),
                        ("capture_indirect", True), ("capture_emission", True)):
        if hasattr(data, attr):
            setattr(data, attr, value)
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()
    return ob


def endless_nave_for_bake():
    """Temporary scene changes for the bake; returns a function that undoes them."""
    sc = bpy.context.scene
    temps = []
    # The stationary object without its rear closure (y ≈ −12.6) and west wall (y ≈ 109–110.4);
    # its floor stays.
    st = bpy.data.objects["PA_Rouen_Stationary"]
    me = bpy.data.meshes.new_from_object(st.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if -13.0 < v.co.y < -12.2 or 108.0 < v.co.y < 111.0],
                     context="VERTS")
    bm.to_mesh(me)
    bm.free()
    open_st = bpy.data.objects.new("TMP_StationaryOpen", me)
    sc.collection.objects.link(open_st)
    temps.append(open_st)
    st.hide_render = st.hide_viewport = True
    # Static copies of the nave, two nave lengths on each side.
    nave = bpy.data.objects["PA_Rouen"]
    for k in (-2, -1, 1, 2):
        c = nave.copy()
        sc.collection.objects.link(c)
        if c.animation_data:
            for fc in list(c.animation_data.drivers):
                c.driver_remove(fc.data_path, fc.array_index)
        c.location = (0, k * NAVE_BAYS * B, 0)
        temps.append(c)
    # A floor under all of it.
    fm = bpy.data.meshes.new("TMP_Floor")
    fm.from_pydata([(-14.7, -340, 0), (14.7, -340, 0), (14.7, 450, 0), (-14.7, 450, 0)], [], [(0, 1, 2, 3)])
    fm.materials.append(bpy.data.materials["PA_Floor"])
    floor = bpy.data.objects.new("TMP_Floor", fm)
    sc.collection.objects.link(floor)
    temps.append(floor)
    # The fill from y = −45 instead of −5, at the same power per area.
    fill = bpy.data.objects["PA_Fill"]
    keep = fill.location.y, fill.data.size_y, fill.data.energy
    lo, hi = -45.0, keep[0] + keep[1] / 2
    fill.location.y, fill.data.size_y = (lo + hi) / 2, hi - lo
    fill.data.energy = keep[2] * (hi - lo) / keep[1]

    def restore():
        fill.location.y, fill.data.size_y, fill.data.energy = keep
        for t in temps:
            data = t.data if t.type == "MESH" and t.name.startswith("TMP_") else None
            bpy.data.objects.remove(t, do_unlink=True)
            if data is not None and data.users == 0:
                bpy.data.meshes.remove(data)
        st.hide_render = st.hide_viewport = False

    return restore


def prepare():
    sc = bpy.context.scene
    sc.frame_set(1)
    # same construction as build.py: pitch above the horizon facing +y, then yaw about z
    rm = (Matrix.Rotation(math.radians(CAM_YAW), 3, "Z")
          @ Euler((math.radians(90 + CAM_PITCH), 0, 0), "XYZ").to_matrix())
    sc.camera.rotation_euler = rm.to_euler("XYZ")
    sc.camera.data.lens = CAM_LENS
    sc.render.engine = "BLENDER_EEVEE"
    ee = sc.eevee
    ee.taa_render_samples = SAMPLES
    ee.use_raytracing = True
    ee.ray_tracing_method = "SCREEN"
    rt = ee.ray_tracing_options
    rt.resolution_scale = "1"
    rt.screen_trace_quality = 0.75
    rt.screen_trace_thickness = 0.5
    rt.trace_max_roughness = 0.6
    ee.use_fast_gi = True
    ee.fast_gi_method = "GLOBAL_ILLUMINATION"
    ee.fast_gi_resolution = "1"
    ee.fast_gi_quality = 0.75
    ee.fast_gi_step_count = 16
    ee.fast_gi_ray_count = 4
    ee.fast_gi_distance = 3.0
    ee.fast_gi_thickness_near = 0.5
    ee.use_shadows = True
    ee.shadow_ray_count = 2
    ee.shadow_step_count = 12
    ee.shadow_resolution_scale = 1.0
    ee.shadow_pool_size = "1024"
    ee.gi_irradiance_pool_size = "256"
    ee.clamp_surface_indirect = 10.0
    ee.use_volumetric_shadows = False

    # The sun's 2° disc gives soft shadow edges with jittered shadows.
    sun_ob = bpy.data.objects["PA_Sun"]
    sun_ob.data.use_shadow_jitter = True
    # The west wall, floor and rear closure stay with the camera while the nave slides, so sun
    # through the moving clerestory slid across the fixed west wall (frames 40–160). Light-link
    # the sun so it skips the stationary object.
    receivers = bpy.data.collections.new("PA_SunReceivers")
    receivers.objects.link(bpy.data.objects["PA_Rouen_Stationary"])
    sun_ob.light_linking.receiver_collection = receivers
    for entry in receivers.collection_objects:
        entry.light_linking.link_state = "EXCLUDE"
    # PA_Fill (10 × 90 m) also stays put while the nave slides through its shadow map. Without
    # jitter EEVEE estimates its soft shadow from one shadow map, and the estimate jumped from
    # frame to frame on the near pier at the bottom left. Jittered shadows hold steady at the same
    # brightness and cost.
    bpy.data.objects["PA_Fill"].data.use_shadow_jitter = True

    # EEVEE's probe light carries fewer effective bounces than Cycles. Lift the upward fill, the
    # window lights (which move with the nave, so they cannot drift) and the indirect light so
    # frame 1 matches the earlier EEVEE pass region by region (vault, walls, near pier).
    bpy.data.objects["PA_Fill"].data.energy *= FILL_BOOST
    ee.indirect_light_intensity = INDIRECT

    # The 46 soft window lights each re-render a shadow map of the 3.7 M-vertex nave on every
    # sample. Without shadows the frame changes by under 0.5/255 and renders 2.3× faster.
    for ob in sc.objects:
        if ob.name.startswith("PA_Clerestory_"):
            ob.data.use_shadow = False
            ob.data.energy *= WINDOW_BOOST

    nave = bpy.data.objects["PA_Rouen"]
    # One uniform volume from y = −70 (well behind the camera) to +160 (past the west wall),
    # with cells of B / 6 along the nave so the probe grid repeats with the bay. The aisle's outer
    # wall runs from |x| = 12.7 to 13.9; ending the volume at 13.3 puts the outermost samples
    # inside that wall, so no sample outside the church lights its inner face.
    cell, y0, ny = B / 6, -70.0, 219
    probe_volume("PA_EeveeProbe", nave, (0, y0 + ny * cell / 2, 15), (26.6, ny * cell, 30), (28, ny, 30))

    restore = endless_nave_for_bake()
    for ob in sc.objects:
        ob.select_set(ob.type == "LIGHT_PROBE")
    bpy.context.view_layer.objects.active = nave
    print("EEVEE_BAKE_START", flush=True)
    bpy.ops.object.lightprobe_cache_bake(subset="ALL")
    print("EEVEE_BAKE_DONE", flush=True)
    restore()

    sc.render.image_settings.media_type = "IMAGE"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.filepath = "//frames/"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "rouen_eevee.blend"), relative_remap=True)
    print("EEVEE_PREPARED", flush=True)


if __name__ == "__main__":
    prepare()
