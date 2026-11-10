"""Tutorial figure: the stone hand in four stages, Workbench clay from the opening camera.

  Blender -b piece.blend --python tutorial/src/hand_stages.py -- OUT_DIR
→ OUT_DIR/_hand_1_spheres.png … _hand_4_weathered.png (1080², crop later), and prints STATS.
The .blend is not saved. Each stage re-wires the end of PA_Hand_GN:
  1 spheres   the skeleton (every point drawn as a sphere of its radius), moved like the stone
  2 raw SDF   Points to SDF Grid → Grid to Mesh, without Fillet and Mean
  3 smoothed  after Fillet and Mean (the tree up to `into the moss`)
  4 weathered the whole tree (lumps, grain, pits, nails)
"""
import sys

import bpy

out_dir = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene
sc.frame_set(1)
keep = {'PA_Hand', 'PA_Ground', 'PA_Camera', 'PA_Target'}
for ob in bpy.data.objects:
    if ob.name not in keep:
        ob.hide_render = True
cam = bpy.data.objects['PA_Camera']
cam.data.dof.use_dof = False

sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light, sh.color_type, sh.single_color = 'STUDIO', 'SINGLE', (0.72, 0.70, 0.66)
sh.show_cavity, sh.cavity_type = True, 'BOTH'
sh.show_shadows = True
sc.display.render_aa = '16'
sc.world.color = (0.035, 0.035, 0.035)
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'

tree = bpy.data.node_groups['PA_Hand_GN']
N, L = tree.nodes, tree.links
by = {n.label: n for n in N if n.label}
out = next(n for n in N if n.type == 'GROUP_OUTPUT')
final_src = out.inputs[0].links[0].from_socket


def wire(sock):
    for lk in list(out.inputs[0].links):
        L.remove(lk)
    L.new(sock, out.inputs[0])


def render(name):
    sc.render.filepath = f'{out_dir}/_hand_{name}.png'
    bpy.ops.render.render(write_still=True)
    print('WROTE', sc.render.filepath)


skel = by['the whole skeleton']
move = by['into the moss: 1.4 × life size']

# 1 · the skeleton as spheres, moved the same way as the stone
ico = N.new('GeometryNodeMeshIcoSphere')
ico.inputs['Radius'].default_value, ico.inputs['Subdivisions'].default_value = 1.0, 3
smooth = N.new('GeometryNodeSetShadeSmooth')
L.new(ico.outputs[0], smooth.inputs[0])
rad = N.new('GeometryNodeInputRadius')
iop = N.new('GeometryNodeInstanceOnPoints')
L.new(skel.outputs[0], iop.inputs['Points'])
L.new(smooth.outputs[0], iop.inputs['Instance'])
L.new(rad.outputs[0], iop.inputs['Scale'])
real = N.new('GeometryNodeRealizeInstances')
L.new(iop.outputs[0], real.inputs[0])
tf = N.new('GeometryNodeTransform')
for k in ('Translation', 'Rotation', 'Scale'):
    tf.inputs[k].default_value = move.inputs[k].default_value
L.new(real.outputs[0], tf.inputs[0])
wire(tf.outputs[0])
dg = bpy.context.evaluated_depsgraph_get()
dg.update()
n_spheres = len(bpy.data.objects['PA_Hand'].evaluated_get(dg).data.vertices) // 162
render('1_spheres')

# 2 · raw distance field: skip Fillet and Mean
sdf = by['spheres → distance field (0.6 mm voxels)']
fil = by['fillet: fill the creases']
mean = by['mean: smooth the bumps']
g2m = mean.outputs[0].links[0].to_node
lk = mean.outputs[0].links[0]
L.remove(lk)
L.new(sdf.outputs[0], g2m.inputs[0])
wire(move.outputs[0])
render('2_raw_sdf')

# 3 · smoothed: Fillet and Mean back in, stop before the weathering
L.remove(next(lk for lk in sdf.outputs[0].links if lk.to_node == g2m))
L.new(mean.outputs[0], g2m.inputs[0])
wire(move.outputs[0])
render('3_smoothed')

# 4 · the whole tree
wire(final_src)
dg = bpy.context.evaluated_depsgraph_get()
dg.update()
me = bpy.data.objects['PA_Hand'].evaluated_get(dg).data
render('4_weathered')
print('STATS spheres', n_spheres, 'hand verts', len(me.vertices), 'faces', len(me.polygons))
