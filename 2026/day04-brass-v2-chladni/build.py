"""Nodevember 2026 · Day 04 · Brass — v2: Chladni.

A square brass plate sits on the shaft of a vibrator in a black void. Four tones per loop, each higher:
the plate sings in the shape of the tone (its reflection smears on the antinodes), the sand is thrown off the antinodes
and settles on the nodal lines: an X of arcs → a rounded square → a ring of loops → lace, and the last tone
drops back to the first.

Sand: points scattered on the plate, each projected onto the zero set of ONE standing-wave formula
    f(u, v) = cos(nπu)·cos(mπv) + cos(mπu)·cos(nπv)        (u, v ∈ [0, 1] across the plate)
by Newton steps in a Repeat Zone (p ← p − f·∇f / |∇f|²). Only (n, m) change per tone. Even n, m make the
centre an antinode (the driven point), as on a centre-driven plate. A grain is thrown by the new tone's
amplitude |f| where it lies: grains on an antinode bounce longest and highest, grains already near a new
nodal line barely move.

Run: Blender -b --factory-startup --python build.py -- [--preview f,f,..] [--look f,f,..] [--still N]
     [--clay] [--save-as x.blend]
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

FRAMES = 240                         # 8 s @ 30 fps: four notes, 2 s each
# a real plate's modes are mixtures: each tone = mode (n, m) + Mix · mode (n2, m2), same symmetry class
TONES = [((0, 4), (2, 4), 0.60),     # an X of four arcs
         ((4, 6), (0, 8), -0.35),    # a rounded square round a ring
         ((4, 8), (2, 10), 0.40),    # a ring of loops
         ((8, 10), (4, 12), 0.40)]   # dense nested lace
NGRAINS = 300000
ITER, MAXSTEP = 24, 0.04             # Newton steps onto the nodal lines, step clamp (plate units)
WARP, WARP_SCALE = 0.17, 0.7         # the plate is not perfectly even: a static noise warp of the wave
CLAMP_R = (0.085, 0.135)             # the bolt clamps the centre: a nodal ring of sand hugs the washer
LINE_W = (0.006, 0.030, 0.048)       # sand line half-width: min, max, k/|∇f| (wide where the slope is gentle)
HALO_P, HALO_K = 0.25, 4.0           # a quarter of the grains spread 4× wider: soft edges
STRAY_P = 0.03                       # grains that stay where they were scattered
EDGE = 0.985                         # grains stay on the plate
DELAY = 0.06                         # tone → sand reaction spread (fraction of a note)
FLY = (0.10, 0.42)                   # flight time near a node … at an antinode (fraction of a note)
AMP_FULL = 1.8                       # |f| that counts as a full antinode
WOB = 0.07                           # sideways random walk at an antinode
HOP_MAX = 0.030                      # hop height at an antinode
R_GRAIN = (0.0016, 0.0030)            # fine sand (plate = 2 units)

PLATE_T = 0.03                       # plate thickness (top at z = 0)
PLATE_RES = 241                      # plate grid (it bends in the shape of each tone)
SHIMMER = 0.16                       # extra brass roughness at a full antinode while the tone sings: the plate
                                     # is rigid to the eye (µm at hundreds of Hz), only its reflection smears

F, V, G, I = "NodeSocketFloat", "NodeSocketVector", "NodeSocketGeometry", "NodeSocketInt"


# ───────────────────────────────────────────────────────── helpers

def new_group(name, ins, outs):
    old = bpy.data.node_groups.get(name)
    if old:
        bpy.data.node_groups.remove(old)
    t = bpy.data.node_groups.new(name, "GeometryNodeTree")
    for n, k, *d in ins:
        s = t.interface.new_socket(n, in_out="INPUT", socket_type=k)
        if d:
            s.default_value = d[0]
    for n, k in outs:
        t.interface.new_socket(n, in_out="OUTPUT", socket_type=k)
    g = pb.Graph(t)
    return t, g, *g.group_io()


SECTIONS = {}
PALETTE = [(0.30, 0.24, 0.10), (0.12, 0.25, 0.16), (0.13, 0.18, 0.32), (0.32, 0.13, 0.12), (0.22, 0.15, 0.30),
           (0.10, 0.25, 0.27), (0.28, 0.19, 0.08), (0.18, 0.22, 0.12)]


def section(g, label):
    marks = SECTIONS.setdefault(g.tree, [])
    marks.append((label, PALETTE[len(marks) % len(PALETTE)], len(g.tree.nodes)))


def frame_sections():
    for tree, marks in SECTIONS.items():
        nodes = list(tree.nodes)
        for i, (label, color, start) in enumerate(marks):
            end = marks[i + 1][2] if i + 1 < len(marks) else len(nodes)
            fr = tree.nodes.new("NodeFrame")
            fr.label, fr.label_size, fr.shrink = label, 48, True
            fr.use_custom_color, fr.color = True, color
            for n in nodes[start:end]:
                if n.bl_idname not in ("NodeGroupInput", "NodeGroupOutput", "NodeFrame"):
                    n.parent = fr
        for n in nodes:
            if n.bl_idname in ("GeometryNodeInputPosition", "ShaderNodeSeparateXYZ", "GeometryNodeInputIndex",
                               "GeometryNodeSplineParameter", "ShaderNodeTexCoord"):
                n.hide = True


def smooth(g, value, lo, hi, label=None):
    n = g.node("ShaderNodeMapRange", label=label, props={"interpolation_type": "SMOOTHSTEP"}, Value=value,
               From_Min=lo, From_Max=hi, To_Min=0.0, To_Max=1.0)
    return g.out(n, "Result")


def xyz(g, v):
    s = g.node("ShaderNodeSeparateXYZ", Vector=v)
    return g.out(s, "X"), g.out(s, "Y"), g.out(s, "Z")


def rnd(g, lo, hi, seed, kind="FLOAT", label=None):
    n = g.node("FunctionNodeRandomValue", label=label, props={"data_type": kind}, Min=lo, Max=hi, Seed=seed)
    return g.out(n, "Value")


def index_switch(g, kind, idx, values, label):
    """Index Switch over sockets (linked) or constants (set)."""
    n = g.node("GeometryNodeIndexSwitch", label=label, props={"data_type": kind})
    while len(n.index_switch_items) < len(values):
        n.index_switch_items.new()
    g.link(idx, n, b_key="Index")
    for i, v in enumerate(values):
        g.set(n, i + 1, v)
    return n


# ───────────────────────────────────────────────────────── node groups

def chladni_group():
    """f and ∇f of the square-plate standing wave cos(nπu)cos(mπv) + cos(mπu)cos(nπv), u = (x+1)/2."""
    t, g, gin, gout = new_group("PA_ChladniWave", [("Position", V), ("n", F, 1.0), ("m", F, 3.0)],
                                [("f", F), ("Gradient", V)])
    t.interface.items_tree["Position"].default_input = "POSITION"
    t.interface.items_tree["Position"].hide_value = True
    M = g.math
    x, y, _ = xyz(g, gin.outputs["Position"])
    a = M("MULTIPLY", gin.outputs["n"], PI / 2)
    b = M("MULTIPLY", gin.outputs["m"], PI / 2)
    X1, Y1 = M("ADD", x, 1.0), M("ADD", y, 1.0)
    ax, bx, ay, by = M("MULTIPLY", a, X1), M("MULTIPLY", b, X1), M("MULTIPLY", a, Y1), M("MULTIPLY", b, Y1)
    cax, sax, cbx, sbx = M("COSINE", ax), M("SINE", ax), M("COSINE", bx), M("SINE", bx)
    cay, say, cby, sby = M("COSINE", ay), M("SINE", ay), M("COSINE", by), M("SINE", by)
    f = M("ADD", M("MULTIPLY", cax, cby), M("MULTIPLY", cbx, cay))
    f.label = "f = cos(nπu)cos(mπv) + cos(mπu)cos(nπv)"
    fx = M("ADD", M("MULTIPLY", M("MULTIPLY", a, sax), cby), M("MULTIPLY", M("MULTIPLY", b, sbx), cay))
    fy = M("ADD", M("MULTIPLY", M("MULTIPLY", b, cax), sby), M("MULTIPLY", M("MULTIPLY", a, cbx), say))
    grad = g.vec(M("MULTIPLY", fx, -1.0), M("MULTIPLY", fy, -1.0), 0.0)
    grad.label = "∇f"
    g.link(f, gout, b_key="f")
    g.link(grad, gout, b_key="Gradient")
    pb.arrange(t)
    return t


def plate_mode_group(wave):
    """One tone of the plate: f = (wave(n, m) + Mix·wave(n2, m2)) at a slightly warped position, times a
    clamp ring at the bolt. Outputs f and ∇f (clamped) and the free f (for the plate's own motion)."""
    t, g, gin, gout = new_group("PA_PlateMode", [("Position", V), ("n", F, 2.0), ("m", F, 4.0), ("n2", F, 0.0),
                                                 ("m2", F, 6.0), ("Mix", F, 0.3)],
                                [("f", F), ("Gradient", V), ("Free f", F)])
    t.interface.items_tree["Position"].default_input = "POSITION"
    t.interface.items_tree["Position"].hide_value = True
    P = gin.outputs["Position"]
    section(g, "a · uneven plate: static noise warp")
    nz = g.node("ShaderNodeTexNoise", label="plate unevenness", Vector=P, Scale=WARP_SCALE, Detail=1.0)
    off = g.vmath("SCALE", g.vmath("SUBTRACT", g.out(nz, "Color"), (0.5, 0.5, 0.5)), scale=WARP)
    ox, oy, _ = xyz(g, off)
    warped = g.vmath("ADD", P, g.vec(ox, oy, 0.0))
    section(g, "b · two standing waves mixed")
    w1 = g.group(wave, Position=warped, n=gin.outputs["n"], m=gin.outputs["m"])
    w2 = g.group(wave, Position=warped, n=gin.outputs["n2"], m=gin.outputs["m2"])
    mix = gin.outputs["Mix"]
    f0 = g.math("ADD", g.out(w1, "f"), g.math("MULTIPLY", g.out(w2, "f"), mix))
    g0 = g.vmath("ADD", g.out(w1, "Gradient"), g.vmath("SCALE", g.out(w2, "Gradient"), scale=mix))
    section(g, "c · bolt clamp ring")
    px, py, _ = xyz(g, P)
    flat = g.vec(px, py, 0.0)
    r = g.out(g.vmath("LENGTH", flat), "Value")
    d = CLAMP_R[1] - CLAMP_R[0]
    tt = g.node("ShaderNodeMath", props={"operation": "MULTIPLY", "use_clamp": True},
                ins={0: g.math("SUBTRACT", r, CLAMP_R[0]), 1: 1.0 / d})
    w = g.math("MULTIPLY", g.math("MULTIPLY", tt, tt), g.math("SUBTRACT", 3.0, g.math("MULTIPLY", tt, 2.0)))
    dw = g.math("DIVIDE", g.math("MULTIPLY", g.math("MULTIPLY", tt, g.math("SUBTRACT", 1.0, tt)), 6.0 / d),
                g.math("MAXIMUM", r, 1e-4))
    f = g.math("MULTIPLY", f0, w)
    f.label = "f"
    grad = g.vmath("ADD", g.vmath("SCALE", g0, scale=w), g.vmath("SCALE", flat, scale=g.math("MULTIPLY", dw, f0)))
    grad.label = "∇f"
    g.link(f, gout, b_key="f")
    g.link(grad, gout, b_key="Gradient")
    g.link(f0, gout, b_key="Free f")
    pb.arrange(t)
    return t


MODE_KEYS = ("n", "m", "n2", "m2", "Mix")


def tone_values(tone):
    (n, m), (n2, m2), mix = tone
    return (float(n), float(m), float(n2), float(m2), float(mix))


def nodal_group(mode):
    """Points → the same points pulled onto the nodal lines f = 0 of one tone, spread into a sand line."""
    t, g, gin, gout = new_group("PA_ToNodalLines", [("Points", G)] + [(k, F, 0.0) for k in MODE_KEYS] +
                                [("Seed", I, 0)], [("Points", G)])
    prm = {k: gin.outputs[k] for k in MODE_KEYS}
    section(g, "a · Newton steps onto f = 0")
    rin, rout = g.zone("repeat", ITER)
    g.link(gin.outputs["Points"], rin, b_key="Geometry")
    w = g.group(mode, **prm)
    gr = g.out(w, "Gradient")
    g2 = g.math("ADD", g.out(g.vmath("DOT_PRODUCT", gr, gr), "Value"), 1e-3)
    k = g.math("DIVIDE", g.math("MULTIPLY", g.out(w, "f"), -1.0), g2)
    step = g.vmath("SCALE", gr, scale=k)
    step.label = "−f·∇f / |∇f|²"
    ln = g.out(g.vmath("LENGTH", step), "Value")
    clampk = g.math("MINIMUM", 1.0, g.math("DIVIDE", MAXSTEP, g.math("ADD", ln, 1e-6)))
    moved = g.vmath("ADD", g.node("GeometryNodeInputPosition"), g.vmath("SCALE", step, scale=clampk))
    inside = g.vmath("MAXIMUM", g.vmath("MINIMUM", moved, (EDGE, EDGE, 0.0)), (-EDGE, -EDGE, 0.0))
    inside.label = "stay on the plate"
    sp = g.node("GeometryNodeSetPosition", Geometry=g.out(rin, "Geometry"), Position=inside)
    g.link(sp, rout, b_key="Geometry")

    section(g, "b · sand line: width, halo, strays")
    w2 = g.group(mode, **prm)
    gr2 = g.out(w2, "Gradient")
    across = g.vmath("NORMALIZE", gr2)
    slope = g.math("ADD", g.out(g.vmath("LENGTH", gr2), "Value"), 1e-3)
    width = g.math("MINIMUM", LINE_W[1], g.math("MAXIMUM", LINE_W[0], g.math("DIVIDE", LINE_W[2], slope)))
    width.label = "line width ∝ 1/|∇f|"
    seed = gin.outputs["Seed"]
    gauss = g.math("SUBTRACT", g.math("ADD", g.math("ADD", rnd(g, 0.0, 1.0, seed), rnd(g, 0.0, 1.0, 101)),
                                     rnd(g, 0.0, 1.0, 202)), 1.5)
    halo = g.node("FunctionNodeRandomValue", label="halo grain?", props={"data_type": "BOOLEAN"},
                  Probability=HALO_P, Seed=505)
    spreadk = g.node("GeometryNodeSwitch", props={"input_type": "FLOAT"}, Switch=g.out(halo, "Value"),
                     False_=2.0, True_=2.0 * HALO_K)
    spread = g.vmath("SCALE", across, scale=g.math("MULTIPLY", g.math("MULTIPLY", gauss, width), spreadk))
    lined = g.vmath("ADD", g.node("GeometryNodeInputPosition"), spread)
    rest = g.node("GeometryNodeSampleIndex", label="where it was scattered",
                  props={"data_type": "FLOAT_VECTOR", "domain": "POINT"}, Geometry=gin.outputs["Points"],
                  Value=g.node("GeometryNodeInputPosition"), Index=g.node("GeometryNodeInputIndex"))
    stray_on = g.node("FunctionNodeRandomValue", label="stray?", props={"data_type": "BOOLEAN"},
                      Probability=STRAY_P, Seed=g.math("ADD", seed, 303.0))
    pos = g.node("GeometryNodeSwitch", props={"input_type": "VECTOR"}, Switch=g.out(stray_on, "Value"),
                 False_=lined, True_=g.out(rest, "Value"))
    pos = g.vmath("MAXIMUM", g.vmath("MINIMUM", pos, (EDGE, EDGE, 0.0)), (-EDGE, -EDGE, 0.0))
    out = g.node("GeometryNodeSetPosition", Geometry=g.out(rout, "Geometry"), Position=pos)
    g.link(out, gout, b_key="Points")
    pb.arrange(t)
    return t


def notes_group(clock):
    """Loop clock → this tone and the previous one (index and mode parameters), and the time inside the tone."""
    outs = [("Tone", F), ("Previous", F), ("Time in tone", F)] + [(k, F) for k in MODE_KEYS] + \
        [(k + " prev", F) for k in MODE_KEYS]
    t, g, gin, gout = new_group("PA_Tones", [], outs)
    ck = g.group(clock)
    q = g.math("MULTIPLY", g.out(ck, "Phase"), float(len(TONES)))
    note, t_in = g.math("FLOOR", q), g.math("FRACT", q)
    prev = g.math("FLOORED_MODULO", g.math("ADD", note, len(TONES) - 1.0), float(len(TONES)))
    for sock, v in (("Tone", note), ("Previous", prev), ("Time in tone", t_in)):
        g.link(v, gout, b_key=sock)
    for i, k in enumerate(MODE_KEYS):
        vals = [tone_values(tn)[i] for tn in TONES]
        g.link(index_switch(g, "FLOAT", note, vals, k), gout, b_key=k)
        g.link(index_switch(g, "FLOAT", prev, vals, k + " prev"), gout, b_key=k + " prev")
    pb.arrange(t)
    return t


def ring_group(mode, tones):
    """How hard the plate sings at Position (0..1): the previous tone fades, the new one swells then rings on
    quietly. Not a displacement: a real plate moves microns at hundreds of Hz, so the eye only sees the
    reflection smear on the antinodes (fed to the brass roughness) and the sand jump."""
    t, g, gin, gout = new_group("PA_PlateRing", [("Position", V)], [("Ring", F)])
    t.interface.items_tree["Position"].default_input = "POSITION"
    t.interface.items_tree["Position"].hide_value = True
    tn = g.group(tones)
    ti = g.out(tn, "Time in tone")
    wa = g.group(mode, Position=gin.outputs["Position"], **{k: g.out(tn, k + " prev") for k in MODE_KEYS})
    wb = g.group(mode, Position=gin.outputs["Position"], **{k: g.out(tn, k) for k in MODE_KEYS})
    env_a = g.math("MULTIPLY", 0.25, g.math("SUBTRACT", 1.0, smooth(g, ti, 0.0, 0.08)))
    swell = g.math("ADD", 0.25, g.math("MULTIPLY", 0.75, g.math("SUBTRACT", 1.0, smooth(g, ti, 0.15, 0.55))))
    env_b = g.math("MULTIPLY", smooth(g, ti, 0.0, 0.08, "new tone builds"), swell)
    shape = g.math("ADD", g.math("MULTIPLY", g.out(wa, "Free f"), env_a),
                   g.math("MULTIPLY", g.out(wb, "Free f"), env_b))
    amt = g.node("ShaderNodeMath", props={"operation": "DIVIDE", "use_clamp": True},
                 ins={0: g.math("ABSOLUTE", shape), 1: AMP_FULL})
    g.link(amt, gout, b_key="Ring")
    pb.arrange(t)
    return t


# ───────────────────────────────────────────────────────── materials

def shader(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, pb.Graph(m.node_tree)


def brass_material():
    """Brushed brass: concentric anisotropic brushing (default radial tangent), faint tarnish clouds,
    rounded edges from the Bevel shader node."""
    m, g = shader("PA_Brass")
    out = g.node("ShaderNodeOutputMaterial")
    co = g.node("ShaderNodeTexCoord")
    clouds = g.out(g.node("ShaderNodeTexNoise", Vector=g.out(co, "Object"), Scale=2.2, Detail=6.0,
                          Roughness=0.62), "Factor")
    tarnish = g.out(g.node("ShaderNodeMapRange", From_Min=0.42, From_Max=0.72, Value=clouds), "Result")
    col = g.node("ShaderNodeMix", props={"data_type": "RGBA"}, Factor=g.math("MULTIPLY", tarnish, 0.22),
                 A=(0.78, 0.52, 0.22, 1.0), B=(0.36, 0.22, 0.09, 1.0))
    ring = g.node("ShaderNodeAttribute", label="how hard the plate sings here",
                  props={"attribute_name": "ring", "attribute_type": "GEOMETRY"})
    rough = g.math("ADD", g.math("ADD", 0.22, g.math("MULTIPLY", tarnish, 0.10)),
                   g.math("MULTIPLY", g.out(ring, "Fac"), SHIMMER))
    bev = g.node("ShaderNodeBevel", Radius=0.004)
    bevel_normal = g.out(bev, "Normal")
    p = g.node("ShaderNodeBsdfPrincipled", Base_Color=g.out(col, "Result"), Metallic=1.0, Roughness=rough,
               Anisotropic=0.55, Normal=bevel_normal)
    g.link(p, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def sand_material():
    m, g = shader("PA_Sand")
    out = g.node("ShaderNodeOutputMaterial")
    tint = g.node("ShaderNodeAttribute", props={"attribute_name": "tint", "attribute_type": "INSTANCER"})
    col = g.node("ShaderNodeMix", props={"data_type": "RGBA"}, Factor=g.out(tint, "Fac"),
                 A=(0.95, 0.92, 0.84, 1.0), B=(0.78, 0.70, 0.58, 1.0))
    p = g.node("ShaderNodeBsdfPrincipled", Base_Color=g.out(col, "Result"), Roughness=0.55)
    g.link(p, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def simple(name, color, rough, coat=0.0, metallic=0.0):
    m, g = shader(name)
    out = g.node("ShaderNodeOutputMaterial")
    p = g.node("ShaderNodeBsdfPrincipled", Base_Color=(*color, 1.0), Roughness=rough, Coat_Weight=coat,
               Metallic=metallic)
    g.link(p, out, b_key="Surface")
    return m


# ───────────────────────────────────────────────────────── build

def build():
    for o in [o for o in bpy.data.objects if not o.name.startswith("PA_")]:   # factory Cube, Light, Camera
        bpy.data.objects.remove(o, do_unlink=True)
    for m in [m for m in bpy.data.materials if not m.name.startswith("PA_")]:        # factory "Material"
        bpy.data.materials.remove(m)
    info = pb.piece("Chladni", aspect="1:1", width=1080, frames=FRAMES, engine="CYCLES", samples=128)
    bpy.context.preferences.addons["cycles"].preferences.kernel_optimization_level = "OFF"
    clock = pb.loop_clock(FRAMES)
    wave = chladni_group()
    mode = plate_mode_group(wave)
    nodal = nodal_group(mode)
    tones = notes_group(clock)
    ring = ring_group(mode, tones)
    brass, sand = brass_material(), sand_material()

    # ───────────── plate, nut, stem
    ob, g = pb.gn_object("Plate", "Chladni")
    section(g, "a · rigid brass plate, ring → shader")
    top = g.node("GeometryNodeMeshGrid", Size_X=2.0, Size_Y=2.0, Vertices_X=PLATE_RES, Vertices_Y=PLATE_RES)
    low = g.node("GeometryNodeTransform", Geometry=g.out(top, "Mesh"), Translation=(0.0, 0.0, -PLATE_T))
    slab = g.node("GeometryNodeExtrudeMesh", Mesh=low, Offset=g.vec(0.0, 0.0, PLATE_T), Offset_Scale=1.0)
    slab.inputs["Individual"].default_value = False
    slab = g.node("GeometryNodeStoreNamedAttribute", label="ring → brass roughness",
                  props={"data_type": "FLOAT", "domain": "POINT"}, Geometry=slab, Name="ring",
                  Value=g.group(ring))
    section(g, "b · centre bolt + vibrator shaft")
    def cyl(verts, r, depth, z, label):
        c = g.node("GeometryNodeMeshCylinder", label=label, Vertices=verts, Radius=r, Depth=depth)
        return g.node("GeometryNodeTransform", Geometry=g.out(c, "Mesh"), Translation=(0.0, 0.0, z))
    washer = cyl(48, 0.085, 0.008, 0.004, "washer")
    nut = cyl(6, 0.062, 0.040, 0.028, "hex nut")
    stud = cyl(32, 0.026, 0.030, 0.060, "stud")
    stem = cyl(48, 0.042, 4.0, -PLATE_T - 2.0, "stem")
    bolt = g.node("GeometryNodeJoinGeometry")
    for part in (stem, stud, nut, washer):
        g.link(part, bolt, b_key="Geometry")
    join = g.node("GeometryNodeJoinGeometry")
    for part in (bolt, slab):
        g.link(part, join, b_key="Geometry")
    g.output(pb.set_material(g, join, brass))
    pb.arrange(g.tree)

    # ───────────── sand
    ob, g = pb.gn_object("Sand", "Chladni")
    seed = g.param("Seed", "int", 7, 0, 10000)
    section(g, "1 · scatter grains")
    grid = g.node("GeometryNodeMeshGrid", Size_X=2.0 * EDGE, Size_Y=2.0 * EDGE, Vertices_X=2, Vertices_Y=2)
    pts = g.node("GeometryNodeDistributePointsOnFaces", Mesh=grid, Density=NGRAINS / (2 * EDGE) ** 2, Seed=seed)
    pts = g.out(pts, "Points")
    section(g, "2 · four tones: sand on each nodal line")
    spots = []
    for i, tone in enumerate(TONES):
        lines = g.group(nodal, Points=pts, Seed=i * 17 + 3, **dict(zip(MODE_KEYS, tone_values(tone))))
        lines.label = "tone %d: (%d,%d) %+.2f·(%d,%d)" % (i + 1, *tone[0], tone[2], *tone[1])
        si = g.node("GeometryNodeSampleIndex", label=f"spot on tone {i + 1}",
                    props={"data_type": "FLOAT_VECTOR", "domain": "POINT"},
                    Geometry=lines, Value=g.node("GeometryNodeInputPosition"), Index=g.node("GeometryNodeInputIndex"))
        spots.append(g.out(si, "Value"))
    section(g, "3 · loop clock → tone, time in tone")
    tn = g.group(tones)
    note, prev, t_in = g.out(tn, "Tone"), g.out(tn, "Previous"), g.out(tn, "Time in tone")
    a = index_switch(g, "VECTOR", prev, spots, "from: previous tone")
    b = index_switch(g, "VECTOR", note, spots, "to: this tone")
    section(g, "4 · amplitude |f| where the grain starts")
    def amplitude(pos, label):
        w = g.group(mode, Position=pos, **{k: g.out(tn, k) for k in MODE_KEYS})
        w.label = label
        return g.out(g.node("ShaderNodeMapRange", label=label, Value=g.math("ABSOLUTE", g.out(w, "f")),
                            From_Min=0.0, From_Max=AMP_FULL), "Result")
    e0 = amplitude(a, "|f| where the grain starts")
    section(g, "5 · flight path to the new line")
    delay = rnd(g, 0.0, DELAY, 11, label="tone → sand delay")
    fly = g.math("ADD", FLY[0], g.math("MULTIPLY", e0, FLY[1] - FLY[0]))
    s = smooth(g, t_in, delay, g.math("ADD", delay, fly), "flight 0 → 1")
    path = g.vmath("ADD", a, g.vmath("SCALE", g.vmath("SUBTRACT", b, a), scale=s))
    arc = g.math("MULTIPLY", g.math("SINE", g.math("MULTIPLY", s, PI)), e0)
    zig = g.math("MULTIPLY", g.math("SINE", g.math("MULTIPLY", s, TAU)), e0)
    wob = g.vmath("ADD",
                  g.vmath("SCALE", rnd(g, (-WOB, -WOB, 0.0), (WOB, WOB, 0.0), 12, "FLOAT_VECTOR"), scale=arc),
                  g.vmath("SCALE", rnd(g, (-WOB, -WOB, 0.0), (WOB, WOB, 0.0), 18, "FLOAT_VECTOR"), scale=zig))
    wob.label = "random walk, bigger at antinodes"
    walk = g.vmath("ADD", path, wob)
    section(g, "6 · bounce and land")
    e = amplitude(walk, "|f| under the grain now")
    nh = g.math("ADD", 1.0, g.math("FLOOR", g.math("MULTIPLY", e0, 4.99)))
    nh.label = "bounces: 1 near a node … 5 at an antinode"
    bounce = g.math("ABSOLUTE", g.math("SINE", g.math("MULTIPLY", g.math("MULTIPLY", s, nh), PI)))
    hop = g.math("MULTIPLY", g.math("MULTIPLY", bounce, e), rnd(g, 0.55 * HOP_MAX, HOP_MAX, 14, label="hop height"))
    r = rnd(g, R_GRAIN[0], R_GRAIN[1], 15, label="grain radius")
    z = g.math("ADD", g.math("MULTIPLY", r, 0.85), hop)
    px, py, _ = xyz(g, walk)
    placed = g.node("GeometryNodeSetPosition", Geometry=pts, Position=g.vec(px, py, z))
    tint = g.node("GeometryNodeStoreNamedAttribute", label="tint", props={"data_type": "FLOAT", "domain": "POINT"},
                  Geometry=placed, Name="tint", Value=rnd(g, 0.0, 1.0, 16))
    section(g, "7 · grains")
    ico = g.node("GeometryNodeMeshIcoSphere", Radius=1.0, Subdivisions=1)
    grain = pb.set_material(g, g.out(ico, "Mesh"), sand)
    inst = g.node("GeometryNodeInstanceOnPoints", Points=tint, Instance=grain,
                  Rotation=rnd(g, (0.0, 0.0, 0.0), (TAU, TAU, TAU), 17, "FLOAT_VECTOR"),
                  Scale=g.vmath("SCALE", rnd(g, (0.8, 0.8, 0.8), (1.15, 1.15, 1.15), 19, "FLOAT_VECTOR",
                                      label="irregular grain"), scale=r))
    g.output(inst)
    pb.arrange(g.tree)

    # ───────────── black void, camera, light
    sc = bpy.context.scene
    sc.frame_set(1)
    st_ = pb.studio("Chladni", style="void", view="high", lens=100, margin=1.0, focus=["PA_Plate"])
    for o in [o for o in bpy.data.collections["PA_Studio"].objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o, do_unlink=True)
    # seamless black for the camera; a dim warm room only in reflections, so the brass reads as brass
    wt = sc.world.node_tree
    bg = wt.nodes["Background"]
    bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    room = wt.nodes.new("ShaderNodeBackground")
    room.inputs["Color"].default_value = (0.022, 0.016, 0.011, 1.0)
    lp = wt.nodes.new("ShaderNodeLightPath")
    mix = wt.nodes.new("ShaderNodeMixShader")
    wt.links.new(lp.outputs["Is Glossy Ray"], mix.inputs[0])
    wt.links.new(bg.outputs[0], mix.inputs[1])
    wt.links.new(room.outputs[0], mix.inputs[2])
    wo = next(n for n in wt.nodes if n.bl_idname == "ShaderNodeOutputWorld")
    wt.links.new(mix.outputs[0], wo.inputs["Surface"])
    piv = bpy.data.objects["PA_Pivot"]
    piv.location = (0.0, 0.05, 0.0)
    az, el, dist = math.radians(32), math.radians(30), 5.3
    cam_dir = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam = bpy.data.objects["PA_Camera"]
    cam.location = cam_dir * dist
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = piv
    cam.data.dof.aperture_fstop = 1.4             # the far edge and the near corner melt a little

    def card(name, size, energy, loc, color=(1.0, 1.0, 1.0), target=(0.0, 0.0, 0.0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape, ld.size, ld.size_y = "RECTANGLE", size[0], size[1]
        ld.energy, ld.color = energy, color
        lo = bpy.data.objects.new(name, ld)
        bpy.data.collections["PA_Studio"].objects.link(lo)
        lo.location = loc
        lo.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        lo.visible_camera = False
        return lo

    mirror = Vector((-cam_dir.x, -cam_dir.y, cam_dir.z))
    card("PA_Softbox", (6.0, 0.7), 110.0, mirror * 6.0 + Vector((0.0, 1.3, 0.0)), (1.0, 0.93, 0.84))
    card("PA_Rake", (1.2, 2.4), 1100.0, (-4.8, 0.8, 0.55), (1.0, 0.86, 0.70))   # low: long grain shadows
    card("PA_Rim", (2.0, 0.6), 500.0, (3.4, 3.2, 1.4), (0.80, 0.88, 1.0))
    card("PA_Top", (3.0, 3.0), 700.0, (0.0, -0.4, 5.0), (1.0, 0.97, 0.92))   # lights the sand; its mirror image falls off-plate
    sc.view_settings.exposure = 0.0
    pb.turntable("swing", 12)                       # slow ±6° sway, one period per loop
    pb.post(bloom=0.08, threshold=2.0)
    frame_sections()
    # node layout tidied in the UI (labelled frames, real node sizes); see tutorial/README.md
    layout = pb.layout_load(os.path.join(DAY, "nodes_layout.json"))
    pb.output(os.path.join(DAY, "loop.mp4"), "video")
    out = ARGS[ARGS.index("--save-as") + 1] if "--save-as" in ARGS else os.path.join(DAY, "chladni.blend")
    pb.save(out)
    return {"piece": info, "studio": st_, "layout": layout}


def clay(path):
    """White clay copy (Workbench = viewport solid shading) for checking the motion."""
    sc = bpy.context.scene
    keep = sc.render.engine
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.studio_light = "STUDIO", "Default"
    sh.color_type = "MATERIAL"
    sh.show_cavity, sh.cavity_type = True, "BOTH"
    sh.show_shadows = True
    for m in bpy.data.materials:
        m.diffuse_color = {"PA_Brass": (0.42, 0.42, 0.42, 1)}.get(m.name, (0.95, 0.95, 0.95, 1))
    sc.display.render_aa = "8"
    sc.world.color = (0.02, 0.02, 0.02)
    cg = sc.compositing_node_group
    sc.compositing_node_group = None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pb.save(path)
    sc.render.engine, sc.compositing_node_group = keep, cg
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
        fr = int(ARGS[ARGS.index("--still") + 1])
        res["still"] = pb.render_still(os.path.join(DAY, f"_still_{fr:03d}.png"), frame=fr)
    if "--clay" in ARGS:
        res["clay"] = clay(os.path.join(DAY, "clay", "chladni_clay.blend"))
    res["audit"] = pb.audit("Chladni")
    res["describe"] = pb.describe("PA_Sand_GN")
    print("BUILD_RESULT", res)
