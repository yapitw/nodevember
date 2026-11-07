"""Make eevee/rouen_eevee.blend: the Cycles colour scene switched to EEVEE.

Run on the colour render copy (the nave already split into a moving object and a still one):

    Blender -b color/rouen_color.blend --python eevee/prepare_eevee.py

Indoor bounce light comes from baked Light Probe Volumes. They are parented to the
moving nave object, so the baked light slides with the stone it was baked on.
"""
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = 128
FILL_BOOST = 3.0   # × PA_Fill's Cycles energy
INDIRECT = 1.5     # scene-wide indirect light intensity


def probe_volume(name, parent, centre, size, res):
    data = bpy.data.lightprobes.new(name, "VOLUME")
    ob = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = centre
    ob.scale = [s / 2 for s in size]  # a probe volume spans -1..1 in its own space
    data.resolution_x, data.resolution_y, data.resolution_z = res
    for attr, value in (("bake_samples", 2048), ("surfel_density", 4), ("capture_world", True),
                        ("capture_indirect", True), ("capture_emission", True)):
        if hasattr(data, attr):
            setattr(data, attr, value)
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()
    return ob


def prepare():
    sc = bpy.context.scene
    sc.frame_set(1)
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
    sun = bpy.data.objects["PA_Sun"].data
    if hasattr(sun, "use_shadow_jitter"):
        sun.use_shadow_jitter = True

    # EEVEE's probe light carries fewer effective bounces than Cycles, so the far elevation
    # and the vault fall dark. Lift the upward fill and the indirect light to match frame 1 of
    # the Cycles loop region by region (vault, far wall).
    bpy.data.objects["PA_Fill"].data.energy *= FILL_BOOST
    ee.indirect_light_intensity = INDIRECT

    # The 46 soft window lights each re-render a shadow map of the 3.7 M-vertex nave on every
    # sample. Without shadows the frame changes by under 0.5/255 and renders 2.3× faster.
    for ob in sc.objects:
        if ob.name.startswith("PA_Clerestory_"):
            ob.data.use_shadow = False

    nave = bpy.data.objects["PA_Rouen"]
    # The aisle's outer wall runs from |x| = 12.7 to 13.9. Ending the volumes at 13.3 puts the
    # outermost samples inside that wall, so no sample outside the church lights its inner face.
    # Near volume: the first ~9 bays the camera sees in detail, plus one bay of travel.
    probe_volume("PA_EeveeProbe_Near", nave, (0, 20, 15), (26.6, 68, 30), (28, 64, 30))
    # Far volume: the rest of the visible nave up to the west wall.
    probe_volume("PA_EeveeProbe_Far", nave, (0, 70, 15), (26.6, 100, 30), (14, 48, 15))

    for ob in sc.objects:
        ob.select_set(ob.type == "LIGHT_PROBE")
    bpy.context.view_layer.objects.active = nave
    print("EEVEE_BAKE_START", flush=True)
    bpy.ops.object.lightprobe_cache_bake(subset="ALL")
    print("EEVEE_BAKE_DONE", flush=True)

    sc.render.image_settings.media_type = "IMAGE"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.filepath = "//frames/"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "rouen_eevee.blend"), relative_remap=True)
    print("EEVEE_PREPARED", flush=True)


if __name__ == "__main__":
    prepare()
