"""Tutorial figure: the two cost fields the mycelium reads, painted on the stone, with the paths drawn on top.

  Blender -b piece.blend --python tutorial/src/cost_fields.py -- OUT_DIR
→ OUT_DIR/_field_d.png    d  = cost down to the soil (0 at a soil patch), with every hypha path
  OUT_DIR/_field_dt.png   dt = cost up to the fingertip, with the cords
EEVEE, opening camera, no depth of field. Bands every tenth of the field's range: the colony's front is a level line
of d (reach = Colony × d at the fingertip × 1.03), so the bands show where it stands as Colony rises 0.1 at a time.
Prints STATS (lattice size, soil sources, curve counts). The .blend is not saved.
"""
import sys

import bpy

out_dir = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene
sc.frame_set(1)                 # the fields and paths do not change with time; frame 1 has the wide camera
for ob in bpy.data.objects:
    if ob.name not in {'PA_Mycelium', 'PA_Camera', 'PA_Target'}:
        ob.hide_render = True
bpy.data.objects['PA_Camera'].data.dof.use_dof = False
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 32
sc.render.resolution_percentage = 100
sc.view_settings.look = 'None'
sc.view_settings.view_transform = 'Standard'
sc.view_settings.exposure = 0.0
for n in sc.world.node_tree.nodes:
    if n.type == 'BACKGROUND':
        n.inputs['Color'].default_value, n.inputs['Strength'].default_value = (0.03, 0.03, 0.03, 1), 1.0


def field_material(name, attr):
    """Field → colour ramp, darkened at grazing angles so the stone keeps its shape; dark level lines every 0.1."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    N.clear()
    a = N.new('ShaderNodeAttribute')
    a.attribute_name = attr
    ramp = N.new('ShaderNodeValToRGB')
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.02, 0.05, 0.25, 1)
    els[1].position, els[1].color = 1.0, (0.98, 0.92, 0.35, 1)
    e = els.new(0.35)
    e.color = (0.10, 0.45, 0.55, 1)
    e = els.new(0.7)
    e.color = (0.55, 0.78, 0.30, 1)
    L.new(a.outputs['Fac'], ramp.inputs['Fac'])
    # level lines: fract(10 f) near 0
    m10 = N.new('ShaderNodeMath')
    m10.operation, m10.inputs[1].default_value = 'MULTIPLY', 10.0
    L.new(a.outputs['Fac'], m10.inputs[0])
    fr = N.new('ShaderNodeMath')
    fr.operation = 'FRACT'
    L.new(m10.outputs[0], fr.inputs[0])
    line = N.new('ShaderNodeMath')
    line.operation, line.inputs[1].default_value = 'GREATER_THAN', 0.06
    L.new(fr.outputs[0], line.inputs[0])
    lw = N.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.5
    shade = N.new('ShaderNodeMath')
    shade.operation = 'MULTIPLY_ADD'
    shade.inputs[1].default_value, shade.inputs[2].default_value = -0.65, 1.0
    L.new(lw.outputs['Facing'], shade.inputs[0])
    k = N.new('ShaderNodeMath')
    k.operation = 'MULTIPLY'
    L.new(shade.outputs[0], k.inputs[0])
    k2 = N.new('ShaderNodeMath')
    k2.operation, k2.inputs[1].default_value = 'MULTIPLY_ADD', 0.6
    k2.inputs[2].default_value = 0.4
    L.new(line.outputs[0], k2.inputs[0])
    L.new(k2.outputs[0], k.inputs[1])
    col = N.new('ShaderNodeVectorMath')
    col.operation = 'SCALE'
    L.new(ramp.outputs['Color'], col.inputs[0])
    L.new(k.outputs[0], col.inputs['Scale'])
    em = N.new('ShaderNodeEmission')
    L.new(col.outputs[0], em.inputs['Color'])
    out = N.new('ShaderNodeOutputMaterial')
    L.new(em.outputs[0], out.inputs['Surface'])
    return mat


def line_material():
    mat = bpy.data.materials.new('_debug_line')
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    N.clear()
    em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1)
    em.inputs['Strength'].default_value = 1.0
    L.new(em.outputs[0], N.new('ShaderNodeOutputMaterial').inputs['Surface'])
    return mat


tree = bpy.data.node_groups['PA_Mycelium_GN']
N, L = tree.nodes, tree.links
by = {n.label: n for n in N if n.label}
out = next(n for n in N if n.type == 'GROUP_OUTPUT')
lattice = next(n for n in N if n.bl_idname == 'GeometryNodeStoreNamedAttribute' and n.label == 'cord')
curves = by['smoothed, on the stone']
dtip, dtmax = by['d at the fingertip'], by['dt max']
mats = {'d': field_material('_debug_d', 'f'), 'dt': field_material('_debug_dt', 'f'), 'line': line_material()}


def node(idname, **kw):
    n = N.new(idname)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def build(which):
    for lk in list(out.inputs[0].links):
        L.remove(lk)
    # normalised field f on the lattice
    na = node('GeometryNodeInputNamedAttribute', data_type='FLOAT')
    na.inputs['Name'].default_value = which
    div = node('ShaderNodeMath', operation='DIVIDE')
    L.new(na.outputs['Attribute'], div.inputs[0])
    L.new(dtip.outputs['Value'] if which == 'd' else dtmax.outputs['Max'], div.inputs[1])
    st = node('GeometryNodeStoreNamedAttribute', data_type='FLOAT', domain='POINT')
    st.inputs['Name'].default_value = 'f'
    L.new(lattice.outputs[0], st.inputs['Geometry'])
    L.new(div.outputs[0], st.inputs['Value'])
    sm = node('GeometryNodeSetMaterial')
    sm.inputs['Material'].default_value = mats[which]
    L.new(st.outputs[0], sm.inputs['Geometry'])
    # the paths of this field: hyphae (kind 0) on d, cords (kind 1) on dt
    kind = node('GeometryNodeInputNamedAttribute', data_type='FLOAT')
    kind.inputs['Name'].default_value = 'kind'
    cmp = node('ShaderNodeMath', operation='LESS_THAN' if which == 'd' else 'GREATER_THAN')
    cmp.inputs[1].default_value = 0.5
    L.new(kind.outputs['Attribute'], cmp.inputs[0])
    inv = node('ShaderNodeMath', operation='SUBTRACT')
    inv.inputs[0].default_value = 1.0
    L.new(cmp.outputs[0], inv.inputs[1])
    dl = node('GeometryNodeDeleteGeometry', domain='CURVE')
    L.new(curves.outputs[0], dl.inputs['Geometry'])
    L.new(inv.outputs[0], dl.inputs['Selection'])
    rad = node('GeometryNodeSetCurveRadius')
    rad.inputs['Radius'].default_value = 0.035 if which == 'd' else 0.06
    L.new(dl.outputs[0], rad.inputs['Curve'])
    lift = node('GeometryNodeSetPosition')
    nrm = node('GeometryNodeInputNamedAttribute', data_type='FLOAT_VECTOR')
    nrm.inputs['Name'].default_value = 'nrm'
    sc_ = node('ShaderNodeVectorMath', operation='SCALE')
    sc_.inputs['Scale'].default_value = 0.06
    L.new(nrm.outputs['Attribute'], sc_.inputs[0])
    L.new(rad.outputs[0], lift.inputs['Geometry'])
    L.new(sc_.outputs[0], lift.inputs['Offset'])
    sl = node('GeometryNodeSetMaterial')
    sl.inputs['Material'].default_value = mats['line']
    L.new(lift.outputs[0], sl.inputs['Geometry'])
    j = node('GeometryNodeJoinGeometry')
    L.new(sl.outputs[0], j.inputs[0])
    L.new(sm.outputs[0], j.inputs[0])
    L.new(j.outputs[0], out.inputs[0])


for which in ('d', 'dt'):
    build(which)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    for inst in dg.object_instances:
        par = inst.parent.name if inst.parent else ''
        if 'PA_Mycelium' not in (inst.object.name, par):
            continue
        d = inst.object.data
        if hasattr(d, 'vertices') and len(d.vertices):
            f = [v.value for v in d.attributes['f'].data]
            print('STATS', which, 'lattice verts', len(d.vertices), 'edges', len(d.edges),
                  'zero (sources)', sum(1 for x in f if x <= 1e-6), 'max f', round(max(f), 3))
        elif hasattr(d, 'curves'):
            print('STATS', which, 'curves', len(d.curves), 'points', len(d.points))
    sc.render.filepath = f'{out_dir}/_field_{which}.png'
    bpy.ops.render.render(write_still=True)
    print('WROTE', sc.render.filepath)
