"""Fingertip / 指尖 — Nodevember 2026, Day 8: Mycelium (v5).

A weathered stone hand rises out of a mossy forest floor, pointing one finger at the sky. White hyphae creep
out of the soil and climb the stone, cords gather up the raised finger, a hyphal knot swells on its tip, and a
bonnet mushroom (the v4 Bonnet) grows there and sheds spores into the back light.

The hand is a skeleton of bones (one chain of three bones and three curls per finger) turned into stone by
Points to SDF Grid. One growth clock (Scene Time) drives a schedule of Float Curves, one per process.

All geometry from Geometry Nodes on empty objects. No simulation, image textures or imported assets.
Units: 1 = 1 cm.

Blender -b --factory-startup --python build.py -- --preview [--frame F]
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _lib in (HERE.parents[1] / 'lib', ROOT / '.agents/skills/procedural-art/scripts'):  # public repo, monorepo
    if (_lib / 'proc_blender.py').exists():
        sys.path.insert(0, str(_lib))
        break
import proc_blender as pb

TAU = math.tau
NAME = 'Fingertip'
F_END = 360
F_GROW = 300                 # growth clock T reaches 1 here, then hold
SUN_DIR = Vector((0.45, -0.78, -0.43)).normalized()     # the way sunlight travels: low (25°), from behind the hand, a little left
CANOPY_Z = 150.0                                    # shadow-only leaf canopy that dapples the sun

# growth schedule: (name, points (T, value), linear)
GROWTH = [
    ('Colony', [(0, 0), (0.02, 0), (0.40, 1), (1, 1)], True),
    ('Cords', [(0, 0), (0.30, 0), (0.50, 1), (1, 1)], False),
    ('Knot', [(0, 0), (0.40, 0), (0.50, 1), (0.60, 0.7), (1, 0.7)], False),
    ('Pin', [(0, 0), (0.46, 0), (0.56, 1), (1, 1)], False),
    ('Stem', [(0, 0), (0.53, 0), (0.64, 0.36), (0.76, 0.86), (0.84, 1), (1, 1)], False),
    ('Cap', [(0, 0), (0.55, 0), (0.70, 0.42), (0.88, 1), (1, 1)], False),
    ('Open', [(0, 0), (0.70, 0), (0.80, 0.45), (0.92, 1), (1, 1)], False),
    ('Sway', [(0, 0), (0.54, 0), (0.66, 1), (0.88, 1), (0.97, 0.25), (1, 0.25)], False),
    ('Spores', [(0, 0), (0.88, 0), (1, 1)], True),
]


# ───────────────────────────────────────────── graph helpers

def group(name, inputs, outputs, kind='GeometryNodeTree'):
    tree = bpy.data.node_groups.new('PA_' + name, kind)
    for label, kind, default in inputs:
        sock = tree.interface.new_socket(label, in_out='INPUT', socket_type=pb._STYPE[kind])
        if default is not None:
            sock.default_value = default
    for label, kind in outputs:
        tree.interface.new_socket(label, in_out='OUTPUT', socket_type=pb._STYPE[kind])
    g = pb.Graph(tree)
    gin, gout = g.group_io()
    return tree, g, gin, gout


def attr(g, name, kind='FLOAT'):
    return g.out(g.node('GeometryNodeInputNamedAttribute', label=name, props={'data_type': kind}, Name=name),
                 'Attribute')


def store(g, geo, name, value, domain='POINT', kind='FLOAT'):
    return g.node('GeometryNodeStoreNamedAttribute', label=name, props={'data_type': kind, 'domain': domain},
                  Geometry=geo, Name=name, Value=value)


def join(g, *geos):
    node = g.node('GeometryNodeJoinGeometry')
    for geo in reversed(geos):
        g.link(geo, node, b_key='Geometry')
    return node


def rand(g, ident, seed, lo=0., hi=1.):
    return g.out(g.node('FunctionNodeRandomValue', props={'data_type': 'FLOAT'}, Min=lo, Max=hi,
                        ID=ident, Seed=seed), 'Value')


def lab(node, text):
    """Name a node in the editor (the label the tutorial quotes); a socket names the node it belongs to."""
    getattr(node, 'node', node).label = text
    return node


def clamp(g, v, lo=0., hi=1.):
    return g.math('MINIMUM', g.math('MAXIMUM', v, lo), hi)


def smoothstep(g, e0, e1, v):
    t = clamp(g, g.math('DIVIDE', g.math('SUBTRACT', v, e0), g.math('SUBTRACT', e1, e0)))
    return g.math('MULTIPLY', g.math('MULTIPLY', t, t), g.math('SUBTRACT', 3., g.math('MULTIPLY', 2., t)))


def mix(g, a, b, t):
    return g.math('ADD', a, g.math('MULTIPLY', g.math('SUBTRACT', b, a), t))


def vmix(g, a, b, t):
    return g.vmath('ADD', a, g.vmath('SCALE', g.vmath('SUBTRACT', b, a), scale=t))


def noise(g, vec, scale=1., detail=2., rough=.5, out='Factor'):
    return g.out(g.node('ShaderNodeTexNoise', Vector=vec, Scale=scale, Detail=detail, Roughness=rough), out)


def xyz(g, v):
    s = g.node('ShaderNodeSeparateXYZ', Vector=v)
    return g.out(s, 'X'), g.out(s, 'Y'), g.out(s, 'Z')


def pos(g):
    return g.node('GeometryNodeInputPosition')


def idx(g):
    return g.node('GeometryNodeInputIndex')


def safe(g, k):
    tiny = g.math('LESS_THAN', g.math('ABSOLUTE', k), 1e-4)
    return g.math('ADD', k, g.math('MULTIPLY', tiny, 1e-4))


def fcurve(g, x, pts, label, linear=False):
    n = g.node('ShaderNodeFloatCurve', label=label, Value=x)
    cm = n.mapping
    c = cm.curves[0]
    while len(c.points) > 2:
        c.points.remove(c.points[-1])
    c.points[0].location, c.points[1].location = pts[0], pts[1]
    for p in pts[2:]:
        c.points.new(*p)
    for p in c.points:
        p.handle_type = 'VECTOR' if linear else 'AUTO_CLAMPED'
    cm.update()
    return n


def delete(g, geo, sel, domain='POINT'):
    return g.node('GeometryNodeDeleteGeometry', props={'domain': domain, 'mode': 'ALL'}, Geometry=geo, Selection=sel)


def grid(g, nx, ny):
    m = g.node('GeometryNodeMeshGrid', Size_X=1.0, Size_Y=1.0, Vertices_X=nx, Vertices_Y=ny)
    px, py, _ = xyz(g, pos(g))
    m = store(g, m, 'a', g.math('ADD', px, 0.5))
    return store(g, m, 'b', g.math('ADD', py, 0.5))


def polar(g, r, phi, z):
    return g.vec(g.math('MULTIPLY', r, g.math('COSINE', phi)), g.math('MULTIPLY', r, g.math('SINE', phi)), z)


def realize(g, geo):
    return g.node('GeometryNodeRealizeInstances', Geometry=geo)


def drop_stubs(g, cur):
    """Delete curves left with < 2 points or ~0 length (they crash the Metal hair BVH)."""
    sl = g.node('GeometryNodeSplineLength')
    bad = g.math('MAXIMUM', g.math('LESS_THAN', g.out(sl, 'Point Count'), 2.0), g.math('LESS_THAN', g.out(sl, 'Length'), 1e-4))
    return g.node('GeometryNodeDeleteGeometry', props={'domain': 'CURVE', 'mode': 'ALL'}, Geometry=cur, Selection=bad)


# ───────────────────────────────────────────── shared groups

def ground_group():
    """Forest-floor height z(x, y): broad swells plus small lumps."""
    tree, g, gin, gout = group('GroundZ', [('P', 'vector', (0, 0, 0))], [('Z', 'float')])
    px, py, _ = xyz(g, g.out(gin, 'P'))
    p = g.vec(px, py, 0.0)
    def f(q):
        big = g.math('MULTIPLY', g.math('SUBTRACT', noise(g, q, 0.10, detail=2.0), 0.5), 1.4)
        small = g.math('MULTIPLY', g.math('SUBTRACT', noise(g, q, 1.1, detail=3.0, rough=0.55), 0.5), 0.16)
        return g.math('ADD', big, small)

    g.link(g.math('SUBTRACT', f(p), f(g.vec(0, 0, 0))), gout, b_key='Z')     # zero at the stem
    pb.arrange(tree)
    return tree


def growth_group():
    """Growth clock T (Scene Time) → one Float Curve per process."""
    tree, g, gin, gout = group('Growth', [], [('T', 'float'), ('Tu', 'float')] + [(n, 'float') for n, _, _ in GROWTH])
    with g.section('a · Clock'):
        st = g.node('GeometryNodeInputSceneTime')
        Tu = lab(g.math('DIVIDE', g.math('SUBTRACT', g.out(st, 'Frame'), 1.0), float(F_GROW - 1)), 'Tu: unclamped clock')
        T = lab(clamp(g, Tu), 'T: growth clock 0 → 1')
        g.link(T, gout, b_key='T')
        g.link(Tu, gout, b_key='Tu')          # keeps running through the hold (spores, sway)
    with g.section('b · One curve per process'):
        for name, pts, lin in GROWTH:
            g.link(fcurve(g, T, pts, name, lin), gout, b_key=name)
    pb.arrange(tree)
    return tree



def cap_group():
    """Cap = an arc of two curvatures that unbends as it inflates, with a small umbo and a margin
    scalloped by the gills. S: 0 centre → 1 margin (arc fraction), Phi: angle."""
    ins = [('S', 'float', 0.0), ('Phi', 'float', 0.0), ('L', 'float', 1.0), ('Th1', 'float', 1.0),
           ('Th2', 'float', 1.0), ('Tc', 'float', 0.1), ('Scallop', 'float', 0.03)]
    tree, g, gin, gout = group('Cap', ins, [('Top', 'vector'), ('Normal', 'vector'), ('Bottom', 'vector')])
    S, phi, L = g.out(gin, 'S'), g.out(gin, 'Phi'), g.out(gin, 'L')
    sec = g.section('a · Arc of two curvatures')
    sec.__enter__()
    s0 = lab(g.math('MULTIPLY', L, 0.45), 'centre part: 45 % of L')
    k1 = safe(g, g.math('DIVIDE', g.out(gin, 'Th1'), s0))
    k2 = safe(g, g.math('DIVIDE', g.out(gin, 'Th2'), g.math('MULTIPLY', L, 0.55)))
    s = g.math('MULTIPLY', S, L)
    s1 = g.math('MINIMUM', s, s0)
    s2 = g.math('MAXIMUM', g.math('SUBTRACT', s, s0), 0.0)
    ta = g.math('MULTIPLY', k1, s1)
    x1 = g.math('DIVIDE', g.math('SINE', ta), k1)
    z1 = g.math('DIVIDE', g.math('SUBTRACT', g.math('COSINE', ta), 1.0), k1)
    th = lab(g.math('ADD', ta, g.math('MULTIPLY', k2, s2)), 'bend angle θ')
    x = lab(g.math('ADD', x1, g.math('DIVIDE', g.math('SUBTRACT', g.math('SINE', th), g.math('SINE', ta)), k2)), 'arc: radius r')
    z = lab(g.math('ADD', z1, g.math('DIVIDE', g.math('SUBTRACT', g.math('COSINE', th), g.math('COSINE', ta)), k2)), 'arc: height z')
    sec.__exit__(None, None, None)
    sec = g.section('b · Umbo and scalloped margin')
    sec.__enter__()
    # umbo: a small central boss
    z = g.math('ADD', z, g.math('MULTIPLY', g.math('MULTIPLY', L, 0.07),
                                g.math('EXPONENT', g.math('MULTIPLY', -1.0, g.math('POWER', g.math('DIVIDE', S, 0.2), 2.0)))))
    # margin: gentle lobes (noise on the circle) and scallops between 20 gills
    ring = g.vec(g.math('COSINE', phi), g.math('SINE', phi), 0.0)
    lob = g.math('SUBTRACT', noise(g, g.vmath('SCALE', ring, scale=1.3), 1.0, detail=1.0), 0.5)
    sc = g.math('SUBTRACT', 1.0, g.math('ABSOLUTE', g.math('COSINE', g.math('MULTIPLY', phi, 10.0))))
    edge = g.math('POWER', S, 6.0)
    x = lab(g.math('MULTIPLY', x, g.math('SUBTRACT', g.math('ADD', 1.0, g.math('MULTIPLY', g.math('MULTIPLY', lob, 0.10), g.math('MULTIPLY', S, S))),
                                     g.math('MULTIPLY', g.math('MULTIPLY', sc, g.out(gin, 'Scallop')), edge))), 'r: lobes, scallops')
    z = lab(g.math('SUBTRACT', z, g.math('MULTIPLY', g.math('MULTIPLY', sc, g.math('MULTIPLY', g.out(gin, 'Scallop'), 1.5)), edge)), 'z: umbo, scallops')
    sec.__exit__(None, None, None)
    sec = g.section('c · Surface, normal, thickness')
    sec.__enter__()
    top = lab(polar(g, x, phi, z), 'top surface')
    nrm = lab(polar(g, g.math('SINE', th), phi, g.math('COSINE', th)), 'normal')
    t = g.math('MULTIPLY', g.out(gin, 'Tc'), g.math('MULTIPLY', g.math('SQRT', g.math('MAXIMUM', g.math('SUBTRACT', 1.0, g.math('MULTIPLY', S, S)), 0.0)),
                                                    g.math('SUBTRACT', 1.0, g.math('MULTIPLY', 0.5, S))))
    g.link(top, gout, b_key='Top')
    g.link(nrm, gout, b_key='Normal')
    g.link(g.vmath('SUBTRACT', top, g.vmath('SCALE', nrm, scale=t)), gout, b_key='Bottom')
    sec.__exit__(None, None, None)
    pb.arrange(tree)
    return tree


# ───────────────────────────────────────────── the stone hand (local frame: life size, palm towards −y, fingers up +z)

HS = 1.4                        # hand scale: 1.4 × life size
HROT = math.radians(-7.0)       # turned about z: the palm faces the camera (local +y is the back of the hand, +x the thumb side)
HZ = 3.5                        # local height of the soil line: the hand rises out of the moss from mid-palm


def fit_chain(joints):
    """Base, Up, Fwd, bone lengths and curls of a planar chain through four joints (for the thumb)."""
    J = [Vector(p) for p in joints]
    d = [(J[k + 1] - J[k]) for k in range(3)]
    up = d[0].normalized()
    n = d[0].cross(d[1] + d[2]).normalized()
    fwd = n.cross(up).normalized()
    if fwd.dot(d[1] + d[2]) < 0:
        fwd = -fwd
    ang = [math.atan2(v.dot(fwd), v.dot(up)) for v in d]
    return (tuple(J[0]), tuple(up), tuple(fwd), tuple(v.length for v in d),
            (ang[0], ang[1] - ang[0], ang[2] - ang[1]))


# the thumb by its joints: wrist, knuckle, middle joint, tip, its last bone lying across the curled middle finger
THUMB = ((2.2, -1.0, 1.6), (3.5, -3.6, 5.6), (2.4, -5.8, 7.7), (0.3, -5.9, 8.3))
# name, knuckle, up, bend direction (towards the palm), bone lengths, curls (rad, per joint), radius at knuckle / tip
FINGERS = [
    ('index: pointing up', (2.9, 0.0, 9.4), (0, 0, 1), (0, -1, 0), (4.0, 2.3, 1.75), (-0.06, 0.10, 0.07), (1.22, 1.0)),
    ('middle: curled', (0.95, 0.0, 9.8), (0, 0, 1), (0, -1, 0), (4.3, 2.7, 1.9), (1.5, 1.7, 1.05), (1.2, 0.97)),
    ('ring: curled', (-0.95, 0.0, 9.5), (0, 0, 1), (0, -1, 0), (4.0, 2.6, 1.8), (1.5, 1.7, 1.05), (1.15, 0.93)),
    ('little: curled', (-2.75, 0.0, 8.8), (0, 0, 1), (0, -1, 0), (3.2, 2.0, 1.65), (1.45, 1.7, 1.05), (1.02, 0.84)),
    ('thumb: folded over the middle finger',)
    + fit_chain(THUMB) + ((1.55, 1.12),),
]


def chain_py(base, up, fwd, L, C):
    """Python twin of PA_Finger: the four joints of a finger and the last bone's direction."""
    up, fwd = Vector(up), Vector(fwd)
    pts, p, a = [Vector(base)], Vector(base), 0.0
    for length, c in zip(L, C):
        a += c
        p = p + (up * math.cos(a) + fwd * math.sin(a)) * length
        pts.append(p)
    return pts, up * math.cos(a) + fwd * math.sin(a)


def hand_world(p):
    v = Vector(p)
    v.z -= HZ
    v = v * HS
    v.rotate(Euler((0.0, 0.0, HROT)))
    return v


_j, _d = chain_py(*FINGERS[0][1:6])
FINGERTIP = hand_world(_j[-1] + _d * FINGERS[0][6][1])     # top of the raised finger, where the mushroom rises


def palm_side(g, up, fwd, a):
    """Perpendicular to a bone turned by a, towards the palm."""
    return g.vmath('SUBTRACT', g.vmath('SCALE', fwd, scale=g.math('COSINE', a)), g.vmath('SCALE', up, scale=g.math('SINE', a)))


def bone_group():
    """Flesh of one finger bone: 44 spheres from joint to joint, slimmer mid-bone, the pad shifted towards the palm."""
    ins = [('Start', 'vector', (0, 0, 0)), ('End', 'vector', (0, 0, 1)), ('R Start', 'float', 1.0), ('R End', 'float', 1.0),
           ('Up', 'vector', (0, 0, 1)), ('Fwd', 'vector', (0, -1, 0)), ('Angle', 'float', 0.0)]
    tree, g, gin, gout = group('Bone', ins, [('Points', 'geometry')])
    o = lambda n: g.out(gin, n)
    with g.section('a · Spheres along the bone'):
        line = g.node('GeometryNodeResampleCurve', label='44 spheres', Count=44,
                      Curve=g.node('GeometryNodeCurvePrimitiveLine', Start=o('Start'), End=o('End')))
        t = g.out(g.node('GeometryNodeSplineParameter'), 'Factor')
        mid = lab(g.math('SINE', g.math('MULTIPLY', t, math.pi)), 'mid-bone: sin(πt)')
        r = lab(g.math('MULTIPLY', mix(g, o('R Start'), o('R End'), t), g.math('SUBTRACT', 1.0, g.math('MULTIPLY', 0.07, mid))),
                'radius: 7 % slimmer mid-bone')
        line = g.node('GeometryNodeSetCurveRadius', Curve=line, Radius=r)
    with g.section('b · Pad on the palm side'):
        # the pad: the middle of each bone shifts towards the palm, so the back stays flat and the joints show
        pad = lab(g.vmath('SCALE', palm_side(g, o('Up'), o('Fwd'), o('Angle')),
                          scale=g.math('MULTIPLY', g.math('MULTIPLY', r, 0.12), mid)), 'pad: 0.12 r towards the palm')
        line = g.node('GeometryNodeSetPosition', Geometry=line, Offset=pad)
        g.link(g.out(g.node('GeometryNodeCurveToPoints', props={'mode': 'EVALUATED'}, Curve=line), 'Points'), gout, b_key='Points')
    pb.arrange(tree)
    return tree


def knuckle_group():
    """Where a joint bends, the head of the bone pushes out on the back of the finger (hardly at all on a straight joint)."""
    ins = [('Joint', 'vector', (0, 0, 0)), ('Angle Before', 'float', 0.0), ('Angle After', 'float', 0.0), ('R', 'float', 1.0),
           ('Up', 'vector', (0, 0, 1)), ('Fwd', 'vector', (0, -1, 0))]
    tree, g, gin, gout = group('Knuckle', ins, [('Points', 'geometry')])
    o = lambda n: g.out(gin, n)
    flex = lab(g.math('MINIMUM', g.math('MAXIMUM', g.math('SUBTRACT', o('Angle After'), o('Angle Before')), 0.0), 1.3),
               'flex: how far the joint bends')
    bis = lab(g.math('MULTIPLY', g.math('ADD', o('Angle Before'), o('Angle After')), 0.5), 'halfway angle')
    out = lab(g.math('MULTIPLY', o('R'), g.math('ADD', 0.25, g.math('MULTIPLY', 0.22, flex))), 'out: (0.25 + 0.22 flex) R')
    p = g.vmath('SUBTRACT', o('Joint'), g.vmath('SCALE', palm_side(g, o('Up'), o('Fwd'), bis), scale=out))
    k = lab(g.node('GeometryNodePoints', Count=1, Position=p, Radius=g.math('MULTIPLY', o('R'), 0.6)), 'one sphere on the back')
    g.link(k, gout, b_key='Points')
    pb.arrange(tree)
    return tree


def finger_group(bone, knuckle):
    """One finger: three bones from the knuckle, each turned by its curl in the (Up, Fwd) plane. Spheres along each bone
    (an oval section, slimmer mid-bone, a pad on the palm side) and a bony knuckle wherever a joint bends."""
    ins = [('Base', 'vector', (0, 0, 0)), ('Up', 'vector', (0, 0, 1)), ('Fwd', 'vector', (0, -1, 0)),
           ('L1', 'float', 4.0), ('L2', 'float', 2.5), ('L3', 'float', 2.0),
           ('C1', 'float', 0.0), ('C2', 'float', 0.0), ('C3', 'float', 0.0), ('R0', 'float', 1.0), ('R1', 'float', 0.8)]
    tree, g, gin, gout = group('Finger', ins, [('Points', 'geometry')])
    o = lambda n: g.out(gin, n)
    up, fwd = o('Up'), o('Fwd')

    def along(a):                    # direction of a bone turned by a
        return g.vmath('ADD', g.vmath('SCALE', up, scale=g.math('COSINE', a)), g.vmath('SCALE', fwd, scale=g.math('SINE', a)))

    with g.section('a · Three bones, three curls'):
        A = [0.0, o('C1')]
        A.append(lab(g.math('ADD', A[1], o('C2')), 'angle of bone 2'))
        A.append(lab(g.math('ADD', A[2], o('C3')), 'angle of bone 3'))
        J = [o('Base')]
        for k, L in ((1, 'L1'), (2, 'L2'), (3, 'L3')):
            J.append(lab(g.vmath('ADD', J[-1], g.vmath('SCALE', along(A[k]), scale=o(L))), 'joint %d' % k))
        R = [o('R0'), lab(mix(g, o('R0'), o('R1'), 0.45), 'radius at joint 1'), lab(mix(g, o('R0'), o('R1'), 0.75), 'radius at joint 2'), o('R1')]
        side = lab(g.vmath('NORMALIZE', g.vmath('CROSS_PRODUCT', up, fwd)), 'side')
    with g.section('b · Flesh'):
        bones = [g.out(lab(g.group(bone, Start=J[k - 1], End=J[k], R_Start=R[k - 1], R_End=R[k], Up=up, Fwd=fwd, Angle=A[k]),
                           'bone %d' % k), 'Points') for k in (1, 2, 3)]
        pts = join(g, *bones)
        # an oval section: two rows side by side, a little smaller
        sw = lab(g.vmath('SCALE', side, scale=g.math('MULTIPLY', g.node('GeometryNodeInputRadius'), 0.18)), 'sideways 0.18 r')
        pts = join(g, g.node('GeometryNodeSetPosition', Geometry=pts, Offset=sw),
                   g.node('GeometryNodeSetPosition', Geometry=pts, Offset=g.vmath('SCALE', sw, scale=-1.0)))
        pts = lab(g.node('GeometryNodeSetPointRadius', Points=pts,
                         Radius=g.math('MULTIPLY', g.node('GeometryNodeInputRadius'), 0.88)), 'oval section')
    with g.section('c · Knuckles'):
        knuckles = [g.out(lab(g.group(knuckle, Joint=J[k], Angle_Before=A[k], Angle_After=A[k + 1], R=R[k], Up=up, Fwd=fwd),
                              'knuckle %d' % k), 'Points') for k in (0, 1, 2)]
        g.link(join(g, pts, *knuckles), gout, b_key='Points')
    pb.arrange(tree)
    return tree


def capsule_group():
    """Spheres along a segment A → B, radius R0 → R1, Count of them: every bone and muscle of the palm is one."""
    ins = [('A', 'vector', (0, 0, 0)), ('B', 'vector', (0, 0, 1)), ('R0', 'float', 1.0), ('R1', 'float', 1.0), ('Count', 'int', 40)]
    tree, g, gin, gout = group('Capsule', ins, [('Points', 'geometry')])
    o = lambda n: g.out(gin, n)
    line = g.node('GeometryNodeResampleCurve', Count=2, Curve=g.node('GeometryNodeCurvePrimitiveLine', Start=o('A'), End=o('B')))
    line = g.node('GeometryNodeSetCurveRadius', Curve=line,
                  Radius=lab(mix(g, o('R0'), o('R1'), g.out(g.node('GeometryNodeSplineParameter'), 'Factor')), 'radius R0 → R1'))
    line = g.node('GeometryNodeResampleCurve', Count=o('Count'), Curve=line)
    g.link(g.out(g.node('GeometryNodeCurveToPoints', props={'mode': 'EVALUATED'}, Curve=line), 'Points'), gout, b_key='Points')
    pb.arrange(tree)
    return tree


def nail_group():
    """A fingernail on the last bone of a finger: a slightly raised plate in a groove, as a displacement along the normal.
    Works in the hand's own frame (LP), so it stays put however the hand is turned."""
    ins = [('LP', 'vector', (0, 0, 0)), ('Tip Joint', 'vector', (0, 0, 0)), ('Along', 'vector', (0, 0, 1)),
           ('Side', 'vector', (1, 0, 0)), ('Back', 'vector', (0, 1, 0)), ('R', 'float', 1.0)]
    tree, g, gin, gout = group('Nail', ins, [('Offset', 'float')])
    o = lambda n: g.out(gin, n)
    R = o('R')
    with g.section('a · Outline'):
        q = g.vmath('SUBTRACT', o('LP'), o('Tip Joint'))
        u = lab(g.vmath('DOT_PRODUCT', q, o('Along')), 'u: along the bone, 0 at the last joint')
        v = lab(g.math('ABSOLUTE', g.vmath('DOT_PRODUCT', q, o('Side'))), 'v: across')
        w = lab(g.vmath('DOT_PRODUCT', q, o('Back')), 'w: towards the back')
        box = lab(g.math('MAXIMUM', g.math('MAXIMUM', g.math('SUBTRACT', g.math('MULTIPLY', R, -1.45), u),
                                                    g.math('SUBTRACT', u, g.math('MULTIPLY', R, 0.42))),
                         g.math('SUBTRACT', v, g.math('MULTIPLY', R, 0.52))), 'box: < 0 inside the nail')
    with g.section('b · Plate and groove'):
        on_back = lab(smoothstep(g, 0.15, 0.45, g.math('DIVIDE', w, R)), 'on the back only')
        groove = lab(g.math('EXPONENT', g.math('MULTIPLY', -1.0, g.math('POWER', g.math('DIVIDE', box, 0.05), 2.0))), 'groove at the outline')
        plate = lab(smoothstep(g, 0.0, -0.08, box), 'plate inside')
        g.link(g.math('MULTIPLY', on_back, g.math('SUBTRACT', g.math('MULTIPLY', plate, 0.02), g.math('MULTIPLY', groove, 0.035))),
               gout, b_key='Offset')
    pb.arrange(tree)
    return tree


def capsule(g, G, a, b, r0, r1, n, label=None):
    node = g.group(G['capsule'], A=a, B=b, R0=r0, R1=r1, Count=n)
    if label:
        node.label = label
    return g.out(node, 'Points')


def nail(g, G, lp, finger):
    """The nail group, placed on the last bone of a chain (its joint, direction and back from the Python twin)."""
    _, base, up, fwd, L, C, R = finger
    J, d = chain_py(base, up, fwd, L, C)
    a = sum(C)
    up, fwd = Vector(up), Vector(fwd)
    back = up * math.sin(a) - fwd * math.cos(a)               # the back of the last bone
    side = up.cross(fwd).normalized()
    return g.out(lab(g.group(G['nail'], LP=lp, Tip_Joint=tuple(J[3]), Along=tuple(d), Side=tuple(side), Back=tuple(back), R=R[1]),
                     'nail: ' + finger[0].split(':')[0]), 'Offset')


def build_hand(piece, G, M):
    ob, g = pb.gn_object('Hand', piece)
    with g.section('1 · Fingers'):
        parts = []
        for label, base, up, fwd, L, C, R in FINGERS:
            n = g.group(G['finger'], Base=base, Up=up, Fwd=fwd, L1=L[0], L2=L[1], L3=L[2],
                        C1=C[0], C2=C[1], C3=C[2], R0=R[0], R1=R[1])
            n.label = label
            parts.append(g.out(n, 'Points'))
    with g.section('2 · Palm and wrist'):
        # a slab, domed on the back and rounder at its edges, narrower towards the wrist
        pg = g.node('GeometryNodeMeshGrid', Size_X=5.4, Size_Y=7.0, Vertices_X=15, Vertices_Y=19)
        px, py, _ = xyz(g, pos(g))
        edge = g.math('MAXIMUM', g.math('ABSOLUTE', g.math('DIVIDE', px, 2.7)), g.math('ABSOLUTE', g.math('DIVIDE', py, 3.5)))
        taper = lab(g.math('ADD', 0.80, g.math('MULTIPLY', 0.20, g.math('DIVIDE', g.math('ADD', py, 3.5), 7.0))), 'narrower at the wrist')
        dome = lab(g.math('MULTIPLY', -0.8, g.math('POWER', g.math('DIVIDE', px, 2.7), 2.0)), 'domed back')
        pg = g.node('GeometryNodeSetPosition', Geometry=pg,
                    Position=g.vec(g.math('MULTIPLY', px, taper), dome, g.math('ADD', py, 5.0)))
        slab = g.node('GeometryNodeSetPointRadius', Points=g.out(g.node('GeometryNodeMeshToPoints', Mesh=pg), 'Points'),
                      Radius=mix(g, 1.45, 0.95, g.math('POWER', edge, 2.0)))
        parts.append(lab(slab, 'palm'))
        for (label, knuckle, *_), carpal in zip(FINGERS[:4], ((1.5, 0.1, 1.2), (0.5, 0.15, 1.0), (-0.5, 0.15, 1.0), (-1.4, 0.1, 1.3))):
            parts.append(capsule(g, G, carpal, knuckle, 0.9, 1.0, 90, 'palm bone: ' + label.split(':')[0]))
        # wrist and forearm, sunk into the soil
        wrist = [capsule(g, G, (x, 0.2, 1.8), (x * 1.15, 0.6, -9.0), r, r * 1.15, 160, 'wrist and forearm')
                 for x, r in ((-1.2, 1.8), (0.0, 2.1), (1.2, 1.8))]
    with g.section('3 · Muscle and fist'):
        # muscle: the ball of the thumb, the edge below the little finger, the mound between thumb and index
        parts.append(capsule(g, G, (1.5, -1.3, 1.0), (3.0, -2.6, 4.6), 1.6, 1.25, 60, 'ball of the thumb'))
        parts.append(capsule(g, G, (-0.4, -0.75, 1.6), (0.4, -0.8, 5.6), 1.2, 1.1, 40, 'hollow of the palm'))
        parts.append(capsule(g, G, (-1.7, -0.55, 1.4), (-2.3, -0.6, 6.8), 1.3, 1.1, 60, 'edge of the little finger'))
        # the web between thumb and index: flesh strung from the thumb's long bone to the index's
        web = []
        for t in (0.25, 0.34, 0.43, 0.52, 0.61, 0.7, 0.79, 0.88, 0.95, 1.0):
            a = Vector(THUMB[0]).lerp(Vector(THUMB[1]), t)
            b = Vector((1.5, 0.1, 1.2)).lerp(Vector(FINGERS[0][1]), 0.2 + 0.65 * t)
            web.append(capsule(g, G, tuple(a), tuple(b), 1.1, 0.95, 40))
        parts.append(lab(join(g, *web), 'web of the thumb'))
        # a carved fist is solid: fill the hollow inside the curled fingers
        parts.append(capsule(g, G, (-2.6, -2.6, 8.0), (1.4, -2.7, 8.3), 1.25, 1.25, 60, 'inside the fist'))
        parts.append(capsule(g, G, (-2.4, -2.3, 6.8), (1.2, -2.4, 7.0), 1.05, 1.05, 50, 'inside the fist, lower'))
        pts = lab(join(g, *(parts + wrist)), 'the whole skeleton')
    with g.section('4 · Stone'):
        sdf = lab(g.node('GeometryNodePointsToSDFGrid', Points=pts, Radius=g.node('GeometryNodeInputRadius'), Voxel_Size=0.06),
                  'spheres → distance field (0.6 mm voxels)')
        sdf = lab(g.node('GeometryNodeSDFGridFillet', Grid=sdf, Iterations=7), 'fillet: fill the creases')
        sdf = lab(g.node('GeometryNodeSDFGridMean', Grid=sdf, Width=1, Iterations=7), 'mean: smooth the bumps')
        mesh = g.node('GeometryNodeGridToMesh', Grid=sdf, Threshold=0.0, Adaptivity=0.0)
        mesh = lab(delete(g, mesh, g.math('LESS_THAN', xyz(g, pos(g))[2], HZ - 4.5)), 'drop the buried forearm')
        mesh = store(g, mesh, 'lp', pos(g), kind='FLOAT_VECTOR')                        # the hand's own frame, for the nails
        mesh = lab(g.node('GeometryNodeTransform', Geometry=mesh, Translation=(0, 0, -HZ * HS), Rotation=(0, 0, HROT), Scale=(HS, HS, HS)),
                   'into the moss: 1.4 × life size')
    with g.section('5 · Weathering'):
        p = pos(g)
        nrm = g.node('GeometryNodeInputNormal')
        lp = attr(g, 'lp', 'FLOAT_VECTOR')
        nails = lab(g.math('ADD', nail(g, G, lp, FINGERS[0]), nail(g, G, lp, FINGERS[4])), 'nails of the index and the thumb')
        lumps = lab(g.math('MULTIPLY', g.math('SUBTRACT', noise(g, p, 0.3, detail=3.0), 0.5), 0.22), 'lumps')
        grain = lab(g.math('MULTIPLY', g.math('SUBTRACT', noise(g, p, 3.0, detail=5.0, rough=0.6), 0.5), 0.05), 'grain')
        cell = g.out(g.node('ShaderNodeTexVoronoi', Vector=p, Scale=1.6), 'Distance')
        pit = lab(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, smoothstep(g, 0.0, 0.16, cell)), 0.07), 'pits')
        disp = lab(g.math('ADD', g.math('SUBTRACT', g.math('ADD', lumps, grain), pit), nails), 'weathering: lumps, grain, pits')
        mesh = g.node('GeometryNodeSetPosition', Geometry=mesh, Offset=g.vmath('SCALE', nrm, scale=disp))
    with g.section('6 · Hollows and height'):
        # hollows: how far the surface lies below a blurred copy of itself
        blur = g.node('GeometryNodeBlurAttribute', props={'data_type': 'FLOAT_VECTOR'}, Value=pos(g), Iterations=25)
        cav = lab(g.vmath('DOT_PRODUCT', g.node('GeometryNodeInputNormal'), g.vmath('SUBTRACT', blur, pos(g))), 'hollows')
        mesh = store(g, mesh, 'cav', g.out(cav, 'Value'))
        soil = g.out(g.group(G['ground'], P=pos(g)), 'Z')
        mesh = store(g, mesh, 'hz', g.math('SUBTRACT', xyz(g, pos(g))[2], soil))
        mesh = pb.set_material(g, g.node('GeometryNodeSetShadeSmooth', Geometry=mesh), M['stone'])
    g.output(mesh)
    pb.arrange(g.tree)
    return ob


def mushroom_params(g, G, stone):
    """Per-frame numbers of the mushroom, from the growth clock, and where the stem stands on the stone."""
    gr = g.group(G['growth'])
    o = lambda n: g.out(gr, n)
    B, st, cp, op = o('Pin'), o('Stem'), o('Cap'), o('Open')
    P = {'gr': gr, 'B': B, 'T': o('T'), 'Tu': o('Tu'), 'Sway': o('Sway')}
    P['H'] = lab(g.math('MULTIPLY', B, mix(g, 0.18, 5.7, st)), 'stem height H')
    P['L'] = lab(g.math('MULTIPLY', B, mix(g, 0.39, 2.5, cp)), 'cap arc length L')
    P['th1'] = lab(mix(g, 1.30, 0.32, op), 'bend of the centre (rad)')
    P['th2'] = lab(mix(g, 0.45, 0.64, op), 'bend of the margin (rad)')
    P['tc'] = lab(g.math('MULTIPLY', B, mix(g, 0.14, 0.22, cp)), 'cap flesh thickness')
    P['rs'] = lab(g.math('MULTIPLY', B, mix(g, 0.1, 0.19, st)), 'stem radius')
    # the SDF's fillet and smoothing wear the stone ~2 mm below the bones' tip: find the real surface with a ray,
    # start the stem 1.5 mm inside it, and keep the cap where it was (the stem grows longer at its foot)
    hit = lab(g.node('GeometryNodeRaycast', Target_Geometry=stone, Source_Position=g.vec(FINGERTIP.x, FINGERTIP.y, FINGERTIP.z + 2.0),
                     Ray_Direction=(0.0, 0.0, -1.0), Ray_Length=10.0), 'the stone under the fingertip')
    P['zs'] = xyz(g, g.out(hit, 'Hit Position'))[2]
    P['z0'] = lab(g.math('SUBTRACT', P['zs'], 0.15), 'stem foot z: inside the stone')
    P['len'] = lab(g.math('SUBTRACT', g.math('ADD', FINGERTIP.z, P['H']), P['z0']), 'stem length: foot → cap')
    P['lean'] = lab(g.math('MULTIPLY', st, 0.28), 'lean')
    # circumnutation: the growing tip circles slowly
    ph = g.math('MULTIPLY', P['Tu'], TAU * 2.2)
    amp = lab(g.math('MULTIPLY', P['Sway'], 0.18), 'circumnutation radius')
    P['swx'] = lab(g.math('MULTIPLY', amp, g.math('SINE', ph)), 'sway x')
    P['swy'] = lab(g.math('MULTIPLY', g.math('MULTIPLY', amp, 0.7), g.math('COSINE', g.math('ADD', ph, 0.8))), 'sway y')
    return P


def spine(g, P, t):
    """Stem axis at fraction t (0 base in the soil → 1 under the cap)."""
    t2 = g.math('MULTIPLY', t, t)
    x = g.math('ADD', FINGERTIP.x, g.math('MULTIPLY', g.math('ADD', P['lean'], P['swx']), t2))
    y = g.math('ADD', FINGERTIP.y, g.math('MULTIPLY', g.math('ADD', g.math('MULTIPLY', P['lean'], -0.25), P['swy']), t2))
    z = g.math('ADD', P['z0'], g.math('MULTIPLY', t, P['len']))
    return g.vec(x, y, z)


# ───────────────────────────────────────────── materials

def _mat(name):
    mat = bpy.data.materials.get('PA_' + name) or bpy.data.materials.new('PA_' + name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    return mat, pb.Graph(mat.node_tree)


def principled(g, **kw):
    p = g.node('ShaderNodeBsdfPrincipled')
    for k, v in kw.items():
        g.set(p, k.replace('_', ' '), v)
    return p


def finish(g, mat, shader):
    g.link(shader, g.node('ShaderNodeOutputMaterial'), b_key='Surface')
    pb.arrange(mat.node_tree)
    return mat


def sattr(g, name):
    return g.out(g.node('ShaderNodeAttribute', props={'attribute_name': name}), 'Fac')


def rgb_mix(g, f, a, b):
    return g.out(g.node('ShaderNodeMix', props={'data_type': 'RGBA'}, ins={'Factor': f, 'A': a, 'B': b}), 'Result')


def ground_material():
    """Damp humus: dark crumbly soil, drier lighter patches, wet glossy hollows."""
    mat, g = _mat('Ground')
    tc = g.out(g.node('ShaderNodeTexCoord'), 'Object')
    fine = g.out(g.node('ShaderNodeTexNoise', Vector=tc, Scale=9.0, Detail=8.0, Roughness=0.65), 'Factor')
    mid = g.out(g.node('ShaderNodeTexNoise', Vector=tc, Scale=0.9, Detail=4.0), 'Factor')
    col = rgb_mix(g, fine, (0.016, 0.011, 0.007, 1), (0.050, 0.033, 0.020, 1))
    col = rgb_mix(g, smoothstep(g, 0.52, 0.72, mid), col, (0.085, 0.058, 0.034, 1))
    rough = g.math('ADD', 0.62, g.math('MULTIPLY', 0.33, smoothstep(g, 0.35, 0.7, mid)))
    h = g.math('ADD', g.out(g.node('ShaderNodeTexVoronoi', Vector=tc, Scale=14.0), 'Distance'),
               g.math('MULTIPLY', 0.5, fine))
    bump = g.node('ShaderNodeBump', Strength=0.7, Distance=0.03, Height=h)
    return finish(g, mat, principled(g, Base_Color=col, Roughness=rough, Normal=bump))


def needle_material():
    """Needle and leaf litter: each piece its own shade, from rotting dark brown to tan, a few bleached grey."""
    mat, g = _mat('Needle')
    nv = sattr(g, 'nv')
    col = rgb_mix(g, smoothstep(g, 0.0, 0.5, nv), (0.035, 0.017, 0.008, 1), (0.13, 0.062, 0.026, 1))
    col = rgb_mix(g, smoothstep(g, 0.5, 0.85, nv), col, (0.27, 0.15, 0.07, 1))
    col = rgb_mix(g, smoothstep(g, 0.9, 0.98, nv), col, (0.26, 0.23, 0.19, 1))
    tc = g.out(g.node('ShaderNodeTexCoord'), 'Object')
    st = g.out(g.node('ShaderNodeTexNoise', Vector=tc, Scale=14.0, Detail=6.0), 'Factor')
    col = rgb_mix(g, g.math('MULTIPLY', smoothstep(g, 0.45, 0.75, st), 0.6), col, (0.025, 0.013, 0.006, 1))
    bump = g.node('ShaderNodeBump', Strength=0.3, Distance=0.01, Height=st)
    return finish(g, mat, principled(g, Base_Color=col, Roughness=0.5, Normal=bump))


def moss_material():
    """Fern moss: olive to brownish bases, yellow-green tips; each frond its own hue, a few dead and brown."""
    mat, g = _mat('Moss')
    tip, fv, fa = sattr(g, 'tipf'), sattr(g, 'fv'), sattr(g, 'fa')
    base = rgb_mix(g, fv, (0.022, 0.036, 0.008, 1), (0.045, 0.040, 0.012, 1))
    top = rgb_mix(g, fv, (0.10, 0.19, 0.022, 1), (0.24, 0.30, 0.045, 1))
    col = rgb_mix(g, smoothstep(g, 0.05, 0.95, tip), base, top)
    col = rgb_mix(g, smoothstep(g, 0.86, 0.94, fa), col, (0.10, 0.065, 0.025, 1))
    hair = g.node('ShaderNodeBsdfHairPrincipled', props={'parametrization': 'COLOR'})
    g.link(col, hair, b_key='Color')
    hair.inputs['Roughness'].default_value = 0.4
    hair.inputs['Radial Roughness'].default_value = 0.55
    return finish(g, mat, hair)


def hypha_material():
    mat, g = _mat('Hypha')
    dk = sattr(g, 'dk')
    hair = g.node('ShaderNodeBsdfHairPrincipled', props={'parametrization': 'COLOR'})
    g.link(rgb_mix(g, dk, (0.62, 0.63, 0.62, 1), (0.90, 0.89, 0.85, 1)), hair, b_key='Color')
    hair.inputs['Roughness'].default_value = 0.5
    hair.inputs['Radial Roughness'].default_value = 0.8
    return finish(g, mat, hair)


def cap_material():
    """Thin translucent cap: dark mauve-brown umbo fading to a pale striate margin; gills show through."""
    mat, g = _mat('Cap')
    S, phi = sattr(g, 'cs'), sattr(g, 'cphi')
    col = rgb_mix(g, smoothstep(g, 0.03, 0.65, S), (0.15, 0.07, 0.07, 1), (0.40, 0.29, 0.26, 1))
    col = rgb_mix(g, smoothstep(g, 0.55, 1.05, S), col, (0.68, 0.60, 0.54, 1))
    stripe = g.math('POWER', g.math('ABSOLUTE', g.math('COSINE', g.math('MULTIPLY', phi, 20.0))), 6.0)
    stri = g.math('MULTIPLY', g.math('MULTIPLY', stripe, smoothstep(g, 0.35, 0.8, S)), 0.22)
    col = rgb_mix(g, stri, col, (0.86, 0.83, 0.79, 1))
    fine = g.math('POWER', g.math('ABSOLUTE', g.math('SINE', g.math('MULTIPLY', phi, 40.0))), 0.6)
    bump = g.node('ShaderNodeBump', Strength=0.25, Distance=0.004,
                  Height=g.math('MULTIPLY', fine, smoothstep(g, 0.25, 0.7, S)))
    p = principled(g, Base_Color=col, Roughness=0.42, Subsurface_Weight=0.6, Subsurface_Radius=(0.9, 0.6, 0.45),
                   Subsurface_Scale=0.12, Sheen_Weight=0.25, Normal=bump)
    tr = g.node('ShaderNodeBsdfTranslucent', Color=rgb_mix(g, 0.5, col, (1.0, 0.93, 0.82, 1)))
    return finish(g, mat, g.node('ShaderNodeMixShader', ins={'Fac': g.math('MULTIPLY', smoothstep(g, 0.15, 1.0, S), 0.55), 1: p, 2: tr}))


def gill_material():
    mat, g = _mat('Gill')
    p = principled(g, Base_Color=(0.93, 0.91, 0.88, 1), Roughness=0.6, Subsurface_Weight=0.7,
                   Subsurface_Radius=(0.8, 0.7, 0.6), Subsurface_Scale=0.08)
    tr = g.node('ShaderNodeBsdfTranslucent', Color=(0.95, 0.92, 0.86, 1))
    return finish(g, mat, g.node('ShaderNodeMixShader', ins={'Fac': 0.3, 1: p, 2: tr}))


def stem_material():
    """Polished, translucent stem: brown at the base, pale under the cap, faint lengthwise fibres, a white felted foot."""
    mat, g = _mat('Stem')
    t, ph = sattr(g, 'st'), sattr(g, 'sphi')
    col = rgb_mix(g, smoothstep(g, 0.0, 0.9, t), (0.22, 0.13, 0.07, 1), (0.64, 0.52, 0.40, 1))
    fib = g.out(g.node('ShaderNodeTexNoise', Scale=1.0, Detail=4.0,
                       Vector=g.vec(g.math('MULTIPLY', g.math('COSINE', ph), 9.0), g.math('MULTIPLY', g.math('SINE', ph), 9.0),
                                    g.math('MULTIPLY', t, 0.8))), 'Factor')
    col = rgb_mix(g, g.math('MULTIPLY', smoothstep(g, 0.4, 0.8, fib), 0.35), col, (0.86, 0.74, 0.58, 1))
    foot = g.math('SUBTRACT', 1.0, smoothstep(g, 0.0, 0.6, g.math('ADD', sattr(g, 'sh'), g.math('MULTIPLY', fib, 0.35))))
    col = rgb_mix(g, g.math('MULTIPLY', foot, 0.85), col, (0.90, 0.87, 0.80, 1))      # the foot whitens into the felt
    bump = g.node('ShaderNodeBump', Strength=0.15, Distance=0.004, Height=fib)
    p = principled(g, Base_Color=col, Roughness=0.3, Subsurface_Weight=0.6, Subsurface_Radius=(0.9, 0.6, 0.4),
                   Subsurface_Scale=0.1, Normal=bump)
    return finish(g, mat, p)


def felt_material():
    """Mycelial felt: matte and velvety (sheen lights its fuzz against the sun), with a fine matted-fibre bump."""
    mat, g = _mat('Felt')
    co = g.out(g.node('ShaderNodeTexCoord'), 'Object')
    fibre = g.out(g.node('ShaderNodeTexNoise', Vector=g.vmath('MULTIPLY', co, (1.0, 1.0, 3.0)), Scale=60.0, Detail=6.0,
                         Roughness=0.7), 'Factor')
    bump = g.node('ShaderNodeBump', Strength=0.5, Distance=0.006, Height=fibre)
    return finish(g, mat, principled(g, Base_Color=(0.78, 0.76, 0.70, 1), Roughness=1.0, Subsurface_Weight=0.5,
                                     Subsurface_Radius=(0.5, 0.5, 0.5), Subsurface_Scale=0.05, Sheen_Weight=1.0,
                                     Sheen_Roughness=0.35, Normal=bump))


def spore_material():
    mat, g = _mat('Spore')
    return finish(g, mat, principled(g, Base_Color=(0.98, 0.96, 0.9, 1), Roughness=0.3,
                                     Emission_Color=(1.0, 0.93, 0.80, 1), Emission_Strength=2.5))


def foliage_material():
    """Leaves of the far undergrowth: glossy (sun glints become bokeh) and translucent against the light."""
    mat, g = _mat('Foliage')
    lv = sattr(g, 'lv')
    col = rgb_mix(g, lv, (0.035, 0.07, 0.012, 1), (0.20, 0.25, 0.04, 1))
    p = principled(g, Base_Color=col, Roughness=0.32)
    tr = g.node('ShaderNodeBsdfTranslucent', Color=rgb_mix(g, lv, (0.20, 0.32, 0.03, 1), (0.50, 0.55, 0.10, 1)))
    return finish(g, mat, g.node('ShaderNodeMixShader', ins={'Fac': 0.4, 1: p, 2: tr}))

def rosettes_group():
    """Crustose lichen: a rosette in some Voronoi cells, each its own size, with a ragged edge."""
    ins = [('Vector', 'vector', (0, 0, 0)), ('Fine', 'float', 0.5), ('Scale', 'float', 1.0), ('Rarity', 'float', 0.5),
           ('Size Min', 'float', 0.2), ('Size Max', 'float', 0.6)]
    tree, g, gin, gout = group('Rosettes', ins, [('Fac', 'float')], kind='ShaderNodeTree')
    o = lambda n: g.out(gin, n)
    vor = g.node('ShaderNodeTexVoronoi', Vector=o('Vector'), Scale=o('Scale'), Randomness=1.0)
    cr = lab(g.out(g.node('ShaderNodeSeparateColor', Color=g.out(vor, 'Color')), 'Red'), 'cell id')
    size = lab(g.math('ADD', o('Size Min'), g.math('MULTIPLY', g.math('FRACT', g.math('MULTIPLY', cr, 7.0)),
                                                    g.math('SUBTRACT', o('Size Max'), o('Size Min')))), 'size of this rosette')
    edge = lab(g.math('ADD', g.out(vor, 'Distance'), g.math('MULTIPLY', g.math('SUBTRACT', o('Fine'), 0.5), 0.35)), 'ragged distance')
    disc = lab(g.math('SUBTRACT', 1.0, smoothstep(g, g.math('SUBTRACT', size, 0.06), size, edge)), 'disc')
    g.link(g.math('MULTIPLY', lab(g.math('GREATER_THAN', cr, o('Rarity')), 'only some cells'), disc), gout, b_key='Fac')
    pb.arrange(tree)
    return tree


def stone_material(rosettes):
    """Weathered sandstone: mottled grey to ochre, iron stains, grime in the hollows, rosettes of crustose lichen, damp near the soil."""
    mat, g = _mat('Stone')
    with g.section('a · Mottled sandstone'):
        tc = g.out(g.node('ShaderNodeTexCoord'), 'Object')
        broad = g.out(g.node('ShaderNodeTexNoise', label='broad mottling', Vector=tc, Scale=0.25, Detail=4.0), 'Factor')
        mid = g.out(g.node('ShaderNodeTexNoise', label='iron stains', Vector=tc, Scale=1.3, Detail=6.0, Roughness=0.6), 'Factor')
        fine = g.out(g.node('ShaderNodeTexNoise', label='fine grain', Vector=tc, Scale=7.0, Detail=8.0, Roughness=0.65), 'Factor')
        col = rgb_mix(g, smoothstep(g, 0.3, 0.7, broad), (0.075, 0.072, 0.064, 1), (0.20, 0.185, 0.155, 1))
        col = rgb_mix(g, g.math('MULTIPLY', smoothstep(g, 0.5, 0.72, mid), 0.55), col, (0.21, 0.14, 0.075, 1))
        speck = smoothstep(g, 0.66, 0.74, g.out(g.node('ShaderNodeTexNoise', label='dark specks', Vector=tc, Scale=26.0, Detail=2.0), 'Factor'))
        col = rgb_mix(g, g.math('MULTIPLY', speck, 0.7), col, (0.05, 0.045, 0.04, 1))
    with g.section('b · Grime in the hollows'):
        cav, hz = sattr(g, 'cav'), sattr(g, 'hz')
        col = rgb_mix(g, g.math('MULTIPLY', smoothstep(g, 0.005, 0.06, cav), 0.85), col, (0.035, 0.032, 0.022, 1))
    with g.section('c · Lichen'):
        up = lab(g.out(g.node('ShaderNodeSeparateXYZ', Vector=g.out(g.node('ShaderNodeNewGeometry'), 'Normal')), 'Z'), 'faces up')
        # colonies: only where a broad noise says so; within them rosettes of every size, merging, with ragged edges
        patch = lab(smoothstep(g, 0.52, 0.62, g.out(g.node('ShaderNodeTexNoise', Vector=tc, Scale=0.45, Detail=3.0), 'Factor')), 'colonies')

        def ros(scale, rarity, s0, s1, label):
            return g.out(lab(g.group(rosettes, Vector=tc, Fine=fine, Scale=scale, Rarity=rarity, Size_Min=s0, Size_Max=s1), label), 'Fac')
        lich = g.math('MULTIPLY', g.math('MULTIPLY', g.math('MAXIMUM', ros(1.4, 0.3, 0.25, 0.75, 'big grey rosettes'),
                                                            ros(3.1, 0.5, 0.2, 0.6, 'small grey rosettes')), patch),
                      smoothstep(g, -0.4, 0.4, up))
        col = rgb_mix(g, g.math('MULTIPLY', lich, 0.7), col, (0.30, 0.32, 0.27, 1))
        orange = g.math('MULTIPLY', ros(4.0, 0.93, 0.2, 0.45, 'rare orange rosettes'), smoothstep(g, 0.4, 0.5, mid))
        col = rgb_mix(g, g.math('MULTIPLY', orange, 0.8), col, (0.40, 0.19, 0.045, 1))
    with g.section('d · Damp, bump, shader'):
        damp = lab(g.math('SUBTRACT', 1.0, smoothstep(g, 0.3, 5.0, hz)), 'damp near the soil')
        col = rgb_mix(g, g.math('MULTIPLY', damp, 0.7), col, (0.05, 0.06, 0.03, 1))
        bump = g.node('ShaderNodeBump', Strength=0.5, Distance=0.02, Height=g.math('ADD', fine, g.math('MULTIPLY', lich, 0.4)))
        rough = g.math('SUBTRACT', 0.9, g.math('MULTIPLY', 0.3, damp))
        return finish(g, mat, principled(g, Base_Color=col, Roughness=rough, Normal=bump))


def shade_material():
    mat, g = _mat('Shade')
    # near black: the forest's dark masses sit behind the sunlit leaves; any lighter and the low sun shows their
    # smooth shapes as pale green slabs in the bokeh
    return finish(g, mat, principled(g, Base_Color=(0.0042, 0.007, 0.0021, 1), Roughness=0.9, Specular_IOR_Level=0.0))   # no sheen at grazing sun


def bark_material():
    mat, g = _mat('Bark')
    n = g.out(g.node('ShaderNodeTexNoise', Vector=g.out(g.node('ShaderNodeTexCoord'), 'Object'), Scale=0.05), 'Factor')
    return finish(g, mat, principled(g, Base_Color=rgb_mix(g, n, (0.035, 0.03, 0.022, 1), (0.10, 0.085, 0.06, 1)),
                                     Roughness=0.9))


# ───────────────────────────────────────────── objects

def curves_object(name, piece):
    tname = 'PA_' + name
    ob = bpy.data.objects.new(tname, bpy.data.hair_curves.new(tname))
    bpy.data.collections['PA_' + piece].objects.link(ob)
    tree = bpy.data.node_groups.new(tname + '_GN', 'GeometryNodeTree')
    tree.is_modifier = True
    tree.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    ob.modifiers.new('PA_Nodes', 'NODES').node_group = tree
    return ob, pb.Graph(tree)


def on_ground(g, G, geo, lift=0.0):
    z = g.out(g.group(G['ground'], P=pos(g)), 'Z')
    return g.node('GeometryNodeSetPosition', Geometry=geo, Offset=g.vec(0, 0, g.math('ADD', z, lift)))


def footprint(g, p, margin=0.0):
    """1 inside the hand's cross-section at the soil line (an ellipse in the hand's own frame), plus a margin."""
    px, py, _ = xyz(g, p)
    c, s_ = math.cos(-HROT), math.sin(-HROT)
    lx = g.math('DIVIDE', g.math('SUBTRACT', g.math('MULTIPLY', px, c), g.math('MULTIPLY', py, s_)), HS)
    ly = g.math('DIVIDE', g.math('ADD', g.math('MULTIPLY', px, s_), g.math('MULTIPLY', py, c)), HS)
    ex = g.math('DIVIDE', g.math('SUBTRACT', lx, 0.5), 4.4 + margin / HS)
    ey = g.math('DIVIDE', g.math('ADD', ly, 0.9), 2.7 + margin / HS)
    return g.math('LESS_THAN', g.math('ADD', g.math('MULTIPLY', ex, ex), g.math('MULTIPLY', ey, ey)), 1.0)


def clearing(g, p, r=2.3):
    """1 inside the bare patch around the stem (where the mycelium shows), 0 outside."""
    px, py, _ = xyz(g, p)
    d = g.vmath('LENGTH', g.vec(px, g.math('MULTIPLY', g.math('SUBTRACT', py, 0.4), 0.85), 0.0))
    d = g.math('ADD', d, g.math('MULTIPLY', g.math('SUBTRACT', noise(g, p, 0.7, detail=3.0), 0.5), 2.2))
    return g.math('LESS_THAN', d, r)


def build_ground(piece, G, M):
    ob, g = pb.gn_object('Ground', piece)
    with g.section('1 · Soil'):
        near = g.node('GeometryNodeMeshGrid', Size_X=70.0, Size_Y=100.0, Vertices_X=350, Vertices_Y=500)
        near = g.node('GeometryNodeTransform', Geometry=near, Translation=(0, 5.0, 0))
        near = on_ground(g, G, near)
        far = g.node('GeometryNodeMeshGrid', Size_X=1400.0, Size_Y=900.0, Vertices_X=140, Vertices_Y=90)
        far = g.node('GeometryNodeTransform', Geometry=far, Translation=(0, 440.0, 0))
        far = delete(g, far, g.math('MULTIPLY', g.math('LESS_THAN', g.math('ABSOLUTE', xyz(g, pos(g))[0]), 35.5),
                                    g.math('LESS_THAN', xyz(g, pos(g))[1], 55.5)))
        far = on_ground(g, G, far, lift=-0.05)
        floor = pb.set_material(g, g.node('GeometryNodeSetShadeSmooth', Geometry=join(g, near, far)), M['ground'])
        # crumbs of humus: many tiny, a few larger
        cp = g.out(g.node('GeometryNodeDistributePointsOnFaces', props={'distribute_method': 'RANDOM'},
                          Mesh=g.node('GeometryNodeMeshGrid', Size_X=44.0, Size_Y=44.0, Vertices_X=2, Vertices_Y=2),
                          Density=2.2, Seed=12), 'Points')
        cp = g.node('GeometryNodeTransform', Geometry=cp, Translation=(0, 1.0, 0))
        ci = idx(g)
        cs = g.math('ADD', 0.01, g.math('MULTIPLY', 0.045, g.math('MULTIPLY', rand(g, ci, 13), rand(g, ci, 14))))
        cp = delete(g, cp, footprint(g, pos(g)))
        crumbs = g.node('GeometryNodeInstanceOnPoints', Points=on_ground(g, G, cp, lift=-0.004),
                        Instance=g.node('GeometryNodeMeshIcoSphere', Radius=1.0, Subdivisions=1),
                        Rotation=g.vec(rand(g, ci, 15, 0.0, TAU), rand(g, ci, 16, 0.0, TAU), 0.0),
                        Scale=g.vec(cs, cs, g.math('MULTIPLY', cs, 0.6)))
        crumbs = pb.set_material(g, realize(g, crumbs), M['ground'])
    with g.section('2 · Needle litter'):
        # tapered, slightly bowed needles; each its own shade; some half sunk into the humus
        pts = g.node('GeometryNodeDistributePointsOnFaces', props={'distribute_method': 'RANDOM'},
                     Mesh=g.node('GeometryNodeMeshGrid', Size_X=110.0, Size_Y=140.0, Vertices_X=2, Vertices_Y=2), Density=0.75, Seed=4)
        pts = g.node('GeometryNodeTransform', Geometry=g.out(pts, 'Points'), Translation=(0, 30.0, 0))
        pts = delete(g, pts, g.math('GREATER_THAN', rand(g, idx(g), 63), g.math('DIVIDE', 1.0, g.math('ADD', 1.0, g.math('MULTIPLY', 0.0006, g.math('POWER', g.vmath('LENGTH', pos(g)), 2.0))))))
        pts = delete(g, pts, footprint(g, pos(g), 1.0))
        i = idx(g)
        pts = store(g, store(g, pts, 'nv', rand(g, i, 65)), 'nb', rand(g, i, 66, -0.05, 0.12))
        proto = g.node('GeometryNodeResampleCurve', Count=9,
                       Curve=g.node('GeometryNodeCurvePrimitiveLine', Start=(-0.5, 0, 0), End=(0.5, 0, 0)))
        proto = store(g, proto, 'nt', g.out(g.node('GeometryNodeSplineParameter'), 'Factor'))
        needles = g.node('GeometryNodeInstanceOnPoints', Points=on_ground(g, G, pts, lift=rand(g, i, 67, -0.03, 0.025)),
                         Instance=proto, Rotation=g.vec(0.0, rand(g, i, 64, -0.08, 0.08), rand(g, i, 61, 0.0, TAU)),
                         Scale=rand(g, i, 62, 1.6, 3.6))
        needles = realize(g, needles)
        nt = attr(g, 'nt')
        arc = g.math('SUBTRACT', 1.0, g.math('POWER', g.math('SUBTRACT', g.math('MULTIPLY', nt, 2.0), 1.0), 2.0))
        needles = g.node('GeometryNodeSetPosition', Geometry=needles, Offset=g.vec(0, 0, g.math('MULTIPLY', attr(g, 'nb'), arc)))
        taper = g.math('MULTIPLY', 0.045, g.math('POWER', g.math('SINE', g.math('MULTIPLY', nt, math.pi)), 0.35))
        needles = g.node('GeometryNodeCurveToMesh', Curve=needles, Scale=taper,
                         Profile_Curve=g.node('GeometryNodeCurvePrimitiveCircle', Resolution=6, Radius=1.0))
        needles = pb.set_material(g, g.node('GeometryNodeSetShadeSmooth', Geometry=needles), M['needle'])
    with g.section('3 · Leaf litter and twigs'):
        lp = g.node('GeometryNodeDistributePointsOnFaces', props={'distribute_method': 'RANDOM'},
                    Mesh=g.node('GeometryNodeMeshGrid', Size_X=64.0, Size_Y=74.0, Vertices_X=2, Vertices_Y=2), Density=0.12, Seed=9)
        lp = g.node('GeometryNodeTransform', Geometry=g.out(lp, 'Points'), Translation=(0, 8.0, 0))
        li = idx(g)
        lp = delete(g, lp, footprint(g, pos(g), 3.0))
        lp = store(g, lp, 'nv', rand(g, li, 33, 0.0, 0.42))
        flake = g.node('GeometryNodeMeshCircle', props={'fill_type': 'TRIANGLE_FAN'}, Vertices=28, Radius=1.0)
        fx, fy, _ = xyz(g, pos(g))
        rr = g.math('ADD', 0.8, g.math('MULTIPLY', 0.7, g.math('SUBTRACT', noise(g, pos(g), 1.4, detail=4.0), 0.5)))
        flake = g.node('GeometryNodeSetPosition', Geometry=flake, Position=g.vec(
            g.math('MULTIPLY', fx, rr), g.math('MULTIPLY', g.math('MULTIPLY', fy, rr), 0.6),
            g.math('MULTIPLY', 0.16, g.math('ADD', g.math('MULTIPLY', fx, fx), g.math('MULTIPLY', fy, fy)))))
        flakes = g.node('GeometryNodeInstanceOnPoints', Points=on_ground(g, G, lp, lift=0.01), Instance=flake,
                        Rotation=g.vec(rand(g, li, 34, -0.12, 0.12), rand(g, li, 35, -0.12, 0.12), rand(g, li, 36, 0.0, TAU)),
                        Scale=rand(g, li, 37, 0.5, 1.4))
        flakes = pb.set_material(g, g.node('GeometryNodeSetShadeSmooth', Geometry=realize(g, flakes)), M['needle'])
        # twigs lying behind the colony
        tw = g.node('GeometryNodePoints', Count=9)
        ti = idx(g)
        tw = g.node('GeometryNodeSetPosition', Geometry=tw, Position=g.vec(rand(g, ti, 41, -30.0, 30.0), rand(g, ti, 42, 9.0, 45.0), 0.0))
        tw = store(g, tw, 'tr', rand(g, ti, 44, 0.08, 0.2))
        line = g.node('GeometryNodeResampleCurve', Count=18,
                      Curve=g.node('GeometryNodeCurvePrimitiveLine', Start=(-0.5, 0, 0), End=(0.5, 0, 0)))
        line = store(g, line, 'nt', g.out(g.node('GeometryNodeSplineParameter'), 'Factor'))
        twigs = realize(g, g.node('GeometryNodeInstanceOnPoints', Points=on_ground(g, G, tw, lift=0.04), Instance=line,
                                  Rotation=g.vec(0.0, 0.0, rand(g, ti, 43, 0.0, TAU)), Scale=rand(g, ti, 45, 6.0, 16.0)))
        wig = g.vmath('MULTIPLY', g.vmath('SUBTRACT', noise(g, pos(g), 0.2, out='Color'), (0.5, 0.5, 0.5)), (1.6, 1.6, 0.25))
        twigs = g.node('GeometryNodeSetPosition', Geometry=twigs, Offset=wig)
        twigs = g.node('GeometryNodeCurveToMesh', Curve=twigs,
                       Scale=g.math('MULTIPLY', attr(g, 'tr'), g.math('SUBTRACT', 1.0, g.math('MULTIPLY', 0.45, attr(g, 'nt')))),
                       Profile_Curve=g.node('GeometryNodeCurvePrimitiveCircle', Resolution=8, Radius=1.0))
        twigs = pb.set_material(g, g.node('GeometryNodeSetShadeSmooth', Geometry=twigs), M['bark'])
    g.output(join(g, floor, crumbs, needles, flakes, twigs))
    pb.arrange(g.tree)
    return ob


def build_forest(piece, M):
    """The forest beyond, only ever seen out of focus. It casts no shadows, so it never steals the back light."""
    ob, g = pb.gn_object('Forest', piece)
    with g.section('1 · Undergrowth and far crowns'):
        # undergrowth: dark masses dressed in single leaves (sun glints on them turn into bokeh)
        bp = g.node('GeometryNodePoints', Count=90)
        bi = idx(g)
        bpos = g.vec(rand(g, bi, 75, -520.0, 520.0), rand(g, bi, 76, 170.0, 650.0), rand(g, bi, 77, -10.0, 30.0))
        bp = g.node('GeometryNodeSetPosition', Geometry=bp, Position=bpos)
        blob = g.node('GeometryNodeMeshIcoSphere', Radius=1.0, Subdivisions=3)
        blob = g.node('GeometryNodeSetPosition', Geometry=blob,
                      Offset=g.vmath('SCALE', pos(g), scale=g.math('MULTIPLY', g.math('SUBTRACT', noise(g, pos(g), 1.5), 0.5), 0.8)))
        br = rand(g, bi, 78, 22.0, 60.0)
        cores = realize(g, g.node('GeometryNodeInstanceOnPoints', Points=bp, Instance=blob,
                                  Scale=g.vec(br, br, g.math('MULTIPLY', br, 0.8))))
        cp = g.node('GeometryNodePoints', Count=80)
        ci = idx(g)
        cp = g.node('GeometryNodeSetPosition', Geometry=cp,
                    Position=g.vec(rand(g, ci, 65, -900.0, 900.0), rand(g, ci, 66, 380.0, 1000.0), rand(g, ci, 67, 70.0, 330.0)))
        cr = rand(g, ci, 68, 50.0, 120.0)
        crown = lab(realize(g, g.node('GeometryNodeInstanceOnPoints', Points=cp, Instance=blob,
                                      Scale=g.vec(cr, cr, g.math('MULTIPLY', cr, 0.7)))), 'far crowns')
        cores = join(g, cores, crown)
        lf = g.node('GeometryNodeDistributePointsOnFaces', props={'distribute_method': 'RANDOM'}, Mesh=cores, Density=0.03, Seed=17)
        lpts = g.out(lf, 'Points')
        lfi = idx(g)
        lpts = g.node('GeometryNodeSetPosition', Geometry=lpts,
                      Offset=g.vmath('SCALE', g.out(lf, 'Normal'), scale=rand(g, lfi, 18, -0.5, 3.0)))
        lpts = store(g, lpts, 'lv', rand(g, lfi, 19))
        leaf = g.node('GeometryNodeMeshCircle', props={'fill_type': 'TRIANGLE_FAN'}, Vertices=12, Radius=1.0)
        lx, ly, _ = xyz(g, pos(g))
        leaf = g.node('GeometryNodeSetPosition', Geometry=leaf,
                      Position=g.vec(lx, g.math('MULTIPLY', ly, 0.42), g.math('MULTIPLY', 0.25, g.math('ABSOLUTE', ly))))
        leaves = g.node('GeometryNodeInstanceOnPoints', Points=lpts, Instance=leaf,
                        Rotation=g.vec(rand(g, lfi, 20, 0.0, TAU), rand(g, lfi, 21, 0.0, TAU), rand(g, lfi, 22, 0.0, TAU)),
                        Scale=rand(g, lfi, 23, 4.0, 8.0))
        leaves = pb.set_material(g, realize(g, leaves), M['foliage'])
        cores = g.node('GeometryNodeSetShadeSmooth', Geometry=cores)       # a low sun turned the flat facets into lit planes
        cores = pb.set_material(g, g.node('GeometryNodeTransform', Geometry=cores, Scale=(0.97, 0.97, 0.97)), M['shade'])
    g.output(join(g, cores, leaves))
    pb.arrange(g.tree)
    ob.visible_shadow = False
    return ob


def build_trunks(piece, M):
    """Far trunks: soft dark verticals in the bokeh. No shadows, and the sun skips them (see rig)."""
    ob, g = pb.gn_object('Trunks', piece)
    with g.section('1 · Trunks'):
        tp = g.node('GeometryNodePoints', Count=34)
        ti = idx(g)
        tpos = g.vec(rand(g, ti, 71, -420.0, 420.0), rand(g, ti, 72, 260.0, 700.0), -10.0)
        tp = g.node('GeometryNodeSetPosition', Geometry=tp, Position=tpos)
        trunk = g.node('GeometryNodeMeshCylinder', Vertices=32, Radius=1.0, Depth=900.0)
        trunk = g.node('GeometryNodeTransform', Geometry=trunk, Translation=(0, 0, 440.0))
        rr = rand(g, ti, 73, 10.0, 26.0)
        trunks = g.node('GeometryNodeInstanceOnPoints', Points=tp, Instance=trunk, Scale=g.vec(rr, rr, 1.0))
        trunks = pb.set_material(g, realize(g, trunks), M['bark'])
    g.output(trunks)
    pb.arrange(g.tree)
    ob.visible_shadow = False
    return ob


def build_canopy(piece, M):
    """Shadow-only leaf canopy that dapples the sun. Holes are drawn in ground-projected space
    (p0 = q - ds * q.z / ds.z): a pool of light falls on the colony and the mushroom; most of the rest is in leaf shade."""
    ob, g = pb.gn_object('Canopy', piece)
    ds = -SUN_DIR
    off = ds * (CANOPY_Z / ds.z)
    tip = Vector((-ds.x / ds.z, -ds.y / ds.z)) * (FINGERTIP.z + 6.0)   # where the light ray through the cap top meets the ground

    def sheet(cx, cy, sx, sy, cell):
        m = g.node('GeometryNodeMeshGrid', Size_X=sx, Size_Y=sy, Vertices_X=int(sx / cell) + 1, Vertices_Y=int(sy / cell) + 1)
        return g.node('GeometryNodeTransform', Geometry=m, Translation=(cx + off.x, cy + off.y, CANOPY_Z))

    with g.section('1 · Sheets'):
        fine = sheet(0.0, 0.0, 130.0, 110.0, 0.5)
        coarse = sheet(0.0, 210.0, 760.0, 560.0, 2.0)
        p0x, p0y, _ = xyz(g, g.vmath('SUBTRACT', pos(g), (off.x, off.y, off.z)))
        inner = g.math('MULTIPLY', g.math('LESS_THAN', g.math('ABSOLUTE', p0x), 64.5),
                       g.math('LESS_THAN', g.math('ABSOLUTE', p0y), 54.5))
        coarse = delete(g, coarse, inner, domain='FACE')
        leaves = lab(join(g, fine, coarse), 'canopy sheets')
    with g.section('2 · Holes'):
        p0 = g.vmath('SUBTRACT', pos(g), (off.x, off.y, off.z))
        p0x, p0y, _ = xyz(g, p0)
        fleck = lab(g.math('GREATER_THAN', noise(g, p0, 0.035, detail=3.0, rough=0.55), 0.535), 'sun flecks')
        # capsule from the stem foot to the cap's ground point, ragged edge
        t = clamp(g, g.math('DIVIDE', g.math('ADD', g.math('MULTIPLY', p0x, tip.x), g.math('MULTIPLY', p0y, tip.y)), tip.length_squared))
        dx = g.math('SUBTRACT', p0x, g.math('MULTIPLY', t, tip.x))
        dy = g.math('SUBTRACT', p0y, g.math('MULTIPLY', t, tip.y))
        dist = g.vmath('LENGTH', g.vec(dx, dy, 0.0))
        dist = g.math('ADD', dist, g.math('MULTIPLY', g.math('SUBTRACT', noise(g, p0, 0.12, detail=3.0), 0.5), 6.0))
        pool = lab(g.math('LESS_THAN', dist, g.math('SUBTRACT', 13.0, g.math('MULTIPLY', 6.0, t))), 'pool of light')   # narrower towards the top
        # keep the forest straight behind the mushroom (as the camera sees it) in leaf shade: dark behind a pale cap
        a, b = (Vector((x, y)) for x, y in BEHIND)
        ab = b - a
        tb = clamp(g, g.math('DIVIDE', g.math('ADD', g.math('MULTIPLY', g.math('SUBTRACT', p0x, a.x), ab.x),
                                                  g.math('MULTIPLY', g.math('SUBTRACT', p0y, a.y), ab.y)), ab.length_squared))
        db = g.vmath('LENGTH', g.vec(g.math('SUBTRACT', p0x, g.math('ADD', a.x, g.math('MULTIPLY', tb, ab.x))),
                                     g.math('SUBTRACT', p0y, g.math('ADD', a.y, g.math('MULTIPLY', tb, ab.y))), 0.0))
        behind = lab(g.math('LESS_THAN', db, g.math('ADD', 16.0, g.math('MULTIPLY', 40.0, tb))), 'shade behind the hand')
        fleck = g.math('MULTIPLY', fleck, g.math('SUBTRACT', 1.0, behind))
        leaves = lab(delete(g, leaves, g.math('MAXIMUM', fleck, pool), domain='FACE'), 'canopy with holes')
    g.output(pb.set_material(g, leaves, M['shade']))
    pb.arrange(g.tree)
    for k in ('camera', 'diffuse', 'glossy', 'transmission', 'volume_scatter'):
        setattr(ob, 'visible_' + k, False)
    ob.visible_shadow = True
    return ob


def frond_proto(g):
    """One fern-moss frond (Thuidium-like), bipinnate, ~1 unit long along +y, arching up then down."""
    with g.section('1 · Frond'):
        def line(n):
            return g.node('GeometryNodeResampleCurve', Count=n,
                          Curve=g.node('GeometryNodeCurvePrimitiveLine', Start=(0, 0, 0), End=(0, 1, 0)))

        def arch(geo, up, droop, wig):
            t = g.out(g.node('GeometryNodeSplineParameter'), 'Factor')
            z = g.math('SUBTRACT', g.math('MULTIPLY', t, up), g.math('MULTIPLY', g.math('MULTIPLY', t, t), droop))
            x = g.math('MULTIPLY', g.math('SINE', g.math('MULTIPLY', t, 5.0)), wig)
            return g.node('GeometryNodeSetPosition', Geometry=geo, Offset=g.vec(x, 0, z))

        def pinnate(axis_n, count, child, t0, ang, lmax, taper, lvl):
            """Child curves along a +y axis, alternating sides; returns realized axis + children."""
            ax = store(g, arch(line(axis_n), 0.18, 0.12, 0.02), 'lvl', float(lvl))
            pts = g.node('GeometryNodeCurveToPoints', props={'mode': 'COUNT'}, Curve=ax, Count=count)
            i = idx(g)
            t = g.math('ADD', t0, g.math('MULTIPLY', g.math('DIVIDE', i, float(count - 1)), 0.97 - t0))
            side = g.math('SUBTRACT', g.math('MULTIPLY', g.math('MODULO', i, 2.0), 2.0), 1.0)
            # resample the axis at t (Curve to Points spaces them evenly; place by Sample Curve instead)
            smp = g.node('GeometryNodeSampleCurve', props={'mode': 'FACTOR'}, Curves=ax, Factor=t)
            p = g.out(smp, 'Position')
            tan = g.out(smp, 'Tangent')
            d = g.node('ShaderNodeVectorRotate', props={'rotation_type': 'Z_AXIS'}, Vector=tan,
                       Angle=g.math('MULTIPLY', side, ang))
            d = g.vmath('NORMALIZE', g.vmath('ADD', d, (0, 0, 0.18)))
            rot = g.node('FunctionNodeAlignRotationToVector', props={'axis': 'Y'}, Vector=d)
            ln = g.math('ADD', g.math('MULTIPLY', lmax, g.math('POWER', g.math('SUBTRACT', 1.0, g.math('MULTIPLY', t, 0.85)), taper)), 0.02)
            pts = g.node('GeometryNodeSetPosition', Geometry=g.out(pts, 'Points'), Position=p)
            kids = g.node('GeometryNodeInstanceOnPoints', Points=pts, Instance=child, Rotation=rot, Scale=ln)
            return join(g, ax, realize(g, kids))

        leaf = store(g, line(3), 'lvl', 2.0)
        branch = pinnate(10, 14, leaf, 0.10, 0.9, 0.17, 1.0, 1)
        frond = pinnate(26, 36, branch, 0.06, 1.0, 0.34, 0.8, 0)
        frond = store(g, frond, 'tipf', g.out(g.node('GeometryNodeSplineParameter'), 'Factor'))
        frond = store(g, frond, 'fd', g.vmath('LENGTH', pos(g)))     # distance from the frond's foot
    return frond


def build_moss(piece, G, M):
    ob, g = curves_object('Moss', piece)
    frond = frond_proto(g)
    with g.section('2 · Clumps'):
        base = g.node('GeometryNodeMeshGrid', Size_X=170.0, Size_Y=190.0, Vertices_X=2, Vertices_Y=2)
        base = g.node('GeometryNodeTransform', Geometry=base, Translation=(0, 55.0, 0))
        pts = g.out(g.node('GeometryNodeDistributePointsOnFaces', props={'distribute_method': 'RANDOM'},
                           Mesh=base, Density=1.9, Seed=8), 'Points')
        p = pos(g)
        px, py, _ = xyz(g, p)
        fore = g.math('EXPONENT', g.math('MULTIPLY', -0.006, g.math('ADD', g.math('POWER', g.math('ADD', px, 14.0), 2.0),
                                                                    g.math('POWER', g.math('ADD', py, 18.0), 2.0))))
        clump = g.math('ADD', noise(g, p, 0.09, detail=2.0), g.math('MULTIPLY', fore, 0.35))
        keep = g.math('MULTIPLY', g.math('GREATER_THAN', clump, 0.44), g.math('SUBTRACT', 1.0, footprint(g, p, 0.3)))
        far = g.math('MAXIMUM', g.math('SUBTRACT', g.vmath('LENGTH', g.vec(px, g.math('MULTIPLY', g.math('ADD', py, 10.0), 0.8), 0.0)), 22.0), 0.0)
        thin = g.math('DIVIDE', 1.0, g.math('ADD', 1.0, g.math('MULTIPLY', 0.0045, g.math('MULTIPLY', far, far))))   # fewer, bigger fronds far away
        keep = g.math('MULTIPLY', keep, g.math('LESS_THAN', rand(g, idx(g), 88), thin))
        pts = delete(g, pts, g.math('SUBTRACT', 1.0, keep))
        pts = store(g, pts, 'far', far)
        pts = on_ground(g, G, pts, lift=-0.02)
        i = idx(g)
        rot = g.vec(rand(g, i, 81, 0.04, 0.4), rand(g, i, 82, -0.25, 0.25), rand(g, i, 83, 0.0, TAU))
        sc = g.math('MULTIPLY', rand(g, i, 84, 1.1, 2.6), g.math('ADD', 1.0, g.math('MULTIPLY', attr(g, 'far'), 0.06)))
        pts = store(g, store(g, store(g, pts, 'fv', rand(g, i, 85)), 'fa', rand(g, i, 86)), 'fs', sc)
        pts = store(g, pts, 'fdr', rand(g, i, 87, 0.0, 0.35))
        moss = realize(g, g.node('GeometryNodeInstanceOnPoints', Points=pts, Instance=frond, Rotation=rot, Scale=sc))
        # each frond droops and leans its own way (nothing in a moss carpet is straight)
        fd2 = g.math('MULTIPLY', attr(g, 'fd'), attr(g, 'fd'))
        sway = g.vmath('SUBTRACT', noise(g, g.vmath('MULTIPLY', pos(g), (0.6, 0.6, 0.6)), 1.0, out='Color'), (0.5, 0.5, 0.5))
        bend = lab(g.vmath('ADD', g.vmath('MULTIPLY', sway, (0.5, 0.5, 0.15)), g.vec(0, 0, g.math('MULTIPLY', -1.0, attr(g, 'fdr')))), 'droop and lean')
        moss = g.node('GeometryNodeSetPosition', label='fronds bent', Geometry=moss,
                      Offset=g.vmath('SCALE', bend, scale=g.math('MULTIPLY', fd2, attr(g, 'fs'))))
    with g.section('3 · Radius'):
        lvl = attr(g, 'lvl')
        r = g.math('ADD', g.math('MULTIPLY', g.math('LESS_THAN', lvl, 0.5), 0.0055),
                   g.math('ADD', g.math('MULTIPLY', g.math('COMPARE', lvl, 1.0, 0.1), 0.0034),
                          g.math('MULTIPLY', g.math('GREATER_THAN', lvl, 1.5), 0.0026)))
        moss = g.node('GeometryNodeSetCurveRadius', Curve=moss, Radius=r)
    g.output(pb.set_material(g, drop_stubs(g, moss), M['moss']))
    pb.arrange(g.tree)
    return ob


def build_mycelium(piece, G, M, hand):
    """Hyphae climb the stone from the soil (shortest paths down to the soil, revealed by a rising front);
    cords gather up the raised finger (shortest paths to the fingertip); the hairy foot of the mushroom."""
    ob, g = curves_object('Mycelium', piece)
    gr = g.group(G['growth'])
    with g.section('1 · Stone lattice'):
        stone = g.out(g.node('GeometryNodeObjectInfo', props={'transform_space': 'ORIGINAL'}, Object=hand), 'Geometry')
        m = g.node('GeometryNodeTriangulate', Mesh=stone)
        soil = g.out(g.group(G['ground'], P=pos(g)), 'Z')
        m = delete(g, m, g.math('LESS_THAN', g.math('SUBTRACT', xyz(g, pos(g))[2], soil), -0.3))
        m = store(g, m, 'nrm', g.node('GeometryNodeInputNormal'), kind='FLOAT_VECTOR')
        # (an unlinked Sample Position means each point's own position: link a vector)
        near_tip = g.out(g.node('GeometryNodeSampleNearest', Geometry=m, Sample_Position=g.vec(*FINGERTIP)), 'Index')
        tip_i = lab(g.node('GeometryNodeSampleIndex', props={'data_type': 'INT', 'domain': 'POINT'}, Geometry=m,
                           Value=idx(g), Index=near_tip), 'fingertip vertex')
        is_tip = g.math('COMPARE', idx(g), g.out(tip_i, 'Value'), 0.5)
        is_soil = lab(g.math('MULTIPLY', g.math('LESS_THAN', g.math('SUBTRACT', xyz(g, pos(g))[2], soil), 0.35),
                                 g.math('GREATER_THAN', noise(g, pos(g), 0.12, detail=1.0), 0.66)), 'where the colony leaves the soil')
    with g.section('2 · Edge cost'):
        ev = g.node('GeometryNodeInputMeshEdgeVertices')
        p1, p2 = g.out(ev, 'Position 1'), g.out(ev, 'Position 2')
        length = g.vmath('DISTANCE', p1, p2)
        mid = g.vmath('SCALE', g.vmath('ADD', p1, p2), scale=0.5)
        wander = noise(g, mid, 0.8, detail=3.0)
        cav = g.out(g.node('GeometryNodeSampleIndex', props={'data_type': 'FLOAT', 'domain': 'POINT'}, Geometry=m,
                           Value=attr(g, 'cav'), Index=g.out(g.node('GeometryNodeInputMeshEdgeVertices'), 'Vertex Index 1')), 'Value')
        hollow = g.math('SUBTRACT', 1.0, g.math('MULTIPLY', 0.6, smoothstep(g, 0.0, 0.06, cav)))
        cost = lab(g.math('MULTIPLY', g.math('MULTIPLY', length, hollow),
                          g.math('ADD', g.math('ADD', 1.0, g.math('MULTIPLY', 7.0, g.math('POWER', wander, 3.0))), rand(g, idx(g), 5, 0.0, 0.9))),
                   'edge cost: hollows are cheap')
    with g.section('3 · Shortest paths'):
        sS = g.node('GeometryNodeInputShortestEdgePaths', label='paths down to the soil', ins={'End Vertex': is_soil, 'Edge Cost': cost})
        sT = g.node('GeometryNodeInputShortestEdgePaths', label='paths up to the fingertip', ins={'End Vertex': is_tip, 'Edge Cost': cost})
        m = store(g, store(g, m, 'd', g.out(sS, 'Total Cost')), 'dt', g.out(sT, 'Total Cost'))
    with g.section('4 · Hyphae and cords'):
        r = rand(g, idx(g), 21)
        rc = rand(g, idx(g), 22)

        def paths(sel, nxt, label):
            return g.out(g.node('GeometryNodeEdgePathsToSelection', label=label,
                                ins={'Start Vertices': sel, 'Next Vertex Index': g.out(nxt, 'Next Vertex Index')}), 'Selection')

        pstart = lab(g.math('ADD', 0.0012, g.math('MULTIPLY', 0.016, g.math('EXPONENT', g.math('DIVIDE', attr(g, 'hz'), -7.0)))),
                     'start chance: dense low, sparse high')
        fine = paths(g.math('LESS_THAN', r, pstart), sS, 'hyphae: paths down to the soil')
        med = paths(g.math('LESS_THAN', r, g.math('MULTIPLY', pstart, 0.25)), sS, 'branches: a quarter of them')
        thick = paths(g.math('LESS_THAN', rc, 0.0035), sT, 'cords: from 0.35 %, to the fingertip')
        m = store(g, m, 'path', fine, domain='EDGE')
        m = store(g, m, 'erank', g.math('ADD', fine, med), domain='EDGE')
        m = store(g, m, 'rank', g.math('DIVIDE', attr(g, 'erank'), g.math('MAXIMUM', attr(g, 'path'), 1e-6)))
        m = store(g, m, 'cord', thick, domain='EDGE')
    with g.section('5 · Stats'):
        dtip = lab(g.node('GeometryNodeSampleIndex', props={'data_type': 'FLOAT', 'domain': 'POINT'}, Geometry=m,
                          Value=attr(g, 'd'), Index=g.out(tip_i, 'Value')), 'd at the fingertip')
        dtmax = lab(g.node('GeometryNodeAttributeStatistic', props={'data_type': 'FLOAT', 'domain': 'POINT'},
                           Geometry=m, Attribute=attr(g, 'dt')), 'dt max')
    with g.section('6 · Network → curves'):
        hy = store(g, g.node('GeometryNodeMeshToCurve', Mesh=m, Selection=attr(g, 'path')), 'kind', 0.0)
        co = store(g, g.node('GeometryNodeMeshToCurve', Mesh=m, Selection=attr(g, 'cord')), 'kind', 1.0)
        cur = join(g, hy, co)
        # the paths follow mesh edges (straight runs, sharp turns): blur them along each curve, ends pinned, then back onto the stone
        blur = g.node('GeometryNodeBlurAttribute', props={'data_type': 'FLOAT_VECTOR'}, Value=pos(g), Iterations=24)
        ends = g.node('GeometryNodeCurveEndpointSelection', Start_Size=1, End_Size=1)
        cur = g.node('GeometryNodeSetPosition', Geometry=cur, Position=vmix(g, blur, pos(g), ends))
        snap = g.out(g.node('GeometryNodeSampleNearestSurface', props={'data_type': 'FLOAT_VECTOR'}, Mesh=stone, Value=pos(g),
                            Sample_Position=pos(g)), 'Value')
        cur = lab(g.node('GeometryNodeSetPosition', Geometry=cur, Position=snap), 'smoothed, on the stone')
    with g.section('7 · Growth front'):
        d = attr(g, 'd')
        reach = lab(g.math('MULTIPLY', g.out(gr, 'Colony'), g.math('MULTIPLY', g.out(dtip, 'Value'), 1.03)), 'reach(T)')
        behind = lab(g.math('SUBTRACT', reach, d), 'behind the front')
        dk = lab(smoothstep(g, 0.3, 5.0, behind), 'age: older = thicker, whiter')
        cur = store(g, cur, 'dk', dk)
        kind = attr(g, 'kind')
        nocord = g.math('MULTIPLY', kind, g.math('LESS_THAN', g.out(gr, 'Cords'), 0.01))
        cur = lab(delete(g, cur, g.math('MAXIMUM', g.math('GREATER_THAN', d, reach), nocord)), 'grown so far')
    with g.section('8 · Radius'):
        young = smoothstep(g, 0.0, 1.5, behind)               # tips taper
        rh = g.math('MULTIPLY', g.math('MULTIPLY', g.math('ADD', 0.0055, g.math('MULTIPLY', 0.007, g.math('POWER', attr(g, 'rank'), 1.6))),
                                       g.math('ADD', 0.45, g.math('MULTIPLY', 0.55, young))),
                    g.math('ADD', 1.0, g.math('MULTIPLY', 0.45, dk)))
        near = g.math('SUBTRACT', 1.0, g.math('DIVIDE', attr(g, 'dt'), g.math('ADD', g.out(dtmax, 'Max'), 0.01)))
        rc = g.math('MULTIPLY', g.math('MULTIPLY', g.out(gr, 'Cords'), 0.017), g.math('ADD', 0.3, g.math('MULTIPLY', 1.2, g.math('POWER', near, 2.0))))
        cur = g.node('GeometryNodeSetCurveRadius', Curve=cur, Radius=mix(g, rh, rc, kind))
        lift = g.math('ADD', g.math('MULTIPLY', g.out(g.node('GeometryNodeInputRadius'), 'Radius'), 0.8),
                      g.math('MULTIPLY', 0.02, noise(g, pos(g), 3.0)))
        cur = g.node('GeometryNodeSetPosition', Geometry=cur, Offset=g.vmath('SCALE', attr(g, 'nrm', 'FLOAT_VECTOR'), scale=lift))
        cur = store(g, cur, 'yg', young)
    with g.section('9 · Cottony fuzz'):
        fp = g.out(g.node('GeometryNodeCurveToPoints', props={'mode': 'LENGTH'}, Curve=cur, Length=0.022), 'Points')
        fi = idx(g)
        fp = delete(g, fp, g.math('GREATER_THAN', rand(g, fi, 31), mix(g, 0.9, 0.45, attr(g, 'dk'))))
        wisp = g.node('GeometryNodeResampleCurve', Count=7,
                      Curve=g.node('GeometryNodeCurvePrimitiveLine', Start=(0, 0, 0), End=(1, 0, 0)))
        wt = g.out(g.node('GeometryNodeSplineParameter'), 'Factor')
        wisp = store(g, wisp, 'wt', wt)
        # a wisp is no bristle: it hooks over and kinks a little
        wisp = lab(g.node('GeometryNodeSetPosition', Geometry=wisp,
                          Offset=g.vec(0.0, g.math('MULTIPLY', 0.45, g.math('MULTIPLY', wt, wt)),
                                       g.math('MULTIPLY', 0.12, g.math('SINE', g.math('MULTIPLY', wt, 7.0))))), 'curled wisp')
        rv = g.vec(rand(g, fi, 32, -1.0, 1.0), rand(g, fi, 33, -1.0, 1.0), rand(g, fi, 35, -1.0, 1.0))
        wdir = g.vmath('ADD', g.vmath('SCALE', attr(g, 'nrm', 'FLOAT_VECTOR'), scale=rand(g, fi, 36, 0.05, 0.4)), g.vmath('SCALE', rv, scale=0.9))   # lying low, tangled
        rot = g.node('FunctionNodeAlignRotationToVector', props={'axis': 'X'}, Vector=wdir)
        rot = g.node('FunctionNodeRotateRotation', props={'rotation_space': 'LOCAL'}, Rotation=rot,
                     Rotate_By=g.node('FunctionNodeEulerToRotation', Euler=g.vec(rand(g, fi, 37, 0.0, TAU), 0.0, 0.0)))   # curl any way
        fz = realize(g, g.node('GeometryNodeInstanceOnPoints', Points=fp, Instance=wisp, Rotation=rot,
                                Scale=rand(g, fi, 34, 0.04, 0.17)))
        fz = g.node('GeometryNodeSetCurveRadius', Curve=fz,
                    Radius=g.math('MULTIPLY', 0.0019, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', 0.6, attr(g, 'wt')))))
        cur = join(g, cur, fz)
    with g.section('10 · Mushroom size'):
        P = mushroom_params(g, G, stone)
    with g.section('11 · Stem foot'):
        # white fibrils fanning from the stem base, draped over the fingertip
        fp = g.node('GeometryNodePoints', Count=340)
        fib = realize(g, g.node('GeometryNodeInstanceOnPoints', Points=fp,
                                Instance=g.node('GeometryNodeResampleCurve', Count=6,
                                                Curve=g.node('GeometryNodeCurvePrimitiveLine', Start=(0, 0, 0), End=(0, 0, 1)))))
        par = g.out(g.node('GeometryNodeSplineParameter'), 'Factor')
        ci = g.out(g.node('GeometryNodeInputIndex'), 'Index')
        cid = g.math('FLOOR', g.math('DIVIDE', ci, 6.0))
        fphi_c = rand(g, cid, 91, 0.0, TAU)
        t_root = g.math('ADD', rand(g, cid, 92, 0.02, 0.07), g.math('DIVIDE', 0.15, P['len']))   # 2–7 % of the stem above the stone
        root_c = g.vmath('ADD', spine(g, P, t_root), polar(g, P['rs'], fphi_c, 0.0))
        fl_c = g.math('MULTIPLY', P['B'], rand(g, cid, 93, 0.35, 1.3))
        tip_c = g.vmath('ADD', root_c, polar(g, fl_c, g.math('ADD', fphi_c, rand(g, cid, 94, -0.4, 0.4)), g.math('MULTIPLY', fl_c, -0.6)))
        line = vmix(g, root_c, tip_c, par)
        on = g.out(g.node('GeometryNodeSampleNearestSurface', props={'data_type': 'FLOAT_VECTOR'}, Mesh=stone, Value=pos(g),
                           Sample_Position=line), 'Value')
        onn = g.out(g.node('GeometryNodeSampleNearestSurface', props={'data_type': 'FLOAT_VECTOR'}, Mesh=stone,
                            Value=g.node('GeometryNodeInputNormal'), Sample_Position=line), 'Value')
        draped = g.vmath('ADD', on, g.vmath('SCALE', onn, scale=0.012))
        fpos = vmix(g, line, draped, smoothstep(g, 0.0, 0.35, par))
        fib = g.node('GeometryNodeSetPosition', Geometry=fib, Position=fpos)
        fib = g.node('GeometryNodeSetCurveRadius', Curve=fib, Radius=mix(g, 0.006, 0.0022, par))
        fib = store(g, fib, 'dk', 1.0)
        fib = delete(g, fib, g.math('LESS_THAN', P['B'], 0.3))
    g.output(pb.set_material(g, drop_stubs(g, join(g, cur, fib)), M['hypha']))
    pb.arrange(g.tree)
    return ob


def build_mushroom(piece, G, M, hand):
    ob, g = pb.gn_object('Mushroom', piece)
    parts = []
    with g.section('1 · Clock → sizes'):
        stone = g.out(g.node('GeometryNodeObjectInfo', props={'transform_space': 'ORIGINAL'}, Object=hand), 'Geometry')
        P = mushroom_params(g, G, stone)
        alive = g.math('GREATER_THAN', P['B'], 0.01)
        top_c = lab(g.vmath('ADD', spine(g, P, 1.0), g.vec(0, 0, P['tc'])), 'cap top centre')

    def cap(S, phi):
        return g.group(G['cap'], S=S, Phi=phi, L=P['L'], Th1=P['th1'], Th2=P['th2'], Tc=P['tc'], Scallop=0.05)

    with g.section('2 · Cap'):
        m = grid(g, 36, 160)
        S, phi = attr(g, 'a'), g.math('MULTIPLY', attr(g, 'b'), TAU)
        c = cap(S, phi)
        top = g.node('GeometryNodeSetPosition', Geometry=m, Position=g.vmath('ADD', g.out(c, 'Top'), top_c))
        top = store(g, store(g, top, 'cs', S), 'cphi', phi)
        top = g.node('GeometryNodeMergeByDistance', Geometry=top, Distance=0.0002)
        parts.append(pb.set_material(g, g.node('GeometryNodeSetShadeSmooth', Geometry=top), M['cap']))
        bot = g.node('GeometryNodeSetPosition', Geometry=g.node('GeometryNodeFlipFaces', Mesh=m),
                     Position=g.vmath('ADD', g.out(c, 'Bottom'), top_c))
        bot = store(g, store(g, bot, 'cs', S), 'cphi', phi)
        bot = g.node('GeometryNodeMergeByDistance', Geometry=bot, Distance=0.0002)
        parts.append(pb.set_material(g, g.node('GeometryNodeSetShadeSmooth', Geometry=bot), M['cap']))

    with g.section('3 · Gills'):
        # 20 gills to the stem, 20 half, 40 quarter; plates hang from the underside
        ng = 80
        strip = grid(g, 26, 4)
        pts = g.node('GeometryNodePoints', Count=ng)
        i = idx(g)
        main = g.math('LESS_THAN', i, 20.0)
        half = g.math('MULTIPLY', g.math('GREATER_THAN', i, 19.5), g.math('LESS_THAN', i, 39.5))
        quarter = g.math('GREATER_THAN', i, 39.5)
        j = g.math('SUBTRACT', i, 40.0)
        phq = g.math('ADD', g.math('FLOOR', g.math('DIVIDE', j, 2.0)), g.math('ADD', 0.25, g.math('MULTIPLY', 0.5, g.math('MODULO', j, 2.0))))
        ph = g.math('ADD', g.math('ADD', g.math('MULTIPLY', main, i), g.math('MULTIPLY', half, g.math('ADD', g.math('SUBTRACT', i, 20.0), 0.5))),
                    g.math('MULTIPLY', quarter, phq))
        pts = store(g, pts, 'gphi', g.math('MULTIPLY', g.math('DIVIDE', ph, 20.0), TAU))
        pts = store(g, pts, 'gs0', g.math('ADD', g.math('ADD', g.math('MULTIPLY', main, 0.10), g.math('MULTIPLY', half, 0.42)),
                                          g.math('MULTIPLY', quarter, 0.70)))
        gl = realize(g, g.node('GeometryNodeInstanceOnPoints', Points=pts, Instance=strip))
        s0 = attr(g, 'gs0')
        S = mix(g, s0, 0.975, attr(g, 'a'))
        c = cap(S, attr(g, 'gphi'))
        depth = g.math('MULTIPLY', g.math('MULTIPLY', P['B'], mix(g, 0.06, 0.40, smoothstep(g, 0.3, 1.9, P['L']))),
                       g.math('MULTIPLY', smoothstep(g, s0, g.math('ADD', s0, 0.16), S),
                              g.math('SUBTRACT', 1.0, smoothstep(g, 0.84, 1.0, S))))
        down = g.vmath('NORMALIZE', g.vmath('ADD', g.vmath('SCALE', g.out(c, 'Normal'), scale=-0.55), (0, 0, -0.45)))
        p = g.vmath('ADD', g.vmath('ADD', g.out(c, 'Bottom'), top_c), g.vmath('SCALE', down, scale=g.math('MULTIPLY', depth, attr(g, 'b'))))
        gl = g.node('GeometryNodeSetPosition', Geometry=gl, Position=p)
        parts.append(pb.set_material(g, g.node('GeometryNodeSetShadeSmooth', Geometry=gl), M['gill']))

    with g.section('4 · Stem'):
        m = grid(g, 90, 24)
        t, phi = attr(g, 'a'), g.math('MULTIPLY', attr(g, 'b'), TAU)
        hs = lab(g.math('SUBTRACT', g.math('MULTIPLY', t, P['len']), 0.15), 'height above the stone')
        zt = g.math('MAXIMUM', hs, 0.0)
        r = g.math('MULTIPLY', P['rs'], g.math('SUBTRACT', 1.12, g.math('MULTIPLY', 0.22, t)))
        r = g.math('ADD', r, g.math('MULTIPLY', P['rs'], g.math('MULTIPLY', 0.6, g.math('EXPONENT', g.math('MULTIPLY', -1.0, g.math('POWER', g.math('DIVIDE', zt, 0.3), 2.0))))))
        r = g.math('ADD', r, g.math('MULTIPLY', g.math('MULTIPLY', P['rs'], 0.35), smoothstep(g, 0.94, 1.0, t)))
        # slightly over-long so the apex sits inside the cap flesh
        tt = g.math('MULTIPLY', t, 1.02)
        st = g.node('GeometryNodeSetPosition', Geometry=m, Position=g.vmath('ADD', spine(g, P, tt), polar(g, r, phi, 0.0)))
        st = store(g, store(g, store(g, st, 'st', t), 'sphi', phi), 'sh', hs)
        st = g.node('GeometryNodeMergeByDistance', Geometry=st, Distance=0.0002)
        parts.append(pb.set_material(g, g.node('GeometryNodeSetShadeSmooth', Geometry=st), M['stem']))

    with g.section('5 · Hyphal knot'):
        gr = P['gr']
        kn = g.out(gr, 'Knot')
        # a felt cushion draped on the fingertip: every point drops a ray onto the stone, and the upper half of the
        # sphere stands up off it, so the rim lies on the stone and the stem rises out of white felt
        k = g.node('GeometryNodeMeshIcoSphere', Radius=1.0, Subdivisions=4)
        ux, uy, uz = xyz(g, pos(g))
        lump = g.math('ADD', 0.55, g.math('MULTIPLY', 0.9, noise(g, pos(g), 1.8, detail=4.0, rough=0.7)))
        R = lab(g.math('MULTIPLY', lump, g.math('MULTIPLY', kn, 0.75)), 'cushion radius')
        kx = g.math('ADD', FINGERTIP.x, g.math('MULTIPLY', ux, R))
        ky = g.math('ADD', FINGERTIP.y, g.math('MULTIPLY', uy, R))
        under = lab(g.node('GeometryNodeRaycast', Target_Geometry=stone, Source_Position=g.vec(kx, ky, FINGERTIP.z + 2.0),
                           Ray_Direction=(0.0, 0.0, -1.0), Ray_Length=10.0), 'the stone under each point')
        sz = g.math('MAXIMUM', xyz(g, g.out(under, 'Hit Position'))[2], FINGERTIP.z - 1.5)
        tuft = g.math('ADD', 0.75, g.math('MULTIPLY', 0.5, noise(g, pos(g), 9.0, detail=3.0, rough=0.6)))
        h = lab(g.math('MULTIPLY', g.math('MULTIPLY', g.math('MULTIPLY', g.math('POWER', g.math('MAXIMUM', uz, 0.0), 1.5), R), tuft), 0.42),
                'felt thickness')
        k = g.node('GeometryNodeSetPosition', Geometry=k, Position=g.vec(kx, ky, g.math('ADD', sz, g.math('SUBTRACT', h, 0.015))))
        k = delete(g, k, g.math('LESS_THAN', kn, 0.01))
        parts.append(pb.set_material(g, g.node('GeometryNodeSetShadeSmooth', Geometry=k), M['felt']))

    with g.section('6 · Spores'):
        # 500 released while the cap opens (T 0.88–1), 380 more during the hold, so the fall never stops
        nm = 880
        sp = g.node('GeometryNodePoints', Count=nm)
        si = idx(g)
        tau = rand(g, si, 51)
        late = g.math('GREATER_THAN', si, 499.5)
        t0 = g.math('ADD', g.math('ADD', 0.88, g.math('MULTIPLY', tau, 0.12)), g.math('MULTIPLY', late, 0.12))
        a = g.math('SUBTRACT', P['Tu'], t0)
        phi = rand(g, si, 53, 0.0, TAU)
        rr = g.math('MULTIPLY', P['L'], rand(g, si, 52, 0.25, 0.9))
        origin = g.vmath('ADD', top_c, polar(g, rr, phi, g.math('MULTIPLY', P['L'], -0.45)))
        drift = g.vec(g.math('MULTIPLY', a, 4.0), g.math('MULTIPLY', a, -2.0), g.math('MULTIPLY', a, rand(g, si, 54, -24.0, -10.0)))
        wob = g.vmath('SCALE', g.vmath('SUBTRACT', noise(g, g.vmath('ADD', origin, g.vec(0, 0, g.math('MULTIPLY', a, 30.0))), 1.5, out='Color'),
                                       (0.5, 0.5, 0.5)), scale=g.math('MULTIPLY', a, 6.0))
        sp = g.node('GeometryNodeSetPosition', Geometry=sp, Position=g.vmath('ADD', g.vmath('ADD', origin, drift), wob))
        sp = delete(g, sp, g.math('LESS_THAN', a, 0.0))
        motes = realize(g, g.node('GeometryNodeInstanceOnPoints', Points=sp,
                                  Instance=g.node('GeometryNodeMeshIcoSphere', Radius=0.0045, Subdivisions=1)))
        parts.append(pb.set_material(g, motes, M['spore']))

    g.output(delete(g, join(g, *parts), g.math('SUBTRACT', 1.0, alive)))
    pb.arrange(g.tree)
    return ob


# ───────────────────────────────────────────── camera, lights

def smooth01(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def sched(name, T):
    """Python twin of a growth curve (smoothstep between keys) for the camera to follow."""
    pts = dict((n, p) for n, p, _ in GROWTH)[name]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if T <= x1:
            return y0 + (y1 - y0) * smooth01((T - x0) / max(x1 - x0, 1e-6))
    return pts[-1][1]


CAM0, TGT0 = Vector((-22.0, -96.0, 10.0)), Vector((-1.2, 0.6, 11.0))
TGT1 = FINGERTIP + Vector((0.6, 0.0, -1.6))
CAM1 = TGT1 + Vector((-13.0, -62.0, -6.0))
# close-up: the whole mushroom from a little below the cap (the gills show), the fingertip at the bottom edge
TGT2 = FINGERTIP + Vector((0.2, -0.05, 3.0))
CAM2 = TGT2 + Vector((-0.06, -0.99, -0.1)).normalized() * 26.0


def _behind():
    ds = -SUN_DIR
    out = []
    for y in (40.0, 400.0):
        d = TGT1 - CAM1
        P = CAM1 + d * ((y - CAM1.y) / d.y)
        out.append((P.x - ds.x * P.z / ds.z, P.y - ds.y * P.z / ds.z))
    return out


BEHIND = _behind()


def cam_phases(f):
    """0→1 eases of the two moves: wide → the finger and its mushroom (T 0.33–0.73), → close-up (T 0.74–0.98)."""
    T = min(max((f - 1) / (F_GROW - 1), 0.0), 1.0)
    return smooth01((T - 0.33) / 0.40), smooth01((T - 0.74) / 0.24)


def cam_at(f):
    c1, c2 = cam_phases(f)
    cam = CAM0.lerp(CAM1, c1).lerp(CAM2, c2)
    tgt = TGT0.lerp(TGT1, c1).lerp(TGT2, c2)
    creep = 1.2 * smooth01((f - F_GROW) / (F_END - F_GROW))       # in the hold the lens keeps drifting in, a little
    cam = cam + (tgt - cam).normalized() * creep
    return cam, tgt, tgt


def rig(piece, F):
    coll = bpy.data.collections['PA_' + piece]
    sc = bpy.context.scene
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    cd = bpy.data.cameras.new('PA_Camera')
    cd.lens, cd.sensor_width = 100.0, 36.0
    cd.clip_start, cd.clip_end = 0.5, 3000.0
    cd.dof.use_dof = True
    cd.dof.aperture_blades = 9
    cam = bpy.data.objects.new('PA_Camera', cd)
    coll.objects.link(cam)
    tgt = bpy.data.objects.new('PA_Target', None)
    coll.objects.link(tgt)
    con = cam.constraints.new('TRACK_TO')
    con.target, con.track_axis, con.up_axis = tgt, 'TRACK_NEGATIVE_Z', 'UP_Y'
    for f in range(1, F + 1):
        c, t, focus = cam_at(f)
        cam.location, tgt.location = c, t
        fwd = (t - c).normalized()
        cd.dof.focus_distance = max((focus - c).dot(fwd), 1.0)
        c1, c2 = cam_phases(f)
        cd.dof.aperture_fstop = 0.11 + (0.05 - 0.11) * c1 + (0.16 - 0.05) * c2     # ≈ f/11 → f/5 → f/16 in this cm scene
        cam.keyframe_insert('location', frame=f)
        tgt.keyframe_insert('location', frame=f)
        cd.dof.keyframe_insert('focus_distance', frame=f)
        cd.dof.keyframe_insert('aperture_fstop', frame=f)
    sc.camera = cam
    # light: a low, hard, golden sun from behind the hand (moss tips, the hand's rim and the stem glow; shadows run
    # towards the camera), a dim cool sky, a fill from the front-left so the hand's face keeps its detail
    sd = bpy.data.lights.new('PA_Sun', 'SUN')
    sd.energy, sd.angle, sd.color = 25.0, math.radians(0.53), (1.0, 0.66, 0.36)
    sun = bpy.data.objects.new('PA_Sun', sd)
    sun.rotation_euler = SUN_DIR.to_track_quat('-Z', 'Y').to_euler()
    coll.objects.link(sun)
    fd = bpy.data.lights.new('PA_Fill', 'AREA')
    fd.energy, fd.size, fd.color = 5e3, 40.0, (0.92, 0.96, 1.0)
    fill = bpy.data.objects.new('PA_Fill', fd)
    fill.location = (-40.0, -60.0, 45.0)
    fill.rotation_euler = (Vector((0, 0, 12.0)) - fill.location).to_track_quat('-Z', 'Y').to_euler()
    coll.objects.link(fill)
    w = sc.world or bpy.data.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    shade = nt.nodes.new('ShaderNodeBackground')          # skylight filtered by the canopy
    shade.inputs['Color'].default_value, shade.inputs['Strength'].default_value = (0.30, 0.42, 0.40, 1), 0.5
    gaps = nt.nodes.new('ShaderNodeBackground')           # sky seen through the leaves
    gaps.inputs['Color'].default_value, gaps.inputs['Strength'].default_value = (1.0, 0.80, 0.50, 1), 1.0
    lp, mx, out = nt.nodes.new('ShaderNodeLightPath'), nt.nodes.new('ShaderNodeMixShader'), nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs['Fac'])
    nt.links.new(shade.outputs[0], mx.inputs[1])
    nt.links.new(gaps.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs['Surface'])
    return cam


def build(samples=128, engine='CYCLES'):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    info = pb.piece(NAME, aspect='1:1', width=1080, fps=24, frames=F_END, engine=engine, samples=samples)
    G = {'ground': ground_group(), 'growth': growth_group(), 'cap': cap_group(), 'finger': finger_group(bone_group(), knuckle_group()),
         'capsule': capsule_group(), 'nail': nail_group()}
    M = {'ground': ground_material(), 'needle': needle_material(), 'moss': moss_material(), 'hypha': hypha_material(),
         'cap': cap_material(), 'gill': gill_material(), 'stem': stem_material(), 'felt': felt_material(),
         'spore': spore_material(), 'bark': bark_material(), 'foliage': foliage_material(), 'shade': shade_material(),
         'stone': stone_material(rosettes_group())}
    build_ground(NAME, G, M)
    build_forest(NAME, M)
    trunks = build_trunks(NAME, M)
    build_moss(NAME, G, M)
    hand = build_hand(NAME, G, M)
    build_mycelium(NAME, G, M, hand)
    build_mushroom(NAME, G, M, hand)
    build_canopy(NAME, M)
    rig(NAME, F_END)
    skip = bpy.data.collections.new('PA_SunSkips')               # light linking: the sun leaves the trunks to the sky
    skip.objects.link(trunks)
    skip.collection_objects[0].light_linking.link_state = 'EXCLUDE'
    bpy.data.objects['PA_Sun'].light_linking.receiver_collection = skip
    sc = bpy.context.scene
    sc.cycles.max_bounces = 10
    sc.cycles.diffuse_bounces = 6
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = 0.4
    pb.post(bloom=0.5)                                           # a glow round the backlit edges and highlights
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--frame', type=int, default=1)
    ap.add_argument('--frames', default='')
    ap.add_argument('--scale', type=int, default=50)
    ap.add_argument('--samples', type=int, default=32)
    ap.add_argument('--engine', default='CYCLES')
    ap.add_argument('--out', default=str(HERE / 'preview.png'))
    ap.add_argument('--save', default='')
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    info = build(engine=args.engine)
    print('INFO', info)
    if args.save:
        pb.save(args.save)
    if args.preview:
        sc = bpy.context.scene
        sc.render.resolution_percentage = args.scale
        if sc.render.engine == 'CYCLES':
            sc.cycles.samples = args.samples
        frames = [int(f) for f in args.frames.split(',')] if args.frames else [args.frame]
        for f in frames:
            sc.frame_set(f)
            out = args.out if len(frames) == 1 else args.out.replace('.png', f'_{f:03d}.png')
            sc.render.filepath = out
            bpy.ops.render.render(write_still=True)
            print('WROTE', out)


if __name__ == '__main__':
    main()
