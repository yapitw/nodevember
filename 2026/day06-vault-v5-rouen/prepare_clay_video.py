"""Run inside Blender on clay/rouen_clay.blend before rendering.

Keep the procedural nave static in its local coordinates and move its object by the
same mathematical loop. The west end stays stationary. This lets Blender cache the
Geometry Nodes mesh between frames; no geometry is baked and no keyframes are added.
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
for rel in ("../../lib", "../../../.agents/skills/procedural-art/scripts"):
    candidate = os.path.abspath(os.path.join(HERE, rel))
    if os.path.isfile(os.path.join(candidate, "proc_blender.py")):
        sys.path.insert(0, candidate)
        break
import proc_blender as pb


def prepare():
    scene = bpy.context.scene
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.resolution_percentage = 100
    scene.render.filepath = "//frames/"
    host = bpy.data.objects["PA_Rouen"]
    if host.get("clay_static_nave"):
        pb.save(os.path.join(HERE, "clay", "rouen_clay.blend"))
        print("CLAY_CACHE_ALREADY_PREPARED", flush=True)
        return
    mod = next(m for m in host.modifiers if m.type == "NODES")
    source = mod.node_group
    walk = next(n for n in source.nodes if n.label.startswith("we walk forward:"))
    out = next(n for n in source.nodes if n.bl_idname == "NodeGroupOutput")
    glazing = out.inputs["Geometry"].links[0].from_node
    assert glazing.bl_idname == "GeometryNodeDeleteGeometry"
    root = glazing.inputs["Geometry"].links[0].from_node
    assert root.bl_idname == "GeometryNodeJoinGeometry"

    nave = source.copy()
    nave.name = "PA_Rouen_ClayNave_GN"
    original_mesh = nave.nodes[walk.name].inputs["Geometry"].links[0].from_socket
    nave.links.new(original_mesh, nave.nodes[glazing.name].inputs["Geometry"])

    stationary = source.copy()
    stationary.name = "PA_Rouen_ClayStationary_GN"
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
    driver = host.driver_add("location", 1).driver
    driver.expression = "-6.3 * ((frame - 1) / 300 - floor((frame - 1) / 300))"
    assert driver.is_simple_expression
    host["clay_static_nave"] = True
    bpy.context.scene.frame_set(1)
    bpy.context.scene.render.filepath = "//frames/"
    print("CLAY_CACHE_AUDIT", pb.audit("Rouen"), flush=True)
    pb.save(os.path.join(HERE, "clay", "rouen_clay.blend"))
    print("CLAY_CACHE_PREPARED", flush=True)


if __name__ == "__main__":
    prepare()
