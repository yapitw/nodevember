"""Inspect the saved scene and its stated procedural / timing constraints."""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]/'.agents/skills/procedural-art/scripts'))
import proc_blender as pb

sc = bpy.context.scene
report = {'audit': pb.audit('Supertree'), 'blender': bpy.app.version_string,
          'animation': {'frames': [sc.frame_start, sc.frame_end], 'fps': sc.render.fps,
                        'seconds': (sc.frame_end-sc.frame_start+1)/sc.render.fps,
                        'seamless_loop': False}, 'trees': [], 'errors': []}

if not report['audit']['strict_procedural']:
    report['errors'].append('Procedural audit failed')
if len(bpy.data.actions):
    report['errors'].append('Unexpected keyframe actions')
bad_nodes = [f'{t.name}/{n.name}' for t in bpy.data.node_groups for n in t.nodes
             if n.bl_idname in ('GeometryNodeSimulationInput', 'GeometryNodeSimulationOutput')]
report['simulation_nodes'] = bad_nodes
report['keyframe_actions'] = len(bpy.data.actions)
report['external_image_files'] = [im.filepath for im in bpy.data.images if im.source == 'FILE' and im.filepath]
if bad_nodes or report['external_image_files']:
    report['errors'].append('Unexpected simulation or external image')

for ob in sc.objects:
    if ob.type == 'MESH' and (len(ob.data.vertices) or not any(m.type == 'NODES' for m in ob.modifiers)):
        report['errors'].append(f'{ob.name}: not an empty GN base')
    if not ob.name.startswith('PA_Supertree_') or ob.type != 'MESH':
        continue
    mod = next(m for m in ob.modifiers if m.type == 'NODES')
    controls = {s.name: pb._mod_get(mod, s.identifier) for s in mod.node_group.interface.items_tree
                if getattr(s, 'in_out', None) == 'INPUT' and s.name != 'Geometry'}
    ob.update_tag()
    sc.frame_set(168)
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    finite = all(math.isfinite(c) for v in mesh.vertices for c in v.co)
    clip = [world_to_camera_view(sc, sc.camera, ob.matrix_world @ Vector(v)) for v in ev.bound_box]
    report['trees'].append({'object': ob.name, 'controls': controls, 'structural_vertices': len(mesh.vertices),
        'finite_coordinates': finite,
        'projected_bounds': [[round(min(p[k] for p in clip), 5), round(max(p[k] for p in clip), 5)] for k in range(3)]})
    if not finite or not len(mesh.vertices):
        report['errors'].append(f'{ob.name}: invalid evaluated mesh')
    ev.to_mesh_clear()

# Inspect the actual evaluated light skin, including its mesh connectivity.
# A correct vertex formula alone would miss a rim-to-neck bridge face.
tree = bpy.data.node_groups['PA_SupertreeArchitecture']
out = next(n for n in tree.nodes if n.bl_idname == 'NodeGroupOutput')
skin = next(n for n in tree.nodes if n.label == 'Curved luminous skin')
original = out.inputs['Geometry'].links[0].from_socket
tree.links.new(skin.outputs['Geometry'], out.inputs['Geometry'])
ob = bpy.data.objects['PA_Supertree_01']
ob.update_tag()
bpy.context.view_layer.update()
ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh = ev.to_mesh()
height, spread = 40., 18.5
neck = height*.0625*1.09
width = spread*.56-neck
ellipse_errors = []
for v in mesh.vertices:
    radius = math.hypot(v.co.x, v.co.y)/.96
    nx = (radius-neck)/width-1
    nz = ((v.co.z-.12)/height-.65)/.25
    ellipse_errors.append(abs(nx*nx+nz*nz-1))
edge_lengths = [(mesh.vertices[e.vertices[0]].co-mesh.vertices[e.vertices[1]].co).length for e in mesh.edges]
report['curved_light_skin'] = {'vertices': len(mesh.vertices),
    'max_quarter_ellipse_error': max(ellipse_errors), 'max_mesh_edge_m': max(edge_lengths),
    'connected_without_rim_to_neck_bridges': max(edge_lengths) < 1.0}
if max(ellipse_errors) > .0001 or max(edge_lengths) >= 1.0:
    report['errors'].append('Light skin curvature or mesh connectivity failed')
ev.to_mesh_clear()
tree.links.new(original, out.inputs['Geometry'])
bpy.context.view_layer.update()

# The framework must be a connected branch graph, not overlapping loose spokes.
frame_node = next(n for n in tree.nodes if n.label == 'Connected branching framework')
tree.links.new(frame_node.outputs['Skeleton'], out.inputs['Geometry'])
ob.update_tag()
bpy.context.view_layer.update()
ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh = ev.to_mesh()
adj = [[] for _ in mesh.vertices]
for edge in mesh.edges:
    a, b = edge.vertices
    adj[a].append(b)
    adj[b].append(a)
unseen = set(range(len(adj)))
components = []
while unseen:
    todo = [unseen.pop()]
    size = 0
    while todo:
        a = todo.pop()
        size += 1
        for b in adj[a]:
            if b in unseen:
                unseen.remove(b)
                todo.append(b)
    components.append(size)
degrees = {str(d): sum(len(ns) == d for ns in adj) for d in sorted({len(ns) for ns in adj})}
report['crown_framework'] = {'vertices': len(mesh.vertices), 'edges': len(mesh.edges),
    'connected_components': len(components), 'component_sizes': sorted(components), 'vertex_degrees': degrees,
    'outer_tips': degrees.get('1', 0), 'expected_outer_tips': 64,
    'independent_outer_rings': 0, 'short_neighbour_ties': 32}
if len(components) != 1 or degrees.get('1', 0) != 64 or degrees.get('3', 0) != 128:
    report['errors'].append('Framework joints or branch topology failed')
ev.to_mesh_clear()
tree.links.new(original, out.inputs['Geometry'])
bpy.context.view_layer.update()

report['light_energy'] = {}
for f in (1, 49, 97, 145, 192):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    report['light_energy'][str(f)] = {l.name: round(l.energy, 3) for l in bpy.data.lights if 'CrownGlow' in l.name}

if not all(v > report['light_energy']['1'][k] for k, v in report['light_energy']['192'].items()):
    report['errors'].append('Crown awakening drivers did not change')
sc.frame_set(168)
report['passed'] = not report['errors']
(HERE/'verification.json').write_text(json.dumps(report, indent=2))
print('SUPERTREE_VERIFY', json.dumps(report), flush=True)
if report['errors']:
    raise RuntimeError(report['errors'])
