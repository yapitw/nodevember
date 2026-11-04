"""Nodevember 2026 · Day 02 · Furniture (v3) — a day in the corner.

A reading corner on a seamless limewash set: a bouclé barrel chair with a chunky-knit lumbar
pillow, a turned walnut side table, a travertine table lamp with a pleated linen shade, a wool
rug and a glazed floor vase of pampas grass. One window, out of frame on the left, is the only
sun. Over a 10-second loop its light rakes across the corner in the morning, falls through the
chair at noon and climbs the wall as a golden window at sunset; the lamp clicks on at blue hour,
the moon comes through the same window, the lamp clicks off at dawn.

Every object is generated in Geometry Nodes (lathes, a swept shell, a pillow from a grid,
plume fibres instanced on curves) and every surface is shader nodes, with no image textures.
The day is functions of the frame: every light property is a driver expression (Blender simple
expressions, so no Python auto-run is needed to render) and the sky is world shader nodes fed by
one of them, so frame 301 == frame 1.

Run: Blender -b --factory-startup --python build.py -- [--preview f,f,..] [--still N] [--out file.blend]
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
FRAMES = 300
TAU = 2 * math.pi

# ── the set (metres; camera looks toward +y, the window is at −x)
RUG_W, RUG_D, RUG_T = 2.0, 1.4, 0.012
CHAIR, CHAIR_ROT = Vector((-0.30, 0.14, RUG_T)), math.radians(-15)
RC, SW, Z0, HB, HA = 0.33, 0.13, 0.13, 0.76, 0.60      # shell: centre radius, thickness, bottom, back top, arm top
PHI0 = math.radians(125)                               # shell wraps ±125° from the back
RBASE, ZS, ZC, YSC = 0.375, 0.29, 0.43, 0.86          # seat: radius, deck top, cushion top, front-back squash
TABLE, TOP_Z = Vector((0.60, 0.40, RUG_T)), 0.52
LAMP = TABLE + Vector((0.03, 0.05, TOP_Z))
VASE = Vector((-0.98, 0.72, 0.0))
WALL_Y0, WALL_R, WALL_H = 0.95, 0.45, 3.6             # floor flat to y0, cove radius, wall height
WIN_X = -2.7                                           # the window wall (invisible to the camera)
WIN_Y, WIN_Z = (-0.90, 0.50), (0.45, 2.25)

# ── the day (t = loop phase 0..1)
T_RISE, T_SET = 0.92, 0.52              # sun is up from t = 0.92 (wraps) to 0.52
AZ0, AZ1, EL_MAX = -15.0, 55.0, 24.0    # sun heading (deg from +x toward +y) morning → evening, peak elevation
SUN_E = 7.0
LAMP_ON, LAMP_OFF = 0.565, 0.935
LAMP_W = 22.0
NIGHT_EV = 1.0                          # camera exposure follows the light (auto-exposure)


def srgb(*c):
    return tuple(x ** 2.2 for x in c) + (1.0,)


def new_tree(name):
    old = bpy.data.node_groups.get(name)
    if old:
        bpy.data.node_groups.remove(old)
    return bpy.data.node_groups.new(name, "GeometryNodeTree")


def new_mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    g = pb.Graph(m.node_tree)
    return m, g, g.node("ShaderNodeOutputMaterial")


def attr(g, name, key="Vector"):
    return g.out(g.node("ShaderNodeAttribute", label=name, props={"attribute_name": name}), key)


def ss(g, v, a, b, label=None, lo=0.0, hi=1.0):
    return g.node("ShaderNodeMapRange", label=label, props={"interpolation_type": "SMOOTHSTEP"},
                  Value=v, From_Min=a, From_Max=b, To_Min=lo, To_Max=hi)


def mixc(g, f, a, b, label=None):
    return g.node("ShaderNodeMix", label=label, props={"data_type": "RGBA"}, Factor=f, A=a, B=b)


def store(g, geo, name, value, kind="FLOAT_VECTOR", domain="POINT", label=None):
    return g.node("GeometryNodeStoreNamedAttribute", label=label, props={"data_type": kind, "domain": domain},
                  Geometry=geo, Name=name, Value=value)


def join(g, parts, label=None):
    j = g.node("GeometryNodeJoinGeometry", label=label)
    for p in parts:
        g.link(p, j, b_key="Geometry")
    return j


def xyz(g, v):
    s = g.node("ShaderNodeSeparateXYZ", Vector=v)
    return g.out(s, "X"), g.out(s, "Y"), g.out(s, "Z")


def index_switch(g, kind, values, label):
    sw = g.node("GeometryNodeIndexSwitch", label=label, props={"data_type": kind})
    while len([s for s in sw.inputs if not pb._virtual(s)]) - 1 < len(values):
        sw.index_switch_items.new()
    g.set(sw, "Index", g.node("GeometryNodeInputIndex"))
    for i, v in enumerate(values):
        g.set(sw, str(i), v)
    return sw


def lathe(g, pts, label, res=128, resample=0):
    """(r, z, corner radius) profile, axis to axis → a solid of revolution about z, normals out.
    resample: even spacing along the profile, so a later subdivide + displace stays even."""
    sw = index_switch(g, "VECTOR", [(r - 1e-4, -z, 0.0) for r, z, _ in pts], f"{label}: profile (r, z)")
    rad = index_switch(g, "FLOAT", [f for _, _, f in pts], f"{label}: corner radii")
    prof = g.node("GeometryNodePointsToCurves", Points=g.node("GeometryNodePoints", Count=len(pts), Position=sw))
    soft = g.node("GeometryNodeFilletCurve", label=f"{label}: round the corners", Curve=prof, Radius=rad, Count=10,
                  Limit_Radius=True)
    soft.inputs["Mode"].default_value = "Poly"
    if resample:
        soft = g.node("GeometryNodeResampleCurve", label=f"{label}: even spacing", Curve=soft, Count=resample)
    ring = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=res, Radius=1e-4)
    m = g.node("GeometryNodeCurveToMesh", label=f"{label}: lathe", Curve=ring, Profile_Curve=soft)
    m = g.node("GeometryNodeMergeByDistance", Geometry=g.node("GeometryNodeFlipFaces", Mesh=m), Distance=2e-4)
    return g.node("GeometryNodeSetShadeSmooth", Geometry=m, Shade_Smooth=True)


# ───────────────────────────────────────────────────────── node groups

def boucle_group():
    """PA_Boucle: push a dense mesh out into irregular bouclé loops (Voronoi cells, jittered by
    noise) and keep the rest coords + loop height for the shader."""
    t = new_tree("PA_Boucle")
    t.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    for n, v in (("Scale", 150.0), ("Depth", 0.0022)):
        s = t.interface.new_socket(n, in_out="INPUT", socket_type="NodeSocketFloat")
        s.default_value = v
    t.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    g = pb.Graph(t)
    gi, go = g.group_io()
    I = gi.outputs
    pos = g.node("GeometryNodeInputPosition")
    co = store(g, I["Geometry"], "bco", pos, label="rest coords for the shader")
    wob = g.node("ShaderNodeTexNoise", label="loops are not a grid", Vector=pos, Scale=40.0, Detail=2.0)
    jit = g.vmath("SCALE", g.vmath("SUBTRACT", g.out(wob, "Color"), (0.5, 0.5, 0.5)), scale=0.008)
    cells = g.node("ShaderNodeTexVoronoi", label="one cell per loop", Vector=g.vmath("ADD", pos, jit), Scale=I["Scale"])
    nub = ss(g, g.out(cells, "Distance"), 0.05, 0.6, "round loop", 1.0, 0.0)
    st = store(g, co, "nub", nub, kind="FLOAT")
    push = g.vmath("SCALE", g.node("GeometryNodeInputNormal"), scale=g.math("MULTIPLY", nub, I["Depth"]))
    out = g.node("GeometryNodeSetPosition", label="push the loops out", Geometry=st, Offset=push)
    g.link(out, go, b_key="Geometry")
    pb.arrange(t)
    return t


# ───────────────────────────────────────────────────────── materials

def boucle_mat():
    m, g, out = new_mat("PA_Boucle")
    co = attr(g, "bco")
    nub = attr(g, "nub", "Fac")
    cells = g.node("ShaderNodeTexVoronoi", label="same loops as the geometry", Vector=co, Scale=150.0)
    big = ss(g, g.out(cells, "Distance"), 0.05, 0.6, "loop", 1.0, 0.0)
    small = g.node("ShaderNodeTexVoronoi", label="small loops", Vector=co, Scale=430.0)
    sm = ss(g, g.out(small, "Distance"), 0.05, 0.55, "small loop", 1.0, 0.0)
    fuzz = g.node("ShaderNodeTexNoise", label="fibre fuzz", Vector=co, Scale=3200.0, Detail=3.0)
    tone = g.node("ShaderNodeTexNoise", label="yarn tone", Vector=co, Scale=55.0, Detail=3.0)
    base = mixc(g, g.out(tone, "Factor"), srgb(0.84, 0.78, 0.68), srgb(0.90, 0.85, 0.76))
    col = mixc(g, g.math("MULTIPLY", g.math("SUBTRACT", 1.0, g.math("MAXIMUM", nub, big)), 0.75), base,
               srgb(0.50, 0.44, 0.37), "shadowed between loops")
    h = g.math("ADD", g.math("ADD", big, g.math("MULTIPLY", sm, 0.45)), g.math("MULTIPLY", g.out(fuzz, "Factor"), 0.35))
    bump = g.node("ShaderNodeBump", Strength=0.55, Distance=0.002, Height=h)
    b = g.node("ShaderNodeBsdfPrincipled", Base_Color=col, Roughness=0.95, Normal=bump)
    b.inputs["Sheen Weight"].default_value = 0.9
    b.inputs["Sheen Roughness"].default_value = 0.35
    b.inputs["Specular IOR Level"].default_value = 0.25
    g.link(b, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def walnut_mat():
    """Rings around a vertical tree axis (wood_co is offset per part): end grain on the top,
    straight grain down the turned column."""
    m, g, out = new_mat("PA_Walnut")
    co = attr(g, "wood_co")
    warp = g.node("ShaderNodeTexNoise", label="rings wander", Vector=g.vmath("MULTIPLY", co, (6.0, 6.0, 0.9)),
                  Scale=1.0, Detail=5.0, Roughness=0.55)
    x, y, _ = xyz(g, co)
    r = g.out(g.vmath("LENGTH", g.vec(x, y, 0.0)), "Value")
    rings = g.math("FRACT", g.math("MULTIPLY_ADD", r, 85.0, g.math("MULTIPLY", g.out(warp, "Factor"), 3.2)))
    rings.label = "growth rings"
    late = ss(g, rings, 0.55, 0.95, "latewood")
    pores = g.node("ShaderNodeTexNoise", label="pores along the grain",
                   Vector=g.vmath("MULTIPLY", co, (420.0, 420.0, 22.0)), Scale=1.0, Detail=2.0)
    pore = ss(g, g.out(pores, "Factor"), 0.6, 0.72, "open pores")
    figure = g.node("ShaderNodeTexNoise", label="figure", Vector=co, Scale=6.0, Detail=4.0)
    c = mixc(g, g.out(figure, "Factor"), srgb(0.42, 0.27, 0.16), srgb(0.56, 0.38, 0.23))
    c = mixc(g, g.math("MULTIPLY", late, 0.8), c, srgb(0.24, 0.14, 0.08), "dark latewood")
    c = mixc(g, g.math("MULTIPLY", pore, 0.6), c, srgb(0.10, 0.05, 0.03))
    bump = g.node("ShaderNodeBump", Strength=0.18, Distance=0.001,
                  Height=g.math("SUBTRACT", g.math("MULTIPLY", late, 0.3), pore))
    b = g.node("ShaderNodeBsdfPrincipled", Base_Color=c, Roughness=0.42, Normal=bump)
    b.inputs["Coat Weight"].default_value = 0.35
    b.inputs["Coat Roughness"].default_value = 0.22
    g.link(b, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def travertine_mat():
    m, g, out = new_mat("PA_Travertine")
    co = attr(g, "stone_co")
    beds = g.node("ShaderNodeTexNoise", label="bedding layers", Vector=g.vmath("MULTIPLY", co, (3.0, 3.0, 55.0)),
                  Scale=1.0, Detail=6.0, Roughness=0.6, Distortion=0.4)
    vug = g.node("ShaderNodeTexVoronoi", label="vugs (holes)", Vector=g.vmath("MULTIPLY", co, (70.0, 70.0, 190.0)),
                 Scale=1.0)
    few = g.node("ShaderNodeTexNoise", Vector=co, Scale=30.0, Detail=2.0)
    hole = g.math("MULTIPLY", ss(g, g.out(vug, "Distance"), 0.08, 0.2, "hole", 1.0, 0.0),
                  ss(g, g.out(few, "Factor"), 0.5, 0.6, "only some cells"))
    c = mixc(g, g.out(beds, "Factor"), srgb(0.78, 0.68, 0.55), srgb(0.90, 0.82, 0.70))
    c = mixc(g, g.math("MULTIPLY", hole, 0.8), c, srgb(0.56, 0.45, 0.33), "holes")
    bump = g.node("ShaderNodeBump", Strength=0.5, Distance=0.0015, Height=g.math("MULTIPLY", hole, -1.0))
    b = g.node("ShaderNodeBsdfPrincipled", Base_Color=c, Roughness=0.5, Normal=bump)
    g.link(b, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def linen_mat():
    """Diffuse outside, translucent through: the shade glows when the lamp is on, and the
    slubs (thick weft threads) show as darker lines."""
    m, g, out = new_mat("PA_Linen")
    uv = attr(g, "suv")
    u, v, _ = xyz(g, uv)
    slub = g.node("ShaderNodeTexNoise", label="slubs: thick weft threads",
                  Vector=g.vec(g.math("MULTIPLY", u, 25.0), g.math("MULTIPLY", v, 520.0), 0.0), Scale=1.0, Detail=2.0)
    thick = ss(g, g.out(slub, "Factor"), 0.55, 0.75, "thick thread")
    weave = g.node("ShaderNodeTexWave", label="weave", props={"wave_type": "BANDS", "bands_direction": "Y"},
                   Vector=g.vec(g.math("MULTIPLY", u, 3.0), g.math("MULTIPLY", v, 3.0), 0.0), Scale=900.0)
    col = mixc(g, g.math("MULTIPLY", thick, 0.35), srgb(0.93, 0.88, 0.79), srgb(0.70, 0.62, 0.50))
    trans = mixc(g, thick, srgb(0.82, 0.66, 0.48), srgb(0.48, 0.34, 0.22), "less light through thick threads")
    bump = g.node("ShaderNodeBump", Strength=0.12, Distance=0.0005,
                  Height=g.math("ADD", g.out(weave, "Factor"), thick))
    face = g.node("ShaderNodeBsdfPrincipled", Base_Color=col, Roughness=0.9, Normal=bump)
    face.inputs["Sheen Weight"].default_value = 0.3
    tr = g.node("ShaderNodeBsdfTranslucent", Color=trans, Normal=bump)
    mix = g.node("ShaderNodeMixShader", ins={0: 0.6, 1: face, 2: tr})
    g.link(mix, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def knit_mat():
    m, g, out = new_mat("PA_Knit")
    h = attr(g, "knit", "Fac")
    co = attr(g, "kuv")
    twist = g.node("ShaderNodeTexWave", label="yarn twist", props={"wave_type": "BANDS", "bands_direction": "DIAGONAL"},
                   Vector=co, Scale=260.0, Distortion=2.0)
    fuzz = g.node("ShaderNodeTexNoise", label="wool fuzz", Vector=co, Scale=2500.0, Detail=3.0)
    col = mixc(g, g.math("POWER", h, 0.7), srgb(0.30, 0.10, 0.05), srgb(0.78, 0.34, 0.15), "dark between stitches")
    bump = g.node("ShaderNodeBump", Strength=0.25, Distance=0.001,
                  Height=g.math("ADD", g.math("MULTIPLY", g.out(twist, "Factor"), 0.5), g.out(fuzz, "Factor")))
    b = g.node("ShaderNodeBsdfPrincipled", Base_Color=col, Roughness=0.9, Normal=bump)
    b.inputs["Sheen Weight"].default_value = 0.8
    b.inputs["Sheen Roughness"].default_value = 0.4
    b.inputs["Specular IOR Level"].default_value = 0.3
    g.link(b, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def rug_mat():
    """Beni Ourain-style wool rug: cream pile, a hand-knotted (wobbly, broken) charcoal diamond
    lattice, a few rust diamonds picked by cell hash, a rust band near the edge, dye-lot streaks."""
    m, g, out = new_mat("PA_Rug")
    co = attr(g, "ruv")
    x, y, _ = xyz(g, co)
    ex = g.math("SUBTRACT", RUG_W / 2, g.math("ABSOLUTE", x))
    ey = g.math("SUBTRACT", RUG_D / 2, g.math("ABSOLUTE", y))
    e = g.math("MINIMUM", ex, ey)
    e.label = "distance to the edge"
    band = g.math("MULTIPLY", ss(g, e, 0.05, 0.056), ss(g, e, 0.086, 0.08))
    band.label = "rust band"
    field = ss(g, e, 0.13, 0.14, "field")
    wob = g.node("ShaderNodeTexNoise", label="hand-knotted wobble", Vector=co, Scale=4.0, Detail=3.0)
    wx, wy, _ = xyz(g, g.vmath("SCALE", g.vmath("SUBTRACT", g.out(wob, "Color"), (0.5, 0.5, 0.5)), scale=0.06))
    xq, yq = g.math("ADD", x, wx), g.math("ADD", y, wy)
    q1 = g.math("ADD", g.math("DIVIDE", xq, 0.22), g.math("DIVIDE", yq, 0.15))
    q2 = g.math("SUBTRACT", g.math("DIVIDE", xq, 0.22), g.math("DIVIDE", yq, 0.15))
    lat = []
    for q in (q1, q2):
        a = g.math("ABSOLUTE", g.math("SUBTRACT", g.math("FRACT", g.math("ADD", q, 0.5)), 0.5))
        lat.append(ss(g, a, 0.045, 0.026, "lattice line"))
    gaps = g.node("ShaderNodeTexNoise", label="knots skip", Vector=co, Scale=26.0, Detail=2.0)
    lattice = g.math("MULTIPLY", g.math("MAXIMUM", lat[0], lat[1]), ss(g, g.out(gaps, "Factor"), 0.3, 0.42))
    cell = g.vec(g.math("FLOOR", q1), g.math("FLOOR", q2), 0.0)
    hsh = g.out(g.node("ShaderNodeTexWhiteNoise", label="pick a cell", props={"noise_dimensions": "3D"}, Vector=cell),
                "Value")
    dc = g.math("ADD", g.math("ABSOLUTE", g.math("SUBTRACT", g.math("FRACT", q1), 0.5)),
                g.math("ABSOLUTE", g.math("SUBTRACT", g.math("FRACT", q2), 0.5)))
    dot = g.math("MULTIPLY", ss(g, dc, 0.2, 0.17, "diamond in the cell"), ss(g, hsh, 0.86, 0.87))
    abr = g.node("ShaderNodeTexNoise", label="abrash: dye lots",
                 Vector=g.vec(g.math("MULTIPLY", x, 1.2), g.math("MULTIPLY", y, 9.0), 0.0), Scale=1.0, Detail=2.0)
    wool = g.node("ShaderNodeTexNoise", label="wool pile", Vector=g.vmath("MULTIPLY", co, (700.0, 700.0, 700.0)),
                  Scale=1.0, Detail=4.0)
    cream = mixc(g, g.out(abr, "Factor"), srgb(0.85, 0.80, 0.69), srgb(0.93, 0.89, 0.80))
    rust = srgb(0.74, 0.30, 0.12)
    c = mixc(g, g.math("MULTIPLY", lattice, field), cream, srgb(0.14, 0.12, 0.11), "lattice")
    c = mixc(g, g.math("MULTIPLY", dot, field), c, rust, "rust diamonds")
    c = mixc(g, band, c, rust, "band")
    c = mixc(g, g.math("MULTIPLY", g.out(wool, "Factor"), 0.25), c, srgb(0.35, 0.30, 0.26), "pile shading")
    bump = g.node("ShaderNodeBump", Strength=0.4, Distance=0.003, Height=g.out(wool, "Factor"))
    b = g.node("ShaderNodeBsdfPrincipled", Base_Color=c, Roughness=0.95, Normal=bump)
    b.inputs["Sheen Weight"].default_value = 0.7
    b.inputs["Sheen Roughness"].default_value = 0.5
    b.inputs["Specular IOR Level"].default_value = 0.2
    g.link(b, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def glaze_mat():
    """Reactive sage glaze that pools into darker drips, stopping short of a bare clay foot."""
    m, g, out = new_mat("PA_Glaze")
    co = attr(g, "vase_co")
    _, _, z = xyz(g, co)
    drip = g.node("ShaderNodeTexNoise", label="drips run down", Vector=g.vmath("MULTIPLY", co, (14.0, 14.0, 2.2)),
                  Scale=1.0, Detail=6.0, Roughness=0.6)
    edge = g.node("ShaderNodeTexNoise", Vector=co, Scale=18.0, Detail=2.0)
    glazed = ss(g, g.math("SUBTRACT", z, g.math("MULTIPLY", g.out(edge, "Factor"), 0.03)), 0.035, 0.04,
                "glaze line above the foot")
    gl = mixc(g, ss(g, g.out(drip, "Factor"), 0.35, 0.65), srgb(0.30, 0.42, 0.30), srgb(0.58, 0.64, 0.46))
    c = mixc(g, glazed, srgb(0.72, 0.55, 0.41), gl, "bare clay foot")
    rough = g.node("ShaderNodeMapRange", Value=glazed, To_Min=0.8, To_Max=0.12)
    b = g.node("ShaderNodeBsdfPrincipled", Base_Color=c, Roughness=rough, Coat_Weight=glazed)
    b.inputs["Coat Roughness"].default_value = 0.05
    g.link(b, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def limewash_mat():
    m, g, out = new_mat("PA_Limewash")
    co = g.out(g.node("ShaderNodeTexCoord"), "Object")
    cloud = g.node("ShaderNodeTexNoise", label="limewash clouds", Vector=co, Scale=1.4, Detail=8.0, Roughness=0.68,
                   Distortion=0.35)
    brush = g.node("ShaderNodeTexNoise", label="brush strokes", Vector=g.vmath("MULTIPLY", co, (5.0, 5.0, 1.6)),
                   Scale=1.0, Detail=5.0, Roughness=0.6)
    c = mixc(g, ss(g, g.out(cloud, "Factor"), 0.38, 0.66), srgb(0.80, 0.76, 0.70), srgb(0.90, 0.87, 0.82))
    c = mixc(g, g.math("MULTIPLY", g.out(brush, "Factor"), 0.25), c, srgb(0.76, 0.71, 0.64))
    grit = g.node("ShaderNodeTexNoise", label="grit", Vector=co, Scale=60.0, Detail=3.0)
    bump = g.node("ShaderNodeBump", Strength=0.08, Height=g.out(grit, "Factor"))
    b = g.node("ShaderNodeBsdfPrincipled", Base_Color=c, Roughness=0.95, Normal=bump)
    b.inputs["Specular IOR Level"].default_value = 0.2
    g.link(b, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def fringe_mat():
    return pb.material("Fringe", "matte", color=(0.62, 0.55, 0.44), roughness=0.9)


def pampas_mat():
    m, g, out = new_mat("PA_Pampas")
    h = g.node("ShaderNodeBsdfHairPrincipled", props={"parametrization": "MELANIN"})
    for k, v in (("Melanin", 0.16), ("Melanin Redness", 0.8), ("Roughness", 0.38), ("Radial Roughness", 0.6),
                 ("Coat", 0.0), ("Random Color", 0.2), ("Random Roughness", 0.2)):
        h.inputs[k].default_value = v
    g.link(h, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


# ───────────────────────────────────────────────────────── geometry

def chair(g, boucle, mats):
    # shell: a rounded section swept 250° around the back, lower at the arms
    arc = g.node("GeometryNodeCurveArc", label="shell path: 250° around the back", Resolution=72, Radius=RC,
                 Start_Angle=math.pi / 2 - PHI0, Sweep_Angle=2 * PHI0)
    quad = g.node("GeometryNodeCurvePrimitiveQuadrilateral", label="shell section", Width=SW, Height=HB - Z0)
    qf = g.node("GeometryNodeFilletCurve", label="padded edges", Curve=quad, Radius=0.05, Count=8, Limit_Radius=True)
    qf.inputs["Mode"].default_value = "Poly"
    qr = g.node("GeometryNodeResampleCurve", label="even spacing", Curve=qf, Count=72)
    qt = g.node("GeometryNodeTransform", Geometry=qr, Translation=(0.0, -(HB + Z0) / 2, 0.0))   # profile y → −z
    shell = g.node("GeometryNodeCurveToMesh", label="sweep", Curve=arc, Profile_Curve=qt, Fill_Caps=True)
    x, y, z = xyz(g, g.node("GeometryNodeInputPosition"))
    phi = g.math("ABSOLUTE", g.math("ARCTAN2", x, y))
    phi.label = "angle from the back"
    w = ss(g, phi, 0.35, PHI0 * 0.97, "back → arms")
    k = g.math("DIVIDE", g.math("SUBTRACT", g.math("MULTIPLY_ADD", w, HA - HB, HB), Z0), HB - Z0)
    zz = g.math("MULTIPLY_ADD", g.math("SUBTRACT", z, Z0), k, Z0)
    shell = g.node("GeometryNodeSetPosition", label="arms lower than the back", Geometry=shell,
                   Position=g.vec(x, y, zz))
    shell = g.node("GeometryNodeSubdivisionSurface", label="soften the arm ends", Mesh=shell, Level=1)
    shell = g.node("GeometryNodeSubdivideMesh", Mesh=shell, Level=2)
    # seat: an upholstered deck and a crowned cushion, squashed front to back
    base = lathe(g, [(0.0, Z0, 0.0), (RBASE, Z0, 0.025), (RBASE, ZS, 0.03), (0.0, ZS, 0.0)], "seat deck", 160, 60)
    cush = lathe(g, [(0.0, ZS, 0.0), (RBASE - 0.004, ZS, 0.035), (RBASE - 0.004, ZC, 0.06), (0.0, ZC + 0.018, 0.0)],
                 "cushion", 160, 60)
    seat = g.node("GeometryNodeTransform", Geometry=join(g, [base, cush]), Scale=(1.0, YSC, 1.0))
    seat = g.node("GeometryNodeSubdivideMesh", Mesh=seat, Level=2)
    body = g.group(boucle, Geometry=join(g, [shell, seat]), Scale=150.0, Depth=0.0022)
    body = pb.set_material(g, body, mats["boucle"])
    # four short turned walnut legs
    feet = g.node("GeometryNodeMeshCircle", label="leg positions", Vertices=4, Radius=0.25)
    feet = g.node("GeometryNodeTransform", Geometry=feet, Rotation=(0.0, 0.0, math.pi / 4))
    leg = g.node("GeometryNodeMeshCone", label="tapered leg", Vertices=32, Radius_Top=0.019, Radius_Bottom=0.012,
                 Depth=Z0 + 0.01)
    leg = g.node("GeometryNodeTransform", Geometry=g.node("GeometryNodeSetShadeSmooth", Geometry=leg,
                                                             Shade_Smooth=True), Translation=(0.0, 0.0, (Z0 + 0.01) / 2))
    legs = g.node("GeometryNodeRealizeInstances", Geometry=g.node("GeometryNodeInstanceOnPoints", Points=feet,
                                                                   Instance=leg))
    legs = store(g, legs, "wood_co", g.vmath("ADD", g.node("GeometryNodeInputPosition"), (0.35, 0.12, 0.0)),
                 label="cut from a wide board")
    legs = pb.set_material(g, legs, mats["walnut"])
    pil = pillow(g)
    pil = g.node("GeometryNodeTransform", label="lean on the back", Geometry=pil,
                 Translation=(0.02, 0.125, ZC + 0.15), Rotation=(math.radians(72), math.radians(3), math.radians(-6)))
    pil = pb.set_material(g, pil, mats["knit"])
    whole = join(g, [body, legs, pil], "chair")
    return g.node("GeometryNodeTransform", label="place the chair", Geometry=whole, Translation=tuple(CHAIR),
                  Rotation=(0.0, 0.0, CHAIR_ROT))


def pillow(g):
    """Chunky-knit lumbar pillow: a grid inflated by (1-|x|^p)(1-|y|^p), stockinette Vs pushed
    out of it, mirrored and stitched shut at the seam."""
    W, H, T = 0.46, 0.30, 0.13
    grid = g.node("GeometryNodeMeshGrid", label="pillow front", Size_X=W, Size_Y=H, Vertices_X=150, Vertices_Y=100)
    x, y, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    fx = g.math("SUBTRACT", 1.0, g.math("POWER", g.math("ABSOLUTE", g.math("DIVIDE", x, W / 2)), 2.4))
    fy = g.math("SUBTRACT", 1.0, g.math("POWER", g.math("ABSOLUTE", g.math("DIVIDE", y, H / 2)), 2.4))
    f = g.math("POWER", g.math("MAXIMUM", g.math("MULTIPLY", fx, fy), 0.0), 0.55)
    f.label = "stuffing"
    u = g.math("ADD", g.math("DIVIDE", x, W), 0.5)
    v = g.math("ADD", g.math("DIVIDE", y, H), 0.5)
    xc = g.math("SUBTRACT", g.math("FRACT", g.math("MULTIPLY", u, 9.0)), 0.5)
    xc.label = "across a stitch column"
    s = g.math("MULTIPLY_ADD", g.math("ABSOLUTE", xc), 0.9, g.math("MULTIPLY", v, 8.0))
    s.label = "rows of Vs"
    ridge = g.math("MULTIPLY_ADD", g.math("COSINE", g.math("MULTIPLY", s, TAU)), -0.5, 0.5)
    legs = g.math("POWER", g.math("SINE", g.math("MULTIPLY", g.math("ABSOLUTE", xc), TAU)), 0.6)
    knit = g.math("MULTIPLY", ridge, legs)
    knit.label = "stockinette"
    zt = g.math("MULTIPLY_ADD", f, T / 2, g.math("MULTIPLY", g.math("MULTIPLY", knit, 0.009),
                                                g.math("POWER", f, 0.3)))
    front = g.node("GeometryNodeSetPosition", label="inflate + stitches", Geometry=grid, Position=g.vec(x, y, zt))
    front = store(g, front, "knit", knit, kind="FLOAT")
    front = store(g, front, "kuv", g.vec(x, y, 0.0))
    back = g.node("GeometryNodeFlipFaces", Mesh=g.node("GeometryNodeTransform", Geometry=front, Scale=(1.0, 1.0, -1.0)))
    shut = g.node("GeometryNodeMergeByDistance", label="seam", Geometry=join(g, [front, back]), Distance=1e-4)
    return g.node("GeometryNodeSetShadeSmooth", Geometry=shut, Shade_Smooth=True)


def side_table(g, mats):
    pts = [(0.0, 0.0, 0.0), (0.19, 0.0, 0.004), (0.19, 0.035, 0.008), (0.085, 0.045, 0.03), (0.058, 0.26, 0.15),
           (0.085, 0.475, 0.03), (0.235, 0.485, 0.008), (0.235, TOP_Z, 0.006), (0.0, TOP_Z, 0.0)]
    t = lathe(g, pts, "spool table", 160)
    t = store(g, t, "wood_co", g.vmath("ADD", g.node("GeometryNodeInputPosition"), (0.025, -0.015, 0.0)),
              label="tree axis just off centre")
    t = pb.set_material(g, t, mats["walnut"])
    return g.node("GeometryNodeTransform", Geometry=t, Translation=tuple(TABLE))


def lamp(g, mats):
    ball = g.node("GeometryNodeMeshUVSphere", label="travertine ball", Segments=96, Rings=48, Radius=0.085)
    x, y, z = xyz(g, g.node("GeometryNodeInputPosition"))
    ball = g.node("GeometryNodeSetPosition", label="flat underneath", Geometry=ball,
                  Position=g.vec(x, y, g.math("ADD", g.math("MAXIMUM", z, -0.078), 0.078)))
    ball = store(g, g.node("GeometryNodeSetShadeSmooth", Geometry=ball, Shade_Smooth=True), "stone_co",
                 g.node("GeometryNodeInputPosition"))
    ball = pb.set_material(g, ball, mats["travertine"])
    stem = g.node("GeometryNodeMeshCylinder", Vertices=24, Radius=0.006, Depth=0.09)
    stem = g.node("GeometryNodeTransform", Geometry=stem, Translation=(0.0, 0.0, 0.195))
    sock = g.node("GeometryNodeMeshCylinder", Vertices=32, Radius=0.017, Depth=0.04)
    sock = g.node("GeometryNodeTransform", Geometry=sock, Translation=(0.0, 0.0, 0.245))
    brass = pb.set_material(g, g.node("GeometryNodeSetShadeSmooth", Geometry=join(g, [stem, sock]),
                                      Shade_Smooth=True), mats["brass"])
    # pleated shade: a zigzag ring swept up a line whose radius tapers
    zig = g.node("GeometryNodeCurvePrimitiveCircle", label="40 pleats", Resolution=80, Radius=1.0)
    alt = g.math("MULTIPLY_ADD", g.math("FLOORED_MODULO", g.node("GeometryNodeInputIndex"), 2.0), 0.09, 0.955)
    alt.label = "in, out, in, out"
    zig = g.node("GeometryNodeSetPosition", Geometry=zig,
                 Position=g.vmath("SCALE", g.node("GeometryNodeInputPosition"), scale=alt))
    path = g.node("GeometryNodeCurvePrimitiveLine", Start=(0.0, 0.0, 0.185), End=(0.0, 0.0, 0.395))
    path = g.node("GeometryNodeResampleCurve", Curve=path, Count=14)
    fac = g.out(g.node("GeometryNodeSplineParameter"), "Factor")
    taper = g.math("MULTIPLY_ADD", fac, 0.105 - 0.17, 0.17)
    taper.label = "tapered: 17 → 10.5 cm"
    shade = g.node("GeometryNodeCurveToMesh", label="pleated shade", Curve=path, Profile_Curve=zig, Scale=taper)
    sx, sy, sz = xyz(g, g.node("GeometryNodeInputPosition"))
    shade = store(g, shade, "suv", g.vec(g.math("MULTIPLY", g.math("ARCTAN2", sy, sx), 1 / TAU), sz, 0.0))
    shade = g.node("GeometryNodeSetShadeSmooth", Geometry=shade, Shade_Smooth=False)
    shade = pb.set_material(g, shade, mats["linen"])
    return g.node("GeometryNodeTransform", label="on the table", Geometry=join(g, [ball, brass, shade]),
                  Translation=tuple(LAMP))


def rug(g, mats):
    slab = g.node("GeometryNodeMeshCube", label="rug", Size=(RUG_W, RUG_D, RUG_T))
    slab = g.node("GeometryNodeTransform", Geometry=slab, Translation=(0.0, 0.0, RUG_T / 2))
    return pb.set_material(g, store(g, slab, "ruv", g.node("GeometryNodeInputPosition")), mats["rug"])


def curves_object(name):
    """Like pb.gn_object, but a Curves (hair) object: Cycles renders GN curves only from these."""
    tname = f"PA_{name}"
    old = bpy.data.objects.get(tname)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    ob = bpy.data.objects.new(tname, bpy.data.hair_curves.new(tname))
    pb._coll("PA_Corner").objects.link(ob)
    tree = new_tree(tname + "_GN")
    tree.is_modifier = True
    tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    ob.modifiers.new("PA_Nodes", "NODES").node_group = tree
    return ob, pb.Graph(tree)


def fringe(mat):
    ob, g = curves_object("Fringe")
    fr = []
    for side in (-1, 1):
        n = 170
        row = g.node("GeometryNodeMeshLine", label="fringe roots", props={"mode": "END_POINTS"}, Count=n,
                     Start_Location=(side * RUG_W / 2, -RUG_D / 2 + 0.03, RUG_T * 0.45),
                     Offset=(side * RUG_W / 2, RUG_D / 2 - 0.03, RUG_T * 0.45))
        strand = g.node("GeometryNodeCurvePrimitiveLine", Start=(0.0, 0.0, 0.0), End=(side * 0.06, 0.0, -0.004))
        strand = g.node("GeometryNodeResampleCurve", Curve=strand, Count=6)
        ln = g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT"}, Min=0.75, Max=1.2, Seed=31 + side)
        tw = g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT"}, Min=-0.22, Max=0.22, Seed=41 + side)
        inst = g.node("GeometryNodeInstanceOnPoints", Points=row, Instance=strand,
                      Rotation=g.vec(0.0, 0.0, g.out(tw, "Value")), Scale=g.out(ln, "Value"))
        fr.append(g.node("GeometryNodeRealizeInstances", Geometry=inst))
    fringe = join(g, fr)
    wig = g.node("ShaderNodeTexNoise", Scale=40.0, Detail=2.0)
    off = g.vmath("MULTIPLY", g.vmath("SUBTRACT", g.out(wig, "Color"), (0.5, 0.5, 0.5)), (0.012, 0.012, 0.0))
    tipf = g.out(g.node("GeometryNodeSplineParameter"), "Factor")
    fringe = g.node("GeometryNodeSetPosition", label="loose ends", Geometry=fringe, Offset=g.vmath("SCALE", off,
                                                                                                    scale=tipf))
    fringe = g.node("GeometryNodeSetCurveRadius", Curve=fringe, Radius=0.0011)
    g.output(pb.set_material(g, fringe, mat))
    pb.arrange(g.tree)
    return ob


def vase(g, mats):
    pts = [(0.0, 0.0, 0.0), (0.075, 0.0, 0.006), (0.125, 0.16, 0.12), (0.112, 0.30, 0.10), (0.046, 0.40, 0.05),
           (0.042, 0.455, 0.01), (0.054, 0.472, 0.005), (0.054, 0.48, 0.003), (0.037, 0.48, 0.003),
           (0.035, 0.44, 0.01), (0.0, 0.43, 0.0)]
    v = lathe(g, pts, "floor vase", 128)
    v = store(g, v, "vase_co", g.node("GeometryNodeInputPosition"))
    v = pb.set_material(g, v, mats["glaze"])
    return g.node("GeometryNodeTransform", Geometry=v, Translation=tuple(VASE))


def cyc(g, mats):
    """Seamless set: flat floor bending up into the wall (no horizon line)."""
    YF = -4.0
    S0 = WALL_Y0 - YF
    L = S0 + math.pi * WALL_R / 2 + WALL_H
    sweep = g.node("GeometryNodeMeshGrid", label="limewash sweep", Size_X=8.0, Size_Y=L, Vertices_X=2, Vertices_Y=320)
    x, y, _ = xyz(g, g.node("GeometryNodeInputPosition"))
    s = g.math("ADD", y, L / 2)
    s.label = "distance along the sweep"
    bend = g.math("MINIMUM", g.math("MAXIMUM", g.math("DIVIDE", g.math("SUBTRACT", s, S0), WALL_R), 0.0), math.pi / 2)
    up = g.math("MAXIMUM", g.math("SUBTRACT", s, S0 + math.pi * WALL_R / 2), 0.0)
    yy = g.math("ADD", g.math("ADD", YF, g.math("MINIMUM", s, S0)), g.math("MULTIPLY", g.math("SINE", bend), WALL_R))
    zz = g.math("ADD", g.math("MULTIPLY", g.math("SUBTRACT", 1.0, g.math("COSINE", bend)), WALL_R), up)
    sw = g.node("GeometryNodeSetPosition", Geometry=sweep, Position=g.vec(g.math("ADD", x, WIN_X + 4.0), yy, zz))
    sw = g.node("GeometryNodeSetShadeSmooth", Geometry=sw, Shade_Smooth=True)
    return pb.set_material(g, sw, mats["limewash"])


def pampas(mat):
    """Nine pampas plumes: Bézier stems, ~13 000 fibres instanced on their top 45 %, drooping,
    swaying once per loop."""
    ob, g = curves_object("Pampas")
    phase = g.out(g.group(pb.loop_clock(FRAMES)), "Phase")
    mouth = VASE + Vector((0.0, 0.0, 0.48))
    stems = []
    spec = [(8, 110, 0.95, (0.006, 0.004)), (17, 55, 0.86, (0.012, -0.004)), (24, 165, 0.78, (-0.012, 0.006)),
            (5, 250, 1.02, (-0.004, -0.01)), (21, 305, 0.80, (0.004, -0.012)), (30, 15, 0.70, (0.014, 0.008)),
            (13, 205, 0.92, (-0.01, -0.004)), (27, 120, 0.66, (0.0, 0.012)), (15, 340, 0.88, (0.01, 0.0))]
    for lean, az, L, (ox, oy) in spec:
        lean, az = math.radians(lean), math.radians(az)
        d = Vector((math.sin(lean) * math.cos(az), math.sin(lean) * math.sin(az), math.cos(lean)))
        a = mouth + Vector((ox, oy, -0.08))
        b = a + d * L
        h1 = a + Vector((d.x * 0.4, d.y * 0.4, 1.0)).normalized() * L * 0.45
        h2 = b - (d + Vector((d.x, d.y, 0.0)) * 0.6).normalized() * L * 0.3
        stems.append(g.node("GeometryNodeCurvePrimitiveBezierSegment", Resolution=40, Start=tuple(a),
                            Start_Handle=tuple(h1), End_Handle=tuple(h2), End=tuple(b)))
    st = join(g, stems, "stems")
    st = store(g, st, "sid", g.out(g.node("GeometryNodeCurveOfPoint"), "Curve Index"), kind="FLOAT")
    st = store(g, st, "fac", g.out(g.node("GeometryNodeSplineParameter"), "Factor"), kind="FLOAT")
    pts = g.node("GeometryNodeCurveToPoints", label="fibre roots", Curve=st, Count=3200)
    pts_t = store(g, g.out(pts, "Points"), "tan", g.out(pts, "Tangent"))
    fac = g.out(g.node("GeometryNodeInputNamedAttribute", props={"data_type": "FLOAT"}, Name="fac"), "Attribute")
    plume = g.node("GeometryNodeDeleteGeometry", label="plume: top 45 %", props={"domain": "POINT"}, Geometry=pts_t,
                   Selection=g.math("LESS_THAN", fac, 0.55))
    xx = g.math("DIVIDE", g.math("SUBTRACT", fac, 0.55), 0.45)
    env = g.math("MULTIPLY", g.math("POWER", g.math("MAXIMUM", g.math("SINE", g.math("MULTIPLY", xx, math.pi)), 0.0),
                                    0.6), g.math("MULTIPLY_ADD", xx, -0.45, 1.0))
    env.label = "plume outline"
    rl = g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT"}, Min=0.55, Max=1.0, Seed=5)
    flen = g.math("MULTIPLY", g.math("MULTIPLY", env, g.out(rl, "Value")), 0.19)
    plume = store(g, plume, "flen", flen, kind="FLOAT")
    tan = g.out(g.node("GeometryNodeInputNamedAttribute", props={"data_type": "FLOAT_VECTOR"}, Name="tan"),
                "Attribute")
    rnd = g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT_VECTOR"}, Min=(-1.0, -1.0, -1.0),
                 Max=(1.0, 1.0, 1.0), Seed=6)
    fdir = g.vmath("ADD", g.vmath("ADD", g.vmath("SCALE", tan, scale=0.8), g.vmath("SCALE", g.out(rnd, "Value"),
                                                                             scale=1.8)), (0.0, 0.0, 0.25))
    rot = g.node("FunctionNodeAlignRotationToVector", props={"axis": "Z"}, Vector=fdir)
    fib = g.node("GeometryNodeResampleCurve", Curve=g.node("GeometryNodeCurvePrimitiveLine", Start=(0.0, 0.0, 0.0),
                                                           End=(0.0, 0.0, 1.0)), Count=6)
    fibs = g.node("GeometryNodeInstanceOnPoints", label="fibres", Points=plume, Instance=fib, Rotation=rot,
                  Scale=g.out(g.node("GeometryNodeInputNamedAttribute", props={"data_type": "FLOAT"}, Name="flen"),
                              "Attribute"))
    fibs = g.node("GeometryNodeRealizeInstances", Geometry=fibs)
    fp = g.out(g.node("GeometryNodeSplineParameter"), "Factor")
    fl = g.out(g.node("GeometryNodeInputNamedAttribute", props={"data_type": "FLOAT"}, Name="flen"), "Attribute")
    fibs = g.node("GeometryNodeSetPosition", label="droop", Geometry=fibs,
                  Offset=g.vec(0.0, 0.0, g.math("MULTIPLY", g.math("MULTIPLY", fp, fp), g.math("MULTIPLY", fl, -0.6))))
    fibs = g.node("GeometryNodeSetCurveRadius", Curve=fibs, Radius=g.math("MULTIPLY_ADD", fp, -0.0003, 0.00045))
    stf = g.out(g.node("GeometryNodeInputNamedAttribute", props={"data_type": "FLOAT"}, Name="fac"), "Attribute")
    st_r = g.node("GeometryNodeSetCurveRadius", Curve=st, Radius=g.math("MULTIPLY_ADD", stf, -0.0012, 0.0024))
    allc = join(g, [st_r, fibs], "pampas")
    sid = g.out(g.node("GeometryNodeInputNamedAttribute", props={"data_type": "FLOAT"}, Name="sid"), "Attribute")
    _, _, pz = xyz(g, g.node("GeometryNodeInputPosition"))
    hgt = g.math("POWER", g.math("MINIMUM", g.math("MAXIMUM", g.math("DIVIDE", g.math("SUBTRACT", pz, mouth.z), 0.9),
                                                    0.0), 1.2), 2.0)
    hgt.label = "bends more toward the tip"
    a1 = g.math("MULTIPLY", g.math("ADD", phase, g.math("MULTIPLY", sid, 0.37)), TAU)
    a2 = g.math("MULTIPLY", g.math("ADD", phase, g.math("MULTIPLY", sid, 0.61)), TAU)
    sway = g.vec(g.math("MULTIPLY", g.math("SINE", a1), 0.022), g.math("MULTIPLY", g.math("COSINE", a2), 0.014), 0.0)
    sway.label = "one slow sway per loop"
    allc = g.node("GeometryNodeSetPosition", label="sway", Geometry=allc, Offset=g.vmath("SCALE", sway, scale=hgt))
    g.output(pb.set_material(g, allc, mat))
    pb.arrange(g.tree)
    return ob


def window_wall():
    """The room's left wall with a 2 × 3 pane window: the sun only reaches the corner through it.
    Invisible to the camera and to reflections."""
    ob, g = pb.gn_object("Window", "Corner")
    Y0, Y1, ZT = -4.0, 2.0, 7.0
    (wy0, wy1), (wz0, wz1) = WIN_Y, WIN_Z
    ym = (wy0 + wy1) / 2
    zs = [wz0 + (wz1 - wz0) * k / 3 for k in (1, 2)]
    boxes = [(Y0, Y1, 0.0, wz0), (Y0, Y1, wz1, ZT), (Y0, wy0, wz0, wz1), (wy1, Y1, wz0, wz1),
             (ym - 0.025, ym + 0.025, wz0, wz1)] + [(wy0, wy1, z - 0.022, z + 0.022) for z in zs]
    parts = []
    for y0, y1, z0, z1 in boxes:
        c = g.node("GeometryNodeMeshCube", Size=(0.12, y1 - y0, z1 - z0))
        parts.append(g.node("GeometryNodeTransform", Geometry=c, Translation=(WIN_X, (y0 + y1) / 2, (z0 + z1) / 2)))
    g.output(pb.set_material(g, join(g, parts, "wall with a window"),
                             pb.material("WindowWall", "matte", color=(0.05, 0.05, 0.05), roughness=1.0)))
    pb.arrange(g.tree)
    ob.visible_camera = False
    ob.visible_glossy = False
    return ob


# ───────────────────────────────────────────────────────── the day: functions of the frame
# Every light is a driver whose expression is a function of the frame. They are Blender "simple
# expressions", so they run in a plain `Blender -b` render without enabling Python auto-execution.
# The sky is world shader nodes fed by one more such driver (a curve too long for one expression).
T = f"fmod(frame-1,{FRAMES})/{FRAMES}"                                     # loop phase 0..1, frame N+1 == frame 1
U = f"min(fmod((frame-1)/{FRAMES}+{1 - T_RISE:.2f},1)/{(T_SET - T_RISE) % 1.0:.2f},1)"   # sun: 0 rise .. 1 set
EL = f"radians({EL_MAX:g})*pow(sin(pi*{U}),0.85)"                          # sun elevation
NIGHT = f"(smoothstep(0.53,0.66,{T})-smoothstep(0.87,0.96,{T}))"           # 0 by day .. 1 at night

SKY = [  # t, colour (linear), strength
    (0.00, (0.62, 0.70, 0.92), 0.20), (0.25, (0.62, 0.74, 1.00), 0.24), (0.44, (0.80, 0.72, 0.70), 0.18),
    (0.52, (0.55, 0.45, 0.62), 0.10), (0.60, (0.16, 0.22, 0.55), 0.06), (0.70, (0.07, 0.11, 0.32), 0.04),
    (0.84, (0.07, 0.11, 0.32), 0.04), (0.90, (0.48, 0.36, 0.55), 0.07), (0.95, (0.72, 0.62, 0.74), 0.14),
    (1.00, (0.62, 0.70, 0.92), 0.20)]


def drive(owner, path, expr, index=None):
    assert len(expr) < 256, (path, len(expr), expr)        # Blender's limit for a driver expression
    fc = owner.driver_add(path) if index is None else owner.driver_add(path, index)
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = expr
    return fc


def sky_nodes(world):
    """Sky colour and strength from time of day: one smoothstep Map Range per stretch between two
    keys, chained Mix nodes (frame-exact piecewise smoothstep)."""
    nt = world.node_tree
    g = pb.Graph(nt)
    bg = nt.nodes["Background"]
    tv = g.node("ShaderNodeValue", label="time of day: fmod(frame-1, 300)/300")
    fc = drive(tv.outputs[0], "default_value", T)
    col = strength = None
    for (t0, c0, s0), (t1, c1, s1) in zip(SKY, SKY[1:]):
        k = g.node("ShaderNodeMapRange", label=f"{t0:.2f} → {t1:.2f}", props={"interpolation_type": "SMOOTHSTEP"},
                   Value=tv, From_Min=t0, From_Max=t1)
        col = mixc(g, k, col if col is not None else (*c0, 1.0), (*c1, 1.0))
        strength = g.node("ShaderNodeMix", props={"data_type": "FLOAT"}, Factor=k,
                          A=strength if strength is not None else s0, B=s1)
    g.link(col, bg, b_key="Color")
    g.link(strength, bg, b_key="Strength")
    pb.arrange(nt)
    return fc


def drive_day(sun, moon, bulb_light, world):
    sc = bpy.context.scene
    sc.view_settings.use_white_balance = True
    sun.rotation_euler = (0.0, 0.0, 0.0)          # −Z tilted down by the elevation (Y), turned to the heading (Z)
    fcs = [
        drive(sun, "rotation_euler", f"-(pi/2-{EL})", 1),
        drive(sun, "rotation_euler", f"radians(lerp({AZ0:g},{AZ1:g},pow({U},1.3)))", 2),
        drive(sun.data, "energy", f"{SUN_E:g}*smoothstep(0,0.06,{U})*smoothstep(1,0.93,{U})"),
        drive(sun.data, "temperature", f"lerp(1900,5600,smoothstep(0,radians(22),{EL}))-350*smoothstep(0.45,0.7,{U})"),
        drive(moon.data, "energy", f"0.14*smoothstep(0.6,0.7,{T})*(1-smoothstep(0.83,0.89,{T}))"),
        drive(bulb_light.data, "energy", f"{LAMP_W:g}*(smoothstep({LAMP_ON:g},{LAMP_ON + 0.006:.3f},{T})"
                                         f"-smoothstep({LAMP_OFF:g},{LAMP_OFF + 0.006:.3f},{T}))"),
        drive(sc, "view_settings.exposure", f"{NIGHT_EV:g}*{NIGHT}"),                  # the camera re-meters
        drive(sc, "view_settings.white_balance_temperature", f"lerp(6500,3900,{NIGHT})"),   # ...and re-balances
        sky_nodes(world),
    ]
    sc.frame_set(2)
    sc.frame_set(1)
    bad = [fc.data_path for fc in fcs if not (fc.driver.is_valid and fc.driver.is_simple_expression)]
    assert not bad, f"drivers that would need Python auto-run: {bad}"
    return {f"{fc.id_data.name}.{fc.data_path}[{fc.array_index}]": fc.driver.expression for fc in fcs}


# ───────────────────────────────────────────────────────── build

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    info = pb.piece("Corner", aspect="1:1", width=1080, frames=FRAMES, engine="CYCLES", samples=96)
    mats = {"boucle": boucle_mat(), "walnut": walnut_mat(), "travertine": travertine_mat(), "linen": linen_mat(),
            "knit": knit_mat(), "rug": rug_mat(), "glaze": glaze_mat(), "limewash": limewash_mat(),
            "fringe": fringe_mat(), "brass": pb.material("Brass", "brass", roughness=0.3)}
    boucle = boucle_group()
    ob, g = pb.gn_object("Corner", "Corner")
    g.output(join(g, [cyc(g, mats), rug(g, mats), chair(g, boucle, mats), side_table(g, mats), lamp(g, mats),
                      vase(g, mats)], "the corner"))
    pb.arrange(g.tree)
    pampas(pampas_mat())
    fringe(mats["fringe"])
    window_wall()

    sc = bpy.context.scene
    st = bpy.data.collections.get("PA_Studio") or bpy.data.collections.new("PA_Studio")
    if st.name not in sc.collection.children:
        sc.collection.children.link(st)
    cam = bpy.data.objects.new("PA_Camera", bpy.data.cameras.new("PA_Camera"))
    st.objects.link(cam)
    cam.data.lens = 55
    cam.location = Vector((-0.95, -3.4, 1.2))   # front left: we see the sunlit sides
    look = Vector((-0.15, 0.40, 0.60))
    cam.rotation_euler = (look - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    focus = bpy.data.objects.new("PA_Focus", None)
    st.objects.link(focus)
    focus.location = CHAIR + Vector((0.0, 0.0, 0.45))
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 4.0
    cam.data.dof.focus_object = focus

    def light(name, kind, **kw):
        lo = bpy.data.objects.new(name, bpy.data.lights.new(name, kind))
        st.objects.link(lo)
        for k, v in kw.items():
            setattr(lo.data, k, v)
        return lo

    sun = light("PA_Sun", "SUN", angle=math.radians(1.0), use_temperature=True)
    moon = light("PA_Moon", "SUN", angle=math.radians(0.6), use_temperature=True, temperature=9000.0)
    moon.rotation_euler = Vector((math.cos(math.radians(28)) * math.cos(math.radians(35)),
                                  math.cos(math.radians(28)) * math.sin(math.radians(35)),
                                  -math.sin(math.radians(28)))).to_track_quat("-Z", "Y").to_euler()
    bulb = light("PA_LampBulb", "POINT", shadow_soft_size=0.028, use_temperature=True, temperature=2900.0)
    bulb.location = LAMP + Vector((0.0, 0.0, 0.29))
    world = bpy.data.worlds.new("PA_World")
    world.use_nodes = True
    sc.world = world
    day = drive_day(sun, moon, bulb, world)   # the point light is the bulb (seen through the shade top)
    sc.cycles.max_bounces = 10
    sc.cycles.transparent_max_bounces = 16
    pb.output(os.path.join(DAY, "loop.mp4"), "video")
    layout = pb.layout_load(os.path.join(DAY, "nodes_layout.json"))   # tidied by hand in the UI (frames, real sizes)
    pb.save(ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else os.path.join(DAY, "corner.blend"))
    return {"piece": info, "day": day, "layout": layout}


def cy_preview(path, frame, pct=40, samples=24):
    sc = bpy.context.scene
    keep = (sc.render.resolution_percentage, sc.cycles.samples)
    sc.render.resolution_percentage, sc.cycles.samples = pct, samples
    try:
        return pb.render_still(path, frame=frame)
    finally:
        sc.render.resolution_percentage, sc.cycles.samples = keep


if __name__ == "__main__":
    res = build()
    if "--preview" in ARGS:
        for fr in ARGS[ARGS.index("--preview") + 1].split(","):
            fr = int(fr)
            res[f"preview_{fr}"] = cy_preview(os.path.join(DAY, f"_preview_{fr:03d}.png"), fr)["seconds"]
    if "--still" in ARGS:
        fr = int(ARGS[ARGS.index("--still") + 1])
        res["still"] = pb.render_still(os.path.join(DAY, f"_still_{fr:03d}.png"), frame=fr)
    res["audit"] = pb.audit("Corner")
    res["describe"] = pb.describe("PA_Corner_GN")
    print("BUILD_RESULT", res)
