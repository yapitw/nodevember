"""Nodevember 2026 · Day 03 · Stitch — v3: kintsugi.

A tea bowl turns on a white sweep, veined with gold. It breaks along exactly those veins (the gold
leaves the edges as a puff of dust, the shards show raw biscuit), hangs apart, and the shards come
home one by one. Each seam locks with a thin line of urushi lacquer; then gold flows down the seams
from the rim until the bowl is whole and golden again.

Bowl: a Cylinder grid (u around, s rim → base) laid onto a filleted chawan profile (outer + inner).
Fracture: 3D Voronoi cells on the bowl (lower cells merged into one anchor piece); a shard id per
face → Split to Instances; crack vertices snapped onto the cell bisector (3 Newton steps through the
noise warp), so shard edges are smooth; Extrude (offset 0) + move the top to the inner profile gives
the inner glaze and the raw crack walls. Seams: the edges between different ids on the unbroken grid,
snapped the same way, become lacquer and gold beads.

Run: Blender -b --factory-startup --python build.py -- [--preview f,f,..] [--still N] [--clay] [--save-as x.blend]
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

DAY = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TAU = 2 * math.pi

FRAMES = 240                       # 8 s @ 30 fps; the bowl turns once per loop
NU, NS = 360, 150                  # grid: around × rim → base
L = 1.7                            # s → height in the fracture space (≈ profile length)
KV = 1.35                          # Voronoi cell density
SEEDV = (17.3, 3.1, 9.7)           # picks the fracture pattern
AMPW, FW = 0.06, 2.2               # crack wiggle (warp of the fracture space)
S_ANCHOR = 0.50                    # cells whose site lies below this s merge into the foot piece
THR = 0.05                         # snap only vertices this close to a bisector (fracture space)

# outer profile (r, z): from the rim down and round the foot ring
OUTER = [(1.00, 1.15), (1.015, 0.98), (1.00, 0.72), (0.90, 0.45), (0.72, 0.25), (0.55, 0.16), (0.48, 0.13),
         (0.47, 0.06), (0.47, 0.0), (0.42, -0.012), (0.37, 0.0), (0.36, 0.06), (0.20, 0.075), (0.0, 0.075)]
BODY = OUTER[:6] + [(0.32, 0.125), (0.12, 0.12), (0.0, 0.12)]   # the same body turning into the well
TH = 0.055                         # wall thickness (inner skin = outer pushed in by TH)
S_SPLIT = 0.6                      # below this s the inner skin stretches over the well
NOSE = 0.07                        # arc length of the rounded lip

# timeline (phase)
B0, B1, GOLD_OFF = 0.05, 0.10, 0.075   # the break; gold gone from the edges by GOLD_OFF
DUST = 0.25                            # dust lifetime
ANCHOR_ORDER = 0.12
O0, OSPAN = 0.17, 0.30                 # shards come home from O0 to O0+OSPAN (first ones spaced widest)
SEW_A, SEW_B = 0.16, 0.08              # flight time of the first … last shard (slow, then quicker)
GLUE = 0.06                            # urushi wiped on along a shard's broken edge before it flies home
CONTACT = 0.80                         # fraction of the flight when the faces meet (press, squeeze-out)
PRESS = 0.04                           # press-in overshoot (fraction of the way out)
RG, SQ = 0.022, 3.5                    # glue bead radius on the broken edge; squeeze-out swell ×
G0, GSPAN, GRAMP = 0.62, 0.24, 0.035   # gold flows from the rim (G0) to the base (G0+GSPAN)
GR, LR = 0.018, 0.0055                 # gold bead / lacquer radius
GOLD = (0.85, 0.60, 0.26, 1.0)         # muted, aged gold
GOLD_K = 0.10                          # gold bead height / width: a painted-on, nearly flush line


# ───────────────────────────────────────────────────────── node groups

F, V, G = "NodeSocketFloat", "NodeSocketVector", "NodeSocketGeometry"


def new_group(name, ins, outs):
    old = bpy.data.node_groups.get(name)
    if old:
        bpy.data.node_groups.remove(old)
    t = bpy.data.node_groups.new(name, "GeometryNodeTree")
    for n, k in ins:
        t.interface.new_socket(n, in_out="INPUT", socket_type=k)
    for n, k in outs:
        t.interface.new_socket(n, in_out="OUTPUT", socket_type=k)
    g = pb.Graph(t)
    return t, g, *g.group_io()


# labelled, coloured frames: every node created after section() belongs to it (see tutorial/README.md)
SECTIONS = {}
PALETTE = [(0.30, 0.24, 0.10), (0.12, 0.25, 0.16), (0.13, 0.18, 0.32), (0.32, 0.13, 0.12), (0.22, 0.15, 0.30),
           (0.10, 0.25, 0.27), (0.28, 0.19, 0.08), (0.18, 0.22, 0.12), (0.26, 0.12, 0.22), (0.14, 0.20, 0.26),
           (0.27, 0.20, 0.14), (0.20, 0.20, 0.20)]


def section(g, label):
    marks = SECTIONS.setdefault(g.tree, [])
    marks.append((label, PALETTE[len(marks) % len(PALETTE)], len(g.tree.nodes)))


def frame_sections():
    for tree, marks in SECTIONS.items():
        nodes = list(tree.nodes)
        for i, (label, color, start) in enumerate(marks):
            end = marks[i + 1][2] if i + 1 < len(marks) else len(nodes)
            fr = tree.nodes.new("NodeFrame")
            fr.label, fr.label_size, fr.shrink = label, 56, True
            fr.use_custom_color, fr.color = True, color
            for n in nodes[start:end]:
                if n.bl_idname not in ("NodeGroupInput", "NodeGroupOutput", "NodeFrame"):
                    n.parent = fr
        for n in nodes:                       # small plumbing nodes collapse to one line (title = what they read)
            if n.bl_idname in ("GeometryNodeInputNamedAttribute", "ShaderNodeAttribute"):
                key = "Name" if "Name" in n.inputs else None
                n.label = n.label or ("“%s”" % (n.inputs["Name"].default_value if key else n.attribute_name))
                n.hide = True
            elif n.bl_idname in ("GeometryNodeInputPosition", "ShaderNodeSeparateXYZ", "GeometryNodeInputIndex",
                                 "GeometryNodeSplineParameter", "GeometryNodeSplineLength",
                                 "GeometryNodeInputMeshEdgeNeighbors", "ShaderNodeNewGeometry", "ShaderNodeTexCoord"):
                n.hide = True


def clamp01(g, op, a, b):
    return g.node("ShaderNodeMath", props={"operation": op, "use_clamp": True}, ins={0: a, 1: b})


def smooth(g, value, lo, hi, label=None, to=(0.0, 1.0)):
    n = g.node("ShaderNodeMapRange", label=label, props={"interpolation_type": "SMOOTHSTEP"}, Value=value,
               From_Min=lo, From_Max=hi, To_Min=to[0], To_Max=to[1])
    return g.out(n, "Result")


def xyz(g, v):
    s = g.node("ShaderNodeSeparateXYZ", Vector=v)
    return g.out(s, "X"), g.out(s, "Y"), g.out(s, "Z")


def index_switch(g, kind, idx, values, label):
    n = g.node("GeometryNodeIndexSwitch", label=label, props={"data_type": kind})
    while len(n.index_switch_items) < len(values):
        n.index_switch_items.new()
    g.link(idx, n, b_key="Index")
    for i, v in enumerate(values):
        n.inputs[i + 1].default_value = v
    return n


def profile_curve(g, pts, label):
    """Control cage (r, z) → a smooth cubic NURBS (tangent and curvature continuous); end points tripled so
    the curve starts and ends on them."""
    pts = [pts[0]] * 2 + list(pts) + [pts[-1]] * 2
    line = g.node("GeometryNodeMeshLine", label=label, Count=len(pts))
    put = g.node("GeometryNodeSetPosition", Geometry=line,
                 Position=index_switch(g, "VECTOR", g.node("GeometryNodeInputIndex"),
                                       [(r, 0.0, z) for r, z in pts], label + " cage (r, z)"))
    cur = g.node("GeometryNodeCurveSplineType", label="cubic NURBS", props={"spline_type": "NURBS"},
                 Curve=g.node("GeometryNodeMeshToCurve", Mesh=put))
    return g.node("GeometryNodeSetSplineResolution", Geometry=cur, Resolution=48)


def chawan_group():
    """(u, s, inner?, lift along the surface normal) → point on the tea bowl.
    Outer skin: one smooth NURBS from the lip round the foot ring to the axis. Inner skin: the body curve (the
    same cage, but turning into the well instead of the foot) pushed in by the wall thickness along its normal.
    Both are sampled by arc length from the lip, so where cracks run (upper body) the two match point for point.
    At the lip the two skins close in a round nose."""
    t, g, gi, go = new_group("PA_Chawan", (("U", F), ("S", F), ("Inner", F), ("Lift", F)), (("Position", V),))
    s, inner, lift = gi.outputs["S"], gi.outputs["Inner"], gi.outputs["Lift"]
    section(g, "a · Two smooth profiles")
    outer = profile_curve(g, OUTER, "outer profile")
    body = profile_curve(g, BODY, "body profile (into the well)")
    section(g, "b · Sample both by arc length from the lip")
    lo = g.out(g.node("GeometryNodeCurveLength", Curve=outer), "Length")
    lb = g.out(g.node("GeometryNodeCurveLength", Curve=body), "Length")

    def sample(curve, length):
        smp = g.node("GeometryNodeSampleCurve", label="along the profile", props={"mode": "LENGTH"},
                     Curves=curve, Length=length)
        tx, _, tz = xyz(g, g.out(smp, "Tangent"))
        return g.out(smp, "Position"), g.vec(g.math("MULTIPLY", tz, -1.0), 0.0, tx)   # point, outward normal

    so = g.math("MULTIPLY", s, lo)
    so.label = "arc length from the lip"
    k = clamp01(g, "DIVIDE", g.math("SUBTRACT", s, S_SPLIT), 1.0 - S_SPLIT)
    si = g.math("ADD", g.math("MINIMUM", so, g.math("MULTIPLY", lo, S_SPLIT)),
                g.math("MULTIPLY", k, g.math("SUBTRACT", lb, g.math("MULTIPLY", lo, S_SPLIT))))
    si.label = "inner: same length above S_SPLIT, then stretched to reach the axis"
    po, no = sample(outer, so)
    pi, ni = sample(body, si)
    section(g, "c · Round lip, wall thickness, around the axis")
    q = clamp01(g, "DIVIDE", so, NOSE)
    h = g.math("MAXIMUM", g.math("MULTIPLY", g.math("SQRT", g.math("SUBTRACT", 1.0, g.math(
        "POWER", g.math("SUBTRACT", 1.0, q), 2.0))), TH * 0.5), 0.0015)
    h.label = "half thickness: round nose at the lip"
    o_off = g.math("ADD", lift, g.math("SUBTRACT", h, TH * 0.5))
    i_off = g.math("ADD", lift, g.math("ADD", h, TH * 0.5))
    pos_o = g.vmath("ADD", po, g.vmath("SCALE", no, scale=o_off))
    pos_i = g.vmath("SUBTRACT", pi, g.vmath("SCALE", ni, scale=i_off))
    rz = g.out(g.node("ShaderNodeMix", props={"data_type": "VECTOR"}, Factor=inner, A=pos_o, B=pos_i), "Result")
    r, _, z = xyz(g, rz)
    phi = g.math("MULTIPLY", gi.outputs["U"], TAU)
    pos = g.vec(g.math("MULTIPLY", r, g.math("COSINE", phi)), g.math("MULTIPLY", r, g.math("SINE", phi)), z)
    g.link(pos, go, b_key="Position")
    pb.arrange(t)
    return t


def fracture_space_group():
    """Cylinder-grid point → fracture space q (warped, scaled, seeded)."""
    t, g, gi, go = new_group("PA_FractureSpace", (("V", V),), (("Q", V),))
    n = g.node("ShaderNodeTexNoise", label="crack wiggle", props={"noise_dimensions": "3D"},
               Vector=g.vmath("SCALE", gi.outputs["V"], scale=FW), Scale=1.0, Detail=4.0, Roughness=0.55)
    w = g.vmath("SCALE", g.vmath("SUBTRACT", g.out(n, "Color"), (0.5, 0.5, 0.5)), scale=2 * AMPW)
    q = g.vmath("ADD", g.vmath("SCALE", g.vmath("ADD", gi.outputs["V"], w), scale=KV), SEEDV)
    g.link(q, go, b_key="Q")
    pb.arrange(t)
    return t


def site_group():
    """Voronoi site → its shard data: anchor?, angle around, height."""
    t, g, gi, go = new_group("PA_SiteInfo", (("Site", V),), (("Anchor", F), ("Order", F), ("Phi", F), ("S", F),
                                                                  ("Sew", F)))
    sx, sy, sz = xyz(g, g.vmath("SUBTRACT", gi.outputs["Site"], SEEDV))
    phi = g.math("ARCTAN2", sy, sx)
    s = g.math("DIVIDE", sz, KV * L)
    anchor = g.math("GREATER_THAN", s, S_ANCHOR)
    anchor.label = "low cells: the foot piece"
    turn = g.math("FRACT", g.math("ADD", g.math("DIVIDE", phi, TAU), 0.15))
    tf = g.math("SUBTRACT", 1.0, g.math("POWER", g.math("SUBTRACT", 1.0, turn), 1.7))
    tf.label = "first ones spaced widest"
    order = g.node("ShaderNodeMix", label="home in turn, around the bowl (foot piece first)", Factor=anchor,
                   A=g.math("MULTIPLY_ADD", tf, OSPAN, O0), B=ANCHOR_ORDER)
    sew = g.math("MULTIPLY_ADD", tf, SEW_B - SEW_A, SEW_A)
    sew.label = "flight time"
    g.link(anchor, go, b_key="Anchor")
    g.link(g.out(order, "Result"), go, b_key="Order")
    g.link(sew, go, b_key="Sew")
    g.link(phi, go, b_key="Phi")
    g.link(s, go, b_key="S")
    pb.arrange(t)
    return t


def cell_group(fs, si):
    """Shard id (0 = foot piece) and Voronoi site for a point of the grid."""
    t, g, gi, go = new_group("PA_Cell", (("V", V),), (("Shard", F), ("Site", V)))
    vor = g.node("ShaderNodeTexVoronoi", label="fracture cells", props={"voronoi_dimensions": "3D", "feature": "F1"},
                 Vector=g.group(fs, V=gi.outputs["V"]), Scale=1.0, Randomness=1.0)
    site = g.out(vor, "Position")
    cid = g.math("ADD", g.math("FLOOR", g.math("MULTIPLY", xyz(g, g.out(vor, "Color"))[0], 997.0)), 1.0)
    anchor = g.out(g.group(si, Site=site), "Anchor")
    g.link(g.math("MULTIPLY", cid, g.math("SUBTRACT", 1.0, anchor)), go, b_key="Shard")
    g.link(site, go, b_key="Site")
    pb.arrange(t)
    return t


def snap_group(fs):
    """Move a point onto the bisector of its two nearest cells (3 Newton steps through the warp)."""
    t, g, gi, go = new_group("PA_SnapToCrack", (("V", V), ("Active", F), ("Keep S", F)),
                             (("V", V), ("Site A", V), ("Site B", V)))
    v = gi.outputs["V"]
    s1 = s2 = None
    for it in range(3):
        section(g, f"Newton step {it + 1}")
        q = g.group(fs, V=v)
        f1 = g.node("ShaderNodeTexVoronoi", label=f"nearest cell ({it + 1})",
                    props={"voronoi_dimensions": "3D", "feature": "F1"}, Vector=q, Scale=1.0, Randomness=1.0)
        f2 = g.node("ShaderNodeTexVoronoi", label=f"second cell ({it + 1})",
                    props={"voronoi_dimensions": "3D", "feature": "F2"}, Vector=q, Scale=1.0, Randomness=1.0)
        s1, s2 = g.out(f1, "Position"), g.out(f2, "Position")
        n = g.vmath("SUBTRACT", s2, s1)
        c = g.math("MULTIPLY", g.math("SUBTRACT", g.out(g.vmath("DOT_PRODUCT", s2, s2), "Value"),
                                      g.out(g.vmath("DOT_PRODUCT", s1, s1), "Value")), 0.5)
        d = g.math("DIVIDE", g.math("SUBTRACT", g.out(g.vmath("DOT_PRODUCT", q, n), "Value"), c),
                   g.out(g.vmath("LENGTH", n), "Value"))
        d.label = "signed distance to the bisector"
        act = g.math("MULTIPLY", gi.outputs["Active"], g.math("LESS_THAN", g.math("ABSOLUTE", d), THR))
        step = g.vmath("SCALE", g.vmath("NORMALIZE", n), scale=g.math("MULTIPLY", g.math("DIVIDE", d, -KV), act))
        sx, sy, sz = xyz(g, step)
        step = g.vec(sx, sy, g.math("MULTIPLY", sz, g.math("SUBTRACT", 1.0, gi.outputs["Keep S"])))
        v = g.vmath("ADD", v, step)
    g.link(v, go, b_key="V")
    g.link(s1, go, b_key="Site A")
    g.link(s2, go, b_key="Site B")
    pb.arrange(t)
    return t


def motion_group(clock, si):
    """Rigid motion of one shard: burst apart at the break, hover, come home in turn."""
    t, g, gi, go = new_group("PA_ShardMotion", (("Position", V), ("Site", V)), (("Position", V),))
    section(g, "a · Whose turn, and when")
    phase = g.out(g.group(clock), "Phase")
    info = g.group(si, Site=gi.outputs["Site"])
    order, phi, s = g.out(info, "Order"), g.out(info, "Phi"), g.out(info, "S")
    moving = g.math("SUBTRACT", 1.0, g.out(info, "Anchor"))
    burst = g.node("ShaderNodeMapRange", label="the break", props={"interpolation_type": "SMOOTHERSTEP"},
                   Value=phase, From_Min=B0, From_Max=B1)
    section(g, "b · Flight: ease in, crawl, press")
    x = clamp01(g, "DIVIDE", g.math("SUBTRACT", phase, order), g.out(info, "Sew"))
    x.label = "flight 0…1"
    rem = g.math("MULTIPLY", g.math("POWER", g.math("SUBTRACT", 1.0, x), 4.0), g.math("MULTIPLY_ADD", x, 4.0, 1.0))
    rem.label = "way left: eases in, crawls the last mm"
    pr = clamp01(g, "DIVIDE", g.math("SUBTRACT", x, CONTACT - 0.1), 1.1 - CONTACT)
    press = g.math("MULTIPLY", g.math("POWER", g.math("SINE", g.math("MULTIPLY", pr, math.pi)), 2.0), PRESS)
    press.label = "press into the seam, settle"
    o = g.math("MULTIPLY", g.math("MULTIPLY", g.out(burst, "Result"), g.math("SUBTRACT", rem, press)), moving)
    o.label = "open (0 whole … 1 apart, <0 pressed)"
    section(g, "c · Out, tumble and hover")
    away = g.vec(g.math("MULTIPLY", g.math("COSINE", phi), 0.07), g.math("MULTIPLY", g.math("SINE", phi), 0.07),
                 g.math("MULTIPLY_ADD", g.math("SUBTRACT", 1.0, s), 0.07, 0.05))
    away.label = "out from where it was, and up"
    snapped_site = g.node("ShaderNodeVectorMath", label="snap (face→point averaging leaves 1-ulp noise)",
                          props={"operation": "SNAP"}, ins={0: gi.outputs["Site"], 1: (0.001, 0.001, 0.001)})
    rnd = g.node("ShaderNodeTexWhiteNoise", props={"noise_dimensions": "3D"}, Vector=snapped_site)
    axis = g.vmath("SUBTRACT", g.out(rnd, "Color"), (0.5, 0.5, 0.5))
    rot = g.node("ShaderNodeVectorRotate", label="tumble", props={"rotation_type": "AXIS_ANGLE"},
                 Vector=gi.outputs["Position"], Center=(0.0, 0.0, 0.55), Axis=axis,
                 Angle=g.math("MULTIPLY", o, 0.16))
    bob = g.math("MULTIPLY", g.math("SINE", g.math("MULTIPLY", g.math("ADD", g.math("MULTIPLY", phase, 2.0),
                                                                      g.out(rnd, "Value")), TAU)), 0.02)
    bob.label = "hover (2 per loop)"
    pos = g.vmath("ADD", rot, g.vmath("SCALE", g.vmath("ADD", away, g.vec(0.0, 0.0, bob)), scale=o))
    g.link(pos, go, b_key="Position")
    pb.arrange(t)
    return t


# ───────────────────────────────────────────────────────── materials

def shader(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    g = pb.Graph(m.node_tree)
    return m, g, g.node("ShaderNodeOutputMaterial")


def glaze_material():
    """Old cream glaze: mottled, iron-speckled, crazed and tea-stained (more in the well than outside), worn at
    the lip; the foot ring is raw clay with grime where it meets the body."""
    m, g, out = shader("PA_CreamGlaze")

    def mix(f, a, b):
        return g.out(g.node("ShaderNodeMix", props={"data_type": "RGBA"}, Factor=f, A=a, B=b), "Result")

    section(g, "a · Where am I: rest position, height, inside or out")
    rest = g.out(g.node("ShaderNodeAttribute", label="rest position (sticks to the shard)",
                        props={"attribute_name": "rest"}), "Vector")
    s = g.out(g.node("ShaderNodeSeparateXYZ", Vector=g.out(g.node("ShaderNodeAttribute",
                                                                     props={"attribute_name": "us"}), "Vector")), "Y")
    rx, ry, rz = xyz(g, rest)
    geo = g.node("ShaderNodeNewGeometry")
    px, py, _ = xyz(g, g.out(geo, "Position"))
    radial = g.vmath("NORMALIZE", g.vec(px, py, 0.0))
    facing = g.out(g.vmath("DOT_PRODUCT", g.out(geo, "Normal"), radial), "Value")
    inside = g.node("ShaderNodeMapRange", label="inside the bowl", Value=facing, From_Min=0.15, From_Max=-0.15)
    inside = g.out(inside, "Result")

    section(g, "b · Uneven cream glaze")
    # uneven glaze: warmer and cooler patches
    drift = g.node("ShaderNodeTexNoise", label="glaze thickness drift", Vector=rest, Scale=2.5, Detail=3.0)
    mott = g.node("ShaderNodeTexNoise", label="warm / cool mottling", Vector=rest, Scale=6.0, Detail=4.0)
    col = mix(g.math("MULTIPLY", g.out(drift, "Factor"), 0.5), (0.84, 0.77, 0.63, 1.0), (0.79, 0.71, 0.56, 1.0))
    col = mix(smooth(g, g.out(mott, "Factor"), 0.42, 0.62, to=(0.0, 0.35)), col, (0.80, 0.78, 0.71, 1.0))
    pool = g.node("ShaderNodeMapRange", label="grey-blue pools toward the well", props={"interpolation_type": "SMOOTHSTEP"},
                  Value=s, From_Min=0.35, From_Max=0.95, To_Min=0.0, To_Max=0.45)
    col = mix(g.math("MULTIPLY", g.out(pool, "Result"), inside), col, (0.62, 0.68, 0.70, 1.0))

    section(g, "c · Crazing and tea stains")
    # crazing (kannyu): two scales of hairline cells, tea-stained; denser and darker toward the well
    warp = g.node("ShaderNodeTexNoise", Vector=rest, Scale=4.0)
    cv = g.vmath("ADD", rest, g.vmath("SCALE", g.vmath("SUBTRACT", g.out(warp, "Color"), (0.5, 0.5, 0.5)), scale=0.06))
    craze = None
    for scale, w, label in ((7.0, 0.018, "crazing, large cells"), (19.0, 0.03, "crazing, fine cells")):
        v = g.node("ShaderNodeTexVoronoi", label=label, props={"voronoi_dimensions": "3D", "feature": "DISTANCE_TO_EDGE"},
                   Vector=cv, Scale=scale)
        line = smooth(g, g.out(v, "Distance"), w, 0.0)
        craze = line if craze is None else g.math("MAXIMUM", craze, g.math("MULTIPLY", line, smooth(g, s, 0.3, 0.8)))
    stain = g.math("MULTIPLY", craze, g.math("ADD", g.math("MULTIPLY", inside, smooth(g, s, 0.1, 0.8, to=(0.30, 0.65))),
                                              g.math("MULTIPLY", g.math("SUBTRACT", 1.0, inside), 0.22)))
    stain.label = "tea in the crazing"
    col = mix(stain, col, (0.42, 0.33, 0.24, 1.0))
    # a very soft tea ring in the well
    rr = g.out(g.vmath("LENGTH", g.vec(rx, ry, 0.0)), "Value")
    ring = g.math("MULTIPLY", g.math("EXPONENT", g.math("MULTIPLY", g.math("POWER", g.math(
        "DIVIDE", g.math("SUBTRACT", rr, 0.36), 0.035), 2.0), -1.0)), g.math("MULTIPLY", inside, 0.10))
    col = mix(ring, col, (0.55, 0.42, 0.28, 1.0))

    section(g, "d · Iron speckles and pinholes")
    # iron speckles and a few pinholes
    for scale, size, keep in ((22.0, 0.17, 0.70), (60.0, 0.18, 0.78), (8.0, 0.09, 0.94)):
        v = g.node("ShaderNodeTexVoronoi", label=f"iron speckles ×{scale:g}", props={"voronoi_dimensions": "3D"},
                   Vector=rest, Scale=scale)
        gate = g.math("GREATER_THAN", g.out(g.node("ShaderNodeSeparateXYZ", Vector=g.out(v, "Color")), "X"), keep)
        n = g.node("ShaderNodeTexNoise", Vector=rest, Scale=9.0)
        r = g.math("MULTIPLY_ADD", g.out(n, "Factor"), size, size * 0.2)
        dot = g.math("MULTIPLY", g.math("LESS_THAN", g.out(v, "Distance"), r), gate)
        col = mix(dot, col, (0.12, 0.065, 0.03, 1.0))
    ph = g.node("ShaderNodeTexVoronoi", label="pinholes", props={"voronoi_dimensions": "3D"}, Vector=rest, Scale=45.0)
    pin = g.math("MULTIPLY", g.math("LESS_THAN", g.out(ph, "Distance"), 0.07),
                 g.math("GREATER_THAN", xyz(g, g.out(ph, "Color"))[1], 0.93))
    col = mix(g.math("MULTIPLY", pin, 0.6), col, (0.50, 0.45, 0.38, 1.0))

    section(g, "e · Worn lip, glossy coat")
    # lip: glaze thins to a brown iron edge, worn matte
    lip = g.node("ShaderNodeMapRange", label="iron edge at the lip", Value=s, From_Min=0.008, From_Max=0.035,
                 To_Min=0.8, To_Max=0.0)
    col = mix(g.out(lip, "Result"), col, (0.38, 0.24, 0.13, 1.0))
    wear = g.math("ADD", smooth(g, s, 0.05, 0.0, to=(0.0, 0.25)),
                  g.math("MULTIPLY", g.out(g.node("ShaderNodeTexNoise", Vector=rest, Scale=12.0), "Factor"), 0.06))
    wear.label = "worn: rougher at the lip"
    bsdf = g.node("ShaderNodeBsdfPrincipled", Base_Color=col, Roughness=g.math("ADD", wear, 0.12))
    for k, v in (("Coat Weight", 1.0), ("Coat IOR", 1.52), ("Subsurface Weight", 0.15), ("Subsurface Scale", 0.02)):
        bsdf.inputs[k].default_value = v
    g.link(g.math("ADD", g.math("MULTIPLY", wear, 0.8), 0.02), bsdf, b_key="Coat Roughness")

    section(g, "f · Raw foot ring")
    # foot ring: raw clay, grime where it meets the body
    foot = smooth(g, rz, 0.165, 0.135, "foot ring (unglazed)")
    grime = g.math("MULTIPLY", g.math("EXPONENT", g.math("MULTIPLY", g.math("POWER", g.math(
        "DIVIDE", g.math("SUBTRACT", rz, 0.135), 0.02), 2.0), -1.0)),
        g.math("MULTIPLY_ADD", g.out(g.node("ShaderNodeTexNoise", Vector=rest, Scale=14.0), "Factor"), 0.5, 0.25))
    clay_col = mix(g.out(g.node("ShaderNodeTexNoise", Vector=rest, Scale=30.0), "Factor"),
                   (0.60, 0.46, 0.34, 1.0), (0.66, 0.52, 0.39, 1.0))
    clay_col = mix(grime, clay_col, (0.30, 0.23, 0.17, 1.0))
    clay = g.node("ShaderNodeBsdfPrincipled", label="raw clay", Base_Color=clay_col, Roughness=0.85)
    body = g.node("ShaderNodeMixShader", ins={0: foot, 1: bsdf, 2: clay})

    section(g, "g · Gold lip")
    # a thin gold lip over the rounded rim
    lipgold = g.math("LESS_THAN", s, 0.008)
    lipgold.label = "gold lip"
    gold = g.node("ShaderNodeBsdfPrincipled", Base_Color=GOLD, Metallic=1.0, Roughness=0.35)
    mixs = g.node("ShaderNodeMixShader", ins={0: lipgold, 1: body, 2: gold})
    g.link(mixs, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def gold_material():
    """Satin warm gold with a faint brushed variation."""
    m, g, out = shader("PA_Gold")
    tc = g.out(g.node("ShaderNodeTexCoord"), "Object")
    brush = g.node("ShaderNodeTexNoise", label="brushed", Vector=tc, Scale=30.0)
    rough = g.math("MULTIPLY_ADD", g.out(brush, "Factor"), 0.08, 0.31)
    bsdf = g.node("ShaderNodeBsdfPrincipled", Base_Color=GOLD, Metallic=1.0, Roughness=rough)
    g.link(bsdf, out, b_key="Surface")
    pb.arrange(m.node_tree)
    return m


def materials():
    glaze = glaze_material()
    biscuit = pb.material("Biscuit", "matte", color=(0.74, 0.62, 0.49), roughness=0.85)
    gold = gold_material()
    urushi = pb.material("Urushi", "matte", color=(0.035, 0.014, 0.008), roughness=0.2, coat=0.8)
    return glaze, biscuit, gold, urushi


# ───────────────────────────────────────────────────────── build

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    info = pb.piece("Kintsugi", aspect="1:1", width=1080, frames=FRAMES, engine="CYCLES", samples=96)
    clock = pb.loop_clock(FRAMES)
    chawan, fs = chawan_group(), fracture_space_group()
    si = site_group()
    cell, snap, move = cell_group(fs, si), snap_group(fs), motion_group(clock, si)
    glaze, biscuit, gold, urushi = materials()

    ob, g = pb.gn_object("Bowl", "Kintsugi")
    section(g, "1 · Loop clock")
    phase = g.out(g.group(clock), "Phase")

    def attr(name, kind="FLOAT"):
        return g.out(g.node("GeometryNodeInputNamedAttribute", props={"data_type": kind}, Name=name), "Attribute")

    def store(geo, name, value, kind="FLOAT", domain="POINT", label=None):
        return g.node("GeometryNodeStoreNamedAttribute", label=label or f"keep {name}",
                      props={"data_type": kind, "domain": domain}, Geometry=geo, Name=name, Value=value)

    def embed():
        x, y, z = xyz(g, g.node("GeometryNodeInputPosition"))
        return g.vec(x, y, g.math("MULTIPLY", g.math("SUBTRACT", 0.5, z), L))

    def unembed(v):
        x, y, z = xyz(g, v)
        xy = g.vmath("NORMALIZE", g.vec(x, y, 0.0))
        xx, yy, _ = xyz(g, xy)
        return g.vec(xx, yy, g.math("SUBTRACT", 0.5, g.math("DIVIDE", z, L)))

    def us_of_position():
        x, y, z = xyz(g, g.node("GeometryNodeInputPosition"))
        return g.vec(g.math("FRACT", g.math("DIVIDE", g.math("ARCTAN2", y, x), TAU)), g.math("SUBTRACT", 0.5, z), 0.0)

    def on_bowl(inner, lift, label=None):
        u, s, _ = xyz(g, attr("us", "FLOAT_VECTOR"))
        n = g.group(chawan, U=u, S=s, Inner=inner, Lift=lift)
        if label:
            n.label = label
        return n

    section(g, "2 · Grid and fracture cells")
    # ───────────── the unbroken grid, with a fracture cell per face
    cyl = g.node("GeometryNodeMeshCylinder", label="(u, s) sheet", props={"fill_type": "NONE"}, Vertices=NU,
                 Side_Segments=NS, Radius=1.0, Depth=1.0)
    cel = g.group(cell, V=embed())
    grid = store(g.out(cyl, "Mesh"), "shard", g.out(cel, "Shard"), domain="FACE", label="shard id per face")
    grid = store(grid, "shard2", g.math("MULTIPLY", g.out(cel, "Shard"), g.out(cel, "Shard")), domain="FACE",
                 label="id² (to spot seams)")
    grid = store(grid, "site", g.out(cel, "Site"), kind="FLOAT_VECTOR", domain="FACE", label="cell site per face")

    section(g, "3 · Shards: split, snap the edges")
    # ───────────── shards
    pieces = g.node("GeometryNodeSplitToInstances", label="break into shards", props={"domain": "FACE"},
                    Geometry=grid, Group_ID=attr("shard"))
    apart = g.node("GeometryNodeRealizeInstances", Geometry=g.out(pieces, "Instances"))
    edge_n = g.node("GeometryNodeInputMeshEdgeNeighbors")
    bnd = store(apart, "bnd", g.math("COMPARE", g.out(edge_n, "Face Count"), 1.0, 0.1), domain="EDGE",
                label="open edges")
    s_now = xyz(g, g.node("GeometryNodeInputPosition"))[2]
    rim = g.math("GREATER_THAN", s_now, 0.499)
    rim.label = "rim row keeps its height"
    snp = g.group(snap, V=embed(), Active=g.math("GREATER_THAN", attr("bnd"), 0.01), Keep_S=rim)
    snapped = g.node("GeometryNodeSetPosition", label="crack edges onto the bisector", Geometry=bnd,
                     Position=unembed(g.out(snp, "V")))
    sh_us = store(store(snapped, "us", us_of_position(), kind="FLOAT_VECTOR"), "psite", attr("site", "FLOAT_VECTOR"),
                  kind="FLOAT_VECTOR", label="site per point (walls inherit it)")
    section(g, "4 · Solid walls on the chawan")
    outer = g.node("GeometryNodeSetPosition", label="outer glaze", Geometry=sh_us, Position=on_bowl(0.0, 0.0))
    ext = g.node("GeometryNodeExtrudeMesh", label="wall", props={"mode": "FACES"}, Mesh=outer, Offset_Scale=0.0,
                         Individual=False)
    top, sides = g.out(ext, "Top"), g.out(ext, "Side")
    inner = g.node("GeometryNodeSetPosition", label="inner glaze", Geometry=g.out(ext, "Mesh"), Selection=top,
                   Position=on_bowl(1.0, 0.0))
    inner_f = g.node("GeometryNodeFlipFaces", Mesh=inner, Selection=top)
    m_in = g.node("GeometryNodeSetMaterial", Geometry=inner_f, Material=glaze)
    cs = xyz(g, attr("us", "FLOAT_VECTOR"))[1]
    on_rim = g.math("LESS_THAN", cs, 0.002)
    m_wall = g.node("GeometryNodeSetMaterial", label="raw biscuit in the cracks", Geometry=m_in,
                    Selection=g.math("MULTIPLY", sides, g.math("SUBTRACT", 1.0, on_rim)), Material=biscuit)
    m_lip = g.node("GeometryNodeSetMaterial", label="lip (glaze shader gilds it)", Geometry=m_wall,
                   Selection=g.math("MULTIPLY", sides, on_rim), Material=glaze)
    flat = g.node("GeometryNodeSetShadeSmooth", label="crack walls flat, lip rounded", Geometry=m_lip,
                  Selection=g.math("MULTIPLY", sides, g.math("SUBTRACT", 1.0, on_rim)), Shade_Smooth=False)
    body = g.node("GeometryNodeJoinGeometry", label="solid shards")
    g.link(g.node("GeometryNodeSetMaterial", Geometry=outer, Material=glaze), body, b_key="Geometry")
    g.link(flat, body, b_key="Geometry")
    section(g, "5 · Makienaoshi: the lost chip")
    # makienaoshi: a lost chip at the lip, raw while broken, filled with gold once the gold has flowed
    cu, cs_, _ = xyz(g, attr("us", "FLOAT_VECTOR"))
    chip_c = g.vec(0.0, -1.0, 0.0)
    chip_c.label = "chip centre (u, s) — set after a first evaluation"
    ccu, ccs, _ = xyz(g, chip_c)
    du = g.math("SUBTRACT", g.math("FRACT", g.math("ADD", g.math("SUBTRACT", cu, ccu), 0.5)), 0.5)
    dist = g.out(g.vmath("LENGTH", g.vec(g.math("MULTIPLY", du, TAU * 0.95), g.math("MULTIPLY", g.math(
        "SUBTRACT", cs_, ccs), 1.6), 0.0)), "Value")
    cn = g.node("ShaderNodeTexNoise", props={"noise_dimensions": "3D"}, Vector=g.node("GeometryNodeInputPosition"),
                Scale=9.0)
    chip = g.math("LESS_THAN", dist, g.math("MULTIPLY_ADD", g.out(cn, "Factor"), 0.10, 0.04))
    chip.label = "the lost chip"
    gilt = g.math("MAXIMUM", g.math("LESS_THAN", phase, GOLD_OFF), g.math("GREATER_THAN", phase, G0 + 0.05))
    chip_raw = g.node("GeometryNodeSetMaterial", Geometry=body, Selection=chip, Material=biscuit)
    chip_g = g.node("GeometryNodeSetMaterial", label="filled with gold", Geometry=chip_raw,
                    Selection=g.math("MULTIPLY", chip, gilt), Material=gold)
    section(g, "6 · Fly apart, come home")
    rest = store(chip_g, "rest", g.node("GeometryNodeInputPosition"), kind="FLOAT_VECTOR",
                 label="rest position (speckles stick)")
    moved = g.node("GeometryNodeSetPosition", label="fly apart, come home", Geometry=rest,
                   Position=g.group(move, Position=g.node("GeometryNodeInputPosition"),
                                    Site=attr("psite", "FLOAT_VECTOR")))

    def tube(curve, scale, radius, res, label):
        """Curve → round bead whose thickness follows `scale`; parts with no thickness are dropped."""
        c = store(curve, "tube_k", scale, label=f"{label} thickness")
        m = g.node("GeometryNodeCurveToMesh", label=label, Fill_Caps=True, Curve=c, Scale=attr("tube_k"),
                   Profile_Curve=g.node("GeometryNodeCurvePrimitiveCircle", Resolution=res, Radius=radius))
        return g.node("GeometryNodeDeleteGeometry", label=f"{label}: drop the empty parts", props={"domain": "POINT"},
                      Geometry=m, Selection=g.math("LESS_THAN", attr("tube_k"), 1e-4))

    section(g, "7 · Glue: urushi on the broken edge")
    # ───────────── glue: urushi wiped along each flying shard's broken edge, riding with it
    gcs = xyz(g, attr("us", "FLOAT_VECTOR"))[1]
    g_edges = g.node("GeometryNodeDeleteGeometry", label="broken edges (not the lip)", props={"domain": "EDGE"},
                     Geometry=sh_us, Selection=g.math("MAXIMUM", g.math("LESS_THAN", attr("bnd"), 0.01),
                                                      g.math("LESS_THAN", gcs, 0.002)))
    g_c = g.node("GeometryNodeSetPosition", label="mid-wall of the broken face",
                 Geometry=g.node("GeometryNodeMeshToCurve", Mesh=g_edges), Position=on_bowl(0.5, 0.0))
    ginfo = g.group(si, Site=attr("psite", "FLOAT_VECTOR"))
    g_ord, g_sew = g.out(ginfo, "Order"), g.out(ginfo, "Sew")
    g_t0 = g.math("MULTIPLY_ADD", g.out(g.node("GeometryNodeSplineParameter"), "Factor"), GLUE * 0.75,
                  g.math("SUBTRACT", g_ord, GLUE))
    g_t0.label = "brush stroke from one end of the edge to the other"
    g_on = smooth(g, phase, g_t0, g.math("ADD", g_t0, GLUE * 0.25), "glue wiped on")
    g_off = smooth(g, phase, g.math("ADD", g_ord, g_sew), g.math("ADD", g.math("ADD", g_ord, g_sew), 0.02),
                   "pressed into the seam", to=(1.0, 0.0))
    g_r = g.math("MULTIPLY", g.math("MULTIPLY", g_on, g_off), g.math("SUBTRACT", 1.0, g.out(ginfo, "Anchor")))
    gwob = g.node("ShaderNodeTexNoise", props={"noise_dimensions": "3D"}, Vector=g.node("GeometryNodeInputPosition"),
                  Scale=11.0)
    glue = tube(g_c, g.math("MULTIPLY", g_r, g.math("MULTIPLY_ADD", g.out(gwob, "Factor"), 0.6, 0.7)), RG, 8,
                "glue bead")
    glue_m = g.node("GeometryNodeSetPosition", label="rides with its shard", Geometry=pb.set_material(
        g, g.node("GeometryNodeSetShadeSmooth", Geometry=glue, Shade_Smooth=True), urushi),
        Position=g.group(move, Position=g.node("GeometryNodeInputPosition"), Site=attr("psite", "FLOAT_VECTOR")))

    section(g, "8 · Seams and gold width")
    # ───────────── seams: grid edges between different shards
    var = g.math("SUBTRACT", attr("shard2"), g.math("MULTIPLY", attr("shard"), attr("shard")))
    var.label = "faces differ (variance of id)"
    seam_e = g.node("GeometryNodeDeleteGeometry", label="keep only the seams", props={"domain": "EDGE", "mode": "ALL"},
                    Geometry=grid, Selection=g.math("LESS_THAN", var, 0.25))
    seam_c = g.node("GeometryNodeMeshToCurve", Mesh=seam_e)
    srim = g.math("GREATER_THAN", xyz(g, g.node("GeometryNodeInputPosition"))[2], 0.499)
    ssnap = g.group(snap, V=embed(), Active=1.0, Keep_S=srim)
    seam_p = g.node("GeometryNodeSetPosition", label="seams onto the bisector", Geometry=seam_c,
                    Position=unembed(g.out(ssnap, "V")))
    def contact(site):
        n = g.group(si, Site=site)
        return g.math("MULTIPLY_ADD", g.out(n, "Sew"), CONTACT, g.out(n, "Order"))
    lock = g.math("MAXIMUM", contact(g.out(ssnap, "Site A")), contact(g.out(ssnap, "Site B")))
    lock.label = "faces meet"
    seam = store(store(seam_p, "lock", lock), "us", us_of_position(), kind="FLOAT_VECTOR")
    # gold width: hairline … wide by a noise along the seam, swelling into puddles where seams meet
    su, ss, _ = xyz(g, attr("us", "FLOAT_VECTOR"))
    ang = g.math("MULTIPLY", su, TAU)
    wn = g.node("ShaderNodeTexNoise", label="width along the seam", props={"noise_dimensions": "3D"},
                Vector=g.vec(g.math("COSINE", ang), g.math("SINE", ang), g.math("MULTIPLY", ss, 1.6)), Scale=4.5,
                Detail=2.0)
    swell = smooth(g, g.out(wn, "Factor"), 0.44, 0.60, "hairline → wide")
    sp = g.node("GeometryNodeSplineParameter")
    slen = g.out(g.node("GeometryNodeSplineLength"), "Length")
    to_end = g.math("MINIMUM", g.out(sp, "Length"), g.math("SUBTRACT", slen, g.out(sp, "Length")))
    pool = g.math("EXPONENT", g.math("DIVIDE", to_end, -0.07))
    pool = g.math("MULTIPLY", pool, smooth(g, ss, 0.0, 0.05, "no puddles on the lip"))
    pool.label = "puddle where seams meet"
    gw = g.math("ADD", g.math("MULTIPLY_ADD", swell, 0.8, 0.6), g.math("MULTIPLY", pool, 0.9))
    seam = store(seam, "gw", gw, label="gold width")

    def surf_n(inner):
        return g.vmath("NORMALIZE", g.vmath("SUBTRACT", g.out(on_bowl(inner, 0.01), "Position"),
                                            g.out(on_bowl(inner, 0.0), "Position")))

    def bead(lift, label):
        out = g.node("GeometryNodeSetPosition", label=f"{label}: outside", Geometry=seam, Position=on_bowl(0.0, lift))
        inn = g.node("GeometryNodeSetPosition", label=f"{label}: inside", Geometry=seam, Position=on_bowl(1.0, lift))
        j = g.node("GeometryNodeJoinGeometry", label=label)
        for part, n in ((out, surf_n(0.0)), (inn, surf_n(1.0))):   # the lip itself is gilt by the glaze shader
            g.link(store(part, "sn", n, kind="FLOAT_VECTOR", label="surface normal"), j, b_key="Geometry")
        return store(j, "c0", g.node("GeometryNodeInputPosition"), kind="FLOAT_VECTOR", label="bead centre"), out

    def flatten(mesh, k, label):
        """Squash a round bead along the surface normal to k of its height: a ribbon lying on the glaze."""
        n = attr("sn", "FLOAT_VECTOR")
        h = g.out(g.vmath("DOT_PRODUCT", g.vmath("SUBTRACT", g.node("GeometryNodeInputPosition"),
                                                 attr("c0", "FLOAT_VECTOR")), n), "Value")
        return g.node("GeometryNodeSetPosition", label=label, Geometry=mesh,
                      Offset=g.vmath("SCALE", n, scale=g.math("MULTIPLY", h, g.math("SUBTRACT", k, 1.0))))

    section(g, "9 · Urushi: squeeze-out, set, hide")
    wob = g.node("ShaderNodeTexNoise", label="organic width", props={"noise_dimensions": "3D"},
                 Vector=g.node("GeometryNodeInputPosition"), Scale=7.0, Detail=2.0)
    width = g.math("MULTIPLY_ADD", g.out(wob, "Factor"), 0.3, 0.85)

    def gold_time():
        gn = g.node("ShaderNodeTexNoise", props={"noise_dimensions": "3D"},
                    Vector=g.out(on_bowl(0.0, 0.0), "Position"), Scale=3.0)
        t = g.math("ADD", g.math("MULTIPLY_ADD", xyz(g, attr("us", "FLOAT_VECTOR"))[1], GSPAN, G0),
                   g.math("MULTIPLY", g.out(gn, "Factor"), 0.04))
        t.label = "gold flows down from the rim"
        return t

    lac_c, _ = bead(0.0, "urushi line")
    lk = attr("lock")
    rise = smooth(g, phase, g.math("SUBTRACT", lk, 0.006), g.math("ADD", lk, 0.010), "squeezed out")
    settle = smooth(g, phase, g.math("ADD", lk, 0.02), g.math("ADD", lk, 0.07), "settles to a slim bead",
                    to=(SQ, 1.0))
    tg = gold_time()
    covered = smooth(g, phase, g.math("ADD", tg, GRAMP * 0.5), g.math("ADD", tg, GRAMP),
                     "gone under the gold", to=(1.0, 0.0))
    lac_r = g.math("MULTIPLY", g.math("MULTIPLY", rise, settle), covered)
    lac = tube(lac_c, g.math("MULTIPLY", lac_r, width), LR, 6, "urushi bead")
    lac_k = g.node("ShaderNodeMapRange", label="round while squeezed out, flat once set", Value=settle,
                   From_Min=SQ, From_Max=1.0, To_Min=0.7, To_Max=0.12)
    lac = flatten(lac, g.out(lac_k, "Result"), "urushi lies flat")
    lac_m = pb.set_material(g, g.node("GeometryNodeSetShadeSmooth", Geometry=lac, Shade_Smooth=True), urushi)

    section(g, "10 · Gold flows down the seams")
    carry = smooth(g, phase, B0, GOLD_OFF, "gold leaves at the break", to=(1.0, 0.0))
    gold_c, gold_out = bead(0.0004, "gold seam (a hair above the glaze)")
    t_gold = gold_time()
    gold_r = g.math("MAXIMUM", smooth(g, phase, t_gold, g.math("ADD", t_gold, GRAMP), "gold arrives"), carry)
    gold_m = tube(gold_c, g.math("MULTIPLY", gold_r, attr("gw")), GR, 8, "gold bead")
    gold_m = flatten(gold_m, GOLD_K, "gold lies flat: lacquer + powder, nearly flush")
    gold_s = pb.set_material(g, g.node("GeometryNodeSetShadeSmooth", Geometry=gold_m, Shade_Smooth=True), gold)

    section(g, "11 · Gold dust at the break")
    # gold dust puffing off the seams at the break
    dust_p = g.node("GeometryNodeCurveToPoints", label="dust from the seams", props={"mode": "LENGTH"}, Curve=gold_out,
                    Length=0.02)
    rnd = g.node("ShaderNodeTexWhiteNoise", props={"noise_dimensions": "3D"},
                 Vector=g.vmath("SCALE", g.node("GeometryNodeInputPosition"), scale=37.0))
    nrm = g.vmath("NORMALIZE", g.vmath("SUBTRACT", on_bowl(0.0, 0.05), on_bowl(0.0, 0.0)))
    vel = g.vmath("SCALE", g.vmath("ADD", nrm, g.vmath("SCALE", g.vmath("SUBTRACT", g.out(rnd, "Color"),
                                                                         (0.5, 0.5, 0.5)), scale=1.6)),
                  scale=g.math("MULTIPLY_ADD", g.out(rnd, "Value"), 0.25, 0.12))
    age = clamp01(g, "DIVIDE", g.math("SUBTRACT", phase, B0), DUST)
    age.label = "dust age"
    ease = g.math("SUBTRACT", 1.0, g.math("POWER", g.math("SUBTRACT", 1.0, age), 3.0))
    drift = g.vmath("ADD", g.vmath("SCALE", vel, scale=ease),
                    g.vec(0.0, 0.0, g.math("MULTIPLY", g.math("MULTIPLY", age, age), -0.12)))
    alive = g.math("MULTIPLY", g.math("GREATER_THAN", phase, B0), g.math("LESS_THAN", phase, B0 + DUST))
    dust_moved = g.node("GeometryNodeSetPosition", Geometry=dust_p, Offset=drift)
    speck = g.node("GeometryNodeMeshIcoSphere", Radius=0.006, Subdivisions=1)
    dust = g.node("GeometryNodeRealizeInstances", Geometry=g.node(
        "GeometryNodeInstanceOnPoints", Points=dust_moved, Instance=speck,
        Scale=g.math("MULTIPLY", alive, g.math("MULTIPLY_ADD", age, -1.0, 1.0))))
    dust_s = pb.set_material(g, dust, gold)

    section(g, "12 · Output: join and turn")
    allg = g.node("GeometryNodeJoinGeometry")
    for part in (moved, glue_m, lac_m, gold_s, dust_s):
        g.link(part, allg, b_key="Geometry")
    spin = g.node("GeometryNodeTransform", label="one turn per loop", Geometry=allg,
                  Rotation=g.vec(0.0, 0.0, g.math("MULTIPLY", phase, -TAU)))
    g.output(spin)
    pb.arrange(g.tree)

    # ───────────── white sweep studio
    sc = bpy.context.scene
    sc.frame_set(1)
    st_ = pb.studio("Kintsugi", style="light", view="high", lens=85, margin=1.0, focus=["PA_Bowl"])
    floor = bpy.data.objects["PA_Floor"]
    floor.data.materials[0] = pb.material("Backdrop", "matte", color=(0.50, 0.51, 0.53), roughness=0.9)
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value, bg.inputs["Strength"].default_value = (0.78, 0.80, 0.83, 1.0), 0.15
    sc.view_settings.exposure = -1.5
    piv = bpy.data.objects["PA_Pivot"]
    piv.location = (0.0, 0.0, 0.45)
    az, el, dist = math.radians(15), math.radians(60), 6.9
    cam = bpy.data.objects["PA_Camera"]
    cam.location = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
    for o in [o for o in bpy.data.collections["PA_Studio"].objects if o.type == "LIGHT"]:
        o.data.energy *= 0.25                            # studio preset: keep as gentle fill only

    def card(name, shape, size, energy, loc, camera=False):
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape = shape
        if shape == "RECTANGLE":
            ld.size, ld.size_y = size
        else:
            ld.size = size
        ld.energy = energy
        lo = bpy.data.objects.new(name, ld)
        bpy.data.collections["PA_Studio"].objects.link(lo)
        lo.location = loc
        lo.rotation_euler = (Vector((0.0, 0.0, 0.5)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        lo.visible_camera = camera
        return lo

    card("PA_Sky", "DISK", 7.0, 450.0, (0.8, -0.6, 6.0))                    # soft daylight from above
    card("PA_SideKey", "RECTANGLE", (2.5, 3.5), 900.0, (-4.2, -1.6, 2.6))   # gradient on the outer wall, soft shadow
    card("PA_CardA", "RECTANGLE", (5.0, 0.9), 350.0, (2.6, 1.4, 3.4))       # highlight bands in the glaze
    card("PA_CardB", "RECTANGLE", (0.8, 4.0), 250.0, (-1.8, 2.8, 3.0))

    # put the gold chip on the lip where a seam meets it, facing the camera at the loop start
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).data
    lac_i = next(i for i, m in enumerate(me.materials) if m and m.name == "PA_Gold")
    tops = {v for p in me.polygons if p.material_index == lac_i for v in p.vertices}
    u_cam = (math.atan2(-math.cos(az), math.sin(az)) / TAU) % 1.0
    best = min((me.vertices[i].co for i in tops if me.vertices[i].co.z > 1.12),
               key=lambda c: abs(((math.atan2(c.y, c.x) / TAU) % 1.0 - u_cam + 0.5) % 1.0 - 0.5))
    chip_u = (math.atan2(best.y, best.x) / TAU) % 1.0
    chip_c.inputs["X"].default_value, chip_c.inputs["Y"].default_value = chip_u, 0.0
    frame_sections()
    # node layout tidied in the UI (labelled frames, real node sizes); see tutorial/README.md
    layout = pb.layout_load(os.path.join(DAY, "nodes_layout.json"))
    pb.output(os.path.join(DAY, "loop.mp4"), "video")
    out = ARGS[ARGS.index("--save-as") + 1] if "--save-as" in ARGS else os.path.join(DAY, "kintsugi.blend")
    pb.save(out)
    return {"piece": info, "studio": st_, "layout": layout}


def clay(path):
    """White clay-model copy (Workbench = viewport solid shading) for checking motion."""
    sc = bpy.context.scene
    keep = sc.render.engine
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.studio_light = "STUDIO", "Default"
    sh.color_type = "MATERIAL"           # white clay, but urushi dark and gold gold, so gluing reads
    sh.show_cavity, sh.cavity_type = True, "BOTH"
    sh.show_shadows = True
    for m in bpy.data.materials:
        m.diffuse_color = {"PA_Urushi": (0.06, 0.03, 0.02, 1), "PA_Gold": (0.85, 0.62, 0.25, 1),
                           "PA_Biscuit": (0.80, 0.74, 0.64, 1)}.get(m.name, (0.9, 0.9, 0.9, 1))
    sc.display.render_aa = "8"
    expo, sc.view_settings.exposure = sc.view_settings.exposure, 0.0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pb.save(path)
    sc.render.engine, sc.view_settings.exposure = keep, expo
    return path


if __name__ == "__main__":
    res = build()
    if "--preview" in ARGS:
        for fr in ARGS[ARGS.index("--preview") + 1].split(","):
            fr = int(fr)
            pb.preview(os.path.join(DAY, f"_preview_{fr:03d}.png"), scale=50, samples=16, frame=fr)
    if "--still" in ARGS:
        fr = int(ARGS[ARGS.index("--still") + 1])
        res["still"] = pb.render_still(os.path.join(DAY, f"_still_{fr:03d}.png"), frame=fr)
    if "--clay" in ARGS:
        res["clay"] = clay(os.path.join(DAY, "clay", "kintsugi_clay.blend"))
    res["audit"] = pb.audit("Kintsugi")
    res["describe"] = pb.describe("PA_Bowl_GN")
    print("BUILD_RESULT", res)
