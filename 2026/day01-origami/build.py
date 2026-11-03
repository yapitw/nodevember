"""Nodevember 2026 · Day 01 · Origami (v2) — a sheet that leaves.

The top sheet of a stack of washi paper folds itself into a paper plane (the classic dart:
corners in, edges in, in half, wings out) and glides off the desk. The next sheet underneath
is already in place, so the loop is seamless.

How the folding works (one group, PA_Fold, used seven times):
  each fold rotates the points on one side of a crease line about that line. While a fold is
  in progress every earlier fold is complete, so the paper is flat again and the crease can
  be given in plain desk coordinates. The flap lands on top of the stack (axis height = current
  max z + one sheet gap), and vertices within ¾ of a grid cell are snapped onto the crease first,
  so fold edges are straight lines instead of grid stair-steps.
  Wings are folded before the half fold in the chain (they are defined on the flat sheet), and
  their creases ride along when the left half turns over.

Run: Blender -b --factory-startup --python build.py -- [--preview] [--still N]
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
for _lib in ("../../lib", "../../../.agents/skills/procedural-art/scripts"):   # public repo / monorepo
    if os.path.exists(os.path.join(HERE, _lib, "proc_blender.py")):
        sys.path.insert(0, os.path.abspath(os.path.join(HERE, _lib)))
        break
import proc_blender as pb  # noqa: E402

importlib.reload(pb)

DAY = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FRAMES = 240
W, H = 0.21, 0.297                 # A4
VX, VY = 176, 248                  # grid vertices (≈1.2 mm cells)
CELL = W / (VX - 1)
GAP = 0.00005                      # layer spacing (Cycles has no z-fighting)
SHEET = 0.00016                    # paper thickness in the stack
SHEETS = 18                        # the stack underneath
ALPHA = math.radians(20)           # fuselage V opening
S22, C22 = math.sin(math.pi / 8), math.cos(math.pi / 8)


def fold_group():
    """PA_Fold: rotate the points on the `Side` of the crease (Point, Direction) by Angle.
    Lift: axis at (max z + Gap) so the flap lands on top; else at Center Z.
    Upward: the flap starts moving up (valley seen from above); else down."""
    name = "PA_Fold"
    old = bpy.data.node_groups.get(name)
    if old:
        bpy.data.node_groups.remove(old)
    t = bpy.data.node_groups.new(name, "GeometryNodeTree")
    sock = {"Geometry": "NodeSocketGeometry", "Point": "NodeSocketVector", "Direction": "NodeSocketVector",
            "Side": "NodeSocketVector", "Angle": "NodeSocketFloat", "Mask": "NodeSocketBool",
            "Lift": "NodeSocketBool", "Upward": "NodeSocketBool", "Center Z": "NodeSocketFloat",
            "Snap": "NodeSocketFloat", "Gap": "NodeSocketFloat"}
    for n, k in sock.items():
        it = t.interface.new_socket(n, in_out="INPUT", socket_type=k)
        if n in ("Mask", "Lift", "Upward"):
            it.default_value = True
    t.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    g = pb.Graph(t)
    gi, go = g.group_io()
    I = gi.outputs
    side = g.vmath("NORMALIZE", I["Side"])
    pos = g.node("GeometryNodeInputPosition")
    flat = g.vmath("MULTIPLY", g.vmath("SUBTRACT", pos, I["Point"]), (1.0, 1.0, 0.0))
    dist = g.vmath("DOT_PRODUCT", flat, side)
    dist.label = "distance from crease"
    near = g.math("LESS_THAN", g.math("ABSOLUTE", g.out(dist, "Value")), I["Snap"])
    snap_sel = g.node("FunctionNodeBooleanMath", props={"operation": "AND"}, ins={0: I["Mask"], 1: near})
    snapped = g.vmath("SUBTRACT", pos, g.vmath("SCALE", side, scale=g.out(dist, "Value")))
    g1 = g.node("GeometryNodeSetPosition", label="snap onto the crease", Geometry=I["Geometry"],
                Selection=snap_sel, Position=snapped)
    zs = g.node("GeometryNodeAttributeStatistic", label="top of the stack", props={"data_type": "FLOAT"},
                Geometry=g1, Attribute=g.out(g.node("ShaderNodeSeparateXYZ", Vector=pos), "Z"))
    moving0 = g.math("GREATER_THAN", g.out(dist, "Value"), 1e-7)
    sel0 = g.node("FunctionNodeBooleanMath", props={"operation": "AND"}, ins={0: I["Mask"], 1: moving0})
    zf = g.node("GeometryNodeAttributeStatistic", label="top of the flap", props={"data_type": "FLOAT"},
                Geometry=g1, Selection=sel0, Attribute=g.out(g.node("ShaderNodeSeparateXYZ", Vector=pos), "Z"))
    lifted = g.math("MULTIPLY", g.math("ADD", g.math("ADD", g.out(zs, "Max"), g.out(zf, "Max")), I["Gap"]), 0.5)
    lifted.label = "flap lands one sheet above the stack"
    zc = g.node("GeometryNodeSwitch", label="land on top", props={"input_type": "FLOAT"}, Switch=I["Lift"],
                False_=I["Center Z"], True_=lifted)
    sep_p = g.node("ShaderNodeSeparateXYZ", Vector=I["Point"])
    center = g.vec(g.out(sep_p, "X"), g.out(sep_p, "Y"), zc)
    upz = g.out(g.node("ShaderNodeSeparateXYZ", Vector=g.vmath("CROSS_PRODUCT", I["Direction"], side)), "Z")
    up = g.node("GeometryNodeSwitch", label="valley / mountain", props={"input_type": "FLOAT"},
                Switch=I["Upward"], False_=-1.0, True_=1.0)
    ang = g.math("MULTIPLY", I["Angle"], g.math("MULTIPLY", g.math("SIGN", upz), up))
    moving = g.math("GREATER_THAN", g.out(dist, "Value"), 1e-7)
    sel = g.node("FunctionNodeBooleanMath", props={"operation": "AND"}, ins={0: I["Mask"], 1: moving})
    rot = g.node("ShaderNodeVectorRotate", label="turn the flap", props={"rotation_type": "AXIS_ANGLE"},
                 Vector=pos, Center=center, Axis=I["Direction"], Angle=ang)
    g2 = g.node("GeometryNodeSetPosition", label="fold", Geometry=g1, Selection=sel, Position=rot)
    g.link(g2, go, b_key="Geometry")
    pb.arrange(t)
    return t


def washi_material():
    """Two-sided washi: seigaiha waves, indigo on cream (front) / cream on indigo (back)."""
    m = bpy.data.materials.get("PA_Washi") or bpy.data.materials.new("PA_Washi")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    g = pb.Graph(nt)
    out = g.node("ShaderNodeOutputMaterial")
    uv = g.node("ShaderNodeAttribute", label="flat sheet coords", props={"attribute_name": "flat"})
    R = 0.016
    p = g.vmath("SCALE", g.out(uv, "Vector"), scale=1.0 / R)
    sp = g.node("ShaderNodeSeparateXYZ", Vector=p)
    px, py = g.out(sp, "X"), g.out(sp, "Y")
    j0 = g.math("FLOOR", py)

    def fan(j):
        par = g.math("FLOORED_MODULO", j, 2.0)
        cx = g.math("MULTIPLY_ADD", g.math("ROUND", g.math("DIVIDE", g.math("SUBTRACT", px, par), 2.0)), 2.0, par)
        return g.vmath("LENGTH", g.vec(g.math("SUBTRACT", px, cx), g.math("SUBTRACT", py, j), 0.0))

    d0 = g.out(fan(j0), "Value")
    d1 = g.out(fan(g.math("ADD", j0, 1.0)), "Value")
    front_row = g.math("LESS_THAN", d0, 1.0)
    front_row.label = "lower row covers the one behind"
    d = g.node("ShaderNodeMix", label="seigaiha distance", props={"data_type": "FLOAT"},
               Factor=front_row, A=d1, B=d0)
    band = g.math("FRACT", g.math("MULTIPLY", d, 4.0))
    a = g.node("ShaderNodeMapRange", Value=band, From_Min=0.70, From_Max=0.76)
    b = g.node("ShaderNodeMapRange", Value=band, From_Min=0.95, From_Max=0.995, To_Min=1.0, To_Max=0.0)
    ring = g.math("MULTIPLY", a, b)
    ring.label = "wave lines"
    cream, indigo = (0.80, 0.74, 0.62, 1), (0.018, 0.035, 0.13, 1)
    front = g.node("ShaderNodeMix", label="front: indigo on cream", props={"data_type": "RGBA"},
                   Factor=ring, A=cream, B=indigo)
    back = g.node("ShaderNodeMix", label="back: cream on indigo", props={"data_type": "RGBA"},
                  Factor=ring, A=indigo, B=cream)
    geo = g.node("ShaderNodeNewGeometry")
    col = g.node("ShaderNodeMix", label="which side faces us", props={"data_type": "RGBA"},
                 Factor=g.out(geo, "Backfacing"), A=front, B=back)
    grain = g.node("ShaderNodeTexNoise", label="washi fibre", Scale=700.0, Detail=6.0)
    bump = g.node("ShaderNodeBump", Strength=0.05, Height=g.out(grain, "Factor"))
    bsdf = g.node("ShaderNodeBsdfPrincipled", Base_Color=col, Roughness=0.72, Normal=bump)
    bsdf.inputs["Sheen Weight"].default_value = 0.3
    trans = g.node("ShaderNodeBsdfTranslucent", Color=col, Normal=bump)
    mix = g.node("ShaderNodeMixShader", label="light through the paper", ins={0: 0.12, 1: bsdf, 2: trans})
    g.link(mix, out, b_key="Surface")
    pb.arrange(nt)
    return m


def wood_floor():
    m = bpy.data.materials.get("PA_Walnut") or bpy.data.materials.new("PA_Walnut")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    g = pb.Graph(nt)
    out = g.node("ShaderNodeOutputMaterial")
    tc = g.node("ShaderNodeTexCoord")
    mp = g.node("ShaderNodeMapping", Vector=g.out(tc, "Object"), Scale=(40.0, 1.5, 1.0))
    grain = g.node("ShaderNodeTexNoise", label="long grain", Vector=mp, Scale=4.0, Detail=8.0, Roughness=0.62)
    ramp = g.node("ShaderNodeMix", props={"data_type": "RGBA"}, Factor=g.out(grain, "Factor"),
                  A=(0.075, 0.036, 0.018, 1), B=(0.13, 0.066, 0.033, 1))
    bsdf = g.node("ShaderNodeBsdfPrincipled", Base_Color=ramp, Roughness=0.62)
    g.link(bsdf, out, b_key="Surface")
    pb.arrange(nt)
    return m


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    info = pb.piece("Origami", aspect="1:1", width=1080, frames=FRAMES, engine="CYCLES", samples=64)
    fold = fold_group()
    washi = washi_material()
    ob, g = pb.gn_object("PaperPlane", "Origami")
    phase = g.out(g.group(pb.loop_clock(FRAMES)), "Phase")

    def window(a, b, label):
        return g.node("ShaderNodeMapRange", label=label, props={"interpolation_type": "SMOOTHERSTEP"},
                      Value=phase, From_Min=a, From_Max=b)

    # ── the sheet, with its flat coordinates and which half each point belongs to
    sheet = g.node("GeometryNodeMeshGrid", label="A4 sheet", Size_X=W, Size_Y=H, Vertices_X=VX, Vertices_Y=VY)
    pos = g.node("GeometryNodeInputPosition")
    uv = g.node("GeometryNodeStoreNamedAttribute", label="flat coords → washi print",
                props={"data_type": "FLOAT_VECTOR", "domain": "POINT"}, Geometry=sheet, Name="flat", Value=pos)
    left = g.math("LESS_THAN", g.out(g.node("ShaderNodeSeparateXYZ", Vector=pos), "X"), 0.0)
    left.label = "left half"
    right = g.node("FunctionNodeBooleanMath", props={"operation": "NOT"}, ins={0: left})

    w, yt, yb = W / 2, H / 2, -H / 2
    nose = (0.0, yt, 0.0)
    r2 = 1 / math.sqrt(2)
    wn, wt = Vector((0.004, yt - 0.012, 0)), Vector((0.026, yb, 0))      # right wing crease
    wd = (wt - wn).normalized()
    folds = [  # label, point, direction, side, window, extra
        ("corner left to centre", nose, (-r2, -r2, 0), (-r2, r2, 0), (0.05, 0.12), {}),
        ("corner right to centre", nose, (r2, -r2, 0), (r2, r2, 0), (0.12, 0.19), {}),
        ("edge left to centre", nose, (-S22, -C22, 0), (-C22, S22, 0), (0.19, 0.27), {}),
        ("edge right to centre", nose, (S22, -C22, 0), (C22, S22, 0), (0.27, 0.35), {}),
    ]
    geo = uv
    for label, p, d, s, (a, b), _ in folds:
        geo = g.group(fold, Geometry=geo, Point=p, Direction=d, Side=s,
                      Angle=g.math("MULTIPLY", window(a, b, label), math.pi), Snap=CELL * 0.75, Gap=GAP)
        geo.label = label
    flat_top = g.node("GeometryNodeAttributeStatistic", label="flat dart: top layer", props={"data_type": "FLOAT"},
                      Geometry=geo, Attribute=g.out(g.node("ShaderNodeSeparateXYZ", Vector=pos), "Z"))
    # wings, defined on the flat (half-unfolded) sheet; they open while the plane stands up
    wing = g.math("MULTIPLY", window(0.50, 0.63, "wings open"), math.pi / 2 - ALPHA / 2 - 0.06)
    geo = g.group(fold, Geometry=geo, Point=tuple(wn), Direction=tuple(wd), Side=(-wd.y, wd.x, 0), Angle=wing,
                  Mask=right, Lift=False, Upward=False, Center_Z=0.0, Snap=CELL * 0.75, Gap=GAP)
    geo.label = "right wing"
    geo = g.group(fold, Geometry=geo, Point=(-wn.x, wn.y, 0), Direction=(-wd.x, wd.y, 0), Side=(wd.y, wd.x, 0),
                  Angle=wing, Mask=left, Lift=False, Upward=False, Center_Z=0.0, Snap=CELL * 0.75, Gap=GAP)
    geo.label = "left wing"
    half = g.math("MULTIPLY", window(0.36, 0.46, "fold in half"), math.pi - ALPHA)
    geo = g.group(fold, Geometry=geo, Point=(0, 0, 0), Direction=(0, 1, 0), Side=(-1, 0, 0), Angle=half,
                  Mask=left, Lift=False, Center_Z=g.math("ADD", g.out(flat_top, "Max"), GAP / 2),
                  Snap=CELL * 0.75, Gap=GAP)
    geo.label = "fold in half"
    geo = g.node("GeometryNodeSetShadeSmooth", label="crisp facets", Geometry=geo, Shade_Smooth=False)

    # ── stand up on the keel, then fly
    stand = g.math("MULTIPLY", window(0.47, 0.60, "stand up on the keel"), -(math.pi / 2 - ALPHA / 2))
    up = g.node("GeometryNodeTransform", label="stand up", Geometry=geo, Rotation=g.vec(0.0, stand, 0.0))
    e = g.node("ShaderNodeMapRange", label="glide", Value=phase, From_Min=0.655, From_Max=0.94)
    e2 = g.math("POWER", e, 2.1)
    lift = g.math("MULTIPLY", window(0.47, 0.64, "lift off"), 0.03)
    fly = g.node("GeometryNodeTransform", label="flight path", Geometry=up,
                 Translation=g.vec(g.math("MULTIPLY", e2, -0.35), g.math("MULTIPLY", e2, 1.9),
                                   g.math("MULTIPLY_ADD", e2, 0.42, lift)),
                 Rotation=g.vec(g.math("MULTIPLY", g.math("SINE", g.math("MULTIPLY", e, math.pi)), 0.16),
                                g.math("MULTIPLY", e, -0.45), g.math("MULTIPLY", e, 0.35)))
    gone = g.math("LESS_THAN", e, 0.999)
    plane = g.node("GeometryNodeSwitch", label="out of sight", props={"input_type": "GEOMETRY"},
                   Switch=gone, True_=fly)

    # ── the stack it came from (the top sheet is aligned, so the loop closes)
    line = g.node("GeometryNodeMeshLine", label="stack", Count=SHEETS, Offset=(0.0, 0.0, SHEET * 1.2))
    box = g.node("GeometryNodeMeshCube", Size=(W, H, SHEET))
    box_uv = g.node("GeometryNodeStoreNamedAttribute", props={"data_type": "FLOAT_VECTOR", "domain": "POINT"},
                    Geometry=box, Name="flat", Value=g.node("GeometryNodeInputPosition"))
    idx = g.node("GeometryNodeInputIndex")
    loose = g.math("LESS_THAN", idx, SHEETS - 1)
    jitter = g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT"}, Min=-0.022, Max=0.022, Seed=7)
    off = g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT_VECTOR"}, Min=(-0.002, -0.002, 0),
                 Max=(0.002, 0.002, 0), Seed=3)
    tilt = g.math("MULTIPLY", g.out(jitter, "Value"), loose)
    inst = g.node("GeometryNodeInstanceOnPoints", Points=line, Instance=box_uv,
                  Rotation=g.vec(0.0, 0.0, tilt))
    shake = g.node("GeometryNodeTranslateInstances", Instances=inst,
                   Translation=g.vmath("SCALE", g.out(off, "Value"), scale=loose))
    stack = g.node("GeometryNodeRealizeInstances", Geometry=shake)
    top_z = SHEET * 1.2 * (SHEETS - 1) + SHEET
    on_stack = g.node("GeometryNodeTransform", label="on top of the stack", Geometry=plane,
                      Translation=(0.0, 0.0, top_z))
    allg = g.node("GeometryNodeJoinGeometry")
    g.link(on_stack, allg, b_key="Geometry")
    g.link(stack, allg, b_key="Geometry")
    g.output(pb.set_material(g, allg, washi))
    pb.arrange(g.tree)

    # ── studio: walnut desk, low warm sun, shallow focus
    sc = bpy.context.scene
    sc.frame_set(1)
    st = pb.studio("Origami", style="warm", view="high", lens=60, margin=1.28, light=0.45)
    piv = bpy.data.objects["PA_Pivot"]
    piv.rotation_euler.z = math.radians(22)
    bpy.data.objects["PA_Floor"].data.materials[0] = wood_floor()
    sun_d = bpy.data.lights.new("PA_Sun", "SUN")
    sun_d.energy, sun_d.angle, sun_d.color = 4.5, math.radians(1.2), (1.0, 0.84, 0.66)
    sun = bpy.data.objects.new("PA_Sun", sun_d)
    bpy.data.collections["PA_Studio"].objects.link(sun)
    sun.rotation_euler = Euler((math.radians(62), 0, math.radians(-128)))
    cam = bpy.data.objects["PA_Camera"].data
    cam.dof.use_dof = True
    cam.dof.focus_object = piv
    cam.dof.aperture_fstop = 4.0
    # node layout tidied in the UI (labelled frames, real node sizes); see tutorial/README.md
    layout = pb.layout_load(os.path.join(DAY, "nodes_layout.json"))
    pb.output(os.path.join(DAY, "loop.mp4"), "video")
    pb.save(os.path.join(DAY, "origami.blend"))
    return {"piece": info, "studio": st, "layout": layout}


def stats():
    dg = bpy.context.evaluated_depsgraph_get()
    ob = bpy.data.objects["PA_PaperPlane"].evaluated_get(dg)
    me = ob.to_mesh()
    r = {"verts": len(me.vertices)}
    ob.to_mesh_clear()
    return r


if __name__ == "__main__":
    res = build()
    sc = bpy.context.scene
    if "--preview" in ARGS:
        for f in ARGS[ARGS.index("--preview") + 1].split(","):
            f = int(f)
            pb.preview(os.path.join(DAY, f"_preview_{f:03d}.png"), scale=50, samples=16, frame=f)
    if "--still" in ARGS:
        f = int(ARGS[ARGS.index("--still") + 1])
        res["still"] = pb.render_still(os.path.join(DAY, f"_still_{f:03d}.png"), frame=f)
    res["audit"] = pb.audit("Origami")
    res["describe"] = pb.describe("PA_PaperPlane_GN")
    print("BUILD_RESULT", res)
