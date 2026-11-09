"""Supertree / 雨後甦醒 — Nodevember 2026 Day 07.

An interpretation of Singapore's Supertree Grove, not a measured reconstruction.
Every visible mesh is generated in Geometry Nodes from an empty base mesh.
No imported geometry, image textures, simulations or keyframes.

Blender -b --factory-startup --python build.py -- --preview
Blender -b --factory-startup --python build.py -- --hero
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _lib in (HERE.parents[1] / 'lib', ROOT / '.agents/skills/procedural-art/scripts'):  # public repo, monorepo
    if (_lib / 'proc_blender.py').exists():
        sys.path.insert(0, str(_lib))
        break
import proc_blender as pb

NAME = 'Supertree'
TAU = math.tau
FPS, FRAMES, HERO = 24, 192, 168


def group(name, inputs, outputs=(('Geometry', 'geometry'),)):
    t = bpy.data.node_groups.new('PA_' + name, 'GeometryNodeTree')
    for label, kind, default in inputs:
        s = t.interface.new_socket(label, in_out='INPUT', socket_type=pb._STYPE[kind])
        if default is not None:
            s.default_value = default
    for label, kind in outputs:
        t.interface.new_socket(label, in_out='OUTPUT', socket_type=pb._STYPE[kind])
    g = pb.Graph(t)
    i, o = g.group_io()
    return t, g, i, o


def join(g, *geos):
    n = g.node('GeometryNodeJoinGeometry')
    for geo in geos:
        g.link(geo, n, b_key='Geometry')
    return n


def xyz(g, value):
    s = g.node('ShaderNodeSeparateXYZ', Vector=value)
    return (s.outputs[k] for k in ('X', 'Y', 'Z'))


def rnd(g, seed, lo=0., hi=1.):
    return g.out(g.node('FunctionNodeRandomValue', props={'data_type': 'FLOAT'}, Min=lo, Max=hi,
                        Seed=seed, ID=g.node('GeometryNodeInputIndex')), 'Value')


def attr(g, name):
    return g.out(g.node('ShaderNodeAttribute', props={'attribute_name': name}), 'Fac')


def store(g, geo, name, value):
    return g.node('GeometryNodeStoreNamedAttribute', label=name,
                  props={'data_type': 'FLOAT', 'domain': 'POINT'}, Geometry=geo, Name=name, Value=value)


def clamp(g, x, lo=0., hi=1.):
    return g.math('MINIMUM', hi, g.math('MAXIMUM', lo, x))


def smooth(g, x):
    x = clamp(g, x)
    return g.math('MULTIPLY', g.math('MULTIPLY', x, x), g.math('SUBTRACT', 3, g.math('MULTIPLY', 2, x)))


def transform(g, geo, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0)):
    return g.node('GeometryNodeTransform', Geometry=geo, Translation=loc, Scale=scale, Rotation=rot)


def shade(g, geo, mat):
    return pb.set_material(g, g.node('GeometryNodeSetShadeSmooth', Geometry=geo), mat)


def tube(g, curve, radius=.04, res=6):
    profile = g.node('GeometryNodeCurvePrimitiveCircle', Resolution=res, Radius=radius)
    return g.node('GeometryNodeCurveToMesh', Curve=curve, Profile_Curve=profile, Fill_Caps=True)


def line(g, a, b, radius, mat):
    c = g.node('GeometryNodeCurvePrimitiveLine', Start=a, End=b)
    return shade(g, tube(g, c, radius), mat)


def clock(g):
    n = g.node('ShaderNodeValue', label='Seconds / scene frame')
    n.outputs[0].driver_add('default_value').driver.expression = '(frame-1)/24'
    return n


_GROUPS = {}


def profile_group():
    """PA_CrownProfile: the one silhouette shared by the light skin, its rim and every steel member.

    u runs from the trunk neck (0) to the branch tips (1.045). The light bowl is a quarter
    ellipse that ends at u=.65, radius .56 of the nominal crown radius; the black branches
    continue straight out to 1.05 radii at u=1.045.
    """
    if 'profile' in _GROUPS:
        return _GROUPS['profile']
    t, g, i, o = group('CrownProfile', [('u', 'float', 0.), ('Height', 'float', 40.),
        ('Trunk Radius', 'float', 2.5), ('Crown Radius', 'float', 18.5)],
        (('Radius', 'float'), ('Z', 'float')))
    u, h, r, spread = (i.outputs[k] for k in ('u', 'Height', 'Trunk Radius', 'Crown Radius'))
    m = g.math
    with g.section('a · Quarter-ellipse bowl'):
        inner = clamp(g, m('DIVIDE', u, .65))
        theta = m('MULTIPLY', inner, math.pi*.5)
        theta.label = 'bowl angle θ'
        neck = m('MULTIPLY', r, 1.09)
        neck.label = 'neck radius 1.09 r'
        bowl_r = m('MULTIPLY', spread, .56)
        bowl_r.label = 'bowl rim 0.56 R'
        radius = m('ADD', neck, m('MULTIPLY', m('SUBTRACT', bowl_r, neck), m('SUBTRACT', 1, m('COSINE', theta))))
    with g.section('b · Straight branch fringe'):
        outer = clamp(g, m('DIVIDE', m('SUBTRACT', u, .65), .395))
        outer.label = 'fringe 0 → 1'
        radius = m('ADD', radius, m('MULTIPLY', m('MULTIPLY', spread, .49), outer))
        z = m('MULTIPLY', h, m('ADD', .65, m('ADD', m('MULTIPLY', .25, m('SINE', theta)),
                                                m('MULTIPLY', .065, m('POWER', outer, 1.35)))))
        radius.label, z.label = 'crown radius R(u)', 'crown height Z(u)'
        g.link(radius, o, b_key='Radius')
        g.link(z, o, b_key='Z')
    pb.arrange(t)
    _GROUPS['profile'] = t
    return t


def crown_profile(g, u, h, r, spread):
    """One PA_CrownProfile node: (radius, z) sockets for parameter u."""
    n = g.group(profile_group(), u=u, Height=h, Trunk_Radius=r, Crown_Radius=spread)
    n.label = 'crown profile'
    return n.outputs['Radius'], n.outputs['Z']


def crown_point_group():
    """PA_CrownPoint: a point on the frame surface at profile parameter u and rib phase."""
    if 'point' in _GROUPS:
        return _GROUPS['point']
    t, g, i, o = group('CrownPoint', [('u', 'float', .63), ('Phase', 'float', 0.), ('Height', 'float', 40.),
        ('Crown Radius', 'float', 18.5), ('Ribs', 'int', 32)], (('Position', 'vector'),))
    u, phase, h, spread, count = (i.outputs[k] for k in ('u', 'Phase', 'Height', 'Crown Radius', 'Ribs'))
    m = g.math
    radius, z = crown_profile(g, u, h, m('MULTIPLY', h, .0625), spread)
    radius = m('MULTIPLY', radius, 1.018)
    radius.label = 'just outside the skin'
    angle = m('DIVIDE', m('MULTIPLY', phase, TAU), count)
    angle.label = 'phase × one rib step'
    pos = g.vec(m('MULTIPLY', radius, m('COSINE', angle)),
                m('MULTIPLY', radius, m('SINE', angle)), m('SUBTRACT', z, .17))
    g.link(pos, o, b_key='Position')
    pb.arrange(t)
    _GROUPS['point'] = t
    return t


def basic(name, color, rough=.4, metal=0.):
    return pb.material(name, 'metal' if metal else 'matte', color=color, roughness=rough, metallic=metal)


def materials():
    mats = {}
    mats['steel'] = basic('OxideBurgundySteel', (.006, .003, .008), .48, .28)
    mats['bronze'] = basic('WarmBrushedBronze', (.31, .16, .052), .31, .78)
    mats['core'] = basic('PlantingFelt', (.014, .021, .015), .86)
    mats['deck'] = basic('SkywayDeck', (.17, .13, .085), .39, .45)
    mats['dark'] = basic('CarbonAndShadow', (.009, .014, .02), .46, .38)
    mats['stone'] = basic('GranitePlanter', (.13, .145, .15), .42)
    mats['shirt'] = basic('LinenShirts', (.64, .56, .40), .7)
    mats['skin'] = basic('WarmSkin', (.28, .13, .075), .62)
    mats['pants'] = basic('DeepBlueClothes', (.015, .029, .045), .73)

    mat = basic('TropicalLivingSkin', (.05, .18, .035), .44)
    g = pb.Graph(mat.node_tree)
    p = next(n for n in g.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
    pos = g.out(g.node('ShaderNodeNewGeometry'), 'Position')
    n = g.node('ShaderNodeTexNoise', Vector=pos, Scale=5.1, Detail=2.8)
    ramp = g.node('ShaderNodeValToRGB', Fac=g.out(n, 'Factor'))
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    for k, (f, c) in enumerate(((0., (.006, .022, .009, 1)), (.38, (.018, .075, .019, 1)),
                               (.65, (.035, .115, .018, 1)), (1., (.15, .23, .035, 1)))):
        e = ramp.color_ramp.elements[0] if k == 0 else ramp.color_ramp.elements.new(f)
        e.position, e.color = f, c
    g.link(ramp, p, b_key='Base Color')
    p.inputs['Subsurface Weight'].default_value = .12
    p.inputs['Subsurface Radius'].default_value = (.3, .6, .15)
    mats['leaf'] = mat

    for name, rgb, strength in (('gold', (1., .38, .055, 1), 3.8),
                                ('pink', (.72, .025, .22, 1), 6.)):
        mat = basic('Light_' + name, rgb[:3], .28, .45)
        g = pb.Graph(mat.node_tree)
        p = next(n for n in g.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
        delay, path = attr(g, 'delay'), attr(g, 'flow')
        arrival = g.math('ADD', g.math('MULTIPLY', delay, 1.05), g.math('MULTIPLY', path, 1.65))
        arrival.label = 'arrival = 1.05 delay + 1.65 flow'
        age = g.math('SUBTRACT', clock(g), arrival)
        age.label = 'seconds since the light arrived'
        on = smooth(g, g.math('DIVIDE', age, .65))
        on.label = 'switched on (0.65 s fade)'
        beat = g.math('EXPONENT', g.math('MULTIPLY', -2., g.math('MULTIPLY', age, age)))
        beat.label = 'arrival flash'
        emission = g.math('ADD', .13, g.math('ADD', g.math('MULTIPLY', on, strength),
                                           g.math('MULTIPLY', beat, 2.2)))
        if name == 'pink':
            palette = g.node('ShaderNodeValToRGB', Fac=g.math('MULTIPLY', delay, .28))
            palette.color_ramp.elements[0].color = (.70, .015, .19, 1)
            palette.color_ramp.elements[1].color = (.5, .007, .9, 1)
            e = palette.color_ramp.elements.new(.38)
            e.color = (.8, .015, .5, 1)
            g.link(palette, p, b_key='Emission Color')
        else:
            p.inputs['Emission Color'].default_value = rgb
        g.link(emission, p, b_key='Emission Strength')
        mats[name] = mat

    mat = basic('LuminousVioletCanopyPanels', (.025, .003, .05), .36, .18)
    g = pb.Graph(mat.node_tree)
    p = next(n for n in g.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
    u, a = attr(g, 'panel_u'), attr(g, 'panel_a')
    ramp = g.node('ShaderNodeValToRGB', Fac=u)
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    for j, (f, rgb) in enumerate(((0., (.25, .002, .75, 1)), (.25, (.55, .008, .85, 1)),
                                 (.52, (.95, .04, 1., 1)), (.72, (1., .20, 1., 1)),
                                 (1., (.50, .004, .8, 1)))):
        e = ramp.color_ramp.elements[0] if not j else ramp.color_ramp.elements.new(f)
        e.position, e.color = f, rgb
    sector = g.math('FLOOR', g.math('MULTIPLY', a, 48))
    gold_sector = g.math('LESS_THAN', g.math('FLOORED_MODULO', sector, 11), 1.)
    band = g.math('MULTIPLY', g.math('GREATER_THAN', u, .3), g.math('LESS_THAN', u, .53))
    gold = g.math('MULTIPLY', gold_sector, band)
    color = g.node('ShaderNodeMixRGB', Fac=gold, Color1=ramp, Color2=(1., .36, .009, 1))
    g.link(color, p, b_key='Emission Color')
    arrival = g.math('ADD', g.math('MULTIPLY', attr(g, 'delay'), 1.05),
                     g.math('MULTIPLY', attr(g, 'flow'), 1.65))
    arrival.label = 'arrival = 1.05 delay + 1.65 flow'
    on = smooth(g, g.math('DIVIDE', g.math('SUBTRACT', clock(g), arrival), .65))
    on.label = 'switched on (0.65 s fade)'
    gold.label = 'one gold sector in 11, mid band'
    g.link(g.math('ADD', .005, g.math('MULTIPLY', on, .8)), p, b_key='Emission Strength')
    mats['panels'] = mat

    mat = basic('RainPolishedPlaza', (.10, .12, .14), .15)
    g = pb.Graph(mat.node_tree)
    p = next(n for n in g.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
    pos = g.out(g.node('ShaderNodeNewGeometry'), 'Position')
    patch = g.node('ShaderNodeTexNoise', Vector=pos, Scale=.32, Detail=3., Roughness=.7)
    puddle = smooth(g, g.math('MULTIPLY', g.math('SUBTRACT', g.out(patch, 'Factor'), .40), 6.))
    rough = g.math('ADD', .045, g.math('MULTIPLY', g.math('SUBTRACT', 1, puddle), .34))
    g.link(rough, p, b_key='Roughness')
    p.inputs['Coat Weight'].default_value = .45
    p.inputs['Coat Roughness'].default_value = .08
    brick = g.node('ShaderNodeTexBrick', Vector=pos, Scale=.85, Mortar_Size=.003,
                   Color1=(.11, .13, .15, 1), Color2=(.065, .08, .095, 1),
                   Mortar=(.028, .035, .042, 1), Brick_Width=1.2, Row_Height=.6)
    g.link(brick, p, a_key='Color', b_key='Base Color')
    fine = g.node('ShaderNodeTexNoise', Vector=pos, Scale=72., Detail=2.)
    bump = g.node('ShaderNodeBump', Height=g.out(fine, 'Factor'), Strength=.2, Distance=.018)
    g.link(bump, p, b_key='Normal')
    mats['wet'] = mat
    for mat in mats.values():
        pb.arrange(mat.node_tree)
    return mats


def plant_group(mat):
    """A bent lanceolate leaf → paired leaflets → three asymmetric fern fronds."""
    t, g, i, o = group('FernAndBromeliad', [])
    m = g.math
    with g.section('1 · Leaflet'):
        grid = g.node('GeometryNodeMeshGrid', Size_X=1, Size_Y=1, Vertices_X=9, Vertices_Y=3)
        x, y, _ = xyz(g, g.node('GeometryNodeInputPosition'))
        f = m('ADD', x, .5)
        width = m('POWER', m('SINE', m('MULTIPLY', math.pi, f)), .7)
        leafpos = g.vec(m('MULTIPLY', f, .29), m('MULTIPLY', m('MULTIPLY', y, width), .105),
                        m('ADD', m('MULTIPLY', m('SINE', m('MULTIPLY', math.pi, f)), .025), m('MULTIPLY', f, .04)))
        leaf = g.node('GeometryNodeSetPosition', Geometry=grid, Position=leafpos)
    with g.section('2 · Paired leaflets on a rachis'):
        stem = g.node('GeometryNodeCurvePrimitiveLine', Start=(0, 0, 0), End=(.04, 0, .95))
        stem = g.node('GeometryNodeResampleCurve', Curve=stem, Count=14)
        f = g.out(g.node('GeometryNodeSplineParameter'), 'Factor')
        stem = g.node('GeometryNodeSetPosition', Geometry=stem,
                      Offset=g.vec(m('MULTIPLY', m('MULTIPLY', f, f), .38), 0, m('MULTIPLY', m('MULTIPLY', f, f), -.22)))
        pts = g.node('GeometryNodeCurveToPoints', props={'mode': 'EVALUATED'}, Curve=stem)
        f = m('DIVIDE', g.node('GeometryNodeInputIndex'), 13.)
        size = m('MULTIPLY', .95, m('POWER', m('SUBTRACT', 1.02, f), .65))
        twigs = []
        for side in (-1, 1):
            twigs.append(g.node('GeometryNodeInstanceOnPoints', Points=g.out(pts, 'Points'), Instance=leaf,
                                 Rotation=(0, -.12, side * 1.02), Scale=g.vec(size, size, size)))
        frond = join(g, *twigs, tube(g, stem, .009, 4))
        frond = g.node('GeometryNodeRealizeInstances', Geometry=frond)
    with g.section('3 · Three fronds'):
        rosette = join(g, transform(g, frond, rot=(.35, 0, 0)),
                       transform(g, frond, scale=(.85, .85, .85), rot=(.55, .1, 2.2)),
                       transform(g, frond, scale=(.65, .65, .65), rot=(.7, -.2, 4.5)))
        g.link(shade(g, rosette, mat), o, b_key='Geometry')
    pb.arrange(t)
    return t


def rib_module_group():
    """PA_RibModule: one primary rib's outer branching, as straight steel segments between profile stations.

    Side (+1 / -1) mirrors the phases; Shift (-0.012 / +0.012) staggers the joints of the mirrored copy.
    """
    if 'module' in _GROUPS:
        return _GROUPS['module']
    t, g, i, o = group('RibModule', [('Height', 'float', 40.), ('Crown Radius', 'float', 18.5), ('Ribs', 'int', 32),
        ('Section Scale', 'float', 1.), ('Side', 'float', 1.), ('Shift', 'float', -.012)])
    h, spread, count, scale, side, shift = (i.outputs[k] for k in
        ('Height', 'Crown Radius', 'Ribs', 'Section Scale', 'Side', 'Shift'))
    m = g.math

    def point(name, u0, du, phase):
        u = m('ADD', u0, m('MULTIPLY', shift, du)) if du else u0
        n = g.group(crown_point_group(), u=u, Phase=m('MULTIPLY', side, phase) if phase else 0.,
                    Height=h, Crown_Radius=spread, Ribs=count)
        n.label = name
        return n

    def segment(a, b, radius):
        c = g.node('GeometryNodeCurvePrimitiveLine', Start=a, End=b)
        return store(g, c, 'frame_radius', m('MULTIPLY', radius, scale))

    with g.section('a · Stations on the profile'):
        a = point('a · rib top u .63', .63, 0, 0)
        # Two long, nearly parallel outer members per curved primary rib.
        l0 = point('l0 · u .735+shift', .735, 1, -.24)
        lt = point('lt · u .805+shift', .805, 1, -.24)
        l1 = point('l1 · u .875+shift', .875, 1, -.24)
        l2 = point('l2 · tip u 1.045', 1.045, 0, -.24)
        r0 = point('r0 · u .75-shift', .75, -1, .24)
        rt = point('rt · u .805+shift', .805, 1, .24)
        r1 = point('r1 · u .925-shift', .925, -1, .24)
        nt = point('nt · u .96-shift', .96, -1, .24)
        r2 = point('r2 · tip u 1.045', 1.045, 0, .24)
        f = point('f · L bend', .875, 1, -.04)
        mt = point('mt · u .96-shift', .96, -1, -.04)
        g1 = point('g1 · L tip', .995, 0, -.04)
        yf = point('Y fork', .995, 0, .46)
        yt = point('Y tip', 1.045, 0, .42)
    with g.section('b · Two long rails'):
        bars = [segment(a, l0, .120), segment(l0, lt, .120), segment(lt, l1, .120), segment(l1, l2, .120),
                segment(a, r0, .120), segment(r0, rt, .120), segment(rt, r1, .120), segment(r1, nt, .120),
                segment(nt, r2, .120)]
    with g.section('c · L bracket and Y fork'):
        # An inward L bracket with an open-ended parallel extension.
        bars.extend((segment(l1, f, .085), segment(f, mt, .085), segment(mt, g1, .085)))
        # The second long member has a short outward Y fork near its end.
        bars.extend((segment(r1, yf, .085), segment(yf, yt, .085)))
    with g.section('d · Two short ties'):
        # Only selected short connections; never a full circumferential ring.
        bars.extend((segment(lt, rt, .055), segment(mt, nt, .055)))
        g.link(join(g, *bars), o, b_key='Geometry')
    pb.arrange(t)
    _GROUPS['module'] = t
    return t


def crown_frame_group(steel):
    """Paired long steel members, L/Y offshoots, and staggered short cross-members.

    The supplied reference shows long radial members and short angular offshoots,
    rather than regular closed honeycomb cells or concentric outer rings.
    """
    t, g, i, o = group('SupertreeCrownFrame', [('Height','float',40.),
        ('Crown Radius','float',18.5),('Ribs','int',32)],
        (('Geometry','geometry'),('Skeleton','geometry'),('Bay','geometry')))
    h, spread, count = (i.outputs[k] for k in ('Height','Crown Radius','Ribs'))
    m = g.math
    templates=[]
    with g.section('1 · Curved main rib'):
        r = m('MULTIPLY',h,.0625)
        # Keep the chosen hero sections, but preserve spacing on small / dense trees.
        section_scale = m('MINIMUM',1.,m('MULTIPLY',m('DIVIDE',spread,18.5),m('DIVIDE',32.,count)))
        section_scale.label = 'section scale (thinner on small, dense crowns)'
        stem = g.node('GeometryNodeCurvePrimitiveLine',Start=(0,0,0),End=(0,0,1))
        stem = g.node('GeometryNodeResampleCurve',Curve=stem,Count=48)
        u = m('MULTIPLY',g.out(g.node('GeometryNodeSplineParameter'),'Factor'),.63)
        radius,z = crown_profile(g,u,h,r,spread)
        stem = g.node('GeometryNodeSetPosition',Geometry=stem,
            Position=g.vec(m('MULTIPLY',radius,1.018),0,m('SUBTRACT',z,.17)))
        stem=store(g,stem,'frame_radius',m('MULTIPLY',.140,section_scale))
    with g.section('2 · Two rib modules'):
        # Module A and its mirror B: side flips the phases, shift swaps which rail runs longer.
        for variant in (0,1):
            mod = g.group(rib_module_group(), Height=h, Crown_Radius=spread, Ribs=count,
                          Section_Scale=section_scale, Side=1. if variant==0 else -1.,
                          Shift=-.012 if variant==0 else .012)
            mod.label = 'module ' + 'AB'[variant] + (' (side +1, shift -0.012)' if variant==0 else ' (side -1, shift +0.012)')
            templates.append(join(g,stem,mod))
            templates[-1].label = 'rib module ' + 'AB'[variant]
    with g.section('3 · Two mirrored families'):
        ring=g.node('GeometryNodeCurvePrimitiveCircle',Resolution=count,Radius=.001)
        pts=g.node('GeometryNodeCurveToPoints',props={'mode':'EVALUATED'},Curve=ring)
        pts=g.node('GeometryNodeSetPosition',Geometry=g.out(pts,'Points'),Position=g.vec(0,0,0))
        index=g.node('GeometryNodeInputIndex')
        parity=m('FLOORED_MODULO',index,2)
        angle=m('MULTIPLY',m('DIVIDE',index,count),TAU)
        families=[]
        for k in (0,1):
            inst=g.node('GeometryNodeInstanceOnPoints',Points=pts,Instance=templates[k],
                Selection=m('COMPARE',parity,k,.1),Rotation=g.vec(0,0,angle))
            families.append(g.node('GeometryNodeRealizeInstances',Geometry=inst))
        collar=g.node('GeometryNodeCurvePrimitiveCircle',Resolution=count,
            Radius=m('MULTIPLY',m('MULTIPLY',r,1.09),1.018))
        collar=transform(g,collar,loc=g.vec(0,0,m('SUBTRACT',m('MULTIPLY',h,.65),.17)))
        collar=store(g,collar,'frame_radius',m('MULTIPLY',.12,section_scale))
    with g.section('4 · Weld and section the steel'):
        curves=join(g,collar,*families)
        wire=g.node('GeometryNodeCurveToMesh',Curve=curves)
        wire=g.node('GeometryNodeMergeByDistance',label='Weld actual side-branch joints',Geometry=wire,Distance=.0002)
        g.link(wire,o,b_key='Skeleton')
        radius=g.out(g.node('GeometryNodeInputNamedAttribute',props={'data_type':'FLOAT'},Name='frame_radius'),'Attribute')
        profile=g.node('GeometryNodeCurvePrimitiveCircle',Resolution=4,Radius=1.)
        profile=transform(g,profile,rot=(0,0,math.pi/4))
        profile=transform(g,profile,scale=(1,.7,1))
        def surface(w):
            c=g.node('GeometryNodeMeshToCurve',Mesh=w)
            mesh=g.node('GeometryNodeCurveToMesh',Curve=c,Profile_Curve=profile,Scale=radius,Fill_Caps=True)
            return pb.set_material(g,mesh,steel)
        g.link(surface(wire),o,b_key='Geometry')
        unit=join(g,templates[0],transform(g,templates[1],rot=g.vec(0,0,m('DIVIDE',TAU,count))))
        unit=g.node('GeometryNodeCurveToMesh',Curve=unit)
        unit=g.node('GeometryNodeMergeByDistance',Geometry=unit,Distance=.0002)
        g.link(surface(unit),o,b_key='Bay')
    pb.arrange(t)
    return t


def tree_group(mats, plants):
    t, g, i, o = group('SupertreeArchitecture', [('Height', 'float', 43.), ('Crown Radius', 'float', 13.),
        ('Ribs', 'int', 32), ('Plant Density', 'float', 4.2), ('Lighting Delay', 'float', 0.), ('Seed', 'int', 21)])
    h, spread, count = (i.outputs[k] for k in ('Height', 'Crown Radius', 'Ribs'))
    m = g.math
    geos = []
    with g.section('1 · Planted trunk'):
        r = m('MULTIPLY', h, .0625)
        r.label = 'trunk radius r = 0.0625 h'
        shell = g.node('GeometryNodeMeshCylinder', Vertices=96, Side_Segments=64, Radius=r, Depth=m('MULTIPLY', h, .63))
        shell = transform(g, shell, loc=g.vec(0, 0, m('MULTIPLY', h, .315)))
        pos = g.node('GeometryNodeInputPosition')
        x, y, z = xyz(g, pos)
        noise = g.node('ShaderNodeTexNoise', Vector=pos, Scale=.8, Detail=3.)
        radial = m('ADD', 1., m('MULTIPLY', g.out(noise, 'Factor'), .045))
        shell = g.node('GeometryNodeSetPosition', Geometry=shell, Position=g.vec(m('MULTIPLY', x, radial), m('MULTIPLY', y, radial), z))
        geos.append(shade(g, shell, mats['core']))
        normal = g.node('GeometryNodeInputNormal')
        _, _, nz = xyz(g, normal)
        selection = m('LESS_THAN', m('ABSOLUTE', nz), .8)
        pts = g.node('GeometryNodeDistributePointsOnFaces', Mesh=shell, Selection=selection,
                     Density=i.outputs['Plant Density'], Seed=i.outputs['Seed'])
        plant = g.group(plants)
        size = rnd(g, i.outputs['Seed'], .67, 1.27)
        foliage = g.node('GeometryNodeInstanceOnPoints', Points=pts, Instance=plant,
                         Rotation=g.out(pts, 'Rotation'), Scale=g.vec(size, size, size))
        geos.append(foliage)
    with g.section('2 · Crown framework'):
        frame_tree = crown_frame_group(mats['steel'])
        frame = g.group(frame_tree, Height=h, Crown_Radius=spread, Ribs=count)
        frame.label = 'Connected branching framework'
        geos.append(g.out(frame, 'Geometry'))
    with g.section('3 · Light bowl'):
        panel = g.node('GeometryNodeMeshGrid', Size_X=1, Size_Y=1, Vertices_X=64, Vertices_Y=193)
        # Parameterise by the flat grid coordinates. Blender Grid stores Y fastest;
        # guessing a stride from Vertices X creates long rim-to-neck bridge faces.
        x, y, _ = xyz(g, g.node('GeometryNodeInputPosition'))
        u = m('ADD', x, .5)
        a = m('ADD', y, .5)
        panel = store(g, panel, 'panel_u', u)
        panel = store(g, panel, 'panel_a', a)
        radial_u = m('ADD', .0125, m('MULTIPLY', .6375, u))
        rad, zz = crown_profile(g, radial_u, h, r, spread)
        rad = m('MULTIPLY', rad, .96)
        angle = m('MULTIPLY', a, TAU)
        panel = g.node('GeometryNodeSetPosition', Geometry=panel,
            Position=g.vec(m('MULTIPLY', rad, m('COSINE', angle)), m('MULTIPLY', rad, m('SINE', angle)), m('ADD', zz, .12)))
        panel = shade(g, panel, mats['panels'])
        panel.label = 'Curved luminous skin'
        geos.append(panel)
        rad, zz = crown_profile(g, .65, h, r, spread)
        rim = g.node('GeometryNodeCurvePrimitiveCircle', Resolution=192, Radius=m('MULTIPLY', rad, .96))
        rim = transform(g, rim, loc=g.vec(0, 0, m('ADD', zz, .18)))
        geos.append(shade(g, tube(g, rim, .17, 8), mats['steel']))
    with g.section('4 · Core and dark cap'):
        core = g.node('GeometryNodeMeshCone', Vertices=64, Radius_Top=m('MULTIPLY', r, 1.25),
                      Radius_Bottom=m('MULTIPLY', r, .83), Depth=m('MULTIPLY', h, .36))
        geos.append(shade(g, transform(g, core, loc=g.vec(0, 0, m('MULTIPLY', h, .61))), mats['dark']))
        cap = g.node('GeometryNodeMeshCylinder', Vertices=128, Radius=m('MULTIPLY', spread, .55), Depth=m('MULTIPLY', h, .075))
        geos.append(shade(g, transform(g, cap, loc=g.vec(0, 0, m('MULTIPLY', h, .94))), mats['dark']))
        # Broad, stacked dark discs above the luminous inner bowl.
        for level, radius, thickness in ((.905, .60, .28), (.935, .575, .24), (.978, .59, .30)):
            disk = g.node('GeometryNodeMeshCylinder', Vertices=128, Radius=m('MULTIPLY', spread, radius), Depth=thickness)
            geos.append(shade(g, transform(g, disk, loc=g.vec(0, 0, m('MULTIPLY', h, level))), mats['dark']))
            ring = g.node('GeometryNodeCurvePrimitiveCircle', Resolution=160, Radius=m('MULTIPLY', spread, radius))
            ring = transform(g, ring, loc=g.vec(0, 0, m('MULTIPLY', h, level)))
            geos.append(shade(g, tube(g, ring, .025, 6), mats['steel']))
    with g.section('5 · Climbing lights and balcony'):
        # One point per rib, at the origin; every sixth one carries a vertical pink light line.
        ring = g.node('GeometryNodeCurvePrimitiveCircle', Resolution=count, Radius=.001)
        points = g.node('GeometryNodeCurveToPoints', props={'mode': 'EVALUATED'}, Curve=ring)
        points = g.node('GeometryNodeSetPosition', Geometry=g.out(points, 'Points'), Position=g.vec(0, 0, 0))
        azimuth = m('MULTIPLY', m('DIVIDE', g.node('GeometryNodeInputIndex'), count), TAU)
        vine = g.node('GeometryNodeCurvePrimitiveLine', Start=g.vec(m('MULTIPLY', r, 1.08), 0, .1),
                      End=g.vec(m('MULTIPLY', r, 1.08), 0, m('MULTIPLY', h, .64)))
        vines = g.node('GeometryNodeInstanceOnPoints', Points=points, Instance=vine,
                       Selection=m('COMPARE', m('FLOORED_MODULO', g.node('GeometryNodeInputIndex'), 6), 0, .1),
                       Rotation=g.vec(0, 0, azimuth))
        vines = g.node('GeometryNodeRealizeInstances', Geometry=vines)
        geos.append(shade(g, tube(g, vines, .012, 5), mats['pink']))
        rim = g.node('GeometryNodeCurvePrimitiveCircle', Resolution=96, Radius=m('MULTIPLY', r, 1.48))
        rim = transform(g, rim, loc=(0, 0, .25))
        geos.append(shade(g, tube(g, rim, .24, 8), mats['stone']))
        # A visitor balcony rings each trunk just below its flared shoulder.
        balcony = g.node('GeometryNodeCurvePrimitiveCircle', Resolution=128, Radius=m('MULTIPLY', r, 1.90))
        balcony = transform(g, balcony, loc=g.vec(0, 0, m('MULTIPLY', h, .58)))
        profile = g.node('GeometryNodeCurvePrimitiveCircle', Resolution=4, Radius=1.)
        profile = transform(g, profile, scale=(.66, .17, 1), rot=(0, 0, math.pi/4))
        deck = g.node('GeometryNodeCurveToMesh', Curve=balcony, Profile_Curve=profile, Fill_Caps=True)
        geos.append(shade(g, deck, mats['dark']))
        for dz in (0., .97):
            rail = g.node('GeometryNodeSetPosition', Geometry=balcony, Offset=(0, 0, dz))
            geos.append(shade(g, tube(g, rail, .035, 6), mats['pink']))
        pp = g.node('GeometryNodeCurveToPoints', Curve=balcony, Count=64)
        post = g.node('GeometryNodeMeshCylinder', Vertices=5, Radius=.018, Depth=.95)
        post = transform(g, post, loc=(0, 0, .475))
        geos.append(pb.set_material(g, g.node('GeometryNodeInstanceOnPoints', Points=g.out(pp, 'Points'), Instance=post), mats['steel']))
    with g.section('6 · Light arrival'):
        all_geo = join(g, *geos)
        all_geo = store(g, all_geo, 'delay', i.outputs['Lighting Delay'])
        _, _, z = xyz(g, g.node('GeometryNodeInputPosition'))
        all_geo = store(g, all_geo, 'flow', m('DIVIDE', z, h))
        g.link(all_geo, o, b_key='Geometry')
    pb.arrange(t)
    return t


# Cubic skyway; its endpoints enter the living skin of the two primary trees.
BRIDGE = ((-12., 19., 23.2), (-5., 10., 22.0), (14., 5., 24.0), (22., 4., 27.84))


def bridge_point(t):
    return tuple((1-t)**3 * BRIDGE[0][k] + 3*(1-t)**2*t*BRIDGE[1][k] +
                 3*(1-t)*t*t*BRIDGE[2][k] + t**3*BRIDGE[3][k] for k in range(3))


def make_bridge(mats):
    ob, g = pb.gn_object('Skyway', NAME)
    m = g.math
    with g.section('1 · Bezier deck'):
        # Bezier-like curve generated analytically from a resampled line.
        c = g.node('GeometryNodeCurvePrimitiveLine', Start=(0, 0, 0), End=(1, 0, 0))
        c = g.node('GeometryNodeResampleCurve', Curve=c, Count=192)
        t = g.out(g.node('GeometryNodeSplineParameter'), 'Factor')
        v = m('SUBTRACT', 1, t)
        weights = (m('POWER', v, 3), m('MULTIPLY', 3, m('MULTIPLY', m('POWER', v, 2), t)),
                   m('MULTIPLY', 3, m('MULTIPLY', v, m('POWER', t, 2))), m('POWER', t, 3))
        coords = []
        for axis in range(3):
            terms = [m('MULTIPLY', weights[j], BRIDGE[j][axis]) for j in range(4)]
            coords.append(m('ADD', m('ADD', terms[0], terms[1]), m('ADD', terms[2], terms[3])))
        c = g.node('GeometryNodeSetPosition', label='cubic Bezier through BRIDGE', Geometry=c, Position=g.vec(*coords))
        c = store(g, c, 'flow', m('SUBTRACT', 1, t))
        profile = g.node('GeometryNodeCurvePrimitiveCircle', Resolution=4, Radius=1.)
        profile = transform(g, profile, scale=(1.23, .145, 1), rot=(0, 0, math.pi/4))
        deck = g.node('GeometryNodeCurveToMesh', Curve=c, Profile_Curve=profile, Fill_Caps=True)
        geos = [shade(g, deck, mats['deck'])]
    with g.section('2 · Rails and pickets'):
        tangent = g.node('GeometryNodeInputTangent')
        sideways = g.vmath('NORMALIZE', g.vmath('CROSS_PRODUCT', tangent, (0, 0, 1)))
        for side in (-1, 1):
            rail = g.node('GeometryNodeSetPosition', Geometry=c,
                          Offset=g.vmath('ADD', g.vmath('SCALE', sideways, scale=side*.87), (0, 0, 1.14)))
            geos.append(shade(g, tube(g, rail, .046, 6), mats['pink']))
            base = g.node('GeometryNodeSetPosition', Geometry=c,
                          Offset=g.vmath('ADD', g.vmath('SCALE', sideways, scale=side*.87), (0, 0, .08)))
            geos.append(shade(g, tube(g, base, .045, 6), mats['gold']))
            pts = g.node('GeometryNodeCurveToPoints', Curve=base, Count=145)
            post = g.node('GeometryNodeMeshCylinder', Vertices=5, Radius=.017, Depth=1.06)
            post = transform(g, post, loc=(0, 0, .53))
            geos.append(pb.set_material(g, g.node('GeometryNodeInstanceOnPoints', Points=g.out(pts, 'Points'), Instance=post), mats['bronze']))
            for z in (.36, .70):
                rail = g.node('GeometryNodeSetPosition', Geometry=base, Offset=(0, 0, z))
                geos.append(shade(g, tube(g, rail, .012, 4), mats['bronze']))
    with g.section('3 · Suspension cables'):
        for k, u in enumerate((.07, .13, .20, .28, .72, .8, .88, .94)):
            p = bridge_point(u)
            end = (-12., 19., 37.) if u < .5 else (22., 4., 44.)
            for side in (-1, 1):
                geos.append(line(g, (p[0]+side*.86, p[1], p[2]+1.12),
                                 (end[0]+side*2.5, end[1], end[2]), .017, mats['bronze']))
        geo = store(g, join(g, *geos), 'delay', 1.7)
        g.output(geo)
    pb.arrange(g.tree)
    return ob


def person_group(mats):
    t, g, i, o = group('Visitors', [])
    geos = []
    torso = g.node('GeometryNodeMeshUVSphere', Segments=12, Rings=8, Radius=1.)
    geos.append(shade(g, transform(g, torso, loc=(0, 0, 1.13), scale=(.205, .125, .34)), mats['shirt']))
    head = g.node('GeometryNodeMeshIcoSphere', Radius=.115, Subdivisions=2)
    geos.append(shade(g, transform(g, head, loc=(0, 0, 1.59), scale=(1, .95, 1.17)), mats['skin']))
    for side in (-1, 1):
        geos.append(line(g, (side*.09, 0, .91), (side*.13, side*.05, .10), .061, mats['pants']))
        geos.append(line(g, (side*.20, 0, 1.34), (side*.25, -.04, .90), .045, mats['shirt']))
    g.link(join(g, *geos), o, b_key='Geometry')
    pb.arrange(t)
    return t


def landscape(mats, plants, people):
    ob, g = pb.gn_object('RainGarden', NAME)
    m = g.math
    with g.section('1 · Wet plaza'):
        ground = g.node('GeometryNodeMeshGrid', Size_X=320, Size_Y=320, Vertices_X=2, Vertices_Y=2)
        geos = [pb.set_material(g, transform(g, ground, loc=(0, 45, -.045)), mats['wet'])]
    with g.section('2 · Planting beds'):
        grid = g.node('GeometryNodeMeshGrid', Size_X=135, Size_Y=65, Vertices_X=90, Vertices_Y=42)
        grid = transform(g, grid, loc=(0, 61, 0))
        pts = g.node('GeometryNodeDistributePointsOnFaces', Mesh=grid, Density=.28, Seed=13)
        size = rnd(g, 31, .75, 2.4)
        inst = g.node('GeometryNodeInstanceOnPoints', Points=pts, Instance=g.group(plants),
                      Rotation=g.vec(0, 0, rnd(g, 17, 0, TAU)), Scale=g.vec(size, size, size))
        geos.append(inst)
        for x, y, sx, sy in ((-20., -8., 9., 17.), (22., 0., 8., 18.)):
            disk = g.node('GeometryNodeMeshCircle', props={'fill_type': 'NGON'}, Vertices=96, Radius=1.)
            disk = transform(g, disk, loc=(x, y, .08), scale=(sx, sy, 1))
            geos.append(pb.set_material(g, disk, mats['core']))
            pp = g.node('GeometryNodeDistributePointsOnFaces', Mesh=disk, Density=2.2, Seed=int(abs(x)))
            size = rnd(g, 29, .65, 1.8)
            geos.append(g.node('GeometryNodeInstanceOnPoints', Points=pp, Instance=g.group(plants),
                              Rotation=g.vec(0, 0, rnd(g, 81, 0, TAU)), Scale=g.vec(size, size, size)))
            rim = g.node('GeometryNodeCurvePrimitiveCircle', Resolution=128, Radius=1.)
            rim = transform(g, rim, loc=(x, y, .08), scale=(sx, sy, 1))
            geos.append(shade(g, tube(g, rim, .10, 6), mats['stone']))
        # Small, dense islands round the actual tree bases.
        for x, y, h, r, delay in TREES:
            disk = g.node('GeometryNodeMeshCircle', props={'fill_type': 'NGON'}, Vertices=64, Radius=h*.074)
            disk = transform(g, disk, loc=(x, y, .02))
            pp = g.node('GeometryNodeDistributePointsOnFaces', Mesh=disk, Density=3.2, Seed=int(h))
            size = rnd(g, int(h), .35, .85)
            geos.append(g.node('GeometryNodeInstanceOnPoints', Points=pp, Instance=g.group(plants),
                              Rotation=g.vec(0, 0, rnd(g, 51, 0, TAU)), Scale=g.vec(size, size, size)))
    with g.section('3 · Visitors'):
        person = g.group(people)
        for u in (.15, .19, .45, .7, .73):
            p = bridge_point(u)
            geos.append(transform(g, person, loc=(p[0], p[1], p[2]+.13), scale=(.96, .96, .96)))
        g.output(join(g, *geos))
    pb.arrange(g.tree)
    return ob


def skyline_ground_height(g, position):
    """One shared height field for the distant land and tower foundations."""
    m = g.math
    x,y,_ = xyz(g,position)
    flat = g.vec(x,y,0)
    noise = g.node('ShaderNodeTexNoise',Vector=flat,Scale=.016,Detail=2.,Roughness=.65)
    height = m('ADD',.18,m('MULTIPLY',g.out(noise,'Factor'),1.1))
    blend = smooth(g,m('DIVIDE',m('SUBTRACT',y,125.),40.))
    ground = m('MULTIPLY',height,blend)
    ground.label = 'shared ground height'
    return ground


def garden_and_city(mats):
    """Layered dark tree masses, a distant skyline and two triangular glass domes."""
    forest = basic('DarkGardenCanopies', (.011, .04, .022), .8)
    g = pb.Graph(forest.node_tree)
    p = next(n for n in g.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
    pos = g.out(g.node('ShaderNodeNewGeometry'), 'Position')
    n = g.node('ShaderNodeTexNoise', Vector=pos, Scale=4.2, Detail=4., Roughness=.75)
    color = g.node('ShaderNodeMixRGB', Fac=g.out(n, 'Factor'), Color1=(.002, .009, .006, 1), Color2=(.018, .067, .031, 1))
    g.link(color, p, b_key='Base Color')
    bump = g.node('ShaderNodeBump', Height=g.out(n, 'Factor'), Strength=.65, Distance=.3)
    g.link(bump, p, b_key='Normal')
    pb.arrange(forest.node_tree)
    ob, g = pb.gn_object('GardenAndSkyline', NAME)
    m = g.math
    with g.section('1 · Tree canopies'):
        ball = g.node('GeometryNodeMeshIcoSphere', Radius=1., Subdivisions=4)
        pos = g.node('GeometryNodeInputPosition')
        n = g.node('ShaderNodeTexNoise', Vector=pos, Scale=4.5, Detail=3.)
        offset = g.vmath('SCALE', g.node('GeometryNodeInputNormal'), scale=m('MULTIPLY', g.out(n, 'Factor'), .32))
        ball = g.node('GeometryNodeSetPosition', Geometry=ball, Offset=offset)
        leaf = g.node('GeometryNodeMeshGrid', Size_X=1, Size_Y=1, Vertices_X=7, Vertices_Y=3)
        x, y, _ = xyz(g, g.node('GeometryNodeInputPosition'))
        f = m('ADD', x, .5)
        width = m('SINE', m('MULTIPLY', math.pi, f))
        leaf = g.node('GeometryNodeSetPosition', Geometry=leaf,
            Position=g.vec(m('MULTIPLY', f, .29), m('MULTIPLY', m('MULTIPLY', y, width), .16), m('MULTIPLY', width, .04)))
        leaf = shade(g, leaf, forest)
        surface = g.node('GeometryNodeDistributePointsOnFaces', Mesh=ball, Density=85., Seed=76)
        leaves = g.node('GeometryNodeInstanceOnPoints', Points=surface, Instance=leaf,
                        Rotation=g.out(surface, 'Rotation'), Scale=g.vec(rnd(g, 77, .75, 1.35), 1, 1))
        leaves = g.node('GeometryNodeRealizeInstances', Geometry=leaves)
        ball = join(g, leaves, shade(g, transform(g, ball, scale=(.82, .82, .82)), forest))
        ball = join(g, ball, transform(g, ball, loc=(.6, .15, .15), scale=(.65, .7, .75)),
                    transform(g, ball, loc=(-.45, -.12, .22), scale=(.7, .65, .8)))
        pts = g.node('GeometryNodeMeshLine', Count=440, Offset=(0, 0, 0))
        size = rnd(g, 84, 1.1, 3.2)
        pts = g.node('GeometryNodeSetPosition', Geometry=pts,
            Position=g.vec(rnd(g, 81, -75., 80.), rnd(g, 82, 12., 130.), m('MULTIPLY', size, .55)))
        crowns = g.node('GeometryNodeInstanceOnPoints', Points=pts, Instance=ball,
                       Scale=g.vec(m('MULTIPLY', size, 1.15), size, m('MULTIPLY', size, .72)))
        geos = [crowns]
    with g.section('2 · Distant land'):
        soil = basic('DistantGround',(.009,.022,.016),.94)
        # Atmospheric perspective prevents the far end reading as a black wall.
        sg = pb.Graph(soil.node_tree)
        surface = next(n for n in sg.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled')
        output = next(n for n in sg.nodes if n.bl_idname=='ShaderNodeOutputMaterial')
        _,distance_y,_ = xyz(sg,sg.out(sg.node('ShaderNodeNewGeometry'),'Position'))
        haze = smooth(sg,sg.math('DIVIDE',sg.math('SUBTRACT',distance_y,290.),550.))
        sky = sg.node('ShaderNodeEmission',Color=(.10,.22,.44,1),Strength=.65)
        mix = sg.node('ShaderNodeMixShader',label='Far land fades into blue-hour haze',ins={0:haze,1:surface,2:sky})
        sg.link(mix,output,b_key='Surface')
        pb.arrange(soil.node_tree)
        land = g.node('GeometryNodeMeshGrid',Size_X=650,Size_Y=1075,Vertices_X=97,Vertices_Y=129)
        land = transform(g,land,loc=(0,662.5,0))
        position = g.node('GeometryNodeInputPosition')
        x,y,_ = xyz(g,position)
        land = g.node('GeometryNodeSetPosition',Geometry=land,
                      Position=g.vec(x,y,skyline_ground_height(g,position)))
        land = pb.set_material(g,land,soil)
        land.label = 'Continuous distant ground'
        geos.append(land)
        # A low, irregular belt softens the transition into the city foundations.
        bush = g.node('GeometryNodeMeshIcoSphere',Radius=1.,Subdivisions=3)
        noise = g.node('ShaderNodeTexNoise',Vector=g.node('GeometryNodeInputPosition'),Scale=4.,Detail=2.)
        bush = g.node('GeometryNodeSetPosition',Geometry=bush,
            Offset=g.vmath('SCALE',g.node('GeometryNodeInputNormal'),scale=m('MULTIPLY',g.out(noise,'Factor'),.25)))
        bush = shade(g,bush,forest)
        belt = g.node('GeometryNodeMeshLine',Count=200,Offset=(0,0,0))
        bx,by,size = rnd(g,201,-170.,170.),rnd(g,202,150.,235.),rnd(g,203,1.5,3.2)
        floor = skyline_ground_height(g,g.vec(bx,by,0))
        belt = g.node('GeometryNodeSetPosition',Geometry=belt,
            Position=g.vec(bx,by,m('ADD',floor,m('MULTIPLY',size,.52))))
        geos.append(g.node('GeometryNodeInstanceOnPoints',Points=belt,Instance=bush,
                          Scale=g.vec(size,size,m('MULTIPLY',size,.65))))
    with g.section('3 · Skyline'):
        city = basic('DistantCityGlass', (.009, .022, .045), .33, .6)
        sg = pb.Graph(city.node_tree)
        p = next(n for n in sg.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
        pos = sg.out(sg.node('ShaderNodeNewGeometry'), 'Position')
        _, _, z = xyz(sg, pos)
        band = sg.math('LESS_THAN', sg.math('FLOORED_MODULO', z, 2.5), .40)
        noise = sg.node('ShaderNodeTexNoise', Vector=pos, Scale=1.9, Detail=1.)
        lit = sg.math('MULTIPLY', band, sg.math('GREATER_THAN', sg.out(noise, 'Factor'), .57))
        p.inputs['Emission Color'].default_value = (.45, .65, 1., 1)
        sg.link(sg.math('MULTIPLY', lit, .5), p, b_key='Emission Strength')
        pb.arrange(city.node_tree)
        cube = pb.set_material(g, g.node('GeometryNodeMeshCube', Size=(1, 1, 1)), city)
        pts = g.node('GeometryNodeMeshLine', Count=36, Offset=(0, 0, 0))
        height = rnd(g, 92, 9, 32)
        pts = store(g, pts, 'tower_h', height)
        tx,ty = rnd(g,90,-150,150),rnd(g,91,230,290)
        terrain_z = skyline_ground_height(g,g.vec(tx,ty,0))
        base_z = m('SUBTRACT',terrain_z,.35)
        pts = store(g,pts,'city_ground_z',terrain_z)
        pts = store(g,pts,'city_base_z',base_z)
        pts = g.node('GeometryNodeSetPosition', Geometry=pts,
            Position=g.vec(tx,ty,m('ADD',base_z,m('MULTIPLY',height,.5))))
        height = g.out(g.node('GeometryNodeInputNamedAttribute', props={'data_type': 'FLOAT'}, Name='tower_h'), 'Attribute')
        width = rnd(g, 93, 3., 8.)
        towers = g.node('GeometryNodeInstanceOnPoints',label='Grounded skyline towers',Points=pts,Instance=cube,
                        Scale=g.vec(width,m('MULTIPLY',width,.8),height))
        geos.append(towers)
    with g.section('4 · Conservatory domes'):
        glass = basic('ConservatoryBlueGlass', (.045, .09, .18), .22, .55)
        p = next(n for n in glass.node_tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
        p.inputs['Emission Color'].default_value = (.04, .1, .23, 1)
        p.inputs['Emission Strength'].default_value = .45
        gridmat = basic('ConservatorySilverFrames', (.3, .4, .55), .3, .5)
        p = next(n for n in gridmat.node_tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
        p.inputs['Emission Color'].default_value = (.18, .36, .7, 1)
        p.inputs['Emission Strength'].default_value = 1.2
        dome = g.node('GeometryNodeMeshIcoSphere', Radius=1., Subdivisions=3)
        _, _, z = xyz(g, g.node('GeometryNodeInputPosition'))
        dome = g.node('GeometryNodeDeleteGeometry', props={'domain': 'POINT'}, Geometry=dome, Selection=m('LESS_THAN', z, 0))
        for x, y, sx, sy, sz in ((29., 133., 17., 21., 11.), (-2., 150., 22., 17., 9.)):
            d = transform(g, dome, loc=(x, y, 0), scale=(sx, sy, sz))
            geos.append(shade(g, d, glass))
            curves = g.node('GeometryNodeMeshToCurve', Mesh=d)
            geos.append(shade(g, tube(g, curves, .085, 4), gridmat))
        g.output(join(g, *geos))
    pb.arrange(g.tree)
    return ob


TREES = ((-12., 19., 40., 18.5, 0.), (22., 4., 48., 22., 2.0),
         (-31., 37., 29., 13.5, 2.9), (4., 43., 33., 14.5, 3.5),
         (34., 70., 28., 13., 4.05), (-12., 78., 25., 12., 3.8),
         (-49., 69., 26., 12.5, 3.5), (14., 98., 24., 11., 3.9),
         (51., 102., 24., 12., 4.0), (-36., 117., 23., 11., 3.6),
         (-56., 38., 30., 14., 3.2))


def point_light(name, loc, color, power, radius=2.):
    data = bpy.data.lights.new('PA_' + name, 'POINT')
    data.energy, data.color, data.shadow_soft_size = power, color, radius
    data.use_shadow = False
    data.volume_factor = 0.
    ob = bpy.data.objects.new('PA_' + name, data)
    bpy.data.collections['PA_' + NAME].objects.link(ob)
    ob.location = loc
    return ob


def area(name, loc, target, color, power, size):
    data = bpy.data.lights.new('PA_' + name, 'AREA')
    data.energy, data.color, data.shape, data.size = power, color, 'DISK', size
    data.volume_factor = 0.
    ob = bpy.data.objects.new('PA_' + name, data)
    bpy.data.collections['PA_' + NAME].objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target)-ob.location).to_track_quat('-Z', 'Y').to_euler()
    return ob


def world_and_lights():
    sc = bpy.context.scene
    world = bpy.data.worlds.new('PA_BlueHour')
    world.use_nodes = True
    sc.world = world
    world.node_tree.nodes.clear()
    g = pb.Graph(world.node_tree)
    out = g.node('ShaderNodeOutputWorld')
    v = g.out(g.node('ShaderNodeTexCoord'), 'Normal')
    x, y, z = xyz(g, v)
    horizon = m = g.math
    # World normal points inward; the upper sky is negative Z.
    ramp = g.node('ShaderNodeValToRGB', Fac=clamp(g, m('MULTIPLY', z, -1.35)))
    ramp.color_ramp.elements[0].position = 0.
    ramp.color_ramp.elements[0].color = (.10, .22, .44, 1)
    ramp.color_ramp.elements[1].position = 1.
    ramp.color_ramp.elements[1].color = (.016, .07, .20, 1)
    clouds = g.node('ShaderNodeTexNoise', Vector=g.vmath('MULTIPLY', v, (1.8, 1.8, 5.5)), Scale=3.2, Detail=4.)
    cloudfac = m('MULTIPLY', smooth(g, m('MULTIPLY', m('SUBTRACT', g.out(clouds, 'Factor'), .51), 5.)), .22)
    mixed = g.node('ShaderNodeMixRGB', Fac=cloudfac, Color1=ramp, Color2=(.12, .22, .38, 1))
    bg = g.node('ShaderNodeBackground', Color=mixed, Strength=.65)
    g.link(bg, out, b_key='Surface')
    pb.arrange(world.node_tree)
    area('CoolSkySoftbox', (-18, -5, 48), (0, 20, 15), (.43, .57, 1.), 8500, 55.)
    area('DuskRim', (35, 42, 30), (0, 20, 12), (.64, .70, 1.), 5000, 28.)
    area('PlazaFill', (-2, -20, 13), (0, 17, 2), (.57, .68, 1.), 1500, 24.)
    for j, (x, y, h, r, delay) in enumerate(TREES):
        fern_light = area(f'FernUplight_{j}', (x-3.5, y-4.5, 1.1), (x, y, h*.40), (1., .58, .14), 550, 2.)
        fern_light.data.use_shadow = j < 2
        color = (.8, .025, .55)
        light = area(f'CrownGlow_{j}', (x-4, y-6, h*.69), (x, y, h*.94), color, 4000, 9.)
        light.data.use_shadow = j < 2
        light.data.driver_add('energy').driver.expression = f'300+3700*min(1,max(0,((frame-1)/24-{delay}-1.0)/1.4))'
        warm_light = area(f'WarmLivingSkin_{j}', (x-2, y-5, h*.34), (x, y, h*.25), (1., .65, .20), 700, 4.)
        warm_light.data.use_shadow = j < 2
        pink_light = area(f'PinkLivingSkin_{j}', (x+1.8, y-3.8, h*.22), (x, y, h*.38), (.85, .015, .30), 450, 3.)
        pink_light.data.use_shadow = False
    # Local bridge spill lands on the wet plaza, independent of reflection visibility.
    for j, u in enumerate((.12, .32, .52, .72, .9)):
        p = bridge_point(u)
        point_light(f'SkywaySpill_{j}', (p[0], p[1], p[2]-.4), (1., .45, .10), 190, 1.2)


def camera():
    sc = bpy.context.scene
    data = bpy.data.cameras.new('PA_GardenCamera')
    ob = bpy.data.objects.new('PA_GardenCamera', data)
    bpy.data.collections['PA_' + NAME].objects.link(ob)
    ob.location = (1., -31., 10.)
    target = Vector((0., 20., 27.))
    ob.rotation_euler = (target-ob.location).to_track_quat('-Z', 'Y').to_euler()
    data.lens, data.sensor_width, data.clip_end = 24., 36., 1600.
    data.dof.use_dof = False
    sc.camera = ob
    for screen in bpy.data.screens:
        for ar in screen.areas:
            if ar.type == 'VIEW_3D':
                ar.spaces.active.region_3d.view_perspective = 'CAMERA'
                ar.spaces.active.overlay.show_overlays = False


def rain_mist():
    mat = bpy.data.materials.new('PA_LowRainMist')
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    g = pb.Graph(mat.node_tree)
    out = g.node('ShaderNodeOutputMaterial')
    pos = g.out(g.node('ShaderNodeNewGeometry'), 'Position')
    noise = g.node('ShaderNodeTexNoise', Vector=g.vmath('MULTIPLY', pos, (.12, .12, .45)), Scale=1., Detail=2.)
    _, _, z = xyz(g, pos)
    low = clamp(g, g.math('SUBTRACT', 1, g.math('DIVIDE', z, 10.)))
    density = g.math('MULTIPLY', .003, g.math('MULTIPLY', low, g.out(noise, 'Factor')))
    volume = g.node('ShaderNodeVolumePrincipled', Color=(.42, .52, .72, 1), Density=density, Anisotropy=.25)
    g.link(volume, out, b_key='Volume')
    pb.arrange(mat.node_tree)
    ob, g = pb.gn_object('LowRainMist', NAME)
    cube = g.node('GeometryNodeMeshCube', Size=(140, 105, 12))
    cube = transform(g, cube, loc=(0, 45, 5.5))
    g.output(pb.set_material(g, cube, mat))
    pb.arrange(g.tree)


def build():
    # This process is factory-startup; unrelated open Blender scenes are untouched.
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    pb.piece(NAME, aspect='1:1', width=960, fps=FPS, frames=FRAMES, engine='EEVEE', samples=48)
    sc = bpy.context.scene
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = .8
    sc.render.film_transparent = False
    sc.eevee.use_raytracing = True
    sc.eevee.taa_render_samples = 48
    mats = materials()
    plants = plant_group(mats['leaf'])
    trees = tree_group(mats, plants)
    for j, (x, y, h, r, delay) in enumerate(TREES):
        ob, g = pb.gn_object(f'Supertree_{j+1:02}', NAME)
        controls = {}
        for name, kind, value, lo, hi in (
            ('Height', 'float', h, 20, 60), ('Crown Radius', 'float', r, 6, 22),
            ('Ribs', 'int', 32, 16, 80), ('Plant Density', 'float', 8.0 if j<2 else 3.5, .1, 14),
            ('Lighting Delay', 'float', delay, 0, 5), ('Seed', 'int', 21+j*17, 0, 1000)):
            controls[name] = g.param(name, kind, value, lo, hi)
        with g.section('Supertree · one call, six controls'):
            geo = g.group(trees, **controls)
            g.output(geo)
        ob.location = (x, y, 0)
        pb.arrange(g.tree)
    make_bridge(mats)
    people = person_group(mats)
    landscape(mats, plants, people)
    garden_and_city(mats)
    rain_mist()
    world_and_lights()
    camera()
    pb.post(bloom=.10, fog=.055, threshold=1.8)
    sc.frame_set(HERO)
    sc['concept'] = 'Violet-white light bowls open above a dense living garden, joined by a rising suspended skyway.'
    sc['reference_revision'] = 'Matched to the user reference: broad flat crowns, luminous segmented bowls, dark radial ribs, layered grove, diagonal skyway.'
    sc['reference'] = 'https://www.gardensbythebay.com.sg/en/things-to-do/attractions/supertree-grove.html'
    sc['constraint'] = 'All artwork geometry generated by Geometry Nodes; no imported assets, image textures, simulation, or keyframes.'
    sc['animation'] = 'One-shot awakening, 8 seconds at 24 fps; the ending holds, not a seamless loop.'
    pb.output(str(HERE/'frames'/'####'), 'png')
    audit = pb.audit(NAME)
    (HERE/'checks'/'audit.json').write_text(json.dumps(audit, indent=2))
    pb.save(str(HERE/'piece.blend'))
    print('SUPERTREE_BUILD_OK', json.dumps(audit))
    return sc


def shape_preview():
    """Side view of the actual light skin, isolated from the scene for QA."""
    sc = bpy.context.scene
    t = bpy.data.node_groups['PA_SupertreeArchitecture']
    out = next(n for n in t.nodes if n.bl_idname == 'NodeGroupOutput')
    skin = next(n for n in t.nodes if n.label == 'Curved luminous skin')
    old = out.inputs['Geometry'].links[0].from_socket
    t.links.new(skin.outputs['Geometry'], out.inputs['Geometry'])
    for ob in sc.objects:
        if ob.type == 'MESH' and ob.name != 'PA_Supertree_01':
            ob.hide_render = True
    camera = sc.camera
    camera.location = (-12, -81, 31)
    camera.rotation_euler = (Vector((-12, 19, 31))-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 39.
    sc.render.resolution_x, sc.render.resolution_y = 1040, 780
    sc.render.resolution_percentage = 100
    pb.render_still(str(HERE/'inspect'/'shape-side.png'), frame=HERO, samples=48)
    t.links.new(old, out.inputs['Geometry'])
    bpy.context.view_layer.update()
    camera.data.ortho_scale = 45.
    pb.render_still(str(HERE/'inspect'/'crown-side.png'), frame=HERO, samples=48)


def structure_preview():
    """Inspect the actual connected frame and two neighbouring branching modules."""
    sc = bpy.context.scene
    t = bpy.data.node_groups['PA_SupertreeArchitecture']
    out = next(n for n in t.nodes if n.bl_idname == 'NodeGroupOutput')
    frame = next(n for n in t.nodes if n.label == 'Connected branching framework')
    old = out.inputs['Geometry'].links[0].from_socket
    t.links.new(frame.outputs['Geometry'], out.inputs['Geometry'])
    for ob in sc.objects:
        if ob.type in ('MESH', 'LIGHT'):
            ob.hide_render = ob.name != 'PA_Supertree_01'
    clay = basic('FrameworkInspectionSilver', (.28, .32, .38), .42, .25)
    sc.view_layers[0].material_override = clay
    area('InspectionKey', (-22, -15, 55), (-12, 19, 33), (1., .94, .86), 26000, 25.)
    area('InspectionFill', (15, 30, 48), (-12, 19, 33), (.62, .76, 1.), 18000, 20.)
    camera = sc.camera
    camera.location = (-40, -45, 45)
    camera.rotation_euler = (Vector((-12, 19, 33))-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 45.
    sc.render.resolution_x, sc.render.resolution_y = 1200, 900
    sc.render.resolution_percentage = 100
    pb.render_still(str(HERE/'inspect'/'structure.png'), frame=HERO, samples=48)
    t.links.new(frame.outputs['Bay'], out.inputs['Geometry'])
    bpy.context.view_layer.update()
    camera.location = (30, -24, 55)
    camera.rotation_euler = (Vector((-1, 19, 32))-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = 23.
    pb.render_still(str(HERE/'inspect'/'structure-bay.png'), frame=HERO, samples=48)
    t.links.new(old, out.inputs['Geometry'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--hero', action='store_true')
    parser.add_argument('--shape', action='store_true')
    parser.add_argument('--structure', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    sc = build()
    if args.preview:
        print(pb.preview(str(HERE/'preview.png'), scale=65, samples=24, frame=HERO))
    if args.hero:
        sc.render.resolution_x = sc.render.resolution_y = 1440
        print(pb.render_still(str(HERE/'render.png'), frame=HERO, samples=96))
    if args.shape:
        shape_preview()
    if args.structure:
        structure_preview()


if __name__ == '__main__':
    main()
