"""Nodevember 2026 · Day 06 · Vault — v5: Rouen / 盧昂主教座堂中殿.

Lying on the floor of an endless Gothic nave with our head towards the west end, looking up: the vault
runs from overhead (bottom of the frame) to the rose window (top). Modelled on the nave of Rouen
Cathedral (28 m high): a four-storey elevation (arcade on compound piers, the "false tribune" that opens
into the tall aisle without a floor, a triforium of small lancets, a deep clerestory with a passage),
continuous shallow-moulded pilasters from the floor to the springing, banded at every storey, and a
quadripartite rib vault (heavy transverse arches, moulded diagonals, rosette bosses, no ridge rib) whose
cells are laid in ochre axial running bond, with each row conforming to the barrel.

Geometry. A bay is the intersection of two pointed barrels, z = Zs + P(min(u, v)) (see v3). Each cell is
parametrised along its barrel axis and curved arch section, with staggered stones cut to each diagonal rib.
One wall bay (Mesh Boolean of a slab and its openings) is built once and instanced on both sides.

Node groups. Every recipe that is used more than once is one node group (PA_PointedProfile, PA_Bays,
PA_LancetCutter, PA_ArchMoulding, PA_HalfArch, PA_VaultCells, PA_SectionLoft, PA_CarvedPilaster,
PA_StoneNormals, PA_AshlarCoordinates, PA_LimestoneNoise), and the two big assemblies are groups too
(PA_WallBay, PA_WestWall). The main tree PA_Rouen_GN is four short sections that call them.

Loop: the camera walks one bay per loop; the nave is periodic, so frame N+1 = frame 1. The west wall
stays at a fixed distance ahead.

Run: Blender -b --factory-startup --python build.py -- [--preview f,..] [--look f,..] [--still N]
     [--clay] [--cam x,y,z,pitch,lens,roll] [--save-as x.blend]
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix

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
NAME = "Rouen"

FRAMES = 300                     # 10 s @ 30 fps: one bay per loop
B = 6.3                          # bay length
W = 11.0                         # nave width (wall face to wall face)
ZS = 20.5                        # springing of the high vault
H = 7.5                          # rise (crown at 28 m)
RHO = 1.35                       # two-centred arch: radius / half-span
K0, K1 = -3, 19                  # bays generated
NB = K1 - K0 + 1
WEST = 17.3 * B                  # west wall, fixed distance ahead of the camera
NT, NL = 44, 36                  # courses stepping over transverse / wall barrel sections
BRICK = 0.78
JOINT = 0.008
T = 1.6                          # wall thickness
TOP = ZS + H + 1.0
AISLE = 5.6                      # aisle width (to the outer wall)
AISLE_TOP = 17.8                 # aisle vault (the false tribune opens into the tall aisle)

# elevation (z): arcade, false tribune, triforium, clerestory
AR_W, AR_SPRING = 4.0, 6.5      # arcade apex ~10.9: a clear spandrel under the tribune sill
TR_W, TR_SPRING, TR_SILL = 3.2, 13.8, 12.2     # flat spandrel above the arcade, then the tribune jambs
TF_SILL, TF_SPRING, TF_TOP = 17.75, 19.0, 19.75
CL_W, CL_SPRING, CL_SILL = 3.8, 24.0, 20.3
STRINGS = (17.55, 19.95)        # (a string under the tribune read as a loose bar from below: dropped)
# Directional light (2026-11-07): a low warm sun through the far (+x) clerestory lays a patch on the near
# elevation in every bay; fills are kept low so the vault reads as bounce light, darker than the patches.
SKY = 2.9
FILL = 1100.0                   # warm fill from the floor (the lamps of the nave)
WINDOW_FILL = 35.0              # soft sky bounce through each high clerestory opening, aimed at the vault
SUN_ELEVATION, SUN_HEADING = 30.0, 75.0     # degrees; heading is the sun lamp's Z rotation (+x side)
SUN_ENERGY, SUN_COLOR = 10.0, (1.0, 0.88, 0.74)
EXPOSURE = 0.92


# ───────────────────────────────────────────────────────── node groups
GROUPS = {}
STYPE = {"float": "NodeSocketFloat", "int": "NodeSocketInt", "bool": "NodeSocketBool",
         "vector": "NodeSocketVector", "geometry": "NodeSocketGeometry"}


def node_group(name, inputs, outputs, body, kind="GeometryNodeTree"):
    """PA_<name>, built once per run. inputs: (socket, type[, default]); outputs: (socket, type).
    body(g, i) gets the Group Input sockets by name and returns {output socket name: node or socket}."""
    full = "PA_" + name
    if full in GROUPS:
        return GROUPS[full]
    old = bpy.data.node_groups.get(full)
    if old is not None:
        bpy.data.node_groups.remove(old)
    t = bpy.data.node_groups.new(full, kind)
    for spec in inputs:
        s = t.interface.new_socket(spec[0], in_out="INPUT", socket_type=STYPE[spec[1]])
        if len(spec) > 2:
            s.default_value = spec[2]
    for nm, typ in outputs:
        t.interface.new_socket(nm, in_out="OUTPUT", socket_type=STYPE[typ])
    g = pb.Graph(t)
    gin, gout = g.group_io()
    res = body(g, {s.name: s for s in gin.outputs if s.name and s.bl_idname != "NodeSocketVirtual"})
    g.end_section()
    for nm, v in res.items():
        g.link(v, gout.inputs[nm])
    pb.arrange(t)
    GROUPS[full] = t
    return t


def call(g, tree, label=None, **inputs):
    n = g.group(tree, **inputs)
    if label:
        n.label = label
    return n


# ───────────────────────────────────────────────────────── helpers
def xyz(g, v):
    n = g.node("ShaderNodeSeparateXYZ", Vector=v)
    return [g.out(n, c) for c in "XYZ"]


def join(g, geos, label=None):
    n = g.node("GeometryNodeJoinGeometry", label=label)
    for geo in geos:
        g.link(geo, n, b_key="Geometry")
    return n


def store(g, geo, name, value, kind="FLOAT", domain="POINT", label=None):
    return g.node("GeometryNodeStoreNamedAttribute", label=label or name, props={"data_type": kind, "domain": domain},
                  Geometry=geo, Name=name, Value=value)


def named(g, name, kind="FLOAT"):
    return g.node("GeometryNodeInputNamedAttribute", props={"data_type": kind}, Name=name)


def realize(g, geo):
    return g.node("GeometryNodeRealizeInstances", Geometry=geo)


def box(g, size, at, label=None):
    return g.node("GeometryNodeTransform", label=label, Geometry=g.node("GeometryNodeMeshCube", Size=size),
                  Translation=at)


def cyl(g, r, depth, at, verts=24, rot=(0, 0, 0), label=None):
    return g.node("GeometryNodeTransform", label=label,
                  Geometry=g.node("GeometryNodeMeshCylinder", Vertices=verts, Radius=r, Depth=depth),
                  Rotation=rot, Translation=at)


def sgn(g, v):
    return g.math("SUBTRACT", g.math("MULTIPLY", v, 2.0), 1.0)


def _pointed_profile(g, i):
    d = g.math("ADD", i["u"], RHO - 1.0)
    inner = g.math("MAXIMUM", g.math("SUBTRACT", RHO * RHO, g.math("MULTIPLY", d, d)), 0.0)
    return {"Height": g.math("MULTIPLY", g.math("SQRT", inner), H / math.sqrt(2 * RHO - 1))}


def P(g, u):
    """PA_PointedProfile: two-centred pointed profile, height above the springing at u (0 = crown, 1 = springing)."""
    t = node_group("PointedProfile", [("u", "float")], [("Height", "float")], _pointed_profile)
    return g.out(call(g, t, "pointed profile P(u)", u=u), "Height")


def template(g, n, name):
    """A polyline of n points with a 0..1 parameter stored as `name`."""
    line = g.node("GeometryNodeResampleCurve", Curve=g.node("GeometryNodeCurvePrimitiveLine", Start=(0, 0, 0),
                                                              End=(1, 0, 0)), Count=n)
    return store(g, line, name, g.out(g.node("GeometryNodeSplineParameter"), "Factor"))


def _bays(g, i):
    per = i["Per"]
    idx = g.node("GeometryNodeInputIndex")
    k = g.math("ADD", K0, g.math("FLOOR", g.math("DIVIDE", idx, per)))
    j = g.math("FLOORED_MODULO", idx, per)
    pts = g.node("GeometryNodePoints", label="one point per copy, in every bay", Count=g.math("MULTIPLY", NB, per))
    pts = store(g, pts, "y0", g.math("MULTIPLY", k, B))
    return {"Points": store(g, pts, "j", j)}


def bays(g, per, label):
    """PA_Bays: points = bays × per, with (bay start y0, sub index j) as fields."""
    t = node_group("Bays", [("Per", "int", 1)], [("Points", "geometry")], _bays)
    return call(g, t, label, Per=per)


# ───────────────────────────────────────────────────────── arch outlines (curves) and their cutters
def arc(g, cy, cz, r, a0, a1, x0, n=20):
    """Circular arc in the wall plane x = x0, centre (cy, cz), angles a0 → a1 (0 = +y, π/2 = up)."""
    c = template(g, n, "t")
    ang = g.math("ADD", a0, g.math("MULTIPLY", named(g, "t"), a1 - a0))
    return g.node("GeometryNodeSetPosition", Geometry=c,
                  Position=g.vec(x0, g.math("ADD", cy, g.math("MULTIPLY", g.math("COSINE", ang), r)),
                                 g.math("ADD", cz, g.math("MULTIPLY", g.math("SINE", ang), r))))


def tube(g, curve, r, res=10):
    prof = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=res, Radius=r)
    return g.node("GeometryNodeCurveToMesh", Curve=curve, Profile_Curve=prof, Fill_Caps=True)


def _lancet(g, i):
    w, spring, sill, depth, yc, x0 = (i[k] for k in ("Width", "Spring", "Sill", "Depth", "Center Y", "Face X"))
    bx = box(g, g.vec(depth, w, g.math("ADD", g.math("SUBTRACT", spring, sill), 0.01)),
             g.vec(x0, yc, g.math("MULTIPLY", g.math("ADD", spring, sill), 0.5)), "jambs: a box up to the springing")
    lens = g.node("GeometryNodeMeshBoolean", label="the pointed head: two circles overlap",
                  props={"operation": "INTERSECT", "solver": "EXACT"})
    half = g.math("MULTIPLY", w, 0.5)
    for s in (-1, 1):
        g.link(cyl(g, w, depth, g.vec(x0, g.math("ADD", yc, g.math("MULTIPLY", half, s)), spring), verts=72,
                   rot=(0, PI / 2, 0)), lens, b_key="Mesh")
    w2 = g.math("ADD", w, 0.02)
    g.link(box(g, g.vec(g.math("ADD", depth, 0.02), w2, w2),
               g.vec(x0, yc, g.math("ADD", spring, g.math("MULTIPLY", w2, 0.5))),
               "arch head: clip lens above springing"), lens, b_key="Mesh")
    return {"Jamb": bx, "Head": lens}


def lancet(g, w, spring, sill, depth, yc, x0):
    """PA_LancetCutter: cutter for an equilateral lancet, jamb box plus only the upper half of the circle lens.

    The full lens is symmetric about spring. Its lower tip can extend below a high sill,
    cutting an unwanted inverted arch into the spandrel (especially the tribune).
    Two outputs, linked into the boolean one by one.
    """
    t = node_group("LancetCutter", [("Width", "float", 1.0), ("Spring", "float"), ("Sill", "float"),
                                    ("Depth", "float", 1.0), ("Center Y", "float"), ("Face X", "float")],
                   [("Jamb", "geometry"), ("Head", "geometry")], _lancet)
    n = call(g, t, "lancet cutter", Width=w, Spring=spring, Sill=sill, Depth=depth, Center_Y=yc, Face_X=x0)
    return [g.out(n, "Jamb"), g.out(n, "Head")]


def solid_lancet(g, w, spring, sill, depth, yc, x0):
    u = g.node("GeometryNodeMeshBoolean", props={"operation": "UNION", "solver": "EXACT"})
    for part in lancet(g, w, spring, sill, depth, yc, x0):
        g.link(part, u, b_key="Mesh")
    return u


def disc(g, r, depth, x0, y, z, verts=40):
    return cyl(g, r, depth, (x0, y, z), verts=verts, rot=(0, PI / 2, 0))


# ───────────────────────────────────────────────────────── materials
def _limestone_noise(g, i):
    at = g.out(g.node("ShaderNodeAttribute", props={"attribute_name": "stone_position"}), "Vector")
    x, y, z = xyz(g, at)
    sx, sy, sz = xyz(g, i["Stretch"])
    angle = g.math("MULTIPLY", y, TAU / B)
    radius = g.math("MULTIPLY", sy, B / TAU)
    noise = g.node("ShaderNodeTexNoise", label="4D noise: y wrapped onto a circle one bay round",
                   props={"noise_dimensions": "4D"},
                   Vector=g.vec(g.math("MULTIPLY", x, sx), g.math("MULTIPLY", g.math("COSINE", angle), radius),
                                g.math("MULTIPLY", z, sz)),
                   W=g.math("MULTIPLY", g.math("SINE", angle), radius),
                   Scale=i["Scale"], Detail=i["Detail"], Roughness=0.72)
    return {"Factor": g.out(noise, "Factor")}


def limestone_noise(g, scale, detail=4.0, stretch=(1, 1, 1), label="limestone grain"):
    """PA_LimestoneNoise: material coordinates stay on the moving stone and repeat seamlessly every nave bay."""
    t = node_group("LimestoneNoise", [("Scale", "float", 5.0), ("Detail", "float", 2.0), ("Stretch", "vector", (1, 1, 1))],
                   [("Factor", "float")], _limestone_noise, kind="ShaderNodeTree")
    return call(g, t, label, Scale=scale, Detail=detail, Stretch=stretch)


def stone(name, color, ashlar=False, row=0.36, brick=0.7, grime=0.5, stains=0.3, courses=False):
    """Limestone: per-stone tone, mottling, ambient-occlusion grime in the hollows; ashlar=True adds coursed
    blocks on the wall's own 'auv' coordinates (stored in GN before the bays are instanced)."""
    st = pb.material(name, "matte", color=color, roughness=0.94)
    g = pb.Graph(st.node_tree)
    p = next(n for n in g.nodes if n.type == "BSDF_PRINCIPLED")
    tone = g.out(g.node("ShaderNodeAttribute", label="per-stone tone", props={"attribute_name": "tone"}), "Fac")
    p.inputs["Specular IOR Level"].default_value = 0.18
    nz = limestone_noise(g, 1.8, 6.0, label="weathered limestone mottling")
    mottling = g.node("ShaderNodeMapRange", Value=g.out(nz, "Factor"), From_Min=0.28, From_Max=0.72,
                      To_Min=0.0, To_Max=1.0)
    base = g.node("ShaderNodeMix", props={"data_type": "RGBA"}, Factor=mottling,
                  A=(*(c * 0.63 for c in color), 1), B=(*(min(1, c * 1.13) for c in color), 1))
    col = g.out(g.node("ShaderNodeMix", label="tone", props={"data_type": "RGBA", "blend_type": "MULTIPLY"}, Factor=1.0,
                       A=g.out(base, "Result"), B=g.vec(tone, tone, g.math("MULTIPLY", tone, 0.98))), "Result")
    fine = limestone_noise(g, 75.0, 3.0, label="fine open stone pores")
    height = g.out(fine, "Factor")
    grain = g.node("ShaderNodeMapRange", Value=height, From_Min=0.30, From_Max=0.70, To_Min=0.79, To_Max=1.0)
    col = g.out(g.node("ShaderNodeMix", label="subtle granular limestone color",
                       props={"data_type": "RGBA", "blend_type": "MULTIPLY"}, Factor=1.0,
                       A=col, B=g.vec(grain, grain, grain)), "Result")
    if ashlar:
        uv = g.node("ShaderNodeAttribute", label="ashlar coordinates", props={"attribute_name": "auv"})
        br = g.node("ShaderNodeTexBrick", label="ashlar courses", props={"offset": 0.5, "offset_frequency": 2},
                    Vector=g.out(uv, "Vector"), Color1=(1.0, 0.99, 0.97, 1), Color2=(0.86, 0.84, 0.80, 1),
                    Mortar=(0.67, 0.64, 0.59, 1), Scale=1.0, Mortar_Size=0.007, Mortar_Smooth=0.5, Bias=0.0,
                    Brick_Width=brick, Row_Height=row)
        col = g.out(g.node("ShaderNodeMix", label="blocks", props={"data_type": "RGBA", "blend_type": "MULTIPLY"},
                           Factor=1.0, A=col, B=g.out(br, "Color")), "Result")
        height = g.math("SUBTRACT", g.math("MULTIPLY", height, 0.15), g.out(br, "Fac"))
    if courses:
        mask = g.out(g.node("ShaderNodeAttribute", props={"attribute_name": "masonry_mask"}), "Fac")
        dist = g.out(g.node("ShaderNodeAttribute", props={"attribute_name": "masonry_distance"}), "Fac")
        course = g.math("DIVIDE", dist, 0.62)
        joint = g.math("MULTIPLY", mask, g.math("LESS_THAN", g.math("FRACT", course), 0.009))
        variation = g.out(g.node("ShaderNodeTexWhiteNoise", label="subtle tone per stone block",
                                 props={"noise_dimensions": "1D"}, W=g.math("FLOOR", course)), "Value")
        block_tone = g.math("ADD", 0.95, g.math("MULTIPLY", variation, 0.08))
        block_tone = g.math("ADD", 1.0, g.math("MULTIPLY", mask, g.math("SUBTRACT", block_tone, 1.0)))
        factor = g.math("MULTIPLY", block_tone, g.math("SUBTRACT", 1.0, g.math("MULTIPLY", joint, 0.18)))
        col = g.out(g.node("ShaderNodeMix", label="fine masonry joints, not applied collars",
                          props={"data_type": "RGBA", "blend_type": "MULTIPLY"}, Factor=1.0,
                          A=col, B=g.vec(factor, factor, factor)), "Result")
        height = g.math("SUBTRACT", height, g.math("MULTIPLY", joint, 0.8))
    ao = g.node("ShaderNodeAmbientOcclusion", label="grime in the hollows", Distance=0.6, Color=(1, 1, 1, 1))
    dirt = g.node("ShaderNodeMapRange", Value=g.out(ao, "AO"), From_Min=0.0, From_Max=1.0, To_Min=1.0 - grime,
                  To_Max=1.0)
    col = g.out(g.node("ShaderNodeMix", label="grime", props={"data_type": "RGBA", "blend_type": "MULTIPLY"}, Factor=1.0,
                       A=col, B=g.vec(dirt, dirt, dirt)), "Result")
    st_n = limestone_noise(g, 0.55, 5.0, stretch=(1.7, 1.2, 0.22), label="long mineral and water streaks")
    st_m = g.node("ShaderNodeMapRange", Value=g.out(st_n, "Factor"), From_Min=0.34, From_Max=0.68, To_Min=stains,
                  To_Max=0.0)
    stain_tint = g.out(g.node("ShaderNodeMix", label="umber mineral deposits", props={"data_type": "RGBA"},
                            Factor=st_m, A=(1, 1, 1, 1), B=(0.31, 0.24, 0.16, 1)), "Result")
    col = g.out(g.node("ShaderNodeMix", label="stains", props={"data_type": "RGBA", "blend_type": "MULTIPLY"},
                       Factor=1.0, A=col, B=stain_tint), "Result")
    g.link(col, p, b_key="Base Color")
    rough = g.node("ShaderNodeMapRange", Value=g.out(fine, "Factor"), From_Min=0.2, From_Max=0.8,
                   To_Min=0.86, To_Max=0.99)
    g.link(rough, p, b_key="Roughness")
    g.link(g.node("ShaderNodeBump", Height=height, Strength=0.28 if ashlar else 0.24,
                  Distance=0.005 if ashlar else 0.003), p, b_key="Normal")
    pb.arrange(g.tree)
    return st


def leaded_glass(name="LeadedGlass", glow=3.0):
    """Clear glazing in diamond quarries with saddle bars; transparent, plus a camera-only glow for the bright
    daylight seen through it, with the pale blue panes visible in the material reference."""
    mt = bpy.data.materials.new("PA_" + name)
    mt.use_nodes = True
    nt = mt.node_tree
    nt.nodes.clear()
    g = pb.Graph(nt)
    uv = g.out(g.node("ShaderNodeAttribute", label="pane coordinates", props={"attribute_name": "guv"}), "Vector")
    _, u, v = xyz(g, uv)
    a = g.math("ADD", g.math("DIVIDE", u, 0.15), g.math("DIVIDE", v, 0.22))
    b = g.math("SUBTRACT", g.math("DIVIDE", u, 0.15), g.math("DIVIDE", v, 0.22))
    came = g.math("MINIMUM", g.math("PINGPONG", a, 0.5), g.math("PINGPONG", b, 0.5))
    lead = g.math("LESS_THAN", came, 0.04)
    bar = g.math("LESS_THAN", g.math("PINGPONG", v, 0.42), 0.014)
    opaque = g.math("MAXIMUM", lead, bar)
    wav = g.node("ShaderNodeTexNoise", label="crown-glass waviness", Vector=uv, Scale=7.0, Detail=2.0)
    tint = g.out(g.node("ShaderNodeMix", props={"data_type": "RGBA"}, Factor=g.out(wav, "Factor"),
                        A=(0.53, 0.76, 0.82, 1), B=(0.82, 0.92, 0.95, 1)), "Result")
    tr = g.node("ShaderNodeBsdfTransparent", Color=tint)
    seen = g.out(g.node("ShaderNodeLightPath"), "Is Camera Ray")
    em = g.node("ShaderNodeEmission", Color=(0.42, 0.70, 0.86, 1), Strength=g.math("MULTIPLY", seen, glow))
    lit = g.node("ShaderNodeAddShader", ins={0: tr, 1: em})
    iron = g.node("ShaderNodeBsdfDiffuse", Color=(0.03, 0.03, 0.03, 1))
    mix = g.node("ShaderNodeMixShader", Fac=opaque, ins={1: lit, 2: iron})
    g.link(mix, g.node("ShaderNodeOutputMaterial"), b_key="Surface")
    pb.arrange(nt)
    return mt


def materials():
    return {
        "wall": stone("Wall", (0.43, 0.415, 0.38), ashlar=True, grime=0.62, stains=0.55),
        "trim": stone("Trim", (0.49, 0.465, 0.41), grime=0.74, stains=0.58, courses=True),
        "rib": stone("Rib", (0.65, 0.55, 0.36), grime=0.65, stains=0.38, courses=True),
        "web": stone("Web", (0.69, 0.465, 0.22), grime=0.60, stains=0.65),
        "aisle": stone("Aisle", (0.38, 0.365, 0.33), ashlar=True, grime=0.62, stains=0.55),
        "glass": leaded_glass(glow=2.0),
        "mortar": pb.material("Mortar", "matte", color=(0.22, 0.14, 0.065), roughness=0.96),
        "roof": pb.material("Roof", "matte", color=(0.08, 0.06, 0.05), roughness=0.9),
        "floor": pb.material("Floor", "matte", color=(0.42, 0.38, 0.33), roughness=0.5),
    }


# ───────────────────────────────────────────────────────── ribs
def fold_list(sw, label):
    """A fixed list in an Index Switch: hide its value sockets (Ctrl+H shows them) so it draws as one small node."""
    sw.label = label
    for s in list(sw.inputs)[1:]:
        if not s.is_linked:
            s.hide = True


def polygon_section(g, coords, filled=False):
    """One closed section, including sampled convex rolls, concave hollows and sharp fillets."""
    coords = [p for i, p in enumerate(coords)
              if i == 0 or math.hypot(p[0] - coords[i - 1][0], p[1] - coords[i - 1][1]) > 1e-8]
    if sum(x * coords[(i + 1) % len(coords)][1] - coords[(i + 1) % len(coords)][0] * y
           for i, (x, y) in enumerate(coords)) < 0:
        coords = list(reversed(coords))
    mesh = g.node("GeometryNodeMeshCircle", label="one continuous moulding section",
                  props={"fill_type": "NGON" if filled else "NONE"}, Vertices=len(coords), Radius=1.0)
    sw = g.node("GeometryNodeIndexSwitch", props={"data_type": "VECTOR"}, Index=g.node("GeometryNodeInputIndex"))
    while len(sw.index_switch_items) < len(coords):
        sw.index_switch_items.new()
    for i, (x, y) in enumerate(coords):
        sw.inputs[str(i)].default_value = (x, y, 0)
    fold_list(sw, f"{len(coords)} section points (x, y)")
    mesh = g.node("GeometryNodeSetPosition", Geometry=mesh, Position=sw)
    return mesh if filled else g.node("GeometryNodeMeshToCurve", Mesh=mesh)


def _stone_normals(g, i):
    mesh = g.node("GeometryNodeSetShadeSmooth", Geometry=i["Mesh"], Shade_Smooth=True)
    angle = g.out(g.node("GeometryNodeInputMeshEdgeAngle"), "Unsigned Angle")
    return {"Mesh": store(g, mesh, "sharp_edge", g.math("GREATER_THAN", angle, math.radians(24)),
                          kind="BOOLEAN", domain="EDGE", label="sharp where the faces meet at more than 24°")}


def stone_normals(g, mesh):
    """PA_StoneNormals: smooth the arch's curvature while preserving the flat faces of the carved section."""
    t = node_group("StoneNormals", [("Mesh", "geometry")], [("Mesh", "geometry")], _stone_normals)
    return call(g, t, "crisp fillets, smooth arch curvature", Mesh=mesh)


def masonry_distance(g, geo, distance):
    geo = store(g, geo, "masonry_distance", distance, label="distance along the laid stone")
    return store(g, geo, "masonry_mask", 1.0, label="stone block courses on mouldings")


def rib_coords():
    """A rounded soffit roll, recessed hollows and small shoulder beads on one stone core (unit size)."""
    half = [(0.20 * i / 16, -0.27 - 0.18 * math.sqrt(max(0, 1 - (i / 16) ** 2))) for i in range(17)]
    half.append((0.22, -0.27))
    for i in range(1, 13):
        t = i / 12
        half.append((0.22 + 0.13 * t, -0.27 + 0.19 * t + 0.055 * math.sin(PI * t)))
    for i in range(17):
        t = i / 16
        half.append((0.35 + 0.11 * t, -0.04 - 0.07 * math.sqrt(max(0, 1 - (2 * t - 1) ** 2))))
    half += [(0.48, -0.04), (0.5, 0.01)]
    return [(-x, y) for x, y in reversed(half[1:])] + half + [(0.5, 0.30), (-0.5, 0.30)]


def _half_arch(g, i):
    g.begin_section("a · Three paths: transverse arch, wall rib, diagonal rib")
    pts = bays(g, i["Per"], "one point per half-arch")
    cur = realize(g, g.node("GeometryNodeInstanceOnPoints", Points=pts, Instance=template(g, 48, "t")))
    j, y0 = named(g, "j"), named(g, "y0")
    u = g.math("SUBTRACT", 1.0, named(g, "t"))
    hz = g.math("ADD", ZS, P(g, u))
    a = sgn(g, g.math("FLOORED_MODULO", j, 2))                     # which end / which half: ±1
    b = sgn(g, g.math("FLOOR", g.math("DIVIDE", j, 2)))            # which side of the nave: ±1
    yc = g.math("ADD", y0, B / 2)
    transverse = g.vec(g.math("MULTIPLY", g.math("MULTIPLY", a, u), W / 2), y0, hz)
    transverse.label = "0 · transverse arch: across the nave on the bay line"
    wall = g.vec(g.math("MULTIPLY", b, W / 2 - 0.05),
                 g.math("ADD", yc, g.math("MULTIPLY", g.math("MULTIPLY", a, u), B / 2)), hz)
    wall.label = "1 · wall rib: along the wall face"
    diag = g.vec(g.math("MULTIPLY", g.math("MULTIPLY", b, u), W / 2),
                 g.math("ADD", yc, g.math("MULTIPLY", g.math("MULTIPLY", a, u), B / 2)), hz)
    diag.label = "2 · diagonal rib: corner to boss"
    pos = g.node("GeometryNodeIndexSwitch", label="path of this kind", props={"data_type": "VECTOR"}, Index=i["Kind"])
    sw_n = g.node("GeometryNodeIndexSwitch", label="section plane of this kind", props={"data_type": "VECTOR"},
                  Index=i["Kind"])
    for sw in (pos, sw_n):
        while len(sw.index_switch_items) < 3:
            sw.index_switch_items.new()
    for k, v in enumerate((transverse, wall, diag)):
        g.link(v, pos, b_key=str(k))
    normals = (g.vec(0, g.math("MULTIPLY", a, -1), 0), g.vec(a, 0, 0),
               g.vmath("NORMALIZE", g.vec(g.math("MULTIPLY", a, B / 2), g.math("MULTIPLY", b, -W / 2), 0)))
    for k, v in enumerate(normals):
        g.link(v, sw_n, b_key=str(k))
    g.begin_section("b · Sweep the rib section along it")
    cur = g.node("GeometryNodeSetPosition", label="onto the arch", Geometry=cur,
                 Position=g.vmath("ADD", pos, g.vec(0, 0, i["Lift"])))
    nrm = g.node("GeometryNodeSetCurveNormal", label="profile square to the arch's plane", Curve=cur, Normal=sw_n)
    nrm.inputs["Mode"].default_value = "Free"
    nrm = masonry_distance(g, nrm, g.out(g.node("GeometryNodeSplineParameter"), "Length"))
    prof = g.node("GeometryNodeTransform", label="rib section, scaled to width × depth",
                  Geometry=polygon_section(g, rib_coords()), Scale=g.vec(i["Rib width"], i["Rib depth"], 1.0))
    m = g.node("GeometryNodeCurveToMesh", Curve=nrm, Profile_Curve=prof, Fill_Caps=True)
    return {"Rib": stone_normals(g, m)}


def half_arches(g, kind, per, wd, dp, label, lift):
    """PA_HalfArch: springing-to-crown half-arches, `per` per bay. Kind 0 = transverse arch, 1 = wall rib,
    2 = diagonal rib; all three follow the same pointed profile P(u)."""
    t = node_group("HalfArch", [("Kind", "int"), ("Per", "int", 2), ("Rib width", "float", 0.3),
                                ("Rib depth", "float", 0.3), ("Lift", "float")], [("Rib", "geometry")], _half_arch)
    return g.out(call(g, t, label, Kind=kind, Per=per, Rib_width=wd, Rib_depth=dp, Lift=lift), "Rib")


def boss_mesh(g, r):
    sph = g.node("GeometryNodeMeshUVSphere", Segments=48, Rings=16, Radius=r)
    px, py, pz = xyz(g, g.node("GeometryNodeInputPosition"))
    ang = g.math("ARCTAN2", py, px)
    rose = g.math("ADD", 1.0, g.math("MULTIPLY", 0.18, g.math("COSINE", g.math("MULTIPLY", ang, 8))))
    return g.node("GeometryNodeSetPosition", label="eight-petal rosette", Geometry=sph,
                  Position=g.vec(g.math("MULTIPLY", px, rose), g.math("MULTIPLY", py, rose),
                                 g.math("MULTIPLY", pz, 0.45)))


def ribs(g):
    tr = half_arches(g, 0, 2, 0.52, 0.42, "transverse arches: 2 halves per bay", lift=-0.16)
    wr = half_arches(g, 1, 4, 0.30, 0.34, "wall ribs (formerets)", lift=-0.08)
    dg = half_arches(g, 2, 4, 0.31, 0.32, "diagonal ribs: 4 halves per bay", lift=-0.12)
    pts = bays(g, 1, "one boss per bay")
    pts = g.node("GeometryNodeSetPosition", Geometry=pts,
                 Position=g.vec(0, g.math("ADD", named(g, "y0"), B / 2), ZS + H - 0.42))
    boss = realize(g, g.node("GeometryNodeInstanceOnPoints", Points=pts, Instance=boss_mesh(g, 0.55)))
    return store(g, join(g, [tr, wr, dg, boss]), "tone", 1.0)


# ───────────────────────────────────────────────────────── the cells, stone by stone
def _vault_cells(g, i):
    n, span, along, lateral, row_gap = i["Courses"], i["Span"], i["Along"], i["Lateral"], i["Row gap"]
    theta_top = math.acos((RHO - 1) / RHO)
    rx, rz = g.math("MULTIPLY", span, RHO), H / math.sqrt(2 * RHO - 1) * RHO
    g.begin_section("a · One point per course")
    pts = bays(g, g.math("MULTIPLY", n, 4), "4 × courses points per bay")
    j = named(g, "j")
    pts = store(g, pts, "side", sgn(g, g.math("FLOOR", g.math("DIVIDE", j, g.math("MULTIPLY", n, 2)))))
    pts = store(g, pts, "half", sgn(g, g.math("FLOORED_MODULO", g.math("FLOOR", g.math("DIVIDE", j, n)), 2)))
    pts = store(g, pts, "course", g.math("FLOORED_MODULO", j, n))
    theta = g.math("MULTIPLY", theta_top,
                   g.math("SUBTRACT", 1, g.math("DIVIDE", g.math("ADD", named(g, "course"), .5), n)))
    u = g.math("SUBTRACT", g.math("MULTIPLY", RHO, g.math("COSINE", theta)), RHO - 1)
    g.begin_section("b · How long is the row")
    pts = store(g, pts, "row_length", g.math("MULTIPLY", along, g.math("SUBTRACT", 1, u)))
    pts = g.node("GeometryNodeDeleteGeometry", label="omit slivers fully covered by the diagonal rib",
                 props={"domain": "POINT"}, Geometry=pts, Selection=g.math("LESS_THAN", named(g, "row_length"), .06))
    pts = store(g, pts, "pieces", g.math("MAXIMUM", 2,
                g.math("ROUND", g.math("DIVIDE", named(g, "row_length"), BRICK))))
    g.begin_section("c · Running bond")
    cur = realize(g, g.node("GeometryNodeInstanceOnPoints", Points=pts, Instance=template(g, 2, "t")))
    cur = g.node("GeometryNodeSetPosition", Geometry=cur,
                 Position=g.vec(g.math("MULTIPLY", named(g, "t"), named(g, "row_length")), 0, 0))
    odd = g.math("FLOORED_MODULO", named(g, "course"), 2)
    trim = g.math("DIVIDE", g.math("MULTIPLY", odd, .5), named(g, "pieces"))
    cur = g.node("GeometryNodeTrimCurve", label="alternate rows offset by half a stone", props={"mode": "FACTOR"},
                 Curve=cur, Start=trim, End=g.math("SUBTRACT", 1, trim))
    cur = g.node("GeometryNodeResampleCurve", Curve=cur,
                 Count=g.math("SUBTRACT", g.math("ADD", named(g, "pieces"), 1), odd))
    cur = store(g, cur, "f", g.out(g.node("GeometryNodeSplineParameter"), "Factor"))
    pts = g.out(g.node("GeometryNodeCurveToPoints", props={"mode": "EVALUATED"}, Curve=cur), "Points")
    px, _, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    fraction = g.math("DIVIDE", px, named(g, "row_length"))
    end = g.math("MULTIPLY", g.math("SUBTRACT", 1, odd),
                 g.math("MAXIMUM", g.math("LESS_THAN", named(g, "f"), .001),
                        g.math("GREATER_THAN", named(g, "f"), .999)))
    center = g.math("ADD", fraction, g.math("MULTIPLY", g.math("DIVIDE", end, named(g, "pieces")),
                  g.math("MULTIPLY", .25, sgn(g, g.math("LESS_THAN", named(g, "f"), .5)))))
    half_width = g.math("MULTIPLY", .5, g.math("SUBTRACT",
                  g.math("DIVIDE", g.math("SUBTRACT", 1, g.math("MULTIPLY", end, .5)), named(g, "pieces")),
                  g.math("DIVIDE", JOINT, named(g, "row_length"))))
    half_width = g.math("MAXIMUM", half_width, .001)
    pts = store(g, pts, "brick_start", g.math("SUBTRACT", center, half_width))
    pts = store(g, pts, "brick_end", g.math("ADD", center, half_width))
    brick_id = g.math("ROUND", g.math("MULTIPLY", 2,
                       g.math("MULTIPLY", named(g, "pieces"),
                              g.math("ADD", named(g, "brick_start"), named(g, "brick_end")))))
    local_id = g.math("ADD", g.math("MULTIPLY", named(g, "course"), 256),
                      g.math("ADD", g.math("MULTIPLY", g.math("ADD", named(g, "side"), 1), 64),
                             g.math("ADD", g.math("MULTIPLY", g.math("ADD", named(g, "half"), 1), 32), brick_id)))
    rnd = g.node("FunctionNodeRandomValue", label="stone tone repeats identically in every nave bay",
                 props={"data_type": "FLOAT"}, Min=.91, Max=1.03, ID=local_id, Seed=i["Seed"])
    pts = store(g, pts, "tone", g.out(rnd, "Value"))
    g.begin_section("d · Every stone onto the barrel")
    pts = g.node("GeometryNodeSetPosition", Geometry=pts, Position=(0, 0, 0))
    stone = g.node("GeometryNodeMeshCube", label="subdivided brick parameter box", Size=(1, 1, 1),
                   Vertices_X=2, Vertices_Y=3, Vertices_Z=2)
    x, y, z = xyz(g, g.node("GeometryNodeInputPosition"))
    stone = store(g, stone, "brick_local", g.vec(g.math("ADD", x, .5), g.math("ADD", y, .5),
                  g.math("ADD", z, .5)), kind="FLOAT_VECTOR")
    mesh = realize(g, g.node("GeometryNodeInstanceOnPoints", Points=pts, Instance=stone))
    t, a, depth = xyz(g, named(g, "brick_local", "FLOAT_VECTOR"))
    course = g.math("ADD", g.math("DIVIDE", named(g, "course"), n), row_gap)
    course = g.math("ADD", course, g.math("MULTIPLY", a, g.math("SUBTRACT", g.math("DIVIDE", 1, n),
                                                                  g.math("MULTIPLY", row_gap, 2))))
    theta = g.math("MULTIPLY", theta_top, g.math("SUBTRACT", 1, course))
    u = g.math("SUBTRACT", g.math("MULTIPLY", RHO, g.math("COSINE", theta)), RHO - 1)
    v = g.math("ADD", named(g, "brick_start"),
               g.math("MULTIPLY", t, g.math("SUBTRACT", named(g, "brick_end"), named(g, "brick_start"))))
    v = g.math("ADD", u, g.math("MULTIPLY", g.math("SUBTRACT", 1, u), v))
    cross = g.math("MULTIPLY", named(g, "half"), g.math("MULTIPLY", span, u))
    along_pos = g.math("MULTIPLY", named(g, "side"), g.math("MULTIPLY", along, v))
    crown = g.math("ADD", ZS, g.math("MULTIPLY", rz, g.math("SINE", theta)))
    yc = g.math("ADD", named(g, "y0"), B / 2)
    pos = g.node("GeometryNodeSwitch", label="transverse cell: courses along y · wall cell: along x",
                 props={"input_type": "VECTOR"}, Switch=lateral,
                 False_=g.vec(cross, g.math("ADD", yc, along_pos), crown),
                 True_=g.vec(along_pos, g.math("ADD", yc, cross), crown))
    nx = g.math("MULTIPLY", named(g, "half"), g.math("MULTIPLY", rz, g.math("COSINE", theta)))
    nz = g.math("MULTIPLY", rx, g.math("SINE", theta))
    normal = g.vmath("NORMALIZE", g.node("GeometryNodeSwitch", label="barrel normal",
                                         props={"input_type": "VECTOR"}, Switch=lateral,
                                         False_=g.vec(nx, 0, nz), True_=g.vec(0, nx, nz)))
    pos = g.vmath("ADD", pos, g.vmath("SCALE", normal, scale=g.math("MULTIPLY", depth, .22)))
    mesh = g.node("GeometryNodeSetPosition", label="each stone conforms to the curved barrel and diagonal edge",
                  Geometry=mesh, Position=pos)
    parity = g.math("MULTIPLY", named(g, "side"), named(g, "half"))
    flip = g.node("GeometryNodeSwitch", label="which quarters are mirrored", props={"input_type": "BOOLEAN"},
                  Switch=lateral, False_=g.math("GREATER_THAN", parity, 0), True_=g.math("LESS_THAN", parity, 0))
    return {"Stones": g.node("GeometryNodeFlipFaces", label="consistent winding on all four mirrored cells",
                             Mesh=mesh, Selection=flip)}


def cells(g, n, lateral):
    """PA_VaultCells: running bond along each barrel's axis; rows step over the curved arch section.

    Each brick is mapped from its own parameter box onto the actual vault surface.
    Its end at the diagonal follows the groin, so there are no protruding flat boxes.
    The joint, as a fraction of the arc from springing to crown, is worked out here and passed in.
    """
    kind = "wall cells" if lateral else "transverse cells"
    span, along = (B / 2, W / 2) if lateral else (W / 2, B / 2)
    theta_top = math.acos((RHO - 1) / RHO)
    rx, rz = span * RHO, H / math.sqrt(2 * RHO - 1) * RHO
    arc_length = sum(math.hypot(rx * math.sin(theta_top * (i + .5) / 256),
                               rz * math.cos(theta_top * (i + .5) / 256))
                     for i in range(256)) * theta_top / 256
    t = node_group("VaultCells", [("Courses", "int", NT), ("Span", "float", W / 2), ("Along", "float", B / 2),
                                  ("Lateral", "bool", False), ("Seed", "int"), ("Row gap", "float")],
                   [("Stones", "geometry")], _vault_cells)
    return call(g, t, f"{kind}: axial running bond, {n} curved courses per half", Courses=n, Span=span, Along=along,
                Lateral=lateral, Seed=11 if lateral else 5, Row_gap=JOINT / (2 * arc_length))


def backing(g):
    """The mortar bed behind the stones (shows in the joints, stops light leaking through them)."""
    grid = g.node("GeometryNodeMeshGrid", Size_X=W, Size_Y=B, Vertices_X=72, Vertices_Y=44)
    x, y, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    u = g.math("DIVIDE", g.math("ABSOLUTE", x), W / 2)
    v = g.math("DIVIDE", g.math("ABSOLUTE", y), B / 2)
    grid = g.node("GeometryNodeSetPosition", label="onto the soffit", Geometry=grid,
                  Position=g.vec(x, y, g.math("ADD", ZS, P(g, g.math("MINIMUM", u, v)))))
    grid = g.node("GeometryNodeSetPosition", label="a stone's depth behind", Geometry=grid,
                  Offset=g.vmath("SCALE", g.node("GeometryNodeInputNormal"), scale=0.06))
    pts = bays(g, 1, "one bed per bay")
    pts = g.node("GeometryNodeSetPosition", Geometry=pts, Position=g.vec(0, g.math("ADD", named(g, "y0"), B / 2), 0))
    return realize(g, g.node("GeometryNodeInstanceOnPoints", Points=pts, Instance=grid))


# ───────────────────────────────────────────────────────── the wall bay
def _ashlar_uv(g, i):
    nx, ny, _ = xyz(g, g.node("GeometryNodeInputNormal"))
    px, py, pz = xyz(g, g.node("GeometryNodeInputPosition"))
    wx = g.math("GREATER_THAN", g.math("ABSOLUTE", nx), 0.6)
    wy = g.math("MULTIPLY", g.math("GREATER_THAN", g.math("ABSOLUTE", ny), 0.6), g.math("SUBTRACT", 1.0, wx))
    wz = g.math("SUBTRACT", g.math("SUBTRACT", 1.0, wx), wy)
    u = g.math("ADD", g.math("MULTIPLY", wx, py), g.math("MULTIPLY", g.math("SUBTRACT", 1.0, wx), px))
    v = g.math("ADD", g.math("MULTIPLY", g.math("ADD", wx, wy), pz), g.math("MULTIPLY", wz, py))
    return {"Geometry": store(g, i["Geometry"], "auv", g.vec(u, v, 0), kind="FLOAT_VECTOR", domain="CORNER",
                              label="project each face onto the plane it faces most")}


def ashlar_uv(g, geo):
    """PA_AshlarCoordinates: a 2D coordinate per face corner for the ashlar shader."""
    t = node_group("AshlarCoordinates", [("Geometry", "geometry")], [("Geometry", "geometry")], _ashlar_uv)
    return call(g, t, "ashlar coordinates", Geometry=geo)


ORDERS = ((0.9, 0.0), (0.45, -0.28), (0.0, -0.62))     # (extra width, arris x) of the three orders of an opening


def orders_cut(g, w, spring, sill, cutters, through, step=0.2):
    """step: how much lower each outer order's sill is. 0 = all orders stop on one sill, so the string course
    below stays on solid wall (with step > 0 it bridged the outer recesses like a pipe)."""
    for k, (dw, xa) in enumerate(ORDERS):
        depth = 2 * abs(ORDERS[k + 1][1]) if k < 2 else through
        cutters += lancet(g, w + dw, spring, sill - step * (2 - k), depth, 0, 0.0)


def arch_section_coords():
    """Fillet, small roll, concave hollow, large roll and chamfered shoulder, in units of the roll radius."""
    section = [(-0.85, -1.6), (0.0, -1.6), (0.0, -1.5)]
    for i in range(1, 13):
        t = i / 12
        section.append((0.10 * math.sqrt(max(0, 1 - (2 * t - 1) ** 2)), -1.5 + 0.4 * t))
    section.append((0.0, -1.0))
    for i in range(1, 13):
        t = i / 12
        section.append((-0.24 * math.sin(PI * t), -1.0 + 0.45 * t))
    for i in range(21):
        t = i / 20
        section.append((0.02 + 0.30 * math.sqrt(max(0, 1 - (2 * t - 1) ** 2)), -0.55 + 1.45 * t))
    section += [(0.02, 0.95), (0.02, 1.25), (-0.15, 1.45), (-0.85, 1.55)]
    return section


def _arch_moulding(g, i):
    w, spring, sill, xa, yc, r = (i[k] for k in ("Width", "Spring", "Sill", "Face X", "Center Y", "Roll radius"))
    d = g.math("MULTIPLY", r, 0.6)
    span = g.math("ADD", w, g.math("MULTIPLY", d, 2))
    x0 = g.math("SUBTRACT", xa, d)
    hw = g.math("MULTIPLY", span, 0.5)
    curve = join(g, [arc(g, g.math("ADD", yc, hw), spring, span, PI, 2 * PI / 3, x0, 40),
                     arc(g, g.math("SUBTRACT", yc, hw), spring, span, PI / 3, 0.0, x0, 40)],
                 label="the order's pointed arch, set back into the arris")
    curve = g.node("GeometryNodeSetCurveNormal", label="section square to the wall", Curve=curve, Normal=(1, 0, 0))
    curve.inputs["Mode"].default_value = "Free"
    curve = masonry_distance(g, curve, g.out(g.node("GeometryNodeSplineParameter"), "Length"))
    prof = g.node("GeometryNodeTransform", label="moulding section, scaled by the roll radius",
                  Geometry=polygon_section(g, arch_section_coords()), Scale=g.vec(r, r, 1.0))
    moulding = stone_normals(g, g.node("GeometryNodeCurveToMesh", Curve=curve, Profile_Curve=prof, Fill_Caps=True))
    # Jamb relief: flattened in depth and embedded in the solid jamb. Even the necking's front
    # is behind the order's face, so nothing stands proud of the wall.
    rc = g.math("MULTIPLY", r, 0.8)
    reliefs = []
    for s in (-1, 1):
        shaft = cyl(g, rc, g.math("SUBTRACT", g.math("SUBTRACT", spring, sill), 0.1),
                    g.vec(0, 0, g.math("MULTIPLY", g.math("SUBTRACT", g.math("ADD", spring, sill), 0.1), 0.5)), 20)
        neck = cyl(g, g.math("MULTIPLY", rc, 1.2), 0.1, g.vec(0, 0, g.math("SUBTRACT", spring, 0.05)), 20)
        y = g.math("ADD", yc, g.math("MULTIPLY", g.math("ADD", g.math("MULTIPLY", w, 0.5), g.math("MULTIPLY", rc, 0.5)), s))
        reliefs.append(g.node("GeometryNodeTransform", label="jamb relief: recessed behind order face",
                              Geometry=join(g, [shaft, neck]), Scale=(0.45, 1, 1),
                              Translation=g.vec(g.math("SUBTRACT", xa, r), y, 0)))
    return {"Moulding": moulding, "Jamb relief": join(g, reliefs)}


def orders_rolls(g, w, spring, sill, yc, trim, r=0.10, jambs=True):
    """PA_ArchMoulding per order: an arch roll on recessed jamb relief, entirely behind each order's face.

    The jambs are shallow engaged profiles in the reveals, with a small necking at the
    springing. Full round shafts, leaf capitals and plinth rings read as loose little posts
    from the nave floor; keep these details within the opening instead.
    """
    t = node_group("ArchMoulding", [("Width", "float", 1.0), ("Spring", "float"), ("Sill", "float"),
                                    ("Face X", "float"), ("Center Y", "float"), ("Roll radius", "float", 0.1)],
                   [("Moulding", "geometry"), ("Jamb relief", "geometry")], _arch_moulding)
    for dw, xa in ORDERS:
        n = call(g, t, "arch moulding of one order", Width=w + dw, Spring=spring, Sill=sill, Face_X=xa,
                 Center_Y=yc, Roll_radius=r)
        trim.append(g.out(n, "Moulding"))
        if jambs:
            trim.append(g.out(n, "Jamb relief"))


def tracery(g, yc, x0):
    """Clerestory bar tracery: four lights, two quatrefoil-ish oculi and a crowning circle, cut from a plate."""
    plate = solid_lancet(g, CL_W, CL_SPRING, CL_SILL, 0.18, yc, x0)
    cut = g.node("GeometryNodeMeshBoolean", label="tracery", props={"operation": "DIFFERENCE", "solver": "EXACT"}, Self_Intersection=True,
                 Mesh_1=plate)
    holes = []
    for dy in (-1.35, -0.45, 0.45, 1.35):
        holes += lancet(g, 0.80, CL_SPRING - 0.5, CL_SILL - 0.1, 0.6, yc + dy, x0)
    for dy in (-0.9, 0.9):
        holes.append(disc(g, 0.55, 0.6, x0, yc + dy, CL_SPRING + 0.85))
    holes.append(disc(g, 0.45, 0.6, x0, yc, CL_SPRING + 2.3))
    for h in holes:
        g.link(h, cut, b_key="Mesh 2")
    return cut


def wall_bay(g, m):
    """One wall bay, inner face at x = 0, outward −x, from bay line y = 0 to y = B (opening centred)."""
    g.begin_section("a · Wall slab and openings")
    yc = B / 2
    slab = box(g, (T, B + 0.01, TOP), (-T / 2, yc, TOP / 2), "wall")
    cut = g.node("GeometryNodeMeshBoolean", label="openings", props={"operation": "DIFFERENCE", "solver": "EXACT"}, Self_Intersection=True,
                 Mesh_1=slab)
    cutters = []
    orders_cut(g, AR_W, AR_SPRING, -0.5, cutters, 3 * T)              # arcade
    orders_cut(g, TR_W, TR_SPRING, TR_SILL, cutters, 3 * T, step=0.0)          # false tribune: open into the aisle
    cutters.append(box(g, (0.75, B - 1.9, TF_TOP - TF_SILL + 0.3), (-0.95, 0, (TF_SILL + TF_TOP) / 2), "triforium passage"))
    for i in range(7):                                               # triforium: seven small lancets
        cutters += lancet(g, 0.46, TF_SPRING, TF_SILL, 1.3, (i - 3) * 0.6, 0.0)
    cutters.append(box(g, (0.5, B - 1.6, TF_TOP - TF_SILL + 0.15), (0.0, 0, (TF_SILL + TF_TOP) / 2 + 0.05),
                       "triforium recess"))
    orders_cut(g, CL_W, CL_SPRING, CL_SILL, cutters, 3 * T, step=0.0)         # clerestory
    cutters.append(box(g, (0.9, CL_W + 0.9, 1.5), (-0.45, 0, CL_SILL + 0.75), "clerestory passage"))
    for c in cutters:
        g.link(g.node("GeometryNodeTransform", Geometry=c, Translation=(0, yc, 0)), cut, b_key="Mesh 2")
    wall = pb.set_material(g, ashlar_uv(g, cut), m["wall"])

    g.begin_section("b · Arch mouldings of the three storeys")
    trim = []
    orders_rolls(g, AR_W, AR_SPRING, 0.0, yc, trim, 0.12, jambs=False)   # the arcade orders land on the pier abacus
    orders_rolls(g, TR_W, TR_SPRING, TR_SILL, yc, trim, 0.10)
    orders_rolls(g, CL_W, CL_SPRING, CL_SILL, yc, trim, 0.09)
    g.begin_section("c · Tympanum, triforium, rail, tracery and glass")
    # The tribune rests on the uncut wall below its sill. Keep this spandrel flush with the
    # wall face: a separate projecting sill read as stacked shelves over the arcade crown.
    # All three orders share TR_SILL (step=0 above), leaving a continuous flat band of stone.
    # tribune: two sub-arches and an oculus in a tympanum, on a central colonnette
    tym = solid_lancet(g, TR_W + 0.01, TR_SPRING, TR_SILL, 0.22, yc, -0.95)
    tc = g.node("GeometryNodeMeshBoolean", label="tribune tympanum", props={"operation": "DIFFERENCE", "solver": "EXACT"}, Self_Intersection=True,
                Mesh_1=tym)
    for dy in (-0.82, 0.82):
        for part in lancet(g, 1.4, TR_SPRING, TR_SILL - 0.2, 0.6, yc + dy, -0.95):
            g.link(part, tc, b_key="Mesh 2")
    g.link(disc(g, 0.45, 0.6, -0.95, yc, TR_SPRING + 1.75), tc, b_key="Mesh 2")
    trim.append(tc)
    trim.append(cyl(g, 0.11, TR_SPRING - TR_SILL, (-0.8, yc, (TR_SPRING + TR_SILL) / 2), label="tribune colonnette"))
    # triforium colonnettes and a moulded frame
    for i in range(6):
        trim.append(cyl(g, 0.045, TF_SPRING - TF_SILL, (-0.025, yc + (i - 2.5) * 0.6, (TF_SPRING + TF_SILL) / 2), 16))
    for zz in STRINGS:            # string courses: a stepped corbel (a free roll under it read as a pipe from below)
        trim.append(box(g, (0.24, B + 0.01, 0.10), (0.12, yc, zz + 0.05), "string course"))
        trim.append(box(g, (0.13, B + 0.01, 0.09), (0.065, yc, zz - 0.045), "string course: lower step"))
    # clerestory passage: a parapet rail on little posts in front of the window
    trim.append(box(g, (0.14, CL_W + 0.9, 0.12), (-0.12, yc, CL_SILL + 1.05), "passage rail"))
    for i in range(9):
        trim.append(cyl(g, 0.035, 1.0, (-0.12, yc + (i - 4) * (CL_W + 0.8) / 8, CL_SILL + 0.5), 8))
    trim.append(tracery(g, yc, -0.48))
    trim = pb.set_material(g, join(g, trim), m["trim"])

    pane = solid_lancet(g, CL_W + 0.02, CL_SPRING, CL_SILL, 0.03, yc, -0.62)
    pane = pb.set_material(g, store(g, pane, "guv", g.node("GeometryNodeInputPosition"), kind="FLOAT_VECTOR",
                                    label="pane coordinates"), m["glass"])
    g.begin_section("d · Pier and vaulting shaft")
    pr = pier(g, m)
    g.begin_section("e · The aisle behind")
    al = aisle(g, m)
    g.end_section()
    return join(g, [wall, trim, pane, pr, al], label="everything in one bay")


def pilaster_coords():
    """The common section used by shafts, their capital seat and the upper service."""
    half = [(0.265 + 0.12 * math.cos(i * PI / 36), 0.18 * math.sin(i * PI / 36)) for i in range(13)]
    half.append((0.325, 0.17))
    for i in range(1, 13):
        t = i / 12
        half.append((0.325 - 0.065 * t - 0.045 * math.sin(PI * t), 0.17 + 0.07 * t))
    half += [(0.26, 0.255), (0.22, 0.255)]
    for i in range(1, 21):
        t = i / 20
        half.append((0.22 + 0.075 * math.sqrt(max(0, 1 - (2 * t - 1) ** 2)), 0.255 + 0.15 * t))
    for i in range(1, 13):
        t = i / 12
        half.append((0.22 - 0.10 * t - 0.035 * math.sin(PI * t), 0.405 + 0.065 * t))
    half += [(0.12, 0.49), (0.07, 0.49)]
    for i in range(1, 17):
        t = i / 16
        half.append((0.07 + 0.07 * math.sqrt(max(0, 1 - (2 * t - 1) ** 2)), 0.49 + 0.12 * t))
    for i in range(1, 13):
        t = i / 12
        half.append((0.07 * (1 - t) ** 2, 0.61 + 0.11 * t))
    coords = [(x, -y) for x, y in reversed(half[1:])] + half + [(-0.18, 0.72), (-0.18, -0.72)]
    return coords


def _carved_pilaster(g, i):
    profile = polygon_section(g, pilaster_coords(), filled=True)
    solid = g.node("GeometryNodeExtrudeMesh", label="continuous carved stone, no separate cylinders",
                   props={"mode": "FACES"}, Mesh=profile, Individual=False, Offset=(0, 0, 1), Offset_Scale=i["Height"])
    bottom = g.node("GeometryNodeFlipFaces", Mesh=profile)
    mesh = g.node("GeometryNodeMergeByDistance", label="cap and weld the single stone section",
                  Geometry=join(g, [bottom, solid]), Distance=0.0001)
    mesh = masonry_distance(g, mesh, xyz(g, g.node("GeometryNodeInputPosition"))[2])
    return {"Mesh": stone_normals(g, mesh)}


def carved_pilaster(g, height, label=None):
    """PA_CarvedPilaster: hierarchical convex rolls, concave hollows and fillets on one engaged stone core."""
    t = node_group("CarvedPilaster", [("Height", "float", 1.0)], [("Mesh", "geometry")], _carved_pilaster)
    return call(g, t, label or "carved pilaster", Height=height)


def compound_outline():
    """Derive the composite section in 2D, before lofting; there are no 3D boolean joints."""
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt
    drum = []
    for i in range(192):
        a = TAU * i / 192
        r = 0.99 + 0.10 * math.cos(8 * a) + 0.018 * math.cos(16 * a)
        drum.append((-T / 2 + r * math.cos(a), r * math.sin(a)))
    polys = [drum, pilaster_coords()]
    vertices, edges, faces = [], [], []
    for poly in polys:
        if sum(x * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * y
               for i, (x, y) in enumerate(poly)) < 0:
            poly = list(reversed(poly))
        start = len(vertices)
        vertices += [Vector(p) for p in poly]
        ids = list(range(start, len(vertices)))
        faces.append(ids)
        edges += [(ids[i], ids[(i + 1) % len(ids)]) for i in range(len(ids))]
    verts, _, triangles, _, _, parents = delaunay_2d_cdt(vertices, edges, faces, 0, 1e-6, True)
    counts = {}
    for tri, covered in zip(triangles, parents):
        if not covered:
            continue
        for i, a in enumerate(tri):
            edge = tuple(sorted((a, tri[(i + 1) % len(tri)])))
            counts[edge] = counts.get(edge, 0) + 1
    neighbors = {}
    for (a, b), count in counts.items():
        if count == 1:
            neighbors.setdefault(a, []).append(b)
            neighbors.setdefault(b, []).append(a)
    assert neighbors and all(len(v) == 2 for v in neighbors.values()), "compound section must be a single simple boundary"
    start = min(neighbors, key=lambda i: (verts[i].x, verts[i].y))
    loop, previous, current = [], None, start
    while True:
        loop.append(current)
        following = next(v for v in neighbors[current] if v != previous)
        previous, current = current, following
        if current == start:
            break
        assert len(loop) <= len(neighbors)
    assert len(loop) == len(neighbors), "compound section must have no holes or detached loops"
    coords = [(float(verts[i].x), float(verts[i].y)) for i in loop]
    if sum(x * coords[(i + 1) % len(coords)][1] - coords[(i + 1) % len(coords)][0] * y
           for i, (x, y) in enumerate(coords)) < 0:
        coords.reverse()
    return coords


def point_list(g, values, label):
    """Points whose positions are a fixed list of 3-vectors (an Index Switch on the point index)."""
    sw = g.node("GeometryNodeIndexSwitch", props={"data_type": "VECTOR"}, Index=g.node("GeometryNodeInputIndex"))
    for _ in range(len(values) - len(sw.index_switch_items)):
        sw.index_switch_items.new()
    for i, v in enumerate(values):
        sw.inputs[str(i)].default_value = v
    fold_list(sw, f"{len(values)} values")
    return g.node("GeometryNodePoints", label=label, Count=len(values), Position=sw)


def loft_section(coords):
    """(x, y, relief weight) per outline point: leaves peak on the drum's lobes and on the front rolls."""
    out = []
    for x, y in coords:
        a = math.atan2(y, x + T / 2)
        weight = max(0.0, math.cos(8 * a)) ** 2 * 0.4
        if x > 0.02 and abs(y) < 0.65:
            weight = max(max(0.0, 1.0 - ((y - yc) / w) ** 2) ** 2
                         for yc, w in ((0.0, 0.12), (-0.33, 0.07), (0.33, 0.07), (-0.55, 0.05), (0.55, 0.05)))
        out.append((x, y, weight))
    return out


def _section_loft(g, i):
    sec, lev, cx, lean = i["Section"], i["Levels"], i["Center X"], i["Lean"]
    cols = g.out(g.node("GeometryNodeAttributeDomainSize", props={"component": "POINTCLOUD"}, Geometry=sec),
                 "Point Count")
    rows = g.out(g.node("GeometryNodeAttributeDomainSize", props={"component": "POINTCLOUD"}, Geometry=lev),
                 "Point Count")
    mesh = g.node("GeometryNodeMeshGrid", label="one column per outline point, one row per level",
                  Size_X=1.0, Size_Y=1.0, Vertices_X=g.math("ADD", cols, 1), Vertices_Y=rows)
    gx, gy, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    col = g.math("ROUND", g.math("MULTIPLY", g.math("ADD", gx, 0.5), cols))
    row = g.math("ROUND", g.math("MULTIPLY", g.math("ADD", gy, 0.5), g.math("SUBTRACT", rows, 1)))
    section = g.node("GeometryNodeSampleIndex", label="outline point (x, y, relief weight)",
                     props={"data_type": "FLOAT_VECTOR", "domain": "POINT"}, Geometry=sec,
                     Value=g.node("GeometryNodeInputPosition"), Index=g.math("FLOORED_MODULO", col, cols))
    layer = g.node("GeometryNodeSampleIndex", label="level (z, scale, relief)",
                   props={"data_type": "FLOAT_VECTOR", "domain": "POINT"}, Geometry=lev,
                   Value=g.node("GeometryNodeInputPosition"), Index=row)
    x, y, weight = xyz(g, section)
    z, scale, relief = xyz(g, layer)
    dx = g.math("SUBTRACT", x, cx)
    radial = g.vmath("NORMALIZE", g.vec(dx, y, 0))
    nx, ny, _ = xyz(g, radial)
    r = g.math("MULTIPLY", weight, relief)
    px = g.math("ADD", cx, g.math("ADD", g.math("MULTIPLY", dx, scale), g.math("MULTIPLY", nx, r)))
    forward = g.math("MINIMUM", 1.0, g.math("MAXIMUM", 0.0, g.math("DIVIDE", g.math("SUBTRACT", scale, 1.0), 0.08)))
    forward = g.math("MULTIPLY", lean, g.math("MULTIPLY", forward, g.math("GREATER_THAN", z, AR_SPRING - 0.65)))
    px = g.math("ADD", px, forward)
    py = g.math("ADD", g.math("MULTIPLY", y, scale), g.math("MULTIPLY", ny, r))
    return {"Mesh": g.node("GeometryNodeSetPosition", label="each ring: outline × scale + leaf relief at its height",
                           Geometry=mesh, Position=g.vec(px, py, z))}


def section_loft(g, coords, levels, center_x=0.0, label=None, lean=0.0):
    """PA_SectionLoft: a single ring grid. Every transition shares vertices with the ring above and below."""
    t = node_group("SectionLoft", [("Section", "geometry"), ("Levels", "geometry"), ("Center X", "float"),
                                   ("Lean", "float")], [("Mesh", "geometry")], _section_loft)
    return call(g, t, label, Section=point_list(g, loft_section(coords), "section: x, y, relief weight"),
                Levels=point_list(g, levels, "levels: z, scale, relief"), Center_X=center_x, Lean=lean)


def continuous_pier(g):
    lower, upper = compound_outline(), pilaster_coords()
    if sum(x * upper[(i + 1) % len(upper)][1] - upper[(i + 1) % len(upper)][0] * y
           for i, (x, y) in enumerate(upper)) < 0:
        upper = list(reversed(upper))
    seat = AR_SPRING + 0.08
    levels = [(0, 1.045, 0), (0.24, 1.045, 0), (0.30, 1.01, 0), (0.36, 1.0, 0),
              (AR_SPRING - 0.63, 1.0, 0), (AR_SPRING - 0.60, 1.015, 0),
              (AR_SPRING - 0.56, 1.015, 0), (AR_SPRING - 0.52, 1.006, 0),
              (AR_SPRING - 0.48, 1.0, 0), (AR_SPRING - 0.42, 1.002, 0.003),
              (AR_SPRING - 0.32, 1.014, 0.010), (AR_SPRING - 0.20, 1.035, 0.018),
              (AR_SPRING - 0.08, 1.052, 0.010), (AR_SPRING - 0.045, 1.055, 0),
              (AR_SPRING - 0.035, 1.065, 0), (AR_SPRING - 0.020, 1.075, 0),
              (AR_SPRING + 0.025, 1.075, 0), (AR_SPRING + 0.045, 1.080, 0), (seat, 1.080, 0)]
    shaft = section_loft(g, lower, levels, -T / 2, "one continuous shaft, neck, capital and abacus", lean=0.03)
    upper_shaft = section_loft(g, upper, [(seat, 1, 0), (seat + 0.04, 1, 0), (ZS - 0.18, 1, 0)],
                               label="upper service starts on the capital bearing")
    top_outline = [(-T / 2 + (x + T / 2) * levels[-1][1] + 0.03, y * levels[-1][1]) for x, y in lower]
    bottom_outline = [(-T / 2 + (x + T / 2) * levels[0][1], y * levels[0][1]) for x, y in lower]
    def inside(point):
        x, y = point
        crossed = False
        for i, (ax, ay) in enumerate(top_outline):
            bx, by = top_outline[(i + 1) % len(top_outline)]
            if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
                crossed = not crossed
        return crossed
    assert all(inside((ax + (upper[(i + 1) % len(upper)][0] - ax) * t,
                       ay + (upper[(i + 1) % len(upper)][1] - ay) * t))
               for i, (ax, ay) in enumerate(upper) for t in (0.0, 0.25, 0.5, 0.75)), \
        "the upper shaft must lie completely inside its capital bearing"
    # A filled annulus shares its inner loop with the upper shaft and outer loop with the capital.
    bearing = g.node("GeometryNodeFillCurve", label="one bearing surface, no overlapping joint faces",
                     Curve=join(g, [polygon_section(g, top_outline), polygon_section(g, upper)]))
    bearing = g.node("GeometryNodeTransform", Geometry=bearing, Translation=(0, 0, seat))
    bottom = g.node("GeometryNodeFlipFaces", Mesh=polygon_section(g, bottom_outline, filled=True))
    top = g.node("GeometryNodeTransform", Geometry=polygon_section(g, upper, filled=True),
                 Translation=(0, 0, ZS - 0.18))
    return g.node("GeometryNodeMergeByDistance", label="one joined pier and continuous vaulting service",
                  Geometry=join(g, [shaft, upper_shaft, bearing, bottom, top]), Distance=0.00001)


def pier(g, m):
    """A continuous loft and an explicit bearing joint replace all stacked capital booleans."""
    core = continuous_pier(g)
    core = masonry_distance(g, core, xyz(g, g.node("GeometryNodeInputPosition"))[2])
    pz = xyz(g, g.node("GeometryNodeInputPosition"))[2]
    core = store(g, core, "masonry_mask", g.math("MAXIMUM", g.math("LESS_THAN", pz, AR_SPRING - 0.56),
                                                     g.math("GREATER_THAN", pz, AR_SPRING + 0.09)))
    p = [stone_normals(g, core)]
    band = carved_pilaster(g, 0.1, "pilaster band, 10 cm")
    for zz in (TR_SPRING, STRINGS[0], STRINGS[1]):
        p.append(g.node("GeometryNodeTransform", label="one continuous pilaster band", Geometry=band,
                        Scale=(1.045, 1.025, 1), Translation=(0, 0, zz - 0.05)))
    p.append(g.node("GeometryNodeTransform", label="unified pilaster capital",
                    Geometry=carved_pilaster(g, 0.30, "pilaster capital, 30 cm"), Scale=(1.10, 1.08, 1),
                    Translation=(0, 0, ZS - 0.42)))
    p.append(box(g, (0.75, 1.75, 0.16), (0.22, 0, ZS - 0.04), "abacus of the vaulting shafts"))
    return pb.set_material(g, join(g, p, label="pier and vaulting shafts"), m["trim"])


def aisle(g, m):
    """The tall aisle behind (seen through the arcade and the false tribune): outer wall with two tiers of
    windows, a flat aisle vault on top."""
    yc = B / 2
    x_out = -T - AISLE
    wl = box(g, (1.2, B + 0.01, AISLE_TOP), (x_out - 0.6, yc, AISLE_TOP / 2), "aisle wall")
    cut = g.node("GeometryNodeMeshBoolean", props={"operation": "DIFFERENCE", "solver": "EXACT"}, Self_Intersection=True, Mesh_1=wl)
    for part in lancet(g, 2.4, 9.0, 3.0, 4.0, yc, x_out) + lancet(g, 2.4, 15.2, 11.6, 4.0, yc, x_out):
        g.link(part, cut, b_key="Mesh 2")
    ceil = box(g, (AISLE + 1.4, B + 0.01, 0.6), (-T - AISLE / 2, yc, AISLE_TOP + 0.3), "aisle vault")
    rib = box(g, (AISLE, 0.5, 0.7), (-T - AISLE / 2, 0, AISLE_TOP - 0.35), "aisle transverse rib")
    a = pb.set_material(g, ashlar_uv(g, join(g, [cut, ceil, rib])), m["aisle"])
    gl = solid_lancet(g, 2.42, 9.0, 3.0, 0.03, yc, x_out - 0.6)
    gl2 = solid_lancet(g, 2.42, 15.2, 11.6, 0.03, yc, x_out - 0.6)
    gl = pb.set_material(g, store(g, join(g, [gl, gl2]), "guv", g.node("GeometryNodeInputPosition"),
                                  kind="FLOAT_VECTOR"), m["glass"])
    return join(g, [a, gl])


def walls(g, m):
    t = node_group("WallBay", [], [("Geometry", "geometry")], lambda g, i: {"Geometry": wall_bay(g, m)})
    unit = call(g, t, "one wall bay")
    pts = bays(g, 2, "two wall bays per bay")
    side = sgn(g, named(g, "j"))
    pts = g.node("GeometryNodeSetPosition", Geometry=pts,
                 Position=g.vec(g.math("MULTIPLY", side, W / 2),
                                g.math("ADD", named(g, "y0"), g.math("MULTIPLY", g.math("ADD", side, 1), B / 2)), 0))
    yaw = g.math("MULTIPLY", g.math("MULTIPLY", g.math("ADD", side, 1), 0.5), PI)
    inst = g.node("GeometryNodeInstanceOnPoints", Points=pts, Instance=unit,
                  Rotation=g.node("FunctionNodeEulerToRotation", Euler=g.vec(0, 0, yaw)))
    return store(g, realize(g, inst), "tone", 1.0)


def roof(g, m):
    L = NB * B
    return pb.set_material(g, box(g, (W + 2 * T, L, 0.5), (0, K0 * B + L / 2, TOP + 0.3), "roof"), m["roof"])


def west_wall(g, m):
    """PA_WestWall: the west wall with its rose window, a fixed distance ahead (it does not move with the walk)."""
    t = node_group("WestWall", [], [("Geometry", "geometry")], lambda g, i: {"Geometry": _west_wall(g, m)})
    return call(g, t, "west wall and rose window")


def _west_wall(g, m):
    zr, rr = 18.2, 4.4
    wl = box(g, (W + 0.2, 1.4, TOP), (0, WEST + 0.7, TOP / 2), "west wall")
    cut = g.node("GeometryNodeMeshBoolean", props={"operation": "DIFFERENCE", "solver": "EXACT"}, Self_Intersection=True, Mesh_1=wl)
    g.link(cyl(g, rr, 3.0, (0, WEST, zr), 96, rot=(PI / 2, 0, 0)), cut, b_key="Mesh 2")
    wall = pb.set_material(g, ashlar_uv(g, cut), m["wall"])
    tr = [tube(g, g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeCurvePrimitiveCircle", Resolution=96,
                                                                    Radius=r), Rotation=(PI / 2, 0, 0),
                         Translation=(0, WEST + 0.3, zr)), 0.07) for r in (rr - 0.05, rr * 0.62, rr * 0.25)]
    for k in range(16):                                              # spokes
        a = k * TAU / 16
        tr.append(g.node("GeometryNodeTransform",
                         Geometry=g.node("GeometryNodeMeshCube", Size=(0.1, 0.12, rr * 0.75)),
                         Rotation=(0, a, 0), Translation=(math.sin(a) * rr * 0.62, WEST + 0.3, zr + math.cos(a) * rr * 0.62)))
    trim = pb.set_material(g, join(g, tr), m["trim"])
    gl = cyl(g, rr, 0.03, (0, WEST + 0.6, zr), 96, rot=(PI / 2, 0, 0))
    _, gy, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    px, _, pz = xyz(g, g.node("GeometryNodeInputPosition"))
    gl = pb.set_material(g, store(g, gl, "guv", g.vec(gy, px, pz), kind="FLOAT_VECTOR"), m["glass"])
    return store(g, join(g, [wall, trim, gl]), "tone", 1.0)


# ───────────────────────────────────────────────────────── build
def clerestory_lights(collection):
    """Broad daylight from the high windows, directed across the nearby vault webs."""
    from mathutils import Vector
    for bay in range(K0, K1 + 1):
        y = (bay + 0.5) * B
        for side in (-1, 1):
            name = f"PA_Clerestory_{bay:+03d}_{side:+d}"
            light = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
            collection.objects.link(light)
            light.data.shape = "RECTANGLE"
            light.data.size, light.data.size_y = 2.5, 3.6
            light.data.energy = WINDOW_FILL
            light.data.color = (0.83, 0.91, 1.0)
            light.data.specular_factor = 0.25
            light.location = (side * (W / 2 - 0.12), y, 22.8)
            light.rotation_euler = (Vector((0, y, 26.5)) - light.location).to_track_quat("-Z", "Y").to_euler()
            light.visible_camera = False
            light.driver_add("location", 1).driver.expression = (
                f"{y!r} - {B!r} * ((frame - 1) / {FRAMES} - floor((frame - 1) / {FRAMES}))")


def build():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    GROUPS.clear()
    info = pb.piece(NAME, aspect="1:1", width=2160, fps=30, frames=FRAMES, samples=512)
    bpy.context.preferences.addons["cycles"].preferences.kernel_optimization_level = "OFF"
    m = materials()
    ob, g = pb.gn_object(NAME, NAME)
    g.begin_section("1 · Wall bays on both sides")
    stand = walls(g, m)
    g.begin_section("2 · Ribs and bosses")
    rb = pb.set_material(g, ribs(g), m["rib"])
    g.begin_section("3 · Cells, stone by stone, and the mortar bed")
    cl = pb.set_material(g, join(g, [cells(g, NT, False), cells(g, NL, True)],
                                 label="vault masonry follows the marked axial direction"), m["web"])
    bed = pb.set_material(g, backing(g), m["mortar"])
    g.begin_section("4 · The walk and the west end")
    clock = g.group(pb.loop_clock(FRAMES))
    walk = g.math("MULTIPLY", g.out(clock, "Phase"), B)
    walk.label = "walked: one bay per loop"
    nave = join(g, [stand, rb, cl, bed, roof(g, m)])
    nave = store(g, nave, "stone_position", g.node("GeometryNodeInputPosition"), kind="FLOAT_VECTOR",
                 label="stone coordinates before the nave moves")
    nave = g.node("GeometryNodeTransform", label="we walk forward: the nave slides back one bay per loop",
                  Geometry=nave, Translation=g.vec(0, g.math("MULTIPLY", walk, -1.0), 0))
    west = west_wall(g, m)
    floor = pb.set_material(g, box(g, (W + 2 * T + 2 * AISLE + 4, NB * B + 40, 0.2), (0, K0 * B + NB * B / 2, -0.1),
                                   "floor"), m["floor"])
    rear = box(g, (W + 2 * T + 2 * AISLE + 4, .4, TOP + 5), (0, -2 * B, (TOP + 5) / 2),
               "fixed rear closure stops changing skylight through the moving nave end")
    rear = pb.set_material(g, store(g, ashlar_uv(g, rear), "tone", 1.0), m["wall"])
    stationary = store(g, join(g, [west, floor, rear]), "stone_position", g.node("GeometryNodeInputPosition"),
                       kind="FLOAT_VECTOR", label="stationary stone coordinates")
    g.output(join(g, [nave, stationary]))
    g.end_section()
    pb.arrange(g.tree)

    sc = bpy.context.scene
    st = bpy.data.collections.get("PA_Studio") or bpy.data.collections.new("PA_Studio")
    if st.name not in sc.collection.children:
        sc.collection.children.link(st)
    clerestory_lights(st)
    cam = bpy.data.objects.new("PA_Camera", bpy.data.cameras.new("PA_Camera"))
    st.objects.link(cam)
    # the final 3/4 view: beside the nave axis, yawed 32° towards the far (+x) elevation, pitched 48°
    cx, cy, cz, pitch, lens, roll, yaw = 1.5, -1.0, 2.0, 48.0, 22.0, 0.0, 32.0
    if "--cam" in ARGS:
        v = [float(a) for a in ARGS[ARGS.index("--cam") + 1].split(",")]
        cx, cy, cz, pitch, lens, roll = v[:6]
        yaw = v[6] if len(v) > 6 else 0.0
    cam.location = (cx, cy, cz)
    # pitch above the horizon facing +y, then rolled about the view axis (180: head towards the west end)
    rm = (Matrix.Rotation(math.radians(yaw), 3, "Z") @ Euler((math.radians(90 + pitch), 0, 0), "XYZ").to_matrix()
          @ Matrix.Rotation(math.radians(roll), 3, "Z"))
    cam.rotation_euler = rm.to_euler("XYZ")
    cam.data.lens = lens
    cam.data.clip_end = 500
    sc.camera = cam
    # warm fill from the floor (lamps, bounce from the pale floor), invisible to the camera
    fl = bpy.data.objects.new("PA_Fill", bpy.data.lights.new("PA_Fill", "AREA"))
    st.objects.link(fl)
    fl.data.shape = "RECTANGLE"
    fl.data.size, fl.data.size_y = W - 1.0, 90.0
    fl.data.energy = FILL
    fl.data.color = (1.0, 0.92, 0.80)
    fl.location = (0, 40, 2.5)
    fl.rotation_euler = (PI, 0, 0)
    fl.visible_camera = False
    sun = bpy.data.objects.new("PA_Sun", bpy.data.lights.new("PA_Sun", "SUN"))
    st.objects.link(sun)
    sun.data.energy = SUN_ENERGY
    sun.data.angle = math.radians(2.0)
    sun.data.color = SUN_COLOR
    sun.rotation_euler = Euler((math.radians(90 - SUN_ELEVATION), 0, math.radians(SUN_HEADING)), "XYZ")
    world = bpy.data.worlds.new("PA_World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.78, 0.85, 1.0, 1.0)
    bg.inputs["Strength"].default_value = SKY
    sc.world = world
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = EXPOSURE
    sc.cycles.max_bounces = 8
    sc.cycles.diffuse_bounces = 5
    sc.cycles.adaptive_threshold = 0.005
    sc.cycles.adaptive_min_samples = 64
    sc.cycles.pixel_filter_type = "BLACKMAN_HARRIS"
    sc.cycles.filter_width = 0.9
    sc.cycles.denoising_prefilter = "ACCURATE"
    if hasattr(sc.cycles, "denoising_quality"):
        sc.cycles.denoising_quality = "HIGH"
    sc.render.use_motion_blur = False
    cam.data.dof.use_dof = False
    sc.compositing_node_group = None
    pb.output(os.path.join(DAY, "loop.mp4"), "video")
    out = ARGS[ARGS.index("--save-as") + 1] if "--save-as" in ARGS else os.path.join(DAY, "rouen.blend")
    pb.save(out)
    return {"piece": info}


def clay(path):
    """White Workbench copy, with glazing removed so the window openings remain readable."""
    sc = bpy.context.scene
    sh = sc.display.shading
    props = ("light", "studio_light", "color_type", "single_color", "show_cavity", "cavity_type",
             "show_shadows", "show_specular_highlight", "background_type")
    previous = {k: getattr(sh, k)[:] if k == "single_color" else getattr(sh, k) for k in props}
    keep = sc.render.engine, sc.compositing_node_group, sc.display.render_aa, sc.world.color[:]
    nt = bpy.data.node_groups["PA_Rouen_GN"]
    out = next(n for n in nt.nodes if n.bl_idname == "NodeGroupOutput")
    original = out.inputs["Geometry"].links[0].from_socket
    selector = nt.nodes.new("GeometryNodeMaterialSelection")
    selector.inputs["Material"].default_value = next(mt for mt in bpy.data.materials if "Glass" in mt.name)
    delete = nt.nodes.new("GeometryNodeDeleteGeometry")
    delete.domain = "FACE"
    nt.links.new(original, delete.inputs["Geometry"])
    nt.links.new(selector.outputs["Selection"], delete.inputs["Selection"])
    nt.links.new(delete.outputs["Geometry"], out.inputs["Geometry"])
    try:
        sc.render.engine = "BLENDER_WORKBENCH"
        sh.light, sh.studio_light = "STUDIO", "Default"
        sh.color_type, sh.single_color = "SINGLE", (0.88, 0.88, 0.88)
        sh.show_cavity, sh.cavity_type = True, "BOTH"
        sh.show_shadows, sh.show_specular_highlight = False, False
        sh.background_type = "WORLD"
        sc.display.render_aa = "16"
        sc.world.color = (1.0, 1.0, 1.0)
        sc.compositing_node_group = None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pb.save(path)
    finally:
        nt.links.new(original, out.inputs["Geometry"])
        nt.nodes.remove(delete)
        nt.nodes.remove(selector)
        sc.render.engine, sc.compositing_node_group, sc.display.render_aa, sc.world.color = keep
        for k, v in previous.items():
            setattr(sh, k, v)
    return path


if __name__ == "__main__":
    res = build()
    tag = ARGS[ARGS.index("--tag") + 1] if "--tag" in ARGS else ""
    if "--preview" in ARGS:
        for fr in ARGS[ARGS.index("--preview") + 1].split(","):
            fr = int(fr)
            pb.preview(os.path.join(DAY, f"_preview_{fr:03d}{tag}.png"), scale=50, samples=16, frame=fr)
    if "--look" in ARGS:
        sc = bpy.context.scene
        sc.render.resolution_percentage = 50
        for fr in ARGS[ARGS.index("--look") + 1].split(","):
            fr = int(fr)
            res[f"cycles_{fr}"] = pb.render_still(os.path.join(DAY, f"_cycles_{fr:03d}{tag}.png"), frame=fr, samples=48)
        sc.render.resolution_percentage = 100
    if "--still" in ARGS:
        fr = int(ARGS[ARGS.index("--still") + 1])
        res["still"] = pb.render_still(os.path.join(DAY, f"_still_{fr:03d}{tag}.png"), frame=fr)
    if "--clay" in ARGS:
        res["clay"] = clay(os.path.join(DAY, "clay", "rouen_clay.blend"))
    res["audit"] = pb.audit(NAME)
    res["describe"] = pb.describe("PA_Rouen_GN")
    print("BUILD_RESULT", res)
