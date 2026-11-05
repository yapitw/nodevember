"""Nodevember 2026 · Day 05 · Clockwork — v3: Four-season music box / 四季音樂盒.

A round wind-up music box. Its stage turns once per loop, and one turn is one year: the tree on it goes
from deep winter through blossom, leaf, fruit and leaf-fall back to snow. A brass index at the front points
at the season emblem passing under it, so the box is a calendar. Behind a plique-à-jour wall (translucent enamel
in brass cells) a Swiss-style movement runs: the pinned cylinder plucks a steel comb, the governor's air brake
spins, the spring barrel turns the stage through a year wheel, and the butterfly key slowly unwinds.
Everything is a function of one loop clock: no keys, no simulation.

Season time u = 4·Phase (0 = deep winter, 1 ≈ late spring, 2 ≈ late summer, 3 ≈ late autumn). Every change is a
window inside (0, 4), so frame N+1 = frame 1.

Run: Blender -b --factory-startup --python build.py -- [--preview f,..] [--look f,..] [--still f,..]
     [--wb f,..] [--clay] [--sound] [--bare] [--white] [--cam x,y,z,tx,ty,tz,lens] [--save-as x.blend]
  --look: Cycles at 50 %, 48 spp · --still: full Cycles · --wb: Workbench · --clay: clay/ copy for a motion check
  --sound: write musicbox.wav · --bare: movement only (no wall, stage or dome) · --white: white studio backdrop
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
for _lib in ("../../lib", "../../../.agents/skills/procedural-art/scripts"):   # public repo / monorepo
    if os.path.exists(os.path.join(HERE, _lib, "proc_blender.py")):
        sys.path.insert(0, os.path.abspath(os.path.join(HERE, _lib)))
        break
import proc_blender as pb  # noqa: E402

importlib.reload(pb)

DAY = HERE
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PI, TAU = math.pi, 2 * math.pi
NAME = "MusicBox"

FRAMES = 360                     # 12 s @ 30 fps, one turn of the stage = one year
Z_BODY = (0.07, 0.56)            # open cage: walnut plinth top → brass bezel underside
Z_GEAR = 0.585                   # bezel top = stage underside
Z_LID = 0.64                     # stage top
HM, RM = 0.12, 0.78              # grassy mound: height, radius
ZG = Z_LID + HM                  # tree base
YEAR_T, YEAR_RP, YEAR_Z = 120, 0.46, 0.525     # year wheel hung under the stage, on its centre shaft
PIN_T = 10
PIN_RP = YEAR_RP * PIN_T / YEAR_T
PIN_AZ = math.atan2(0.344, -0.36)                # its pinion tops the spring barrel's arbor (back left)
BARREL = ((YEAR_RP + PIN_RP) * math.cos(PIN_AZ), (YEAR_RP + PIN_RP) * math.sin(PIN_AZ), 0.17)   # x, y, radius
PLATE_Z = 0.10                                   # top of the movement's zamak bedplate
DOME_H = 1.10                                    # cloche: straight wall height above the stage (cap 0.62 on top)
DOME_RIM = 0.25                                  # cloche highlights, relative to the rim lights
CELL_MIN, CELL_DENSITY, CELL_INSET = 0.05, 130.0, 0.86   # plique-à-jour: seed spacing / density, pane size in cell
CYL_Y, CYL_Z, CYL_R = 0.20, 0.27, 0.11      # pinned cylinder (axis along X), Mapsa-style layout
TEETH = 24                       # comb teeth
ALPHA_C = PI / 4                 # pins meet the comb tips 45° below the front
TRUNK_H = 0.61
TREE_S = 1.15                    # whole tree scale about its foot (heights, lengths, thickness, leaves, fruit)
N1, M1 = 8, 12                   # branches × points
N2, M2 = 7, 6                    # twigs per branch × points
# the comb is tuned diatonically, A3 (longest tooth, left) … C7 (shortest, right)
COMB = [n + str(o) for o in range(3, 8) for n in "CDEFGAB"][5:5 + TEETH]
BEATS = 16                       # one loop = four bars of 4/4 = one bar per season, 80 bpm
SCORE = [                        # (beat, note): an original tune pinned onto the cylinder
    # winter → thaw (Am): sparse and high
    (0, "A3"), (0, "E5"), (1, "A5"), (1.5, "C6"), (2, "E4"), (2, "G5"), (2.5, "E5"), (3, "D5"),
    # spring (C → G): rising
    (4, "C4"), (4, "C5"), (4.5, "D5"), (5, "E5"), (6, "G4"), (6, "D5"), (6, "G5"), (6.5, "A5"), (7, "G5"),
    # summer (F → G): fullest, in thirds
    (8, "F4"), (8, "C5"), (8, "A5"), (9.5, "C6"), (10, "G4"), (10, "B5"), (10.5, "A5"), (11, "B4"), (11, "G5"),
    # autumn (Am → E): falling, left hanging on B to fall back into winter's E
    (12, "A3"), (12, "G5"), (12.5, "F5"), (13, "E5"), (14, "E4"), (14, "D5"), (14.5, "C5"), (15, "B3"), (15, "B4"),
]
PINS = [(COMB.index(n), b / BEATS) for b, n in SCORE]       # (tooth, loop phase of its pluck)
# where the season emblems sit on the stage (season time of the moment each one passes the index)
EMBLEMS = (("spring", 0.75), ("summer", 1.75), ("autumn", 2.75), ("winter", 3.75))


# ───────────────────────────────────────────────────────── helpers
def xyz(g, v):
    n = g.node("ShaderNodeSeparateXYZ", Vector=v)
    return [g.out(n, c) for c in "XYZ"]


def join(g, geos, label=None):
    n = g.node("GeometryNodeJoinGeometry", label=label)
    for geo in geos:
        g.link(geo, n, b_key="Geometry")
    return n


def smooth(g, geo):
    return g.node("GeometryNodeSetShadeSmooth", Geometry=geo)


def ease(g, v, a, b, label=None, lo=0.0, hi=1.0):
    return g.node("ShaderNodeMapRange", label=label, props={"interpolation_type": "SMOOTHSTEP"},
                  Value=v, From_Min=a, From_Max=b, To_Min=lo, To_Max=hi)


def lin(g, v, a, b, label=None):
    return g.node("ShaderNodeMapRange", label=label, Value=v, From_Min=a, From_Max=b, To_Min=0.0, To_Max=1.0)


def rnd(g, ident, seed, lo=0.0, hi=1.0):
    return g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT"}, Min=lo, Max=hi, ID=ident, Seed=seed)


def index_switch(g, kind, values, label):
    sw = g.node("GeometryNodeIndexSwitch", label=label, props={"data_type": kind})
    while len([x for x in sw.inputs if not pb._virtual(x)]) - 1 < len(values):
        sw.index_switch_items.new()
    g.set(sw, "Index", g.node("GeometryNodeInputIndex"))
    for i, v in enumerate(values):
        g.set(sw, str(i), v)
    return sw


def mix(g, a, b, t):
    return g.math("ADD", a, g.math("MULTIPLY", g.math("SUBTRACT", b, a), t))


def group(name, inputs, outputs):
    t = bpy.data.node_groups.new("PA_" + name, "GeometryNodeTree")
    for nm, kind, value in inputs:
        s = t.interface.new_socket(nm, in_out="INPUT", socket_type="NodeSocket" + kind)
        if value is not None:
            s.default_value = value
    for nm, kind in outputs:
        t.interface.new_socket(nm, in_out="OUTPUT", socket_type="NodeSocket" + kind)
    g = pb.Graph(t)
    gi, go = g.group_io()
    return t, g, gi, go


def tube(g, curve, radius, res=12, caps=True, by_radius=False):
    """Curve → round tube. by_radius: thickness from the curve's radius attribute (5.x needs it as Scale)."""
    prof = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=res, Radius=radius)
    n = g.node("GeometryNodeCurveToMesh", Curve=curve, Profile_Curve=prof, Fill_Caps=caps)
    if by_radius:
        g.link(g.node("GeometryNodeInputRadius"), n, b_key="Scale")
    return n


def store(g, geo, name, value, kind="FLOAT", domain="POINT"):
    return g.node("GeometryNodeStoreNamedAttribute", label=name, props={"data_type": kind, "domain": domain},
                  Geometry=geo, Name=name, Value=value)


def lathe(g, profile, segs=128, rings=96, label=None):
    """Turned part: a cylinder whose radius at height z follows profile(g, k) → (r, z); k = 0..1."""
    cy = g.node("GeometryNodeMeshCylinder", label=label, props={"fill_type": "NONE"}, Vertices=segs,
                Side_Segments=rings, Radius=1.0, Depth=1.0)
    x, y, z = xyz(g, g.node("GeometryNodeInputPosition"))
    k = g.math("ADD", z, 0.5)
    r, zz = profile(g, k)
    a = g.math("ARCTAN2", y, x)
    return g.node("GeometryNodeSetPosition", Geometry=cy,
                  Position=g.vec(g.math("MULTIPLY", r, g.math("COSINE", a)), g.math("MULTIPLY", r, g.math("SINE", a)),
                                 zz))


def cylinder(g, r, z0, z1, verts=None, fill="NGON"):
    """Smooth-sided cylinder, flat caps; enough segments that big ones don't facet in reflections."""
    verts = verts or max(32, min(384, int(r * 360)))
    c = g.node("GeometryNodeMeshCylinder", props={"fill_type": fill}, Vertices=verts, Radius=r, Depth=z1 - z0)
    c = g.node("GeometryNodeSetShadeSmooth", Geometry=g.out(c, "Mesh"), Selection=g.out(c, "Side"))
    return g.node("GeometryNodeTransform", Geometry=c, Translation=(0, 0, (z0 + z1) / 2))


def ground_z(g, r):
    """Height of the grassy mound at radius r (stage coordinates)."""
    q = g.math("MINIMUM", 1.0, g.math("DIVIDE", r, RM))
    return g.math("ADD", Z_LID, g.math("MULTIPLY", HM, g.math("POWER", g.math("SUBTRACT", 1.0,
                                                                                  g.math("MULTIPLY", q, q)), 1.4)))


def mesh_phase(w, t1, t2, beta):
    """Angle for gear 2 (t2 teeth, centre at azimuth beta from gear 1) when gear 1 (t1 teeth) is at w.
    PA_Gear teeth are centred at π/(4T), gaps at 5π/(4T): put a tooth of 1 into a gap of 2 at beta."""
    return lambda g: g.math("ADD", g.math("MULTIPLY", g.math("ADD", g.math("SUBTRACT", w, beta), PI / (4 * t1)),
                                          -t1 / t2), beta + PI - 5 * PI / (4 * t2))


# ───────────────────────────────────────────────────────── materials
def attr_color(mat, attr, a, b):
    """Base colour = mix(a, b) by a stored float attribute (the season state written by the nodes)."""
    g = pb.Graph(mat.node_tree)
    p = next(n for n in g.nodes if n.type == "BSDF_PRINCIPLED")
    at = g.node("ShaderNodeAttribute", props={"attribute_name": attr})
    mx = g.node("ShaderNodeMix", props={"data_type": "RGBA"}, Factor=g.out(at, "Fac"), A=(*a, 1), B=(*b, 1))
    g.link(g.out(mx, "Result"), p, b_key="Base Color")
    pb.arrange(g.tree)
    return mat


def plique_material():
    """Translucent enamel: per-cell colour from the same Voronoi as the brass cloisons, tinted by season round the
    drum (spring green-rose at the front left, summer, autumn amber, winter blue at the back)."""
    mat = bpy.data.materials.get("PA_Plique") or bpy.data.materials.new("PA_Plique")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    g = pb.Graph(nt)
    out = g.node("ShaderNodeOutputMaterial")
    co = g.node("ShaderNodeTexCoord")
    cell = g.out(g.node("ShaderNodeAttribute", label="per-cell random (from the nodes)",
                        props={"attribute_name": "cell"}), "Fac")
    tone = g.node("ShaderNodeCombineColor", Red=g.math("ADD", 0.55, g.math("MULTIPLY", 0.45, cell)),
                  Green=g.math("ADD", 0.55, g.math("MULTIPLY", 0.45, cell)),
                  Blue=g.math("ADD", 0.55, g.math("MULTIPLY", 0.45, cell)))
    ox, oy, _ = xyz(g, g.out(co, "Object"))
    az = g.math("DIVIDE", g.math("ADD", g.math("ARCTAN2", oy, ox), PI), TAU)
    ramp = g.node("ShaderNodeValToRGB", label="season round the drum", Fac=g.math("FRACT", g.math("ADD", az, g.math(
        "MULTIPLY", cell, 0.12))))
    cr = ramp.color_ramp
    stops = [(0.0, (0.10, 0.22, 0.65)), (0.2, (0.20, 0.55, 0.30)), (0.4, (0.85, 0.35, 0.45)),
             (0.6, (0.25, 0.60, 0.12)), (0.8, (0.95, 0.50, 0.08)), (1.0, (0.10, 0.22, 0.65))]
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], (*stops[-1][1], 1)
    for pos, c in stops[1:-1]:
        e = cr.elements.new(pos)
        e.color = (*c, 1)
    shade = g.node("ShaderNodeMix", props={"data_type": "RGBA", "blend_type": "MULTIPLY"}, Factor=0.35,
                   A=g.out(ramp, "Color"), B=tone)
    old = g.node("ShaderNodeHueSaturation", label="aged enamel: duller, a touch amber", Saturation=0.72, Value=0.82,
                 Color=g.out(shade, "Result"))
    old = g.node("ShaderNodeMix", props={"data_type": "RGBA", "blend_type": "MULTIPLY"}, Factor=0.35,
                 A=g.out(old, "Color"), B=(1.0, 0.82, 0.55, 1))
    glass = g.node("ShaderNodeBsdfTransparent", Color=g.out(old, "Result"))
    glow = g.node("ShaderNodeBsdfTranslucent", Color=g.out(old, "Result"))
    body = g.node("ShaderNodeMixShader", Fac=0.12, ins={1: glass, 2: glow})   # mostly see-through
    gloss = g.node("ShaderNodeBsdfGlossy", Roughness=0.12)            # old enamel: a little hazy
    fres = g.node("ShaderNodeFresnel", IOR=1.55)
    sh = g.node("ShaderNodeMixShader", Fac=fres, ins={1: body, 2: gloss})
    g.link(sh, out, b_key="Surface")
    pb.arrange(nt)
    mat.diffuse_color = (0.9, 0.9, 0.9, 1)
    return mat


def age(mat, tarnish=0.5, crevice=0.55, verdigris=0.0, seed=0.0):
    """Antique patina on a metal: blotchy dark-brown tarnish (noise), grime and green-blue verdigris packed into
    the crevices (AO), polished-back high spots, and roughness that wanders, so the brass reads as a century
    old: handled, never cleaned in the corners."""
    g = pb.Graph(mat.node_tree)
    p = next(n for n in g.nodes if n.type == "BSDF_PRINCIPLED")
    base = tuple(p.inputs["Base Color"].default_value)
    rough = p.inputs["Roughness"].default_value
    co = g.node("ShaderNodeTexCoord")
    n1 = g.node("ShaderNodeTexNoise", label="tarnish blotches", props={"noise_dimensions": "4D"},
                Vector=g.out(co, "Object"), W=seed, Scale=4.0, Detail=10.0, Roughness=0.66)
    n2 = g.node("ShaderNodeTexNoise", label="fine wear", props={"noise_dimensions": "3D"},
                Vector=g.out(co, "Object"), Scale=70.0, Detail=6.0)
    n3 = g.node("ShaderNodeTexNoise", label="verdigris speckle", props={"noise_dimensions": "4D"},
                Vector=g.out(co, "Object"), W=seed + 10.0, Scale=22.0, Detail=6.0, Roughness=0.7)
    blot = g.node("ShaderNodeMapRange", Value=g.out(n1, "Factor"), From_Min=0.30, From_Max=0.62)
    ao = g.node("ShaderNodeAmbientOcclusion", label="crevices", props={"only_local": True}, Distance=0.07)
    cav = g.math("POWER", g.math("SUBTRACT", 1.0, g.out(ao, "AO")), 0.7)
    cav.label = "cavity"
    dark = tuple(0.28 * (0.5 * c + 0.5 * sum(base[:3]) / 3) for c in base[:3])
    dark = (dark[0] * 1.1, dark[1] * 0.95, dark[2] * 0.75)                     # oxidised: brown, not grey
    col = g.node("ShaderNodeMix", label="tarnish", props={"data_type": "RGBA"},
                 Factor=g.math("MULTIPLY", g.out(blot, "Result"), tarnish), A=base, B=(*dark, 1))
    grime = g.node("ShaderNodeMix", label="grime in the crevices", props={"data_type": "RGBA", "blend_type": "MULTIPLY"},
                   Factor=g.math("MINIMUM", 1.0, g.math("MULTIPLY", cav, crevice)),
                   A=g.out(col, "Result"), B=(0.10, 0.08, 0.06, 1))
    spk = g.node("ShaderNodeMapRange", Value=g.out(n3, "Factor"), From_Min=0.5, From_Max=0.68)
    vmask = g.node("ShaderNodeMapRange", label="verdigris: only deep in the crevices, in patches", Value=g.math(
        "MULTIPLY", cav, g.out(spk, "Result")), From_Min=0.3, From_Max=0.6)
    vm = g.math("MULTIPLY", g.out(vmask, "Result"), verdigris)
    verd = g.node("ShaderNodeMix", label="verdigris", props={"data_type": "RGBA"}, Factor=vm,
                  A=g.out(grime, "Result"), B=(0.16, 0.30, 0.24, 1))
    g.link(g.out(verd, "Result"), p, b_key="Base Color")
    g.link(g.math("SUBTRACT", 1.0, vm), p, b_key="Metallic")                    # the crust isn't metal
    r = g.math("ADD", rough, g.math("ADD", g.math("MULTIPLY", g.out(blot, "Result"), 0.30 * tarnish),
                                    g.math("MULTIPLY", g.out(n2, "Factor"), 0.16)))
    g.link(g.math("ADD", r, g.math("MULTIPLY", vm, 0.6)), p, b_key="Roughness")
    pb.arrange(g.tree)
    return mat


def age_glass(mat):
    """Old cloche: faintly yellowed, with a breath of haze and dust that varies over the surface."""
    g = pb.Graph(mat.node_tree)
    p = next((n for n in g.nodes if "Roughness" in n.inputs and n.type != "OUTPUT_MATERIAL"), None)
    co = g.node("ShaderNodeTexCoord")
    dust = g.node("ShaderNodeTexNoise", label="dust and haze", Vector=g.out(co, "Object"), Scale=9.0, Detail=8.0)
    hz = g.node("ShaderNodeMapRange", Value=g.out(dust, "Factor"), From_Min=0.45, From_Max=0.75, To_Min=0.0,
                To_Max=0.05)
    g.link(g.out(hz, "Result"), p, b_key="Roughness")
    pb.arrange(g.tree)
    return mat


def materials():
    m = {}
    m["brass"] = pb.material("Brass", "brass", color=(0.80, 0.55, 0.22), roughness=0.22)
    m["gold"] = pb.material("Gold", "gold", color=(0.86, 0.64, 0.32), roughness=0.28)
    m["steel"] = pb.material("Steel", "metal", color=(0.70, 0.70, 0.72), roughness=0.18)
    m["zamak"] = pb.material("Zamak", "metal", color=(0.42, 0.43, 0.45), roughness=0.48)   # die-cast frame
    m["comb"] = pb.material("CombSteel", "metal", color=(0.36, 0.37, 0.39), roughness=0.30)  # hardened comb
    m["blued"] = pb.material("BluedSteel", "metal", color=(0.02, 0.05, 0.24), roughness=0.16)
    m["glass"] = age_glass(pb.material("Glass", "glass", color=(0.95, 0.92, 0.82), roughness=0.0, ior=1.5))
    for k, tn, vd, sd in (("brass", 1.0, 0.7, 1.0), ("gold", 0.9, 0.4, 2.0), ("steel", 0.8, 0.0, 3.0),
                          ("zamak", 0.9, 0.0, 4.0), ("comb", 0.7, 0.0, 5.0)):
        age(m[k], tn, crevice=1.0, verdigris=vd, seed=sd)
    # walnut: turned grain from position, lacquered
    wal = pb.material("Walnut", "matte", color=(0.12, 0.055, 0.025), roughness=0.35)
    g = pb.Graph(wal.node_tree)
    p = next(n for n in g.nodes if n.type == "BSDF_PRINCIPLED")
    co = g.node("ShaderNodeTexCoord")
    sk = g.node("ShaderNodeMapping", Vector=g.out(co, "Object"), Scale=(1.0, 1.0, 9.0))
    wv = g.node("ShaderNodeTexWave", label="grain", props={"wave_type": "BANDS", "bands_direction": "Z"},
                Vector=sk, Scale=3.0, Distortion=6.0, Detail=3.0, Detail_Scale=1.5)
    ramp = g.node("ShaderNodeMix", props={"data_type": "RGBA"}, Factor=g.out(wv, "Fac"),
                  A=(0.025, 0.010, 0.005, 1), B=(0.09, 0.040, 0.018, 1))
    g.link(g.out(ramp, "Result"), p, b_key="Base Color")
    p.inputs["Coat Weight"].default_value = 1.0
    p.inputs["Coat Roughness"].default_value = 0.22          # old lacquer, rubbed dull
    p.inputs["Coat Tint"].default_value = (0.85, 0.7, 0.45, 1.0)
    pb.arrange(g.tree)
    m["walnut"] = wal
    # enamel leaves: green → amber/red by the stored "turn", per-leaf hue
    leaf = pb.material("LeafEnamel", "matte", color=(0.1, 0.3, 0.05), roughness=0.3)
    g = pb.Graph(leaf.node_tree)
    p = next(n for n in g.nodes if n.type == "BSDF_PRINCIPLED")
    turn = g.node("ShaderNodeAttribute", props={"attribute_name": "turn"})
    hue = g.node("ShaderNodeAttribute", props={"attribute_name": "hue"})
    fall = g.node("ShaderNodeMix", props={"data_type": "RGBA"}, Factor=g.out(hue, "Fac"),
                  A=(0.80, 0.42, 0.03, 1), B=(0.62, 0.06, 0.02, 1))
    green = g.node("ShaderNodeMix", props={"data_type": "RGBA"}, Factor=g.out(hue, "Fac"),
                   A=(0.06, 0.28, 0.03, 1), B=(0.20, 0.42, 0.04, 1))
    col = g.node("ShaderNodeMix", props={"data_type": "RGBA"}, Factor=g.out(turn, "Fac"),
                 A=g.out(green, "Result"), B=g.out(fall, "Result"))
    g.link(g.out(col, "Result"), p, b_key="Base Color")
    p.inputs["Coat Weight"].default_value = 0.6
    p.inputs["Coat Roughness"].default_value = 0.12
    p.inputs["Subsurface Weight"].default_value = 0.15
    pb.arrange(g.tree)
    m["leaf"] = leaf
    m["blossom"] = pb.material("Blossom", "pearl", color=(0.98, 0.80, 0.84), roughness=0.25)
    m["fruit"] = attr_color(pb.material("Fruit", "matte", color=(0.6, 0.05, 0.04), roughness=0.25, coat=1.0),
                            "ripe", (0.22, 0.42, 0.05), (0.62, 0.03, 0.03))
    m["grass"] = attr_color(pb.material("Grass", "matte", color=(0.10, 0.25, 0.04), roughness=0.5),
                            "dry", (0.07, 0.22, 0.03), (0.45, 0.32, 0.10))
    m["moss"] = pb.material("Moss", "matte", color=(0.05, 0.09, 0.02), roughness=0.9)
    for k in ("grass", "moss"):
        bsdf = next(n for n in m[k].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Specular IOR Level"].default_value = 0.15
        bsdf.inputs["Roughness"].default_value = 0.85
    m["plique"] = plique_material()
    m["snow"] = pb.material("Snow", "matte", color=(0.80, 0.82, 0.86), roughness=0.6, subsurface=0.3)
    return m


# ───────────────────────────────────────────────────────── node groups
def gear_group():
    """Flat gear (XY, thickness +Z): trapezoid teeth from a 4·T-point circle, arbor and lightening holes."""
    t, g, gi, go = group("Gear", [("Teeth", "Int", 16), ("Pitch Radius", "Float", 0.03),
                                  ("Thickness", "Float", 0.003), ("Holes", "Int", 5)], [("Gear", "Geometry")])
    T, rp, th = gi.outputs["Teeth"], gi.outputs["Pitch Radius"], gi.outputs["Thickness"]
    module = g.math("DIVIDE", rp, T)
    circ = g.node("GeometryNodeCurvePrimitiveCircle", label="4 points per tooth",
                  Resolution=g.math("MULTIPLY", T, 4), Radius=1.0)
    tip = g.math("LESS_THAN", g.math("FLOORED_MODULO", g.node("GeometryNodeInputIndex"), 4), 1.5)
    r = g.math("ADD", g.math("SUBTRACT", rp, g.math("MULTIPLY", module, 1.15)),
               g.math("MULTIPLY", tip, g.math("MULTIPLY", module, 2.3)))
    rim = g.node("GeometryNodeSetPosition", Geometry=circ,
                 Position=g.vmath("SCALE", g.node("GeometryNodeInputPosition"), scale=r))
    hub = g.node("GeometryNodeCurvePrimitiveCircle", label="arbor hole", Resolution=24,
                 Radius=g.math("MULTIPLY", rp, 0.14))
    hp = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=gi.outputs["Holes"],
                Radius=g.math("MULTIPLY", rp, 0.52))
    hole = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=24, Radius=g.math("MULTIPLY", rp, 0.24))
    holes = g.node("GeometryNodeRealizeInstances", Geometry=g.node(
        "GeometryNodeInstanceOnPoints", label="lightening holes",
        Points=g.node("GeometryNodeCurveToPoints", props={"mode": "EVALUATED"}, Curve=hp), Instance=hole))
    fill = g.node("GeometryNodeFillCurve", label="holes cut by nesting", Curve=join(g, [rim, hub, holes]))
    ext = g.node("GeometryNodeExtrudeMesh", props={"mode": "FACES"}, Mesh=fill, Offset=g.vec(0, 0, th),
                 Individual=False)
    solid = join(g, [g.node("GeometryNodeFlipFaces", Mesh=fill), g.out(ext, "Mesh")])
    g.link(g.node("GeometryNodeMergeByDistance", Geometry=solid, Distance=1e-6), go, b_key="Gear")
    pb.arrange(t)
    return t


def flat_shape(g, curve, th):
    """Filled closed curve → a slab th thick (for emblems)."""
    fill = g.node("GeometryNodeFillCurve", Curve=curve)
    ext = g.node("GeometryNodeExtrudeMesh", props={"mode": "FACES"}, Mesh=fill, Offset=g.vec(0, 0, th),
                 Individual=False)
    slab = g.node("GeometryNodeMergeByDistance", label="weld the back on", Geometry=join(
        g, [g.node("GeometryNodeFlipFaces", Mesh=fill), g.out(ext, "Mesh")]), Distance=1e-5)
    # both faces flat, only the side walls smooth: front and back shade alike
    _, _, nz = xyz(g, g.node("GeometryNodeInputNormal"))
    return g.node("GeometryNodeSetShadeSmooth", label="flat faces, smooth walls", props={"domain": "FACE"},
                  Geometry=slab, Shade_Smooth=g.math("LESS_THAN", g.math("ABSOLUTE", nz), 0.5))


def polar_curve(g, rfun, res=120):
    """Closed curve r = rfun(g, θ) around the origin."""
    c = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=res, Radius=1.0)
    x, y, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    th = g.math("ARCTAN2", y, x)
    r = rfun(g, th)
    return g.node("GeometryNodeSetPosition", Geometry=c,
                  Position=g.vec(g.math("MULTIPLY", r, g.math("COSINE", th)), g.math("MULTIPLY", r, g.math("SINE", th)),
                                 0))


def emblem(g, kind, size, th=0.006):
    """Season emblem in XY around the origin, ~size across."""
    if kind == "spring":      # five-petal blossom
        cur = polar_curve(g, lambda gg, t: gg.math("ADD", 0.3, gg.math("MULTIPLY", 0.7, gg.math(
            "POWER", gg.math("ABSOLUTE", gg.math("COSINE", gg.math("MULTIPLY", t, 2.5))), 0.6))))
        shp = flat_shape(g, cur, th)
    elif kind == "summer":    # sun: disc and twelve rays
        rays = g.node("GeometryNodeCurveStar", Points=12, Inner_Radius=0.62, Outer_Radius=1.0, Twist=0.0)
        disc = g.node("GeometryNodeTransform", Geometry=flat_shape(
            g, g.node("GeometryNodeCurvePrimitiveCircle", Resolution=48, Radius=0.5), th),
            Translation=(0, 0, th * 0.6))
        shp = join(g, [flat_shape(g, rays, th), disc])
    elif kind == "autumn":    # leaf: pointed at the tip, round at the base, with a stalk
        c = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=96, Radius=1.0)
        x, y, _ = xyz(g, g.node("GeometryNodeInputPosition"))
        w = g.math("MULTIPLY", 0.5, g.math("SQRT", g.math("MULTIPLY", g.math("SUBTRACT", 1.0, x), 0.5)))
        cur = g.node("GeometryNodeSetPosition", Geometry=c, Position=g.vec(x, g.math("MULTIPLY", y, w), 0))
        stalk = g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCube", Size=(0.5, 0.08, th)),
                       Translation=(-1.1, 0, th / 2))
        shp = g.node("GeometryNodeTransform", Geometry=join(g, [flat_shape(g, cur, th), stalk]),
                     Rotation=(0, 0, PI / 4))
    else:                     # snowflake: six arms with side twigs
        arm = join(g, [g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCube", Size=(1.0, 0.1, th)),
                              Translation=(0.5, 0, th / 2))] +
                   [g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCube", Size=(0.36, 0.08, th)),
                           Rotation=(0, 0, s * 0.8), Translation=(0.62 + 0.12 * math.cos(s * 0.8),
                                                                 0.12 * math.sin(s * 0.8), th / 2))
                    for s in (1, -1)])
        arms = g.node("GeometryNodeInstanceOnPoints", Points=g.node("GeometryNodePoints", Count=6), Instance=arm,
                      Rotation=g.node("FunctionNodeEulerToRotation", Euler=g.vec(0, 0, g.math(
                          "MULTIPLY", g.node("GeometryNodeInputIndex"), TAU / 6))))
        shp = g.node("GeometryNodeRealizeInstances", Geometry=arms)
    return g.node("GeometryNodeTransform", label=f"{kind} emblem", Geometry=shp, Scale=(size / 2, size / 2, 1))


def leaf_mesh(g):
    """Leaf in XY, stalk at the origin, tip along +Y, V-folded on the midrib, bent down at the tip."""
    grid = g.node("GeometryNodeMeshGrid", Size_X=1.0, Size_Y=1.0, Vertices_X=5, Vertices_Y=9)
    x, y, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    t = g.math("ADD", y, 0.5)
    w = g.math("MULTIPLY", 0.55, g.math("POWER", g.math("SINE", g.math("MULTIPLY", t, PI)), 0.8))
    X = g.math("MULTIPLY", x, w)
    Z = g.math("SUBTRACT", g.math("MULTIPLY", g.math("ABSOLUTE", X), 0.45), g.math("MULTIPLY", 0.25,
                                                                                  g.math("MULTIPLY", t, t)))
    return g.node("GeometryNodeSetPosition", label="leaf", Geometry=grid, Position=g.vec(X, t, Z))


def blossom_mesh(g):
    cur = polar_curve(g, lambda gg, t: gg.math("ADD", 0.35, gg.math("MULTIPLY", 0.65, gg.math(
        "POWER", gg.math("ABSOLUTE", gg.math("COSINE", gg.math("MULTIPLY", t, 2.5))), 0.7))), 80)
    fill = g.node("GeometryNodeFillCurve", Curve=cur)
    fill = g.node("GeometryNodeSubdivideMesh", Mesh=fill, Level=1)
    p = g.node("GeometryNodeInputPosition")
    x, y, _ = xyz(g, p)
    d2 = g.math("ADD", g.math("MULTIPLY", x, x), g.math("MULTIPLY", y, y))
    cup = g.node("GeometryNodeSetPosition", label="cupped blossom", Geometry=fill,
                 Offset=g.vec(0, 0, g.math("MULTIPLY", d2, 0.35)))
    heart = g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshUVSphere", Segments=10, Rings=6,
                                                            Radius=0.16), Translation=(0, 0, 0.04))
    return join(g, [cup, heart])


def fall(g, P, u, td, dur, r, spread, lift, label):
    """Something let go at season time td drifts from P to the mound in `dur`, then lies there.
    Returns (position, progress)."""
    p = lin(g, u, td, g.math("ADD", td, dur), label=label)
    px, py, pz = xyz(g, P)
    s = g.math("ADD", spread[0], g.math("MULTIPLY", r, spread[1]))
    gx, gy = g.math("MULTIPLY", px, s), g.math("MULTIPLY", py, s)
    rr = g.math("SQRT", g.math("ADD", g.math("MULTIPLY", gx, gx), g.math("MULTIPLY", gy, gy)))
    k = g.math("MINIMUM", 1.0, g.math("DIVIDE", 0.71, g.math("MAXIMUM", rr, 1e-4)))
    gx, gy = g.math("MULTIPLY", gx, k), g.math("MULTIPLY", gy, k)
    gz = g.math("ADD", ground_z(g, g.math("MULTIPLY", rr, k)), lift)
    sp = ease(g, p, 0.0, 1.0)
    bump = g.math("SINE", g.math("MULTIPLY", p, PI))
    sway = g.math("MULTIPLY", g.math("MULTIPLY", bump, 0.06), g.math(
        "SINE", g.math("ADD", g.math("MULTIPLY", p, TAU * 1.3), g.math("MULTIPLY", r, TAU))))
    sway2 = g.math("MULTIPLY", g.math("MULTIPLY", bump, 0.06), g.math(
        "COSINE", g.math("ADD", g.math("MULTIPLY", p, TAU * 1.1), g.math("MULTIPLY", r, TAU))))
    X = g.math("ADD", mix(g, px, gx, sp), sway)
    Y = g.math("ADD", mix(g, py, gy, sp), sway2)
    Z = mix(g, pz, gz, g.math("POWER", p, 1.3))
    return g.vec(X, Y, Z), p


# ───────────────────────────────────────────────────────── the tree
def trunk_pos(g, t):
    """A gently S-curved trunk that comes back over its roots, so the crown sits balanced. Below t = 0 it goes
    straight down into the mound, so the leaning foot never lifts a cut edge off the grass."""
    s = g.math("SINE", g.math("MULTIPLY", g.math("MAXIMUM", t, 0.0), TAU))
    return g.vec(g.math("MULTIPLY", 0.045 * TREE_S, s), g.math("MULTIPLY", -0.02 * TREE_S, s),
                 g.math("ADD", ZG - 0.04, g.math("MULTIPLY", t, (TRUNK_H + 0.04) * TREE_S)))


def zigzag(g, f, segs, key, seed, a_side, a_up):
    """Natural crooks: two triangle waves (kinks every 2 and every 3 segments, random signs) sideways and up, so the
    bends are irregular. Kinks fall on control points (f·segs is an integer there), so the curve through them
    stays close to this formula and side shoots computed from it stay attached. Grows from 0 at the base."""
    x = g.math("MULTIPLY", f, segs)
    t2 = g.math("SUBTRACT", g.math("PINGPONG", x, 2.0), 1.0)
    t3 = g.math("SUBTRACT", g.math("MULTIPLY", g.math("PINGPONG", x, 3.0), 2 / 3), 1.0)
    t2b = g.math("SUBTRACT", g.math("PINGPONG", g.math("ADD", x, 1.0), 2.0), 1.0)

    def sgn(k):
        return g.math("SIGN", rnd(g, key, seed + k if isinstance(seed, int) else g.math("ADD", seed, k), -1.0, 1.0))
    ramp = g.math("POWER", f, 0.7)
    side = g.math("MULTIPLY", g.math("MULTIPLY", ramp, a_side), g.math(
        "ADD", g.math("MULTIPLY", t2, sgn(0)), g.math("MULTIPLY", g.math("MULTIPLY", t3, sgn(1)), 0.7)))
    up = g.math("MULTIPLY", g.math("MULTIPLY", ramp, a_up), g.math(
        "ADD", g.math("MULTIPLY", t2b, sgn(2)), g.math("MULTIPLY", g.math("MULTIPLY", t3, sgn(3)), 0.5)))
    return side, up


def limb_group():
    """PA_MB_Limb: the point at fraction Along of one limb (branch or twig), as its own node group so every caller is a
    single node. Heading/Elevation aim it from Base; it sags by Droop·f² and its tip lifts by Lift·f³; then the
    crooks (zigzag) bend it sideways and up by Sideways/Up × Length."""
    t = bpy.data.node_groups.get("PA_MB_Limb")
    if t:
        return t
    t, g, gi, go = group("MB_Limb", [("Base", "Vector", None), ("Heading", "Float", 0.0), ("Elevation", "Float", 0.0),
                                     ("Length", "Float", 0.5), ("Along", "Float", 0.0), ("Droop", "Float", 0.0),
                                     ("Lift", "Float", 0.0), ("Segments", "Float", 11.0), ("Key", "Float", 0.0),
                                     ("Seed", "Int", 0), ("Sideways", "Float", 0.0), ("Up", "Float", 0.0)],
                         [("Position", "Vector")])
    o = gi.outputs
    base, az, el, L, f = o["Base"], o["Heading"], o["Elevation"], o["Length"], o["Along"]
    g.begin_section("a · Heading, sag and lift")
    h = g.math("MULTIPLY", g.math("MULTIPLY", L, f), g.math("COSINE", el))
    f2 = g.math("MULTIPLY", f, f)
    bend = g.math("ADD", g.math("MULTIPLY", g.math("MULTIPLY", f2, f), o["Lift"]),
                  g.math("MULTIPLY", f2, g.math("MULTIPLY", o["Droop"], -1.0)))
    v = g.math("MULTIPLY", L, g.math("ADD", g.math("MULTIPLY", f, g.math("SINE", el)), bend))
    dx, dy = g.math("MULTIPLY", h, g.math("COSINE", az)), g.math("MULTIPLY", h, g.math("SINE", az))
    g.begin_section("b · Crooks")
    sd, up = zigzag(g, f, o["Segments"], o["Key"], o["Seed"], o["Sideways"], o["Up"])
    sd, up = g.math("MULTIPLY", sd, L), g.math("MULTIPLY", up, L)
    dx = g.math("SUBTRACT", dx, g.math("MULTIPLY", sd, g.math("SINE", az)))
    dy = g.math("ADD", dy, g.math("MULTIPLY", sd, g.math("COSINE", az)))
    v = g.math("ADD", v, up)
    g.link(g.vmath("ADD", base, g.vec(dx, dy, v)), go, b_key="Position")
    g.end_section()
    pb.arrange(t)
    return t


def limb(g, base, az, el, L, f, droop, tip, zig):
    """One PA_MB_Limb node. zig = (segments, key, seed, sideways, up): the crooks, as fractions of L."""
    segs, key, seed, a_side, a_up = zig
    return g.group(limb_group(), Base=base, Heading=az, Elevation=el, Length=L, Along=f, Droop=droop, Lift=tip,
                   Segments=segs, Key=key, Seed=seed, Sideways=a_side, Up=a_up)


def branch(g, b):
    """Branch b: eight even directions round the trunk (3/8 turn apart), low ones long and near level, sagging a
    little then lifting at the tip, top ones short and upright: a rounded, balanced crown."""
    bn = g.math("DIVIDE", b, N1 - 1)
    fb = g.math("ADD", 0.38, g.math("MULTIPLY", bn, 0.62))
    az = g.math("ADD", g.math("MULTIPLY", b, TAU * 3 / 8), rnd(g, b, 11, -0.2, 0.2))
    el = g.math("ADD", g.math("ADD", 0.38, g.math("MULTIPLY", g.math("POWER", bn, 1.3), 0.72)), rnd(g, b, 12, -0.06, 0.06))
    L = g.math("MULTIPLY", TREE_S, g.math("ADD", g.math("SUBTRACT", 0.676, g.math("MULTIPLY", bn, 0.312)),
                                         rnd(g, b, 13, -0.03, 0.03)))
    droop = g.math("MULTIPLY", 0.16, g.math("SUBTRACT", 1.0, bn))
    return dict(base=trunk_pos(g, fb), az=az, el=el, L=L, droop=droop, tip=0.26, key=b)


def branch_at(g, br, f):
    return limb(g, br["base"], br["az"], br["el"], br["L"], f, br["droop"], br["tip"],
                zig=(M1 - 1, br["key"], 81, 0.07, 0.05))


def twig_f0(g, j):
    """Where twig j sits on its branch: 0.25 … 0.75, so the branch runs on past its last twig as the leader."""
    return g.math("ADD", 0.25, g.math("MULTIPLY", j, 0.5 / (N2 - 1)))


def twig(g, b, j):
    br = branch(g, b)
    tid = g.math("ADD", g.math("MULTIPLY", b, N2), j)
    f0 = twig_f0(g, j)
    side = g.math("SUBTRACT", g.math("MULTIPLY", g.math("FLOORED_MODULO", j, 2), 2.0), 1.0)
    az = g.math("ADD", br["az"], g.math("MULTIPLY", side, rnd(g, tid, 21, 0.5, 1.0)))
    el = rnd(g, tid, 22, 0.05, 0.5)
    L = g.math("MULTIPLY", rnd(g, tid, 23, 0.12 * TREE_S, 0.22 * TREE_S), g.math("SUBTRACT", 1.25, g.math("MULTIPLY", f0, 0.9)))
    return dict(base=branch_at(g, br, f0), az=az, el=el, L=L, key=tid)


def tree_group():
    """Tree on the mound: wood, snow on the branches, leaves, blossom, fruit (all in stage coordinates)."""
    t, g, gi, go = group("MB_Tree", [("Season", "Float", 0.0), ("Phase", "Float", 0.0)],
                         [("Wood", "Geometry"), ("Branch Snow", "Geometry"), ("Leaves", "Geometry"),
                          ("Blossom", "Geometry"), ("Fruit", "Geometry")])
    u, phase = gi.outputs["Season"], gi.outputs["Phase"]
    idx = g.node("GeometryNodeInputIndex")

    g.begin_section("a · Trunk")
    # trunk
    tf = g.math("DIVIDE", g.math("SUBTRACT", idx, 1), 11)       # first point sunk into the mound
    trunk_pts = g.node("GeometryNodePoints", label="trunk", Count=13, Position=trunk_pos(g, tf))
    trunk = g.node("GeometryNodePointsToCurves", Points=trunk_pts, Weight=tf)
    sf = g.node("GeometryNodeSplineParameter")
    fac = g.out(sf, "Factor")
    th = g.math("MAXIMUM", tf, 0.0)
    trunk = g.node("GeometryNodeSetCurveRadius", Curve=trunk, Radius=g.math("ADD", g.math(
        "MULTIPLY", 0.075 * TREE_S, g.math("SUBTRACT", 1.0, g.math("MULTIPLY", th, 0.6))), g.math(
        "MULTIPLY", 0.052 * TREE_S, g.math("POWER", g.math("SUBTRACT", 1.0, th), 6.0))))
    g.begin_section("b · Branches")
    # branches
    b = g.math("FLOOR", g.math("DIVIDE", idx, M1))
    f = g.math("DIVIDE", g.math("FLOORED_MODULO", idx, M1), M1 - 1)
    br = branch(g, b)
    br_pts = g.node("GeometryNodePoints", label=f"{N1} branches", Count=N1 * M1,
                    Position=branch_at(g, br, f))
    branches = g.node("GeometryNodePointsToCurves", Points=br_pts, Curve_Group_ID=b, Weight=f)
    def taper(tip, k):
        """1 at the base → `tip` at the end, thinning faster towards the end, so limbs finish in a point."""
        return g.math("ADD", tip, g.math("MULTIPLY", 1.0 - tip, g.math("POWER", g.math("SUBTRACT", 1.0, fac), k)))

    branches = g.node("GeometryNodeSetCurveRadius", Curve=branches, Radius=g.math(
        "MULTIPLY", 0.033 * TREE_S, taper(0.18, 0.9)))
    g.begin_section("c · Twigs")
    # twigs
    b2 = g.math("FLOOR", g.math("DIVIDE", idx, N2 * M2))
    j2 = g.math("FLOORED_MODULO", g.math("FLOOR", g.math("DIVIDE", idx, M2)), N2)
    f2 = g.math("DIVIDE", g.math("FLOORED_MODULO", idx, M2), M2 - 1)
    tw = twig(g, b2, j2)
    tw_pts = g.node("GeometryNodePoints", label=f"{N2} twigs per branch", Count=N1 * N2 * M2,
                    Position=limb(g, tw["base"], tw["az"], tw["el"], tw["L"], f2, 0.05, 0.3,
                                  zig=(M2 - 1, tw["key"], 91, 0.08, 0.05)))
    twigs = g.node("GeometryNodePointsToCurves", Points=tw_pts,
                   Curve_Group_ID=g.math("FLOOR", g.math("DIVIDE", idx, M2)), Weight=f2)
    # a twig is half as thick as its branch where it leaves it, so it never outweighs the branch tip
    tw_r0 = g.math("MULTIPLY", 0.0165 * TREE_S, g.math("SUBTRACT", 1.0, g.math("MULTIPLY", twig_f0(g, j2), 0.72)))
    twigs = g.node("GeometryNodeSetCurveRadius", Curve=twigs, Radius=g.math("MULTIPLY", tw_r0, taper(0.25, 0.9)))
    limbs = join(g, [trunk, branches, twigs])
    limbs = g.node("GeometryNodeCurveSplineType", props={"spline_type": "CATMULL_ROM"}, Curve=limbs)
    limbs = g.node("GeometryNodeSetSplineResolution", Geometry=limbs, Resolution=4)
    limbs = g.node("GeometryNodeSetCurveTilt", label="twisted like drawn wire", Curve=limbs,
                   Tilt=g.math("MULTIPLY", g.out(g.node("GeometryNodeSplineParameter"), "Length"), 9.0))
    prof = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=32, Radius=1.0)
    qx, qy, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    qr = g.math("ADD", 1.0, g.math("MULTIPLY", 0.12, g.math("COSINE", g.math("MULTIPLY", g.math("ARCTAN2", qy, qx), 7.0))))
    prof = g.node("GeometryNodeSetPosition", label="fluted section", Geometry=prof,
                  Position=g.vmath("SCALE", g.node("GeometryNodeInputPosition"), scale=qr))
    wood = g.node("GeometryNodeCurveToMesh", Curve=limbs, Profile_Curve=prof, Fill_Caps=True)
    g.link(g.node("GeometryNodeInputRadius"), wood, b_key="Scale")
    g.link(smooth(g, wood), go, b_key="Wood")

    g.begin_section("d · Snow on the branches")
    # snow lying on the branches: the same curves, thinner, lifted onto their tops
    bs = g.math("ADD", g.math("SUBTRACT", 1.0, ease(g, u, 0.05, 0.35)), ease(g, u, 3.35, 3.8))
    bs.label = "branch snow: melts in early spring, settles late in winter"
    rad = g.node("GeometryNodeInputRadius")
    sn = g.node("GeometryNodeSetPosition", Geometry=join(g, [branches, twigs]),
                Offset=g.vec(0, 0, g.math("MULTIPLY", g.math("MULTIPLY", rad, 0.75), bs)))
    sn = g.node("GeometryNodeSetCurveRadius", Curve=sn, Radius=g.math("MULTIPLY", rad,
                                                                      g.math("MULTIPLY", bs, 0.9)))
    sn = g.node("GeometryNodeCurveSplineType", props={"spline_type": "CATMULL_ROM"}, Curve=sn)
    g.link(smooth(g, tube(g, sn, 1.0, 8, by_radius=True)), go, b_key="Branch Snow")

    g.begin_section("e · Anchors")
    # anchors for leaves and blossom: points ON the wood, evenly along the outer part of every twig and along the
    # leading end of every branch (past its last twig), so no leaf hangs in the air
    def along(curve, count, keep_from, label):
        p = g.node("GeometryNodeCurveToPoints", label=label, props={"mode": "COUNT"}, Curve=curve, Count=count)
        pts = store(g, g.out(p, "Points"), "tan", g.out(p, "Tangent"), kind="FLOAT_VECTOR")   # which way the wood runs
        return g.node("GeometryNodeDeleteGeometry", props={"domain": "POINT"}, Geometry=pts,
                      Selection=g.math("LESS_THAN", g.math("FLOORED_MODULO", idx, count), keep_from - 0.5))

    tw_anchor = along(twigs, 10, 2, "outer twig")
    br_anchor = along(branches, 16, 6, "branch leader")
    anchors = join(g, [tw_anchor, br_anchor], label="leaf anchors")
    pos = g.node("GeometryNodeInputPosition")
    tan = g.node("GeometryNodeInputNamedAttribute", label="tan: the way the wood runs",
                 props={"data_type": "FLOAT_VECTOR"}, Name="tan")
    across = g.vmath("NORMALIZE", g.vmath("CROSS_PRODUCT", g.out(tan, "Attribute"), (0.0, 0.0, 1.0)))
    across.label = "across the twig"
    side = g.math("SIGN", rnd(g, idx, 36, -1.0, 1.0))      # left or right of the twig, at random
    side.label = "left or right"

    def facing(along_w, side_w, up_w, wobble, seed):
        """Unit direction off the wood: forward along it, to one side, and up, plus a little randomness.
        Returns (yaw, pitch) for a shape whose tip/face starts along +Y / +Z."""
        w = g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT_VECTOR"}, Min=(-wobble,) * 3,
                   Max=(wobble,) * 3, Seed=seed)
        d = g.vmath("ADD", g.vmath("ADD", g.vmath("SCALE", g.out(tan, "Attribute"), scale=along_w),
                                   g.vmath("SCALE", across, scale=g.math("MULTIPLY", side, side_w))),
                    g.vmath("ADD", g.vec(0, 0, up_w), w))
        dx, dy, dz = xyz(g, g.vmath("NORMALIZE", d))
        return g.math("SUBTRACT", g.math("ARCTAN2", dy, dx), PI / 2), dz

    def scatter(amount, seed, jit):
        d = g.node("GeometryNodeDuplicateElements", props={"domain": "POINT"}, Geometry=anchors, Amount=amount)
        off = g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT_VECTOR"}, Min=(-jit, -jit, -jit * 0.6),
                     Max=(jit, jit, jit), Seed=seed)
        return g.node("GeometryNodeSetPosition", Geometry=g.out(d, "Geometry"), Offset=off)

    g.begin_section("f · Leaves")
    # ── leaves: grow in late spring, turn in autumn, let go, lie on the mound until the snow covers them
    lp = scatter(5, 3, 0.03 * TREE_S)
    r = rnd(g, idx, 31)
    grow = ease(g, u, g.math("ADD", 0.9, g.math("MULTIPLY", r, 0.2)), g.math("ADD", 1.25, g.math("MULTIPLY", r, 0.2)),
                label="leaves unfold")
    turn = ease(g, u, g.math("ADD", 2.05, g.math("MULTIPLY", r, 0.3)), g.math("ADD", 2.4, g.math("MULTIPLY", r, 0.3)),
                label="leaves turn")
    td = g.math("ADD", 2.5, g.math("MULTIPLY", r, 0.55))
    P, p = fall(g, pos, u, td, 0.38, r, (1.1, 0.35), 0.004, "leaf fall")
    gone = ease(g, u, 3.45, 3.75, label="under the snow")
    scale = g.math("MULTIPLY", g.math("MULTIPLY", grow, g.math("SUBTRACT", 1.0, gone)), 0.084 * TREE_S)
    # each leaf leaves its twig to one side, leaning towards the tip and a little up (toward the light)
    yaw, dz = facing(0.55, 1.0, 0.4, 0.3, 32)
    flutter = g.math("MULTIPLY", 0.12, g.math("SINE", g.math("MULTIPLY", g.math("ADD", g.math("MULTIPLY", phase, 14),
                                                                                     r), TAU)))
    tilt = g.math("ADD", g.math("ARCSINE", dz), flutter)
    tumble = g.math("SINE", g.math("MULTIPLY", p, PI))
    ex = g.math("ADD", mix(g, tilt, 0.0, p), g.math("MULTIPLY", tumble, rnd(g, idx, 34, -2.5, 2.5)))
    ey = g.math("MULTIPLY", tumble, 1.2)
    ez = g.math("ADD", yaw, g.math("MULTIPLY", p, rnd(g, idx, 35, -2.0, 2.0)))
    lp = g.node("GeometryNodeSetPosition", Geometry=lp, Position=P)
    lp = store(g, lp, "turn", turn)
    lp = store(g, lp, "hue", r)
    lv = g.node("GeometryNodeInstanceOnPoints", label="leaves", Points=lp, Instance=leaf_mesh(g),
                Rotation=g.node("FunctionNodeEulerToRotation", Euler=g.vec(ex, ey, ez)), Scale=scale)
    g.link(g.node("GeometryNodeRealizeInstances", Geometry=lv), go, b_key="Leaves")

    g.begin_section("g · Blossom")
    # ── blossom: opens in spring, petals... the whole flower lets go and fades into the grass
    bp = scatter(2, 5, 0.025 * TREE_S)
    rb = rnd(g, idx, 41)
    bloom = ease(g, u, g.math("ADD", 0.3, g.math("MULTIPLY", rb, 0.2)), g.math("ADD", 0.55, g.math("MULTIPLY", rb, 0.2)),
                 label="blossom opens")
    tdb = g.math("ADD", 0.75, g.math("MULTIPLY", rb, 0.35))
    Pb, pbp = fall(g, pos, u, tdb, 0.32, rb, (1.05, 0.45), 0.006, "blossom falls")
    gone_b = ease(g, u, g.math("ADD", tdb, 0.35), g.math("ADD", tdb, 0.6), label="withers in the grass")
    scale_b = g.math("MULTIPLY", g.math("MULTIPLY", bloom, g.math("SUBTRACT", 1.0, gone_b)), 0.05 * TREE_S)
    # each blossom opens upward and out to its side of the twig: its face (+Z) turns to that direction
    yaw_b, nz = facing(0.2, 0.6, 0.8, 0.3, 42)
    tum_b = g.math("SINE", g.math("MULTIPLY", pbp, PI))
    exb = g.math("ADD", mix(g, g.math("MULTIPLY", -1.0, g.math("ARCCOSINE", nz)), 0.0, pbp), g.math("MULTIPLY", tum_b,
                                                                             rnd(g, idx, 43, -3.0, 3.0)))
    bp = g.node("GeometryNodeSetPosition", Geometry=bp, Position=Pb)
    bl = g.node("GeometryNodeInstanceOnPoints", label="blossom", Points=bp, Instance=blossom_mesh(g),
                Rotation=g.node("FunctionNodeEulerToRotation", Euler=g.vec(exb, g.math("MULTIPLY", tum_b, 1.5), yaw_b)),
                Scale=scale_b)
    g.link(g.node("GeometryNodeRealizeInstances", Geometry=bl), go, b_key="Blossom")

    g.begin_section("h · Fruit")
    # ── fruit: sets in summer, ripens, drops straight down late summer / autumn
    bf = g.math("FLOOR", g.math("DIVIDE", idx, 3))
    ff = g.math("ADD", 0.45, g.math("MULTIPLY", g.math("FLOORED_MODULO", idx, 3), 0.2))
    brf = branch(g, bf)
    fp = g.node("GeometryNodePoints", label="fruit", Count=N1 * 3,
                Position=g.vmath("ADD", branch_at(g, brf, ff),
                                 (0.0, 0.0, -0.058 * TREE_S)))
    rf = rnd(g, idx, 51)
    grow_f = ease(g, u, g.math("ADD", 1.45, g.math("MULTIPLY", rf, 0.2)), g.math("ADD", 1.95, g.math("MULTIPLY", rf, 0.2)),
                  label="fruit sets")
    ripe = ease(g, u, g.math("ADD", 1.9, g.math("MULTIPLY", rf, 0.2)), g.math("ADD", 2.35, g.math("MULTIPLY", rf, 0.2)))
    tdf = g.math("ADD", 2.45, g.math("MULTIPLY", rf, 0.6))
    Pf, _ = fall(g, pos, u, tdf, 0.1, rf, (1.0, 0.15), 0.035, "fruit drops")
    gone_f = ease(g, u, 3.45, 3.75)
    scale_f = g.math("MULTIPLY", g.math("MULTIPLY", grow_f, g.math("SUBTRACT", 1.0, gone_f)), 0.04 * TREE_S)
    fp = g.node("GeometryNodeSetPosition", Geometry=fp, Position=Pf)
    fp = store(g, fp, "ripe", ripe)
    apple = join(g, [g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshUVSphere", Segments=16, Rings=10,
                                                                     Radius=1.0), Scale=(1, 1, 0.88)),
                     g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCylinder", Vertices=6,
                                                                     Radius=0.08, Depth=0.6),
                            Translation=(0, 0, 1.05))])
    fr = g.node("GeometryNodeInstanceOnPoints", label="fruit", Points=fp, Instance=apple, Scale=scale_f)
    g.link(smooth(g, g.node("GeometryNodeRealizeInstances", Geometry=fr)), go, b_key="Fruit")
    g.end_section()
    pb.arrange(t)
    return t


# ───────────────────────────────────────────────────────── stage (turns)
def stage_group(gear, tree, m):
    t, g, gi, go = group("MB_Stage", [("Season", "Float", 0.0), ("Phase", "Float", 0.0)],
                         [("Stage", "Geometry")])
    u, phase = gi.outputs["Season"], gi.outputs["Phase"]
    parts = []
    g.begin_section("a · Plate and season emblems")
    # the stage plate (turned from below by the year wheel)
    plate = cylinder(g, 0.95, Z_GEAR, Z_LID)
    bead = tube(g, g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeCurvePrimitiveCircle", Resolution=128,
                                                                   Radius=0.95), Translation=(0, 0, Z_LID - 0.004)),
                0.007, 8)
    ring = tube(g, g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeCurvePrimitiveCircle", Resolution=128,
                                                                   Radius=0.795), Translation=(0, 0, Z_LID)), 0.005, 8)
    parts.append(pb.set_material(g, join(g, [plate, smooth(g, bead), smooth(g, ring)]), m["brass"]))
    # season emblems round the rim: each passes the front index when its season is on
    ems = []
    for kind, us in EMBLEMS:
        a = -PI / 2 - TAU * us / 4
        e = emblem(g, kind, 0.1, 0.01)
        ems.append(g.node("GeometryNodeTransform", Geometry=e, Rotation=(0, 0, a + PI / 2),
                          Translation=(0.862 * math.cos(a), 0.862 * math.sin(a), Z_LID)))
    for k in range(16):       # small dots between the emblems
        a = -PI / 2 - TAU * (k + 0.5) / 16 - TAU * 0.75 / 4
        if k % 4 == 1:
            continue
        ems.append(g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshUVSphere", Segments=12, Rings=6,
                                                                   Radius=0.011),
                          Translation=(0.862 * math.cos(a), 0.862 * math.sin(a), Z_LID)))
    parts.append(pb.set_material(g, join(g, ems, label="season dial"), m["gold"]))

    g.begin_section("b · Mound and snow cover")
    # mound
    def mound(gg, k):
        r = gg.math("MULTIPLY", RM, gg.math("SUBTRACT", 1.0, k))
        return r, ground_z(gg, r)
    ground = g.node("GeometryNodeMergeByDistance", Geometry=lathe(g, mound, 128, 40, label="mound"), Distance=1e-5)
    parts.append(pb.set_material(g, smooth(g, ground), m["moss"]))
    # snow on the mound: the same dome lifted by the snow depth (below the moss when there is none)
    sd = g.math("ADD", g.math("SUBTRACT", 1.0, ease(g, u, 0.15, 0.5)), ease(g, u, 3.25, 3.7))
    sd.label = "snow depth: melts in spring, falls late in autumn"
    nz = g.node("ShaderNodeTexNoise", Scale=5.0, Detail=2.0)

    def snowdome(gg, k):
        r = gg.math("MULTIPLY", RM - 0.012, gg.math("SUBTRACT", 1.0, k))
        return r, ground_z(gg, r)
    sdome = g.node("GeometryNodeMergeByDistance", Geometry=lathe(g, snowdome, 128, 40, label="snow"), Distance=1e-5)
    edge = g.math("SUBTRACT", 1.0, g.math("POWER", g.math("DIVIDE", g.node("ShaderNodeVectorMath", props={
        "operation": "LENGTH"}, Vector=g.vmath("MULTIPLY", g.node("GeometryNodeInputPosition"), (1, 1, 0))), RM), 8.0))
    depth = g.math("SUBTRACT", g.math("MULTIPLY", g.math("MULTIPLY", sd, edge),
                                      g.math("ADD", 0.025, g.math("MULTIPLY", g.out(nz, "Factor"), 0.03))), 0.004)
    sdome = g.node("GeometryNodeSetPosition", Geometry=sdome, Offset=g.vec(0, 0, depth))
    parts.append(pb.set_material(g, smooth(g, sdome), m["snow"]))
    g.begin_section("c · Grass")
    # grass
    gpts = g.node("GeometryNodeDistributePointsOnFaces", props={"distribute_method": "RANDOM"}, Mesh=ground,
                  Density=650.0, Seed=4)
    gx, gy, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    gr = g.math("SQRT", g.math("ADD", g.math("MULTIPLY", gx, gx), g.math("MULTIPLY", gy, gy)))
    gpts = g.node("GeometryNodeDeleteGeometry", props={"domain": "POINT"}, Geometry=g.out(gpts, "Points"),
                  Selection=g.math("LESS_THAN", gr, 0.07))
    gs = g.math("SUBTRACT", g.math("SUBTRACT", g.math("ADD", 0.15, ease(g, u, 0.45, 1.2, lo=0.0, hi=0.85)),
                                   ease(g, u, 2.4, 3.0, hi=0.25)), ease(g, u, 3.2, 3.6, hi=0.6))
    gs.label = "grass height through the year"
    blade_g = g.node("GeometryNodeMeshGrid", Size_X=1.0, Size_Y=1.0, Vertices_X=2, Vertices_Y=5)
    bx, by, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    bt = g.math("ADD", by, 0.5)
    blade = g.node("GeometryNodeSetPosition", label="grass blade", Geometry=blade_g, Position=g.vec(
        g.math("MULTIPLY", bx, g.math("MULTIPLY", 0.012, g.math("SUBTRACT", 1.0, bt))),
        g.math("MULTIPLY", 0.3, g.math("MULTIPLY", bt, bt)), bt))
    gh = g.math("MULTIPLY", g.math("MULTIPLY", gs, 0.042), rnd(g, g.node("GeometryNodeInputIndex"), 61, 0.6, 1.4))
    grass = g.node("GeometryNodeInstanceOnPoints", label="grass", Points=gpts, Instance=blade,
                   Rotation=g.node("FunctionNodeEulerToRotation", Euler=g.vec(0, 0, rnd(
                       g, g.node("GeometryNodeInputIndex"), 62, 0, TAU))),
                   Scale=g.vec(1.0, gh, gh))
    grass = store(g, g.node("GeometryNodeRealizeInstances", Geometry=grass), "dry", ease(g, u, 2.3, 2.9))
    parts.append(pb.set_material(g, grass, m["grass"]))
    g.begin_section("d · The tree")
    # the tree
    tr = g.group(tree, Season=u, Phase=phase)
    parts += [pb.set_material(g, g.out(tr, "Wood"), m["gold"]),
              pb.set_material(g, g.out(tr, "Branch Snow"), m["snow"]),
              pb.set_material(g, smooth(g, g.out(tr, "Leaves")), m["leaf"]),
              pb.set_material(g, smooth(g, g.out(tr, "Blossom")), m["blossom"]),
              pb.set_material(g, g.out(tr, "Fruit"), m["fruit"])]
    g.begin_section("e · Snowfall")
    # snowfall: periodic flakes, shown late autumn → early spring
    env = g.math("ADD", g.math("SUBTRACT", 1.0, ease(g, u, 0.0, 0.25)), ease(g, u, 3.05, 3.3))
    env.label = "snowfall"
    idx = g.node("GeometryNodeInputIndex")
    r1, r2, r3 = rnd(g, idx, 71), rnd(g, idx, 72), rnd(g, idx, 73)
    fr = g.math("FRACT", g.math("ADD", r3, g.math("MULTIPLY", phase, 10.0)))
    rad = g.math("MULTIPLY", g.math("SQRT", r1), 0.72)
    fa = g.math("ADD", g.math("MULTIPLY", r2, TAU), g.math("MULTIPLY", 0.25, g.math("SINE", g.math(
        "MULTIPLY", fr, TAU * 2))))
    ztop = g.math("ADD", Z_LID + DOME_H - 0.05, g.math("MULTIPLY", 0.6, g.math("SQRT", g.math("MAXIMUM", 0.0, g.math(
        "SUBTRACT", 1.0, g.math("POWER", g.math("DIVIDE", rad, 0.86), 2.0))))))
    zfl = mix(g, ztop, ground_z(g, rad), fr)
    flakes = g.node("GeometryNodePoints", label="snowflakes", Count=420, Position=g.vec(
        g.math("MULTIPLY", rad, g.math("COSINE", fa)), g.math("MULTIPLY", rad, g.math("SINE", fa)), zfl))
    fs = g.math("MULTIPLY", g.math("MULTIPLY", env, 0.008), g.math("MULTIPLY", ease(g, fr, 0.0, 0.05), g.math(
        "SUBTRACT", 1.0, ease(g, fr, 0.95, 1.0))))
    flakes = g.node("GeometryNodeInstanceOnPoints", Points=flakes, Instance=g.node(
        "GeometryNodeMeshIcoSphere", Radius=1.3, Subdivisions=1), Scale=fs)
    parts.append(pb.set_material(g, g.node("GeometryNodeRealizeInstances", Geometry=flakes), m["snow"]))
    st = join(g, parts)
    st = g.node("GeometryNodeTransform", label="the stage turns once a year", Geometry=st,
                Rotation=g.vec(0, 0, g.math("MULTIPLY", phase, TAU)))
    g.end_section()
    g.link(st, go, b_key="Stage")
    pb.arrange(t)
    return t


def dome_object(m):
    """Glass cloche as its own object, so the key and top lights can skip it (light linking): its edges come from
    the rim strips, without big softbox reflections across the tree."""
    ob, g = pb.gn_object("Dome", NAME)
    def dome(gg, k):
        kk = gg.math("MINIMUM", 1.0, gg.math("MAXIMUM", 0.0, gg.math("MULTIPLY", gg.math("SUBTRACT", k, 0.5), 2.0)))
        a = gg.math("MULTIPLY", kk, PI / 2)
        r = gg.math("MULTIPLY", 0.875, gg.math("COSINE", a))
        z = gg.math("ADD", gg.math("ADD", Z_LID, gg.math("MULTIPLY", DOME_H, gg.math("MINIMUM", 1.0, gg.math(
            "MULTIPLY", k, 2.0)))), gg.math("MULTIPLY", 0.62, gg.math("SINE", a)))
        return r, z
    shell = g.node("GeometryNodeMergeByDistance", Geometry=lathe(g, dome, 160, 80, label="glass dome"),
                   Distance=1e-5)
    ext = g.node("GeometryNodeExtrudeMesh", props={"mode": "FACES"}, Mesh=shell, Offset_Scale=0.008,
                 Individual=False)
    shell = join(g, [g.node("GeometryNodeFlipFaces", Mesh=shell), g.out(ext, "Mesh")])
    knob = g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshUVSphere", Segments=24, Rings=12,
                                                           Radius=0.035), Translation=(0, 0, Z_LID + DOME_H + 0.64))
    foot = tube(g, g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeCurvePrimitiveCircle",
                                                                   Resolution=128, Radius=0.885),
                          Translation=(0, 0, Z_LID + 0.008)), 0.012, 10)
    domeg = join(g, [pb.set_material(g, smooth(g, shell), m["glass"]),
                     pb.set_material(g, smooth(g, join(g, [knob, foot])), m["brass"])])
    g.output(domeg)
    pb.arrange(g.tree)
    return ob


# ───────────────────────────────────────────────────────── drum, movement (fixed)
def drum_group(gear, m):
    """Base: a walnut plinth and a brass bezel joined by a plique-à-jour wall (translucent enamel in a brass cell
    lattice, lit from inside), so the movement shows through coloured light.
    The stage is driven from inside: a big wheel on the centre shaft (one turn a year) and its pinion on the
    spring barrel. The key sits on the barrel's own arbor."""
    t, g, gi, go = group("MB_Drum", [("Phase", "Float", 0.0)], [("Drum", "Geometry")])
    phase = gi.outputs["Phase"]
    parts = []
    z0, z1 = Z_BODY
    g.begin_section("a · Plinth and bezel")
    plinth = cylinder(g, 1.035, 0.0, z0)
    parts.append(pb.set_material(g, plinth, m["walnut"]))
    beads = [tube(g, g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeCurvePrimitiveCircle",
                                                                     Resolution=160, Radius=r), Translation=(0, 0, z)),
                  rr, 10) for r, z, rr in ((1.035, 0.004, 0.010), (1.035, z0, 0.010), (1.025, z1 - 0.002, 0.010))]
    band = cylinder(g, 1.025, z1, Z_GEAR)
    parts.append(pb.set_material(g, join(g, ([] if "--bare" in ARGS else [band]) + [smooth(g, join(g, beads))]),
                                 m["brass"]))

    # plique-à-jour wall: brass cloisons (Voronoi cell edges on the cylinder) over translucent enamel
    H = z1 - z0
    bare = "--bare" in ARGS           # look at the movement without the wall
    g.begin_section("b · Cells: Delaunay → Dual Mesh")
    # cells: seed points on the drum → Delaunay (convex hull of the points lifted onto a paraboloid, after a
    # conformal map of the drum onto an annulus) → Dual Mesh = one polygon per seed
    za, zb = z0 - 0.15, z1 + 0.15                      # seeds well past both rails, so no ragged cells show
    seedc = cylinder(g, 1.0, za, zb, 256, fill="NONE")
    seeds = g.node("GeometryNodeDistributePointsOnFaces", label="cell seeds", props={"distribute_method": "POISSON"},
                   Mesh=seedc, Distance_Min=CELL_MIN, Density_Max=CELL_DENSITY, Seed=7)
    sx, sy, sz = xyz(g, g.node("GeometryNodeInputPosition"))
    th = g.math("ARCTAN2", sy, sx)
    rr = g.math("EXPONENT", g.math("SUBTRACT", sz, (za + zb) / 2))   # drum height → annulus radius (conformal)
    lift = g.node("GeometryNodeSetPosition", label="drum → annulus, lifted onto a paraboloid", Geometry=g.out(
        seeds, "Points"), Position=g.vec(g.math("MULTIPLY", rr, g.math("COSINE", th)),
                                         g.math("MULTIPLY", rr, g.math("SINE", th)), g.math("MULTIPLY", rr, rr)))
    hull = g.node("GeometryNodeConvexHull", label="lower hull = Delaunay", Geometry=lift)
    hx, hy, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    hr = g.node("ShaderNodeVectorMath", props={"operation": "LENGTH"}, Vector=g.vec(hx, hy, 0.0))
    back = g.node("GeometryNodeSetPosition", label="annulus → drum", Geometry=hull, Position=g.vec(
        g.math("COSINE", g.math("ARCTAN2", hy, hx)), g.math("SINE", g.math("ARCTAN2", hy, hx)),
        g.math("ADD", g.math("LOGARITHM", g.out(hr, "Value"), math.e), (za + zb) / 2)))
    cx_, cy_, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    near = g.node("ShaderNodeVectorMath", props={"operation": "LENGTH"}, Vector=g.vec(cx_, cy_, 0.0))
    tri = g.node("GeometryNodeDeleteGeometry", label="drop the hull's caps (faces cutting through the drum)",
                 props={"domain": "FACE"}, Geometry=back, Selection=g.math("LESS_THAN", g.out(near, "Value"), 0.99))
    dual = g.node("GeometryNodeDualMesh", label="Voronoi-like cells", Mesh=tri, Keep_Boundaries=False)
    dx_, dy_, dz_ = xyz(g, g.node("GeometryNodeInputPosition"))
    dl = g.node("ShaderNodeVectorMath", props={"operation": "LENGTH"}, Vector=g.vec(dx_, dy_, 0.0))
    dual = g.node("GeometryNodeSetPosition", label="back onto the drum", Geometry=dual, Position=g.vec(
        g.math("DIVIDE", dx_, g.out(dl, "Value")), g.math("DIVIDE", dy_, g.out(dl, "Value")),
        g.node("ShaderNodeClamp", Value=dz_, Min=z0 - 0.02, Max=z1 + 0.012)))   # squash the margin under the rails
    dual = store(g, dual, "cell", g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT"},
                                         ID=g.node("GeometryNodeInputIndex"), Seed=3), domain="FACE")
    g.begin_section("c · Cloisons and enamel panes")
    # inset every cell: the ring between its outline and its shrunk copy is the cloison, the copy is the pane
    inx = g.node("GeometryNodeExtrudeMesh", props={"mode": "FACES"}, Mesh=dual, Offset_Scale=0.0, Individual=True)
    ins = g.node("GeometryNodeScaleElements", label="inset (cloison width)", props={"domain": "FACE"},
                 Geometry=g.out(inx, "Mesh"), Selection=g.out(inx, "Top"), Scale=CELL_INSET)
    panes = g.node("GeometryNodeSeparateGeometry", props={"domain": "FACE"}, Geometry=ins,
                   Selection=g.out(inx, "Top"))
    keep = g.out(panes, "Inverted")
    ex, ey, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    rad = g.node("ShaderNodeVectorMath", props={"operation": "NORMALIZE"}, Vector=g.vec(ex, ey, 0.0))
    ext = g.node("GeometryNodeExtrudeMesh", props={"mode": "FACES"}, Mesh=keep, Offset=g.out(rad, "Vector"),
                 Offset_Scale=0.007, Individual=False)
    wires = join(g, [g.node("GeometryNodeFlipFaces", Mesh=keep), g.out(ext, "Mesh")])
    rails = [cylinder(g, 1.012, z, z + 0.028, fill="NONE") for z in (z0, z1 - 0.028)]   # rings, not lids
    parts.append(pb.set_material(g, join(g, ([] if bare else [wires]) + rails), m["gold"]))
    enamel = g.node("GeometryNodeTransform", Geometry=g.out(panes, "Selection"), Scale=(0.998, 0.998, 1.0))
    if not bare:
        parts.append(pb.set_material(g, enamel, m["plique"]))
    g.begin_section("d · Season index")
    # brass index at the front: points at the season on the dial
    post = g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCylinder", Vertices=16, Radius=0.011,
                                                           Depth=Z_LID + 0.02 - Z_GEAR),
                  Translation=(0, -0.99, (Z_LID + 0.02 + Z_GEAR) / 2))
    kite = g.node("GeometryNodeCurvePrimitiveQuadrilateral", props={"mode": "KITE"}, Width=0.05, Bottom_Height=0.025,
                  Top_Height=0.085)
    hand = g.node("GeometryNodeTransform", Geometry=flat_shape(g, kite, 0.006), Translation=(0, -0.99, Z_LID + 0.02))
    parts.append(pb.set_material(g, join(g, [smooth(g, post), hand]), m["gold"]))
    g.begin_section("e · Stage drive")
    # stage drive: year wheel on the centre shaft, its pinion riding on the spring barrel
    w = g.math("MULTIPLY", phase, TAU)
    yw = g.group(gear, Teeth=YEAR_T, Pitch_Radius=YEAR_RP, Thickness=0.012, Holes=6)
    yw = g.node("GeometryNodeTransform", label="year wheel: one turn a year", Geometry=yw, Rotation=g.vec(0, 0, w),
                Translation=(0, 0, YEAR_Z))
    shaft = cylinder(g, 0.018, YEAR_Z - 0.03, Z_GEAR)
    a2 = mesh_phase(w, YEAR_T, PIN_T, PIN_AZ)(g)
    a2.label = f"pinion: {YEAR_T // PIN_T} turns a year"
    pin = g.group(gear, Teeth=PIN_T, Pitch_Radius=PIN_RP, Thickness=0.016, Holes=3)
    cx, cy = (YEAR_RP + PIN_RP) * math.cos(PIN_AZ), (YEAR_RP + PIN_RP) * math.sin(PIN_AZ)
    pin = g.node("GeometryNodeTransform", Geometry=pin, Rotation=g.vec(0, 0, a2), Translation=(cx, cy, YEAR_Z - 0.002))
    parb = g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCylinder", Vertices=16, Radius=0.008,
                                                           Depth=YEAR_Z - 0.30), Translation=(cx, cy, (YEAR_Z + 0.30) / 2))
    parts.append(pb.set_material(g, join(g, [pin] if "--bare" in ARGS else [yw, pin]), m["brass"]))
    parts.append(pb.set_material(g, smooth(g, join(g, [shaft, parb])), m["steel"]))
    g.begin_section("f · Winding key")
    # winding key: its stem runs from the barrel out through the wall on the left
    bx0, by, bz = BARREL[0] - BARREL[2], BARREL[1], 0.20
    kx = -1.06
    warb = g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCylinder", Vertices=16, Radius=0.012,
                                                           Depth=bx0 - kx), Rotation=(0, PI / 2, 0),
                  Translation=((kx + bx0) / 2, by, bz))
    parts.append(pb.set_material(g, smooth(g, warb), m["steel"]))
    # classic butterfly key: a flat two-lobed bow with a pierced eye in each wing, on a turned shank
    def cyl_x(r, xa, xb, v=32):
        return g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCylinder", Vertices=v, Radius=r,
                                                               Depth=xb - xa), Rotation=(0, PI / 2, 0),
                      Translation=((xa + xb) / 2, 0, 0))
    bow = polar_curve(g, lambda gg, th: gg.math("ADD", 0.062, gg.math("MULTIPLY", 0.115, gg.math(
        "POWER", gg.math("ABSOLUTE", gg.math("SINE", th)), 2.6))), 160)
    eyes = [g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeCurvePrimitiveCircle", Resolution=48,
                                                             Radius=0.036), Translation=(0, s_ * 0.105, 0))
            for s_ in (1, -1)]
    bow = flat_shape(g, join(g, [bow] + eyes), 0.016)
    bow = g.node("GeometryNodeTransform", label="butterfly bow", Geometry=bow, Translation=(0.215, 0, -0.008))
    shank = join(g, [cyl_x(0.019, 0.0, 0.16), cyl_x(0.042, 0.012, 0.030, 48), cyl_x(0.03, 0.12, 0.165, 48)])
    beads = [tube(g, g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeCurvePrimitiveCircle", Resolution=48,
                                                                     Radius=r_),
                          Rotation=(0, PI / 2, 0), Translation=(x_, 0, 0)), 0.007, 10)
             for r_, x_ in ((0.042, 0.021), (0.03, 0.12))]
    key = join(g, [bow, smooth(g, join(g, [shank] + beads))])
    key = g.node("GeometryNodeTransform", label="key unwinds", Geometry=key,
                 Rotation=g.vec(g.math("MULTIPLY", phase, -TAU), 0, 0))
    key = g.node("GeometryNodeTransform", Geometry=key, Rotation=(0, 0, PI), Translation=(kx, by, bz))
    parts.append(pb.set_material(g, key, m["gold"]))      # shank already smooth; bow keeps flat faces
    g.end_section()
    g.link(join(g, parts), go, b_key="Drum")
    pb.arrange(t)
    return t


def movement_group(gear, m):
    """A Swiss cylinder movement after the Mapsa/Reuge layout: zamak bedplate with a raised frame loop, spring
    barrel back left, pinned brass cylinder back right with its great wheel, a spur-train governor ending in a
    spinning air brake front left, and the steel comb screwed down in front of the cylinder.
    Each tooth is bent down by the pin passing its tip, then rings out:
    deflection = Σ over its pin slots of pluck(where that pin is)."""
    t, g, gi, go = group("MB_Movement", [("Phase", "Float", 0.0)], [("Movement", "Geometry")])
    phase = gi.outputs["Phase"]
    psi = g.math("MULTIPLY", phase, TAU)
    psi.label = "cylinder: one turn per loop"
    x0, x1 = 0.03, 0.59
    dx = (x1 - x0) / (TEETH - 1)
    idx = g.node("GeometryNodeInputIndex")
    parts, zamak, brass, steel = [], [], [], []

    def box(sx, sy, sz, cx, cy, cz):
        return g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCube", Size=(sx, sy, sz)),
                      Translation=(cx, cy, cz))

    def rrect(xa, xb, ya, yb, r, res=12):
        q = g.node("GeometryNodeCurvePrimitiveQuadrilateral", Width=xb - xa, Height=yb - ya)
        q = g.node("GeometryNodeFilletCurve", Curve=q, Radius=r, Count=res, Limit_Radius=True)
        q.inputs["Mode"].default_value = "Poly"
        return g.node("GeometryNodeTransform", Geometry=q, Translation=((xa + xb) / 2, (ya + yb) / 2, 0))

    def on_x(geo, ang, x, y, z):
        """A part built in the local XY plane, turned by ang about its axis, stood up on an arbor along X."""
        if ang is not None:
            geo = g.node("GeometryNodeTransform", Geometry=geo, Rotation=g.vec(0, 0, ang))
        return g.node("GeometryNodeTransform", Geometry=geo, Rotation=(0, PI / 2, 0), Translation=(x, y, z))

    def arbor(xa, xb, y, z, r=0.009):
        return g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCylinder", Vertices=16, Radius=r,
                                                               Depth=xb - xa), Rotation=(0, PI / 2, 0),
                      Translation=((xa + xb) / 2, y, z))

    def screw(x, y, z, r, rot):
        head = g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCylinder", Vertices=32, Radius=r,
                                                               Depth=r * 0.6), Translation=(x, y, z + r * 0.3))
        slot = g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCube", Size=(2.4 * r, 0.22 * r,
                                                                                              0.5 * r)),
                      Rotation=(0, 0, rot), Translation=(x, y, z + r * 0.6))
        cut = g.node("GeometryNodeMeshBoolean", props={"operation": "DIFFERENCE"}, Mesh_1=head)
        g.link(slot, cut, b_key="Mesh 2")
        return cut

    g.begin_section("a · Bedplate, frame and barrel")
    # bedplate and the raised frame loop round the cylinder and comb
    bed = g.node("GeometryNodeTransform", Geometry=flat_shape(g, rrect(-0.70, 0.76, -0.40, 0.56, 0.18), 0.03),
                 Translation=(0, 0, Z_BODY[0]))
    loop = tube(g, g.node("GeometryNodeTransform", Geometry=rrect(-0.17, 0.74, -0.34, 0.50, 0.16),
                          Translation=(0, 0, PLATE_Z + 0.03)), 0.04, 12)
    loop = g.node("GeometryNodeTransform", label="frame loop", Geometry=loop, Scale=(1, 1, 1.0))
    cheek_r = box(0.05, 0.16, CYL_Z + 0.05 - PLATE_Z, 0.665, CYL_Y, (CYL_Z + 0.05 + PLATE_Z) / 2)
    zamak += [bed, smooth(g, loop), cheek_r]
    # spring barrel (vertical arbor, back left): a squat die-cast drum
    bxx, byy, br = BARREL

    def barrel_prof(gg, k):
        rr = gg.math("MULTIPLY", br, gg.math("SQRT", gg.math("SUBTRACT", 1.0, gg.math("POWER", gg.math(
            "MAXIMUM", 0.0, gg.math("DIVIDE", gg.math("SUBTRACT", gg.math("ABSOLUTE", gg.math("SUBTRACT", k, 0.5)),
                                                      0.36), 0.14)), 2.0))))
        return rr, gg.math("ADD", PLATE_Z, gg.math("MULTIPLY", k, 0.20))
    barrel = g.node("GeometryNodeTransform", Geometry=lathe(g, barrel_prof, 64, 40, label="spring barrel"),
                    Translation=(bxx, byy, 0))
    hub = g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCylinder", Vertices=32, Radius=0.06,
                                                          Depth=0.01), Translation=(bxx, byy, PLATE_Z + 0.205))
    zamak += [smooth(g, barrel), hub]
    g.begin_section("b · Cylinder and great wheel")
    # pinned cylinder, its arbor and great wheel
    cyl = arbor(0.0, 0.62, CYL_Y, CYL_Z, CYL_R)
    cyl = g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeMeshCylinder", Vertices=64, Radius=CYL_R,
                                                          Depth=0.62), Rotation=(0, PI / 2, 0),
                 Translation=(0.31, CYL_Y, CYL_Z))
    brass.append(smooth(g, cyl))
    steel.append(arbor(-0.14, 0.69, CYL_Y, CYL_Z, 0.012))
    GW, GWR = 72, 0.15
    gw = on_x(g.group(gear, Teeth=GW, Pitch_Radius=GWR, Thickness=0.008, Holes=5), psi, -0.05, CYL_Y, CYL_Z)
    brass.append(gw)
    g.begin_section("c · Governor and air brake")
    # governor: great wheel → pinion (×6) → wheel 40 / pinion 10 (×4) → air brake, 24 turns a loop
    th1 = math.radians(190)                     # direction (in the Y-Z plane) from the cylinder to arbor 1
    P1T, P1R = 12, GWR * 12 / GW
    y1, z1_ = CYL_Y + (GWR + P1R) * math.cos(th1), CYL_Z + (GWR + P1R) * math.sin(th1)
    a1 = mesh_phase(psi, GW, P1T, th1 + PI / 2)(g)
    a1.label = "governor arbor: 6 turns a loop"
    brass.append(on_x(g.group(gear, Teeth=P1T, Pitch_Radius=P1R, Thickness=0.016, Holes=0), a1, -0.05, y1, z1_))
    W2T, W2R, P2T = 40, 0.05, 10
    P2R = W2R * P2T / W2T
    brass.append(on_x(g.group(gear, Teeth=W2T, Pitch_Radius=W2R, Thickness=0.006, Holes=4), a1, -0.25, y1, z1_))
    th2 = math.radians(250)
    y2, z2 = y1 + (W2R + P2R) * math.cos(th2), z1_ + (W2R + P2R) * math.sin(th2)
    a2 = mesh_phase(a1, W2T, P2T, th2 + PI / 2)(g)
    a2.label = "air brake: 24 turns a loop"
    steel.append(on_x(g.group(gear, Teeth=P2T, Pitch_Radius=P2R, Thickness=0.02, Holes=0), a2, -0.25, y2, z2))
    steel += [arbor(-0.55, -0.03, y1, z1_), arbor(-0.55, -0.22, y2, z2, 0.006)]
    vane = g.node("GeometryNodeMeshCube", Size=(0.13, 0.0035, 0.06))
    vane = g.node("GeometryNodeTransform", Geometry=vane, Rotation=(0.0, 0.0, 0.0))
    brass.append(on_x(vane, a2, -0.44, y2, z2))
    # brass governor bracket: a plate on the bed with two uprights carrying the arbors
    brass += [box(0.46, 0.20, 0.012, -0.33, 0.0, PLATE_Z + 0.006),
              box(0.016, 0.14, z1_ + 0.03 - PLATE_Z, -0.56, (y1 + y2) / 2, (z1_ + 0.03 + PLATE_Z) / 2),
              box(0.016, 0.30, CYL_Z + 0.04 - PLATE_Z, -0.125, (y2 + CYL_Y + 0.06) / 2, (CYL_Z + 0.04 + PLATE_Z) / 2)]
    g.begin_section("d · Score pins")
    # pins: one per note of the score, placed so it lets go of its tooth at the note's time
    tooth_of = index_switch(g, "INT", [k for k, _ in PINS], "pin → tooth (the score)")
    phi = index_switch(g, "FLOAT", [ALPHA_C - TAU * ph for _, ph in PINS], "pin angle: plucks at its beat")
    al = g.math("ADD", phi, psi)
    rp = CYL_R + 0.007
    ppos = g.vec(g.math("ADD", x0, g.math("MULTIPLY", tooth_of, dx)),
                 g.math("SUBTRACT", CYL_Y, g.math("MULTIPLY", rp, g.math("COSINE", al))),
                 g.math("SUBTRACT", CYL_Z, g.math("MULTIPLY", rp, g.math("SINE", al))))
    pin_pts = g.node("GeometryNodePoints", label=f"{len(PINS)} pins", Count=len(PINS), Position=ppos)
    pins = g.node("GeometryNodeInstanceOnPoints", Points=pin_pts, Instance=g.node(
        "GeometryNodeMeshCylinder", Vertices=8, Radius=0.0035, Depth=0.016),
        Rotation=g.node("FunctionNodeEulerToRotation", Euler=g.vec(g.math("ADD", al, PI / 2), 0, 0)))
    steel.append(g.node("GeometryNodeRealizeInstances", Geometry=pins))
    g.begin_section("e · Pluck, summed per tooth")
    # each pin's pluck (x: where it is in its turn, 0 = just let go), summed per tooth
    x = g.math("FRACT", g.math("DIVIDE", g.math("SUBTRACT", al, ALPHA_C), TAU))
    push = g.math("MULTIPLY", g.math("GREATER_THAN", x, 0.96), g.math("DIVIDE", g.math("SUBTRACT", x, 0.96), 0.04))
    ring = g.math("MULTIPLY", g.math("LESS_THAN", x, 0.3), g.math("MULTIPLY", g.math(
        "EXPONENT", g.math("DIVIDE", x, -0.025)), g.math("COSINE", g.math("MULTIPLY", x, TAU / 0.012))))
    pl_pin = g.math("ADD", push, ring)
    pl_pin.label = "pluck: pushed down by the pin, then rings"
    acc = g.node("GeometryNodeAccumulateField", label="sum per tooth", props={"data_type": "FLOAT", "domain": "POINT"},
                 Value=pl_pin, Group_ID=tooth_of)
    first = {}
    for i, (k, _) in enumerate(PINS):
        first.setdefault(k, i)
    rep = index_switch(g, "INT", [first.get(k, -1) for k in range(TEETH)], "tooth → one of its pins")
    defl = g.node("GeometryNodeSampleIndex", label="tooth deflection", props={"data_type": "FLOAT", "domain": "POINT",
                                                                              "clamp": False},
                  Geometry=pin_pts, Value=g.out(acc, "Total"), Index=rep)
    defl = g.out(defl, "Value")
    tlen = g.math("ADD", 0.22, g.math("MULTIPLY", 0.06, g.math("SUBTRACT", 1.0, g.math("DIVIDE", idx, TEETH - 1))))
    tip_y = CYL_Y - (CYL_R + 0.01) * math.cos(ALPHA_C) + 0.006
    tip_z = CYL_Z - (CYL_R + 0.01) * math.sin(ALPHA_C) - 0.003
    tpts = g.node("GeometryNodePoints", Count=TEETH, Position=g.vec(g.math("ADD", x0, g.math("MULTIPLY", idx, dx)),
                                                                     tip_y, tip_z))
    tpts = store(g, tpts, "pluck", g.math("MULTIPLY", defl, 0.014))
    tpts = store(g, tpts, "tlen", tlen)
    tooth = g.node("GeometryNodeMeshCube", Size=(dx * 0.78, 1.0, 0.007), Vertices_X=2, Vertices_Y=10, Vertices_Z=2)
    tooth = g.node("GeometryNodeTransform", Geometry=tooth, Translation=(0, -0.5, -0.0035))
    teeth = g.node("GeometryNodeInstanceOnPoints", Points=tpts, Instance=tooth)
    teeth = g.node("GeometryNodeRealizeInstances", Geometry=teeth)
    g.begin_section("f · Comb teeth")
    # stretch each tooth to its length and bend it: s = 0 at the tip … 1 at the root
    px, py, pz = xyz(g, g.node("GeometryNodeInputPosition"))
    tl = g.node("GeometryNodeInputNamedAttribute", props={"data_type": "FLOAT"}, Name="tlen")
    pl = g.node("GeometryNodeInputNamedAttribute", props={"data_type": "FLOAT"}, Name="pluck")
    s = g.math("SUBTRACT", tip_y, py)                 # 0..1 (unit cube)
    yy = g.math("SUBTRACT", tip_y, g.math("MULTIPLY", s, tl))
    bendz = g.math("MULTIPLY", pl, g.math("POWER", g.math("SUBTRACT", 1.0, s), 2.0))
    teeth = g.node("GeometryNodeSetPosition", label="comb teeth", Geometry=teeth,
                   Position=g.vec(px, yy, g.math("SUBTRACT", pz, bendz)))
    g.begin_section("g · Comb plate, screws, stop spring")
    # comb plate (same steel as the teeth) on a die-cast block, held by two big slotted screws
    ya, yb = tip_y - 0.36, tip_y - 0.22
    comb = box(x1 - x0 + 0.03, yb - ya, 0.007, (x0 + x1) / 2, (ya + yb) / 2, tip_z - 0.0035)
    block = box(x1 - x0 + 0.03, yb - ya - 0.02, tip_z - 0.007 - PLATE_Z, (x0 + x1) / 2, (ya + yb) / 2 - 0.01,
                (tip_z - 0.007 + PLATE_Z) / 2)
    combs = [teeth, comb]
    zamak.append(block)
    ym = ya + 0.055
    screws = [screw(xs, ym, tip_z, 0.045, rot) for xs, rot in ((0.17, 0.5), (0.45, -0.3))]
    screws += [screw(xs, ys, PLATE_Z + 0.07, 0.022, rot) for xs, ys, rot in
               ((0.70, -0.30, 1.1), (-0.13, 0.46, 0.2), (0.70, 0.46, -0.7), (-0.62, -0.30, 0.9))]
    # the stop spring: a wire from the comb screw out to the frame
    wire = g.node("GeometryNodeCurveQuadraticBezier", Resolution=32, Start=(0.45, ym, tip_z + 0.03),
                  Middle=(0.70, ym - 0.16, tip_z + 0.06), End=(0.72, -0.30, PLATE_Z + 0.09))
    steel += [smooth(g, tube(g, wire, 0.0045, 8))]
    g.begin_section("h · Materials and output")
    parts += [pb.set_material(g, join(g, zamak), m["zamak"]), pb.set_material(g, join(g, brass), m["brass"]),
              pb.set_material(g, join(g, steel + screws), m["steel"]), pb.set_material(g, join(g, combs), m["comb"])]
    g.link(join(g, parts), go, b_key="Movement")
    g.end_section()
    pb.arrange(t)
    return t


# ───────────────────────────────────────────────────────── build
def build():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    info = pb.piece(NAME, aspect="1:1", width=1080, fps=30, frames=FRAMES, samples=128)
    bpy.context.preferences.addons["cycles"].preferences.kernel_optimization_level = "OFF"
    m = materials()
    gear = gear_group()
    tree = tree_group()
    stage = stage_group(gear, tree, m)
    drum = drum_group(gear, m)
    mov = movement_group(gear, m)
    ob, g = pb.gn_object(NAME, NAME)
    clock = g.group(pb.loop_clock(FRAMES))
    phase = g.out(clock, "Phase")
    u = g.math("MULTIPLY", phase, 4.0)
    u.label = "season time: 0 deep winter … 4 deep winter"
    st = g.group(stage, Season=u, Phase=phase)
    dr = g.group(drum, Phase=phase)
    mv = g.group(mov, Phase=phase)
    g.output(join(g, [dr, mv] if "--bare" in ARGS else [st, dr, mv]))   # --bare: movement only, for checking
    pb.arrange(g.tree)
    dome = dome_object(m)
    if "--bare" in ARGS:
        dome.hide_render = True

    # ───── black void, camera, light
    sc = bpy.context.scene
    stc = bpy.data.collections.get("PA_Studio") or bpy.data.collections.new("PA_Studio")
    if stc.name not in sc.collection.children:
        sc.collection.children.link(stc)
    cam = bpy.data.objects.new("PA_Camera", bpy.data.cameras.new("PA_Camera"))
    stc.objects.link(cam)
    cam.data.lens = 85
    cam.data.clip_start = 0.05
    look = Vector((0.0, 0.0, 1.1))
    el, dist, az = math.radians(15), 7.9, math.radians(-90)
    cam.location = look + Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))) * dist
    if "--cam" in ARGS:
        v = [float(a) for a in ARGS[ARGS.index("--cam") + 1].split(",")]
        cam.location, look, cam.data.lens = Vector(v[:3]), Vector(v[3:6]), v[6]
    cam.rotation_euler = (look - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (Vector((0, -0.3, 0.9)) - cam.location).length
    cam.data.dof.aperture_fstop = 8.0

    def light(name, size, energy, loc, color=(1, 1, 1), target=(0, 0, 0.8)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape, ld.size, ld.size_y = "RECTANGLE", size[0], size[1]
        ld.energy, ld.color = energy, color
        lo = bpy.data.objects.new(name, ld)
        stc.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        lo.visible_camera = False
        return lo

    white = "--white" in ARGS
    key = light("PA_Key", (3.0, 2.0), 900.0, (-3.6, -3.4, 4.0), (1.0, 0.92, 0.82))
    top = light("PA_Top", (2.4, 2.4), 160.0, (0.5, 0.4, 5.0), (1.0, 0.97, 0.92))
    no_dome = bpy.data.collections.new("PA_NoDome")
    no_dome.objects.link(dome)
    next(c for c in no_dome.collection_objects).light_linking.link_state = "EXCLUDE"
    for lo in (key, top):
        lo.light_linking.receiver_collection = no_dome
    # low lights at cage height, so the open movement isn't a dark slot
    # a warm lamp inside the drum: the enamel glows like stained glass
    lamp = bpy.data.lights.new("PA_Inside", "POINT")
    lamp.energy, lamp.color, lamp.shadow_soft_size = 45.0, (1.0, 0.82, 0.6), 0.15
    lo_in = bpy.data.objects.new("PA_Inside", lamp)
    stc.objects.link(lo_in)
    lo_in.location = (0.15, 0.72, 0.42)          # behind the movement: it reads as a silhouette on the far wall
    fill = bpy.data.lights.new("PA_InsideFill", "POINT")
    fill.energy, fill.color, fill.shadow_soft_size = 10.0, (1.0, 0.85, 0.65), 0.1
    lo_f = bpy.data.objects.new("PA_InsideFill", fill)
    stc.objects.link(lo_f)
    lo_f.location = (0.2, -0.55, 0.45)
    lows = [light("PA_LowKey", (1.6, 0.6), 420.0, (-2.4, -2.6, 0.45), (1.0, 0.88, 0.72), target=(0, -0.45, 0.25)),
            light("PA_LowBack", (1.6, 0.6), 200.0, (2.6, 2.2, 0.40), (0.85, 0.9, 1.0), target=(0, -0.3, 0.25))]
    for lo in lows:                   # no softbox reflections in the cloche from these either
        lo.light_linking.receiver_collection = no_dome
    rims = [light("PA_RimL", (0.8, 4.0), 1200.0, (-3.6, 3.2, 1.6), (0.85, 0.9, 1.0)),
            light("PA_RimR", (0.8, 4.0), 900.0, (3.8, 2.6, 1.2), (1.0, 0.86, 0.72))]
    for lo in rims:                   # rims only catch the cloche's very edge, through a dimmer twin below
        lo.light_linking.receiver_collection = no_dome
    dome_only = bpy.data.collections.new("PA_DomeOnly")
    dome_only.objects.link(bpy.data.objects["PA_Dome"])
    next(c for c in dome_only.collection_objects).light_linking.link_state = "INCLUDE"
    for lo in rims:                   # a quarter-strength twin that lights the glass only: thin edge lines, no glare
        tw = light(lo.name + "_Glass", (lo.data.size, lo.data.size_y), lo.data.energy * DOME_RIM, tuple(lo.location),
                   tuple(lo.data.color))
        tw.rotation_euler = lo.rotation_euler
        tw.light_linking.receiver_collection = dome_only
    for lo in [key, top] + rims + lows:      # thin glass barely dims light: don't let the cloche black out the stage
        lo.light_linking.blocker_collection = no_dome
    world = bpy.data.worlds.new("PA_World")
    world.use_nodes = True
    wt = world.node_tree
    bg = wt.nodes["Background"]
    bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    room = wt.nodes.new("ShaderNodeBackground")
    room.inputs["Color"].default_value = (0.03, 0.022, 0.016, 1.0)
    if white:
        studio_white(stc)
        bg.inputs["Color"].default_value = (0.85, 0.85, 0.85, 1.0)
        bg.inputs["Strength"].default_value = 0.25
        room.inputs["Color"].default_value = (0.85, 0.85, 0.85, 1.0)
        room.inputs["Strength"].default_value = 0.25
    lp = wt.nodes.new("ShaderNodeLightPath")
    mx = wt.nodes.new("ShaderNodeMixShader")
    wt.links.new(lp.outputs["Is Glossy Ray"], mx.inputs[0])
    wt.links.new(bg.outputs[0], mx.inputs[1])
    wt.links.new(room.outputs[0], mx.inputs[2])
    wo = next(n for n in wt.nodes if n.bl_idname == "ShaderNodeOutputWorld")
    wt.links.new(mx.outputs[0], wo.inputs["Surface"])
    sc.world = world
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.1 if white else -0.3
    sc.cycles.max_bounces = 12
    sc.cycles.adaptive_threshold = 0.02
    pb.output(os.path.join(DAY, "loop.mp4"), "video")
    out = ARGS[ARGS.index("--save-as") + 1] if "--save-as" in ARGS else os.path.join(DAY, "musicbox.blend")
    pb.save(out)
    return {"piece": info}


def studio_white(stc):
    """Seamless white sweep (floor bending up into a wall) and two black flags that only reflections see,
    so the glass keeps dark edges on white."""
    ob, g = pb.gn_object("Backdrop", NAME)
    S1, RB, Y0 = 9.0, 2.5, -9.0
    grid = g.node("GeometryNodeMeshGrid", Size_X=30.0, Size_Y=30.0, Vertices_X=2, Vertices_Y=300)
    x, y, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    sarc = g.math("ADD", y, 15.0)
    a = g.math("MINIMUM", PI / 2, g.math("MAXIMUM", 0.0, g.math("DIVIDE", g.math("SUBTRACT", sarc, S1), RB)))
    yy = g.math("ADD", g.math("ADD", Y0, g.math("MINIMUM", sarc, S1)), g.math("MULTIPLY", RB, g.math("SINE", a)))
    zz = g.math("ADD", g.math("MULTIPLY", RB, g.math("SUBTRACT", 1.0, g.math("COSINE", a))),
                g.math("MAXIMUM", 0.0, g.math("SUBTRACT", sarc, S1 + RB * PI / 2)))
    sweep = g.node("GeometryNodeSetPosition", label="floor bends up into the wall", Geometry=grid,
                   Position=g.vec(x, yy, zz))
    paper = pb.material("Backdrop", "matte", color=(0.82, 0.82, 0.82), roughness=0.9)
    g.output(smooth(g, pb.set_material(g, sweep, paper)))
    pb.arrange(g.tree)
    flag = pb.material("Flag", "matte", color=(0.0, 0.0, 0.0), roughness=1.0)
    # side flags darken the brass flanks; the two behind show through the glass edges as dark lines
    for nm, size, loc, rz in (("FlagL", (1.6, 3.0), (-2.6, 0.3, 1.2), PI / 2 + 0.25),
                              ("FlagR", (1.6, 3.0), (2.6, 0.3, 1.2), PI / 2 - 0.25),
                              ("FlagBL", (0.9, 4.0), (-1.45, 2.4, 1.5), 0.0),
                              ("FlagBR", (0.9, 4.0), (1.45, 2.4, 1.5), 0.0)):
        fo, fg = pb.gn_object(nm, NAME)
        pl = fg.node("GeometryNodeMeshGrid", Size_X=size[0], Size_Y=size[1])
        pl = fg.node("GeometryNodeTransform", Geometry=pl, Rotation=(PI / 2, 0, rz), Translation=loc)
        fg.output(pb.set_material(fg, pl, flag))
        fo.visible_camera = fo.visible_diffuse = fo.visible_shadow = False
    return ob


def sound(path, rate=48000):
    """The tune the pins play: each pluck rings like a cantilevered steel tooth (modes 1 : 6.27 : 17.55 of the
    fundamental, the high ones dying fast), panned by where its tooth is, tails wrapped round the loop and a
    circular reverb, so the audio loops as seamlessly as the picture. Exactly FRAMES/30 s of 16-bit stereo."""
    import numpy as np
    n = int(rate * FRAMES / 30)
    out = np.zeros((n, 2))
    semis = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    tail = np.arange(int(rate * 6.0)) / rate
    rng = np.random.default_rng(5)
    for k, ph in PINS:
        name = COMB[k]
        f = 440.0 * 2 ** ((semis[name[0]] + 12 * (int(name[1]) + 1) - 69) / 12)
        tau = float(np.clip(2.4 * (220.0 / f) ** 0.5, 0.45, 3.0))
        v = np.sin(TAU * f * tail) * np.exp(-tail / tau)
        for ratio, amp, life in ((6.267, 0.16, 0.12), (17.55, 0.05, 0.04)):
            if f * ratio < rate * 0.4:
                v += amp * np.sin(TAU * f * ratio * tail + 0.3) * np.exp(-tail / (tau * life))
        click = rng.standard_normal(tail.size) * np.exp(-tail / 0.0015) * 0.06
        v = (v + click) * (0.8 if f < 300 else 1.0) * min(1.0, 600.0 / f + 0.45)
        pan = (k / (TEETH - 1) - 0.5) * 0.8
        lr = np.array([math.cos((pan + 1) * PI / 4), math.sin((pan + 1) * PI / 4)])
        i0 = int(round(ph * n))
        idx = (i0 + np.arange(tail.size)) % n
        np.add.at(out, idx, v[:, None] * lr[None, :])
    t = np.arange(n) / rate
    ir_len = int(rate * 1.6)
    for c in range(2):                                    # circular reverb: the room wraps round the loop too
        ir = np.zeros(n)
        ir[:ir_len] = rng.standard_normal(ir_len) * np.exp(-t[:ir_len] / 0.35)
        ir[:int(rate * 0.012)] = 0.0
        wet = np.fft.irfft(np.fft.rfft(out[:, c]) * np.fft.rfft(ir), n)
        out[:, c] = out[:, c] + 0.22 * wet / np.max(np.abs(wet)) * np.max(np.abs(out[:, c]))
    out *= 0.89 / np.max(np.abs(out))
    # stdlib writer, not aud: aud pads the file to its block size (+512 samples), and a loop has to be exactly
    # FRAMES/30 s long, or it drifts against the picture and clicks at the seam
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.round(out * 32767).astype("<i2").tobytes())
    return path


def clay(path):
    """White clay copy (Workbench = viewport solid shading) for checking the motion; no glass."""
    sc = bpy.context.scene
    keep = sc.render.engine
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.studio_light = "STUDIO", "Default"
    sh.color_type = "MATERIAL"
    sh.show_cavity, sh.cavity_type = True, "BOTH"
    sh.show_shadows = True
    for mt in bpy.data.materials:
        mt.diffuse_color = (0.9, 0.9, 0.9, 1)
    sc.display.render_aa = "8"
    sc.world.color = (0.02, 0.02, 0.02)
    ob = bpy.data.objects["PA_" + NAME]
    dome = bpy.data.objects["PA_Dome"]
    dome.hide_render = True
    cg = sc.compositing_node_group
    sc.compositing_node_group = None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pb.save(path)
    sc.render.engine, sc.compositing_node_group = keep, cg
    dome.hide_render = False
    return path


if __name__ == "__main__":
    res = build()
    if "--preview" in ARGS:
        for fr in ARGS[ARGS.index("--preview") + 1].split(","):
            fr = int(fr)
            pb.preview(os.path.join(DAY, f"_preview_{fr:03d}.png"), scale=50, samples=16, frame=fr)
    if "--look" in ARGS:
        sc = bpy.context.scene
        sc.render.resolution_percentage = 50
        for fr in ARGS[ARGS.index("--look") + 1].split(","):
            fr = int(fr)
            res[f"cycles_{fr}"] = pb.render_still(os.path.join(DAY, f"_cycles_{fr:03d}.png"), frame=fr, samples=48)
        sc.render.resolution_percentage = 100
    if "--still" in ARGS:
        for fr in ARGS[ARGS.index("--still") + 1].split(","):
            fr = int(fr)
            res[f"still_{fr}"] = pb.render_still(os.path.join(DAY, f"_still_{fr:03d}.png"), frame=fr)
    if "--wb" in ARGS:
        sc = bpy.context.scene
        clay(os.path.join(DAY, "clay", "musicbox_clay.blend"))
        sc.render.engine = "BLENDER_WORKBENCH"
        bpy.data.objects["PA_Dome"].hide_render = True
        sc.render.resolution_percentage = 50
        sc.render.image_settings.media_type = "IMAGE"
        sc.render.image_settings.file_format = "PNG"
        for fr in ARGS[ARGS.index("--wb") + 1].split(","):
            sc.frame_set(int(fr))
            sc.render.filepath = os.path.join(DAY, f"_wb_{int(fr):03d}.png")
            bpy.ops.render.render(write_still=True)
        sc.render.resolution_percentage = 100
    if "--sound" in ARGS:
        res["sound"] = sound(os.path.join(DAY, "musicbox.wav"))
    if "--clay" in ARGS:
        res["clay"] = clay(os.path.join(DAY, "clay", "musicbox_clay.blend"))
    res["audit"] = pb.audit(NAME)
    res["describe"] = pb.describe("PA_MusicBox_GN")
    print("BUILD_RESULT", res)
