"""Prepare the colored nave loop with cached procedural geometry and moving window light.

Run inside Blender on rouen.blend. Geometry stays in nodes; only the nave object's
translation changes. This avoids rebuilding the whole nave on every movie frame.
"""
import os
import runpy

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
config = runpy.run_path(os.path.join(HERE, "build.py"))
pb = config["pb"]


def apply_lighting():
    """Copy build.py's light constants onto an already-built scene (no geometry rebuild)."""
    import math
    scene = bpy.context.scene
    sun = bpy.data.objects["PA_Sun"]
    sun.rotation_euler = (math.radians(90 - config["SUN_ELEVATION"]), 0, math.radians(config["SUN_HEADING"]))
    sun.data.energy = config["SUN_ENERGY"]
    sun.data.color = config["SUN_COLOR"]
    bpy.data.objects["PA_Fill"].data.energy = config["FILL"]
    for light in bpy.data.objects:
        if light.name.startswith("PA_Clerestory_"):
            light.data.energy = config["WINDOW_FILL"]
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = config["SKY"]
    scene.view_settings.exposure = config["EXPOSURE"]


def prepare():
    scene = bpy.context.scene
    scene.frame_set(1)
    apply_lighting()
    host = bpy.data.objects["PA_Rouen"]
    if not host.get("color_static_nave"):
        mod = next(m for m in host.modifiers if m.type == "NODES")
        source = mod.node_group
        walk = next(n for n in source.nodes if n.label.startswith("we walk forward:"))
        out = next(n for n in source.nodes if n.bl_idname == "NodeGroupOutput")
        root = out.inputs["Geometry"].links[0].from_node
        assert root.bl_idname == "GeometryNodeJoinGeometry"

        nave = source.copy()
        nave.name = "PA_Rouen_ColorNave_GN"
        original = nave.nodes[walk.name].inputs["Geometry"].links[0].from_socket
        nave.links.new(original, nave.nodes[out.name].inputs["Geometry"])

        stationary = source.copy()
        stationary.name = "PA_Rouen_ColorStationary_GN"
        for link in list(stationary.nodes[root.name].inputs["Geometry"].links):
            if link.from_node.name == walk.name:
                stationary.links.remove(link)
        for tree in (nave, stationary):
            tree.nodes.remove(tree.nodes[walk.name])
            for node in list(tree.nodes):
                if node.bl_idname == "GeometryNodeGroup" and node.node_tree.name == "PA_LoopClock":
                    tree.nodes.remove(node)
            pb.arrange(tree)

        fixed = host.copy()
        fixed.name = "PA_Rouen_Stationary"
        fixed.data = host.data.copy()
        fixed.animation_data_clear()
        host.users_collection[0].objects.link(fixed)
        next(m for m in fixed.modifiers if m.type == "NODES").node_group = stationary
        mod.node_group = nave
        expression = "-6.3 * ((frame - 1) / 300 - floor((frame - 1) / 300))"
        host.driver_add("location", 1).driver.expression = expression
        host["color_static_nave"] = True

    # Keep the daylight at the moving clerestory openings throughout the loop.
    for light in bpy.data.objects:
        if light.name.startswith("PA_Clerestory_"):
            bay = int(light.name.split("_")[2])
            y = (bay + .5) * config["B"]
            light.driver_add("location", 1).driver.expression = (
                f"{y!r} - 6.3 * ((frame - 1) / 300 - floor((frame - 1) / 300))")

    scene.render.resolution_x = scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.frame_start, scene.frame_end = 1, 300
    scene.render.use_persistent_data = True
    scene.cycles.samples = 256
    scene.cycles.adaptive_threshold = .01
    scene.cycles.adaptive_min_samples = 64
    scene.cycles.use_animated_seed = False
    scene.cycles.seed = 0
    scene.cycles.filter_width = .9
    # The AO node's default 16 rays are repeated at every path sample. Four rays
    # at 256 path samples retain the same grime shading with less redundant work.
    for material in bpy.data.materials:
        if material.use_nodes and material.node_tree:
            for node in material.node_tree.nodes:
                if node.bl_idname == "ShaderNodeAmbientOcclusion":
                    node.samples = 4
    scene.compositing_node_group = None
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = "//frames/"
    pb.save(os.path.join(HERE, "color", "rouen_color.blend"))
    print("COLOR_CACHE_PREPARED", pb.audit("Rouen"), flush=True)


if __name__ == "__main__":
    prepare()
