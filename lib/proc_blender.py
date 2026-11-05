"""Procedural-art helpers for Blender 5.2 (Geometry Nodes, shader nodes, compositor).

Runs inside Blender: Blender MCP `execute_blender_code`, or `Blender -b file.blend --python x.py`.

    import sys, importlib
    sys.path.insert(0, "<skill dir>/scripts")
    import proc_blender as pb; importlib.reload(pb)

Everything this module creates is named PA_*; nothing else in the file is touched.
Sections: scene · node building · layout · loop helpers · materials · studio · post FX ·
render · node screenshot · audit.
"""
import math
import os
import shutil
import subprocess
import time

import bpy
from mathutils import Vector

P = "PA_"
ASPECTS = {"1:1": (1, 1), "4:5": (4, 5), "5:4": (5, 4), "16:9": (16, 9), "9:16": (9, 16), "3:2": (3, 2)}
TAU = math.tau


# ───────────────────────────────────────────────────────── scene

def _coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def _clear_coll(c):
    for ob in list(c.objects):
        data = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if data is not None and data.users == 0:
            for coll in (bpy.data.meshes, bpy.data.lights, bpy.data.cameras):
                if coll.get(data.name) == data:
                    coll.remove(data)
                    break


def _use_gpu(sc):
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        return "CPU"
    for dev in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = dev
            prefs.get_devices()
        except TypeError:
            continue
        if any(d.type == dev for d in prefs.devices):
            for d in prefs.devices:
                d.use = True
            sc.cycles.device = "GPU"
            return dev
    return "CPU"


def piece(name, aspect="4:5", width=1080, fps=30, frames=120, engine="CYCLES", samples=96, gpu=True):
    """Set up the scene for one artwork and return its collection PA_<name>.
    aspect: 1:1 | 4:5 (feeds) | 16:9 | 9:16 (reels) | 3:2 | 5:4.  width = short side in px.
    frames = loop length: frames 1..N play, frame N+1 would equal frame 1 (see loop_clock)."""
    sc = bpy.context.scene
    a, b = ASPECTS[aspect]
    short = width
    if a <= b:
        sc.render.resolution_x, sc.render.resolution_y = short, round(short * b / a)
    else:
        sc.render.resolution_x, sc.render.resolution_y = round(short * a / b), short
    sc.render.resolution_percentage = 100
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = 1, frames
    sc["pa_loop_frames"] = frames
    sc.render.engine = {"EEVEE": "BLENDER_EEVEE"}.get(engine, engine)
    device = None
    if sc.render.engine == "CYCLES":
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.cycles.sample_clamp_indirect = 10.0
        device = _use_gpu(sc) if gpu else "CPU"
    else:
        sc.eevee.taa_render_samples = samples
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    c = _coll(P + name)
    return {"collection": c.name, "resolution": [sc.render.resolution_x, sc.render.resolution_y],
            "fps": fps, "frames": frames, "seconds": round(frames / fps, 2), "engine": sc.render.engine,
            "device": device}


def gn_object(name, piece_name=None, base="EMPTY"):
    """Object driven by a new Geometry Nodes tree. base="EMPTY" keeps the object's own mesh empty
    so everything is generated in nodes (strict procedural). Returns (obj, Graph)."""
    tname = f"{P}{name}"
    old = bpy.data.objects.get(tname)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(tname)
    if base == "PLANE":
        me.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(tname, me)
    coll = _coll(P + piece_name) if piece_name else bpy.context.scene.collection
    coll.objects.link(ob)
    tree = bpy.data.node_groups.get(tname + "_GN")
    if tree is not None:
        bpy.data.node_groups.remove(tree)
    tree = bpy.data.node_groups.new(tname + "_GN", "GeometryNodeTree")
    tree.is_modifier = True
    tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    mod = ob.modifiers.new("PA_Nodes", "NODES")
    mod.node_group = tree
    g = Graph(tree)
    return ob, g


# ───────────────────────────────────────────────────────── node building

_STYPE = {"float": "NodeSocketFloat", "int": "NodeSocketInt", "bool": "NodeSocketBool",
          "vector": "NodeSocketVector", "color": "NodeSocketColor", "geometry": "NodeSocketGeometry",
          "material": "NodeSocketMaterial", "object": "NodeSocketObject", "rotation": "NodeSocketRotation",
          "string": "NodeSocketString", "menu": "NodeSocketMenu", "shader": "NodeSocketShader",
          "collection": "NodeSocketCollection"}


def _mod_set(mod, ident, value):
    props = getattr(mod, "properties", None)        # 5.2: modifier inputs are not ID properties
    if props is not None and hasattr(props, "inputs"):
        getattr(props.inputs, ident).value = value
    else:
        mod[ident] = value


def _mod_get(mod, ident):
    props = getattr(mod, "properties", None)
    if props is not None and hasattr(props, "inputs"):
        return getattr(props.inputs, ident).value
    return mod[ident]


def set_inputs(obj, **values):
    """Move modifier sliders by display name: set_inputs("PA_Cloth", Amplitude=0.4)."""
    obj = bpy.data.objects[obj] if isinstance(obj, str) else obj
    mod = next(m for m in obj.modifiers if m.type == "NODES")
    items = {i.name: i for i in mod.node_group.interface.items_tree if getattr(i, "in_out", None) == "INPUT"}
    for k, v in values.items():
        it = items[k]
        if it.socket_type == "NodeSocketInt":
            v = int(round(v))
        elif it.socket_type == "NodeSocketFloat":
            v = float(v)
        _mod_set(mod, it.identifier, v)
    obj.update_tag()
    return {k: _mod_get(mod, items[k].identifier) for k in values}


_ALIAS = {"Fac": "Factor", "Factor": "Fac"}


def _virtual(s):
    return s.bl_idname == "NodeSocketVirtual"


def _find(sockets, key):
    """Socket by index, name or 'Name#2' (2nd enabled socket with that name). Underscores match
    spaces; Fac/Factor are interchangeable; 'Geometry' falls back to the first geometry socket
    (Mesh / Curve / Points / Instances). Never returns a virtual 'extend' socket: linking into one
    from Python corrupts zones/groups and crashed Blender 5.2 on evaluation."""
    if isinstance(key, int):
        s = sockets[key]
        if _virtual(s):
            raise KeyError(f"socket {key} is the empty 'extend' socket; add an item first "
                           f"(Graph.zone_item / tree.interface.new_socket). Sockets: {[x.name for x in sockets]}")
        return s
    name, _, nth = key.partition("#")
    real = [s for s in sockets if not _virtual(s)]
    bare = name.rstrip("_")      # True_=, False_= (Python keywords) mean the "True"/"False" sockets
    for cand in (name, name.replace("_", " "), bare, bare.replace("_", " "), _ALIAS.get(name)):
        if not cand:
            continue
        hits = [s for s in real if s.name == cand and s.enabled] or [s for s in real if s.name == cand]
        if hits:
            return hits[int(nth) - 1 if nth else 0]
    if name == "Geometry":
        hits = [s for s in real if s.type == "GEOMETRY" and s.enabled]
        if hits:
            return hits[0]
    raise KeyError(f"{key!r} not in {[s.name for s in real if s.enabled]}")


class Graph:
    """Tiny builder over any node tree.

        g = pb.Graph(tree)
        grid = g.node("GeometryNodeMeshGrid", Size_X=4, Size_Y=4, Vertices_X=200, Vertices_Y=200)
        noise = g.node("ShaderNodeTexNoise", Scale=3)
        g.node("GeometryNodeSetPosition", Geometry=grid, Offset=g.vec(0, 0, noise))  # see vec()
        g.output(...)

    Keyword values that are sockets or nodes are linked (a node means its first enabled output);
    other values set default_value. Underscores in keyword names stand for spaces; use ins={...}
    for index keys or 'Name#2'. props={...} sets node properties (operation, data_type, ...)."""

    def __init__(self, tree):
        self.tree = tree
        self.nodes, self.links = tree.nodes, tree.links

    # tutorial sections
    def section(self, label, color=None):
        """Context manager: every node made inside `with g.section("2 · Sheet"):` goes into one labelled frame.
        arrange() then lays each frame out as its own block (left to right, in the order made), and
        scripts/tutorial_shots.py cuts each frame out into its own screenshot. See references/tutorial.md."""
        return _Section(self, label, color)

    def begin_section(self, label, color=None):
        """Same as `with g.section(label):` without re-indenting: closes the open section, starts this one.
        Call end_section() before arrange()."""
        self.end_section()
        self._open = _Section(self, label, color).__enter__()

    def end_section(self):
        sec, self._open = getattr(self, "_open", None), None
        if sec is not None:
            sec.__exit__(None, None, None)

    # sockets
    @staticmethod
    def out(node, key=None):
        if isinstance(node, bpy.types.NodeSocket):
            if _virtual(node):
                raise ValueError("cannot link from an empty 'extend' socket")
            return node
        if key is None:
            return next(s for s in node.outputs if s.enabled and not _virtual(s))
        return _find(node.outputs, key)

    def set(self, node, key, value):
        sock = _find(node.inputs, key)
        if isinstance(value, (bpy.types.Node, bpy.types.NodeSocket)):
            self.links.new(self.out(value), sock)
        else:
            if isinstance(value, (tuple, list)) and hasattr(sock, "default_value") and \
                    hasattr(sock.default_value, "__len__") and len(value) == 3 and len(sock.default_value) == 4:
                value = (*value, 1.0)
            sock.default_value = value
        return node

    def node(self, idname, label=None, props=None, ins=None, **inputs):
        n = self.nodes.new(idname)
        if label:
            n.label = label
        for k, v in (props or {}).items():
            setattr(n, k, v)
        for k, v in {**(ins or {}), **inputs}.items():
            self.set(n, k, v)
        return n

    def link(self, a, b, a_key=None, b_key=0):
        src = self.out(a, a_key)
        dst = b if isinstance(b, bpy.types.NodeSocket) else _find(b.inputs, b_key)
        if _virtual(dst):
            raise ValueError("cannot link into an empty 'extend' socket; add a zone/group item first")
        return self.links.new(src, dst)

    # group interface
    def group_io(self):
        gin = next((n for n in self.nodes if n.bl_idname == "NodeGroupInput"), None) or \
            self.nodes.new("NodeGroupInput")
        gout = next((n for n in self.nodes if n.bl_idname == "NodeGroupOutput"), None) or \
            self.nodes.new("NodeGroupOutput")
        return gin, gout

    def param(self, name, kind="float", default=None, min=None, max=None, description=""):
        """Expose a modifier slider; returns the Group Input output socket to link from."""
        it = self.tree.interface.new_socket(name, in_out="INPUT", socket_type=_STYPE[kind],
                                            description=description)
        if default is not None:
            it.default_value = default
        if min is not None:
            it.min_value = min
        if max is not None:
            it.max_value = max
        if default is not None:   # modifiers made before the socket existed start at 0, not default
            for ob in bpy.data.objects:
                for m in ob.modifiers:
                    if m.type == "NODES" and m.node_group == self.tree:
                        _mod_set(m, it.identifier, default)
        gin, _ = self.group_io()
        return gin.outputs[name]

    def output(self, geometry, name="Geometry"):
        _, gout = self.group_io()
        self.links.new(self.out(geometry), gout.inputs[name])
        return gout

    # shortcuts
    def math(self, op, a, b=None, c=None):
        n = self.node("ShaderNodeMath", props={"operation": op})
        for i, v in enumerate((a, b, c)):
            if v is not None:
                self.set(n, i, v)
        return n

    def vmath(self, op, a, b=None, scale=None):
        n = self.node("ShaderNodeVectorMath", props={"operation": op})
        for i, v in enumerate((a, b)):
            if v is not None:
                self.set(n, i, v)
        if scale is not None:
            self.set(n, "Scale", scale)
        return n

    def vec(self, x=0.0, y=0.0, z=0.0):
        return self.node("ShaderNodeCombineXYZ", X=x, Y=y, Z=z)

    def group(self, group_tree, **inputs):
        kind = {"GeometryNodeTree": "GeometryNodeGroup", "ShaderNodeTree": "ShaderNodeGroup",
                "CompositorNodeTree": "CompositorNodeGroup"}[self.tree.bl_idname]
        n = self.nodes.new(kind)
        n.node_tree = bpy.data.node_groups[group_tree] if isinstance(group_tree, str) else group_tree
        for k, v in inputs.items():
            self.set(n, k, v)
        return n

    def zone(self, kind="repeat", iterations=None):
        """Zone pair: kind repeat | simulation | foreach. Returns (input_node, output_node).
        Repeat/simulation start with a Geometry item. For-each: input node takes Geometry + Selection and
        gives Index + Element; output node's inputs are main items, then 'Geometry' (per-element
        generated geometry) and generation items; outputs are 'Geometry' (main, with main items as
        attributes) and 'Geometry#2' (all generated geometry joined). Add items with zone_item()."""
        ids = {"repeat": ("GeometryNodeRepeatInput", "GeometryNodeRepeatOutput"),
               "simulation": ("GeometryNodeSimulationInput", "GeometryNodeSimulationOutput"),
               "foreach": ("GeometryNodeForeachGeometryElementInput", "GeometryNodeForeachGeometryElementOutput")}
        a, b = (self.nodes.new(i) for i in ids[kind])
        a.pair_with_output(b)
        if iterations is not None:
            self.set(a, "Iterations", iterations)
        return a, b

    def zone_item(self, zone_out, name, kind="float", role="main"):
        """Add an item to a zone (always via the OUTPUT node). Repeat → repeat_items, simulation →
        state_items, for-each → role main (per-element value stored on the element) | generation
        (geometry/values generated per element) | input (field evaluated per element, appears on the
        input node). Returns the item name; link to it by name afterwards."""
        if hasattr(zone_out, "repeat_items"):
            items = zone_out.repeat_items
        elif hasattr(zone_out, "state_items"):
            items = zone_out.state_items
        else:
            items = getattr(zone_out, {"main": "main_items", "generation": "generation_items",
                                       "input": "input_items"}[role])
        items.new({"float": "FLOAT", "int": "INT", "vector": "VECTOR", "geometry": "GEOMETRY",
                   "bool": "BOOLEAN", "color": "RGBA", "rotation": "ROTATION"}[kind], name)
        return name


# ───────────────────────────────────────────────────────── layout (readable node screenshots)

SECTION_COLORS = [(0.36, 0.30, 0.16), (0.18, 0.32, 0.22), (0.20, 0.26, 0.40), (0.38, 0.22, 0.20),
                  (0.30, 0.22, 0.38), (0.16, 0.32, 0.34), (0.34, 0.30, 0.22), (0.26, 0.26, 0.26)]


class _Section:
    def __init__(self, g, label, color):
        self.g, self.label, self.color = g, label, color

    def __enter__(self):
        self.before = {n.as_pointer() for n in self.g.tree.nodes}
        return self

    def __exit__(self, *exc):
        if exc[0] is not None:
            return False
        t = self.g.tree
        new = [n for n in t.nodes if n.as_pointer() not in self.before and n.bl_idname not in
               ("NodeFrame", "NodeGroupInput", "NodeGroupOutput") and n.parent is None]
        if not new:
            return False
        k = sum(1 for n in t.nodes if n.bl_idname == "NodeFrame")
        fr = t.nodes.new("NodeFrame")
        fr.name, fr.label, fr.label_size, fr.shrink = f"Section {k + 1:02d}", self.label, 28, True
        fr.use_custom_color, fr.color = True, self.color or SECTION_COLORS[k % len(SECTION_COLORS)]
        for n in new:
            n.parent = fr
        return False

def _est_height(n):
    if n.dimensions.y > 1:
        return n.dimensions.y
    socks = sum(1 for s in n.outputs if s.enabled and not s.hide) + \
        sum(1 for s in n.inputs if s.enabled and not s.hide)
    extra = 46 if any(p.identifier in ("operation", "data_type", "domain", "mode", "noise_dimensions")
                      for p in n.bl_rna.properties) else 0
    return 36 + 22 * socks + extra


def _set_loc(n, x, y):
    if n.parent is not None and hasattr(n, "location_absolute"):
        n.location_absolute = (x, y)
    else:
        n.location = (x, y)


def arrange(tree, gap_x=70, gap_y=28):
    """Layered left-to-right layout: column = longest path from sources, zones stay bracketed.
    Run before node screenshots; screenshots of tidy trees get read, tangles get skipped.
    A tree with section frames (Graph.section) is laid out frame by frame instead: arrange_sections."""
    if any(n.parent is not None for n in tree.nodes):
        return arrange_sections(tree, gap_x, gap_y)
    pos = _layered([n for n in tree.nodes if n.bl_idname not in ("NodeFrame",)], tree, gap_x, gap_y)
    for n, (x, y) in pos.items():
        n.location = (x, y)
    return {"columns": len({x for x, _ in pos.values()}), "nodes": len(pos)}


def arrange_sections(tree, gap_x=70, gap_y=28, pad=90):
    """Each section frame is laid out on its own (layered), then the frames are placed as blocks in the order
    they were made, wrapping into rows; Group Input sits at the far left, outputs at the far right."""
    frames = [n for n in tree.nodes if n.bl_idname == "NodeFrame"]
    io_in = [n for n in tree.nodes if n.bl_idname == "NodeGroupInput"]
    io_out = [n for n in tree.nodes if n.bl_idname in ("NodeGroupOutput", "ShaderNodeOutputMaterial",
                                                        "ShaderNodeOutputWorld") and n.parent is None]
    loose = [n for n in tree.nodes if n.parent is None and n.bl_idname != "NodeFrame" and n not in io_in + io_out]
    blocks = [[n for n in tree.nodes if n.parent == f] for f in frames] + ([loose] if loose else [])
    laid = []
    for nodes in blocks:
        if not nodes:
            continue
        pos = _layered(nodes, tree, gap_x, gap_y)
        xs = [x for x, _ in pos.values()]
        ys = [y for _, y in pos.values()]
        x0, y1 = min(xs), max(ys)
        w = max(x + n.width for n, (x, _) in pos.items()) - x0
        h = y1 - min(y - _est_height(n) for n, (_, y) in pos.items())
        laid.append(({n: (x - x0, y - y1) for n, (x, y) in pos.items()}, w, h))
    area = sum((w + pad) * (h + pad) for _, w, h in laid) or 1.0
    row_w = max(2400.0, 1.7 * area ** 0.5, max((w for _, w, _ in laid), default=0))
    x, y, row_h, right = 0.0, 0.0, 0.0, 0.0
    for pos, w, h in laid:
        if x > 0 and x + w > row_w:
            x, y, row_h = 0.0, y - row_h - 2 * pad, 0.0
        for n, (px, py) in pos.items():
            _set_loc(n, x + px, y + py - 60)          # room for the frame label
        x += w + 2 * pad
        right = max(right, x)
        row_h = max(row_h, h + 60)
    for i, n in enumerate(io_in):
        n.location = (-n.width - 3 * pad, -220.0 * i)
    for i, n in enumerate(io_out):
        n.location = (right + pad, -220.0 * i)
    return {"sections": len(frames), "rows": round(-y / max(row_h, 1)) + 1, "nodes": sum(len(p) for p, _, _ in laid)}


def _layered(nodes, tree, gap_x, gap_y):
    """Positions {node: (x, top y)} for a layered layout of `nodes` (links to nodes outside are ignored)."""
    preds = {n: set() for n in nodes}
    for l in tree.links:
        if l.from_node in preds and l.to_node in preds and l.from_node != l.to_node:
            preds[l.to_node].add(l.from_node)
    for n in nodes:
        po = getattr(n, "paired_output", None)
        if po is not None and po in preds:
            preds[po].add(n)
    depth, seen = {}, set()

    def d(n):
        if n in depth:
            return depth[n]
        if n in seen:
            return 0
        seen.add(n)
        depth[n] = 1 + max((d(p) for p in preds[n]), default=-1)
        return depth[n]

    for n in nodes:
        d(n)
    outs = [n for n in nodes if n.bl_idname in ("NodeGroupOutput", "ShaderNodeOutputMaterial",
                                                  "ShaderNodeOutputWorld")]
    last = max(depth.values(), default=0)
    for n in outs:
        depth[n] = max(depth[n], last)
    # pull every node right, next to its first consumer ("as late as possible"): constants and primitives
    # then sit beside the node that uses them, instead of piling up in one tall first column
    succs = {n: [m for m in nodes if n in preds[m]] for n in nodes}
    for n in sorted(nodes, key=lambda n: -depth[n]):
        if succs[n] and n not in outs:
            depth[n] = max(depth[n], min(depth[m] for m in succs[n]) - 1)
    cols = {}
    for n in nodes:
        cols.setdefault(depth[n], []).append(n)
    x = 0.0
    ypos, pos = {}, {}
    for c in sorted(cols):
        col = cols[c]
        col.sort(key=lambda n: (sum(ypos.get(p, 0) for p in preds[n]) / len(preds[n])) if preds[n] else 0,
                 reverse=True)
        # wrap a column taller than MAX_COL into side-by-side sub-columns, so a big Join (twenty emblems,
        # thirty materials) doesn't stretch the section into a thin tower
        chunks, cur, h = [], [], 0.0
        for n in col:
            if cur and h + _est_height(n) > MAX_COL:
                chunks.append(cur)
                cur, h = [], 0.0
            cur.append(n)
            h += _est_height(n) + gap_y
        chunks.append(cur)
        for ch in chunks:
            width = max(n.width for n in ch)
            total = sum(_est_height(n) for n in ch) + gap_y * (len(ch) - 1)
            y = total / 2
            for n in ch:
                pos[n] = (x, y)
                ypos[n] = y - _est_height(n) / 2
                y -= _est_height(n) + gap_y
            x += width + gap_x * (0.5 if ch is not chunks[-1] else 1.0)
    return pos


MAX_COL = 1500.0   # tallest node column before it wraps (node-editor units)


def _layout_key(tree):
    for m in bpy.data.materials:
        if m.node_tree == tree:
            return "MAT:" + m.name
    for w in bpy.data.worlds:
        if w.node_tree == tree:
            return "WORLD:" + w.name
    return "GN:" + tree.name


def layout_save(path, trees):
    """Store node positions and frames of trees tidied in a UI session (where real node sizes exist),
    so a headless rebuild can restore them with layout_load. Keys are node names, which a build script
    creates in the same order every run."""
    import json
    data = {}
    for t in (_tree(t) for t in trees):
        frames = [{"name": n.name, "label": n.label, "label_size": n.label_size, "shrink": n.shrink,
                   "color": list(n.color) if n.use_custom_color else None}
                  for n in t.nodes if n.bl_idname == "NodeFrame"]
        nodes = {n.name: {"loc": [round(n.location_absolute.x, 1), round(n.location_absolute.y, 1)],
                          "parent": n.parent.name if n.parent else None}
                 for n in t.nodes if n.bl_idname != "NodeFrame"}
        data[_layout_key(t)] = {"frames": frames, "nodes": nodes}
    with open(path, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    return {"file": path, "trees": {k: len(v["nodes"]) for k, v in data.items()}}


def layout_load(path):
    """Apply a layout_save file after building (call it in place of / after arrange). Nodes missing
    from the file keep their arranged position. Returns per-tree counts, or None if there is no file."""
    import json
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    res = {}
    for key, d in data.items():
        kind, name = key.split(":", 1)
        owner = {"MAT": bpy.data.materials, "WORLD": bpy.data.worlds}.get(kind, bpy.data.node_groups).get(name)
        t = owner.node_tree if kind in ("MAT", "WORLD") and owner else owner
        if t is None:
            continue
        for n in [n for n in t.nodes if n.bl_idname == "NodeFrame"]:
            t.nodes.remove(n)
        frames = {}
        for fd in d["frames"]:
            fr = t.nodes.new("NodeFrame")
            fr.name, fr.label, fr.label_size, fr.shrink = fd["name"], fd["label"], fd["label_size"], fd["shrink"]
            if fd["color"]:
                fr.use_custom_color, fr.color = True, fd["color"]
            frames[fd["name"]] = fr
        hit = 0
        for name_, nd in d["nodes"].items():
            n = t.nodes.get(name_)
            if n is None or n.bl_idname == "NodeFrame":
                continue
            n.parent = frames.get(nd["parent"])
            n.location_absolute = nd["loc"]
            hit += 1
        res[key] = {"placed": hit, "of": len(t.nodes) - len(frames), "frames": len(frames)}
    return res


# ───────────────────────────────────────────────────────── loop helpers

def loop_clock(frames=None):
    """GN group PA_LoopClock → Phase (0..1, wraps every `Frames`), Angle (0..τ), Sin, Cos.
    Drive anything periodic from Phase/Angle and frame N+1 == frame 1: a seamless loop."""
    frames = frames or bpy.context.scene.get("pa_loop_frames", 120)
    name = P + "LoopClock"
    t = bpy.data.node_groups.get(name)
    if t is not None:
        t.interface.items_tree["Frames"].default_value = frames
        return t
    t = bpy.data.node_groups.new(name, "GeometryNodeTree")
    it = t.interface.new_socket("Frames", in_out="INPUT", socket_type="NodeSocketInt")
    it.default_value, it.min_value = frames, 1
    t.interface.new_socket("Offset", in_out="INPUT", socket_type="NodeSocketFloat")
    for o in ("Phase", "Angle", "Sin", "Cos"):
        t.interface.new_socket(o, in_out="OUTPUT", socket_type="NodeSocketFloat")
    g = Graph(t)
    gin, gout = g.group_io()
    st = g.node("GeometryNodeInputSceneTime")
    f0 = g.math("SUBTRACT", g.out(st, "Frame"), 1.0)
    ph = g.math("FRACT", g.math("ADD", g.math("DIVIDE", f0, gin.outputs["Frames"]), gin.outputs["Offset"]))
    ang = g.math("MULTIPLY", ph, TAU)
    g.link(ph, gout, b_key="Phase")
    g.link(ang, gout, b_key="Angle")
    g.link(g.math("SINE", ang), gout, b_key="Sin")
    g.link(g.math("COSINE", ang), gout, b_key="Cos")
    arrange(t)
    return t


def loop_noise():
    """GN group PA_LoopNoise: 4D noise that loops. Samples W and an extra offset along a circle
    of `Radius` in noise space driven by `Phase` (0..1), so Phase 0 and 1 give identical fields.
    Inputs Vector (defaults to Position), Scale, Detail, Roughness, Radius, Phase → Factor, Color."""
    name = P + "LoopNoise"
    t = bpy.data.node_groups.get(name)
    if t is not None:
        return t
    t = bpy.data.node_groups.new(name, "GeometryNodeTree")
    v = t.interface.new_socket("Vector", in_out="INPUT", socket_type="NodeSocketVector")
    v.default_input = "POSITION"
    v.hide_value = True
    for nm, dv in (("Scale", 3.0), ("Detail", 2.0), ("Roughness", 0.5), ("Radius", 0.6), ("Phase", 0.0)):
        s = t.interface.new_socket(nm, in_out="INPUT", socket_type="NodeSocketFloat")
        s.default_value = dv
    t.interface.new_socket("Factor", in_out="OUTPUT", socket_type="NodeSocketFloat")
    t.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    g = Graph(t)
    gin, gout = g.group_io()
    ang = g.math("MULTIPLY", gin.outputs["Phase"], TAU)
    ox = g.math("MULTIPLY", g.math("COSINE", ang), gin.outputs["Radius"])
    w = g.math("MULTIPLY", g.math("SINE", ang), gin.outputs["Radius"])
    vec = g.vmath("ADD", gin.outputs["Vector"], g.vec(ox, 0.0, 0.0))
    nz = g.node("ShaderNodeTexNoise", props={"noise_dimensions": "4D"}, Vector=vec, W=w,
                Scale=gin.outputs["Scale"], Detail=gin.outputs["Detail"], Roughness=gin.outputs["Roughness"])
    g.link(g.out(nz, "Factor"), gout, b_key="Factor")
    g.link(g.out(nz, "Color"), gout, b_key="Color")
    arrange(t)
    return t


# ───────────────────────────────────────────────────────── materials

PRESETS = {
    "matte":  dict(color=(0.8, 0.8, 0.8), roughness=0.6),
    "clay":   dict(color=(0.75, 0.6, 0.5), roughness=0.75),
    "metal":  dict(color=(0.9, 0.9, 0.9), metallic=1.0, roughness=0.22),
    "brass":  dict(color=(0.89, 0.72, 0.38), metallic=1.0, roughness=0.28),
    "copper": dict(color=(0.95, 0.56, 0.42), metallic=1.0, roughness=0.25),
    "gold":   dict(color=(0.98, 0.73, 0.38), metallic=1.0, roughness=0.12),
    "glass":  dict(color=(1, 1, 1), transmission=1.0, roughness=0.0, ior=1.5),
    "prism":  dict(color=(1, 1, 1), transmission=1.0, roughness=0.0, ior=1.65),
    "pearl":  dict(color=(0.93, 0.9, 0.86), roughness=0.22, coat=1.0, coat_roughness=0.05,
                   thin_film=420.0, thin_film_ior=1.55, subsurface=0.15),
    "nacre":  dict(color=(0.75, 0.75, 0.8), roughness=0.18, metallic=0.4, thin_film=520.0, thin_film_ior=1.6),
    "neon":   dict(color=(0.02, 0.02, 0.02), emission=(1.0, 0.1, 0.35), strength=12.0),
    "biolum": dict(color=(0.02, 0.05, 0.06), emission=(0.1, 1.0, 0.75), strength=4.0, subsurface=0.4),
}


def material(name, kind="matte", **kw):
    """Principled presets: matte clay metal brass copper gold glass prism pearl nacre neon biolum,
    plus kind="xray" (fresnel-rim emission over transparency, for X-ray / Ghost looks).
    Overrides: color, metallic, roughness, transmission, ior, coat, coat_roughness, thin_film (nm),
    thin_film_ior, subsurface, emission (rgb), strength."""
    mname = P + name
    mat = bpy.data.materials.get(mname) or bpy.data.materials.new(mname)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    g = Graph(nt)
    out = g.node("ShaderNodeOutputMaterial")
    if kind == "xray":
        col = kw.get("color", (0.35, 0.75, 1.0))
        lw = g.node("ShaderNodeLayerWeight", Blend=kw.get("blend", 0.35))
        ramp = g.node("ShaderNodeValToRGB")
        g.link(g.out(lw, "Facing"), ramp, b_key="Fac")
        em = g.node("ShaderNodeEmission", Color=col, Strength=g.math("MULTIPLY", g.out(ramp, "Color"),
                                                                       kw.get("strength", 3.0)))
        tr = g.node("ShaderNodeBsdfTransparent")
        add = g.node("ShaderNodeAddShader", ins={0: em, 1: tr})
        g.link(add, out, b_key="Surface")
        try:
            mat.surface_render_method = "BLENDED"
        except (AttributeError, TypeError):
            pass
        arrange(nt)
        return mat
    spec = {**PRESETS[kind], **kw}
    p = g.node("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*spec.get("color", (0.8, 0.8, 0.8)), 1)
    for key, sock in (("metallic", "Metallic"), ("roughness", "Roughness"), ("transmission", "Transmission Weight"),
                      ("ior", "IOR"), ("coat", "Coat Weight"), ("coat_roughness", "Coat Roughness"),
                      ("thin_film", "Thin Film Thickness"), ("thin_film_ior", "Thin Film IOR"),
                      ("subsurface", "Subsurface Weight"), ("strength", "Emission Strength")):
        if key in spec:
            p.inputs[sock].default_value = spec[key]
    if "emission" in spec:
        p.inputs["Emission Color"].default_value = (*spec["emission"], 1)
    g.link(p, out, b_key="Surface")
    arrange(nt)
    return mat


def set_material(graph, geometry, mat):
    """Insert a Set Material node after `geometry` in a GN graph; returns the node."""
    return graph.node("GeometryNodeSetMaterial", Geometry=geometry,
                      Material=bpy.data.materials[mat] if isinstance(mat, str) else mat)


# ───────────────────────────────────────────────────────── studio

def _bbox(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for ob in objs:
        ev = ob.evaluated_get(dg)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c)
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    if lo.x > hi.x:
        lo, hi = Vector((-1, -1, -1)), Vector((1, 1, 1))
    return lo, hi


def _area_light(name, coll, size, loc, target, power, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape, ld.size, ld.energy, ld.color = "RECTANGLE", size[0], power, color
    ld.size_y = size[1]
    ob = bpy.data.objects.new(name, ld)
    coll.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


WORLD = {"dark": (0.006, 0.006, 0.007), "light": (0.72, 0.72, 0.7), "void": (0.0, 0.0, 0.0),
         "warm": (0.05, 0.035, 0.025), "cool": (0.02, 0.03, 0.05)}


def studio(piece_name, style="dark", view="three_quarter", lens=85, margin=1.15, floor=True,
           light=1.0, focus=None):
    """Camera + 3 area lights + world + optional floor around PA_<piece_name>.
    style: dark | light | void (no floor, black) | warm | cool.  view: three_quarter | front |
    top | side | low | high.  The camera hangs off PA_Pivot (at the piece centre) so
    turntable() can spin it.  focus: object names to frame instead of the whole piece."""
    sc = bpy.context.scene
    st = _coll(P + "Studio")
    _clear_coll(st)
    for n in (P + "Pivot",):
        if n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    objs = [bpy.data.objects[n] for n in focus] if focus else \
        [o for o in bpy.data.collections[P + piece_name].all_objects if o.type in ("MESH", "CURVES", "CURVE",
                                                                                 "VOLUME", "POINTCLOUD")]
    lo, hi = _bbox(objs)
    ctr, r = (lo + hi) / 2, max((hi - lo).length / 2, 1e-3)

    pivot = bpy.data.objects.new(P + "Pivot", None)
    st.objects.link(pivot)
    pivot.location = ctr
    cam_d = bpy.data.cameras.new(P + "Camera")
    cam_d.lens, cam_d.sensor_width = lens, 36
    cam_d.clip_start, cam_d.clip_end = r * 0.01, r * 200
    cam = bpy.data.objects.new(P + "Camera", cam_d)
    st.objects.link(cam)
    az, el = {"three_quarter": (35, 22), "front": (0, 6), "top": (0, 89), "side": (90, 8),
              "low": (28, 4), "high": (25, 50)}.get(view, (35, 22))
    az, el = math.radians(az), math.radians(el)
    direction = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    rx, ry = sc.render.resolution_x, sc.render.resolution_y
    t_long = 18 / lens                                   # sensor fit AUTO: 36 mm spans the long side
    t_short = t_long * min(rx, ry) / max(rx, ry)
    tx, ty = (t_long, t_short) if rx >= ry else (t_short, t_long)
    rot = (-direction).to_track_quat("-Z", "Y").to_matrix()
    right, up = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
    corners = [Vector((x, y, z)) - ctr for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    dist = max(max(abs(p.dot(right)) / tx, abs(p.dot(up)) / ty) * margin + p.dot(direction) for p in corners)
    cam.parent = pivot
    cam.location = direction * dist
    con = cam.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = pivot, "TRACK_NEGATIVE_Z", "UP_Y"
    sc.camera = cam

    S = r * 2
    k = 60.0 * S * S * light
    _area_light(P + "Key", st, (S * 1.6, S * 1.0), ctr + Vector((-1.8 * S, -1.4 * S, 1.6 * S)), ctr, k)
    _area_light(P + "Rim", st, (S * 1.6, S * 0.4), ctr + Vector((0.8 * S, 2.0 * S, 1.2 * S)), ctr, k * 0.9)
    _area_light(P + "Fill", st, (S * 1.4, S * 1.4), ctr + Vector((2.0 * S, -1.0 * S, 0.6 * S)), ctr, k * 0.25)

    world = bpy.data.worlds.get(P + "World") or bpy.data.worlds.new(P + "World")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*WORLD[style], 1)
    bg.inputs["Strength"].default_value = 1.0
    sc.world = world

    if floor and style != "void":
        me = bpy.data.meshes.new(P + "Floor")
        F = S * 60
        me.from_pydata([(-F, -F, 0), (F, -F, 0), (F, F, 0), (-F, F, 0)], [], [(0, 1, 2, 3)])
        fl = bpy.data.objects.new(P + "Floor", me)
        st.objects.link(fl)
        fl.location.z = lo.z - S * 0.002
        fm = material("Floor_" + style, "matte", color=WORLD[style] if style != "light" else (0.7, 0.7, 0.68),
                      roughness=0.35 if style in ("dark", "warm", "cool") else 0.6)
        me.materials.append(fm)
    return {"camera": cam.name, "center": [round(c, 3) for c in ctr], "radius": round(r, 3),
            "distance": round(dist, 3), "style": style}


def caustics(casters, receivers, lights=None):
    """Cycles MNEE shadow caustics (sharp refractive caustics through glass/water onto receivers).
    casters/receivers/lights: object names. Lights default to every light in PA_Studio.
    Casters need smooth normals and low roughness; MNEE only finds paths through ONE refractive surface pair."""
    for n in casters:
        bpy.data.objects[n].cycles.is_caustics_caster = True
    for n in receivers:
        bpy.data.objects[n].cycles.is_caustics_receiver = True
    lights = lights or [o.name for o in bpy.data.collections[P + "Studio"].objects if o.type == "LIGHT"]
    for n in lights:
        bpy.data.objects[n].data.cycles.is_caustics_light = True
    sc = bpy.context.scene
    sc.cycles.caustics_refractive = sc.cycles.caustics_reflective = True
    return {"casters": casters, "receivers": receivers, "lights": lights}


def turntable(mode="spin", degrees=360.0, turns=1):
    """Animate PA_Pivot with a driver (no keyframes): mode spin = `turns`×`degrees` per loop;
    swing = ±degrees/2 sine sway. Both loop perfectly over the scene's frame range."""
    sc = bpy.context.scene
    pv = bpy.data.objects[P + "Pivot"]
    n = sc.frame_end - sc.frame_start + 1
    pv.driver_remove("rotation_euler", 2)
    fc = pv.driver_add("rotation_euler", 2)
    rad = math.radians(degrees)
    if mode == "spin":
        fc.driver.expression = f"(frame - {sc.frame_start}) / {n} * {rad * turns:.6f}"
    else:
        fc.driver.expression = f"sin((frame - {sc.frame_start}) / {n} * {TAU:.6f}) * {rad / 2:.6f}"
    return {"expression": fc.driver.expression, "frames": n}


# ───────────────────────────────────────────────────────── post FX (Blender 5.x compositor)

def post(bloom=0.0, fog=0.0, halation=0.0, streaks=0.0, sunbeams=None, chromatic=0.0, threshold=0.8,
         exposure=0.0):
    """Compositor chain in node group PA_Post (scene.compositing_node_group; 5.x has no Composite node).
    bloom/fog/streaks: Glare strength.  halation: red-orange Fog Glow (film halation).
    sunbeams: (x, y[, strength=0.35]) source in 0..1 image space.  chromatic: Lens Distortion dispersion (0.01–0.08).
    All zeros removes the effects (keeps a pass-through)."""
    sc = bpy.context.scene
    ng = bpy.data.node_groups.get(P + "Post")
    if ng is None:
        ng = bpy.data.node_groups.new(P + "Post", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    ng.nodes.clear()
    g = Graph(ng)
    cur = g.out(g.node("CompositorNodeRLayers"), "Image")
    used = []

    def glare(kind, strength, **kw):
        n = g.node("CompositorNodeGlare", Image=cur)
        n.inputs["Type"].default_value = kind
        n.inputs["Strength"].default_value = strength
        n.inputs["Threshold"].default_value = kw.pop("thr", threshold)
        for k2, v in kw.items():
            g.set(n, k2, v)
        used.append(kind)
        return g.out(n, "Image")

    if exposure:
        cur = g.out(g.node("CompositorNodeExposure", Image=cur, Exposure=exposure), "Image")
    if bloom:
        cur = glare("Bloom", bloom, Size=0.6)
    if fog:
        cur = glare("Fog Glow", fog, Size=0.5)
    if halation:
        cur = glare("Fog Glow", halation, Tint=(1.0, 0.28, 0.12), Size=0.35, thr=threshold * 0.7)
    if streaks:
        cur = glare("Streaks", streaks, Streaks=6)
    if sunbeams:
        sx, sy, *ss = sunbeams
        cur = glare("Sun Beams", ss[0] if ss else 0.35, Sun_Position=(sx, sy), Size=0.6, thr=threshold * 0.5)
    if chromatic:
        ld = g.node("CompositorNodeLensdist", Image=cur, Dispersion=chromatic)
        cur = g.out(ld, "Image")
        used.append("Lens Distortion")
    gout = g.node("NodeGroupOutput")
    ng.links.new(cur, gout.inputs["Image"])
    sc.compositing_node_group = ng
    sc.render.use_compositing = True
    arrange(ng)
    return {"group": ng.name, "effects": used}


# ───────────────────────────────────────────────────────── render

def output(path, kind="video", crf="HIGH"):
    """Configure output only (so a saved .blend renders with `Blender -b file.blend -a`).
    kind: video (H.264 MP4) | png (sequence, path should end with '_' or '####')."""
    sc = bpy.context.scene
    r = sc.render
    r.filepath = path
    im = r.image_settings
    if kind == "video":
        im.media_type = "VIDEO"
        im.file_format = "FFMPEG"
        r.ffmpeg.format, r.ffmpeg.codec = "MPEG4", "H264"
        r.ffmpeg.constant_rate_factor = crf
        r.ffmpeg.ffmpeg_preset = "GOOD"
        r.ffmpeg.audio_codec = "NONE"
    else:
        im.media_type = "IMAGE"
        im.file_format = "PNG"
    return {"filepath": path, "kind": kind}


def render_still(path, frame=None, samples=None):
    """Render one frame to PNG (blocks; keep MCP calls short: ≤ ~60 s)."""
    sc = bpy.context.scene
    if frame is not None:
        sc.frame_set(frame)
    if samples:
        if sc.render.engine == "CYCLES":
            sc.cycles.samples = samples
        else:
            sc.eevee.taa_render_samples = samples
    im = sc.render.image_settings
    old = (im.media_type, im.file_format, sc.render.filepath)
    im.media_type, im.file_format = "IMAGE", "PNG"
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    im.media_type, im.file_format, sc.render.filepath = old[0], old[1], old[2]
    return {"file": path, "seconds": round(time.time() - t, 1),
            "resolution": [sc.render.resolution_x, sc.render.resolution_y]}


def preview(path, scale=50, samples=16, frame=None):
    """Cheap look-dev still: EEVEE, reduced resolution and samples; restores settings after."""
    sc = bpy.context.scene
    keep = (sc.render.engine, sc.render.resolution_percentage, sc.eevee.taa_render_samples)
    sc.render.engine, sc.render.resolution_percentage = "BLENDER_EEVEE", scale
    sc.eevee.taa_render_samples = samples
    try:
        return render_still(path, frame=frame)
    finally:
        sc.render.engine, sc.render.resolution_percentage, sc.eevee.taa_render_samples = keep


def render_loop(path, samples=None, gif_width=0):
    """Render the frame range to H.264 MP4 (blocks for the whole range: prefer saving the .blend
    and running `Blender -b file.blend -a` in the background). gif_width>0 also writes a GIF
    with ffmpeg (palette-optimised) next to the MP4."""
    sc = bpy.context.scene
    if samples:
        if sc.render.engine == "CYCLES":
            sc.cycles.samples = samples
        else:
            sc.eevee.taa_render_samples = samples
    output(path, "video")
    t = time.time()
    bpy.ops.render.render(animation=True)
    res = {"file": path, "seconds": round(time.time() - t, 1), "frames": sc.frame_end - sc.frame_start + 1}
    if gif_width:
        res["gif"] = to_gif(path, gif_width, sc.render.fps)
    return res


def to_gif(mp4, width=720, fps=30):
    ff = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    gif = os.path.splitext(mp4)[0] + ".gif"
    vf = f"fps={min(fps, 25)},scale={width}:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];" \
         f"[b][p]paletteuse=dither=sierra2_4a"
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", mp4, "-vf", vf, gif], check=True)
    return gif


# ───────────────────────────────────────────────────────── node screenshot (needs the UI)

def _tree(tree):
    if isinstance(tree, str):
        tree = bpy.data.node_groups.get(tree) or bpy.data.materials[tree].node_tree
    return tree


def show_tree(tree, area=None):
    """Turn the largest area (or `area`) into a node editor pinned to `tree`. Returns (win, area, old_ui)."""
    tree = _tree(tree)
    win = bpy.context.window_manager.windows[0]
    area = area or max(win.screen.areas, key=lambda a: a.width * a.height)
    old_ui = area.ui_type
    area.ui_type = tree.bl_idname          # GeometryNodeTree | ShaderNodeTree | CompositorNodeTree
    space = area.spaces.active
    space.pin = True
    space.node_tree = tree
    for attr in ("show_region_ui", "show_region_toolbar", "show_region_asset_shelf"):
        try:
            setattr(space, attr, False)
        except (AttributeError, TypeError):       # read-only in some editors (asset shelf, 5.2)
            pass
    return win, area, old_ui


def _in_region(win, area, op, **kw):
    region = next(r for r in area.regions if r.type == "WINDOW")
    with bpy.context.temp_override(window=win, area=area, region=region):
        return op(**kw)


def frame_tree(win, area):
    """View All without the smooth-view animation (otherwise a screenshot catches it mid-zoom)."""
    view = bpy.context.preferences.view
    keep = view.smooth_view
    view.smooth_view = 0
    try:
        _in_region(win, area, bpy.ops.node.view_all)
    finally:
        view.smooth_view = keep


def node_screenshot(tree, path):
    """Screenshot a node tree in this Blender UI session (e.g. over Blender MCP), then restore the
    area. Background mode cannot draw: use scripts/node_shot.py on the saved .blend instead.
    Call arrange(tree) first for generated trees."""
    if bpy.app.background:
        raise RuntimeError("node_screenshot needs the Blender UI; run scripts/node_shot.py on the saved .blend")
    tree = _tree(tree)
    win, area, old_ui = show_tree(tree)
    for _ in range(2):          # the region must be drawn once before View All knows its size
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
        frame_tree(win, area)
    bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
    _in_region(win, area, bpy.ops.screen.screenshot_area, filepath=path)
    area.spaces.active.pin = False
    area.ui_type = old_ui
    return {"file": path, "tree": tree.name, "size": [area.width, area.height]}


# ───────────────────────────────────────────────────────── audit

_NOTABLE = {"GeometryNodeRepeatInput": "repeat zone", "GeometryNodeSimulationInput": "simulation zone",
            "GeometryNodeForeachGeometryElementInput": "for-each zone", "NodeClosureInput": "closure",
            "NodeCombineBundle": "bundle", "GeometryNodeXPBDSolver": "XPBD solver",
            "GeometryNodeMeshToSDFGrid": "SDF grid", "GeometryNodeSDFGridBoolean": "SDF boolean",
            "GeometryNodeGridAdvect": "grid advect", "GeometryNodeRaycast": "raycast",
            "GeometryNodeInputShortestEdgePaths": "shortest paths", "GeometryNodeDualMesh": "dual mesh",
            "GeometryNodeFieldToList": "lists", "GeometryNodeSampleSoundFrequencies": "sound sampling",
            "GeometryNodeStringToCurves": "string to curves", "GeometryNodeVolumeToMesh": "volume to mesh"}


def _walk(tree, seen):
    if tree is None or tree.name in seen:
        return
    seen[tree.name] = tree
    for n in tree.nodes:
        if getattr(n, "node_tree", None) is not None:
            _walk(n.node_tree, seen)


def describe(tree):
    """Counts for captions: nodes (incl. nested groups), groups, notable techniques."""
    tree = bpy.data.node_groups[tree] if isinstance(tree, str) else tree
    seen = {}
    _walk(tree, seen)
    nodes = [n for t in seen.values() for n in t.nodes if n.bl_idname not in ("NodeFrame", "NodeReroute")]
    notable = sorted({_NOTABLE[n.bl_idname] for n in nodes if n.bl_idname in _NOTABLE})
    return {"tree": tree.name, "nodes": len(nodes), "groups": len(seen) - 1, "techniques": notable}


def audit(piece_name=None):
    """Procedural-purity check for 'nodes only' constraints. Flags hand-made mesh data, sculpt /
    multires, shape keys, image textures, imported files, and non-PA objects pulled into node trees."""
    sc = bpy.context.scene
    objs = list(bpy.data.collections[P + piece_name].all_objects) if piece_name else \
        [o for o in sc.objects if not o.name.startswith(P + "Studio")]
    issues, notes, trees = [], [], {}
    for ob in objs:
        mods = [m.type for m in ob.modifiers]
        if ob.type == "MESH":
            nv = len(ob.data.vertices)
            if nv and "NODES" not in mods:
                issues.append(f"{ob.name}: modelled mesh ({nv} verts) without Geometry Nodes")
            elif nv > 8:
                notes.append(f"{ob.name}: base mesh has {nv} verts (fine only if it is a primitive)")
            if ob.data.shape_keys:
                issues.append(f"{ob.name}: shape keys")
        elif ob.type in ("CURVE", "CURVES", "GREASEPENCIL", "SURFACE", "META"):
            if "NODES" not in mods:
                issues.append(f"{ob.name}: {ob.type.lower()} object with hand-made data")
        for m in ob.modifiers:
            if m.type in ("MULTIRES",):
                issues.append(f"{ob.name}: sculpt (multires)")
            if m.type == "NODES" and m.node_group:
                _walk(m.node_group, trees)
        for slot in ob.material_slots:
            if slot.material and slot.material.node_tree:
                _walk(slot.material.node_tree, trees)
    for t in list(trees.values()):
        for n in t.nodes:
            img = getattr(n, "image", None)
            if img is not None and img.source != "GENERATED":
                issues.append(f"{t.name}/{n.name}: image texture '{img.name}'")
            if n.bl_idname.startswith("GeometryNodeImport"):
                issues.append(f"{t.name}/{n.name}: imports external file")
            if n.bl_idname in ("GeometryNodeObjectInfo", "GeometryNodeCollectionInfo"):
                notes.append(f"{t.name}/{n.name}: references scene data — check it is procedural too")
    if sc.world and sc.world.node_tree:
        for n in sc.world.node_tree.nodes:
            if n.bl_idname == "ShaderNodeTexEnvironment" and n.image:
                notes.append(f"world uses HDRI '{n.image.name}' (lighting only; state it if strict)")
    return {"strict_procedural": not issues, "issues": issues, "notes": notes, "trees": sorted(trees)}


def save(path):
    """Save a copy of the current file (keeps the user's open file path unchanged). An absolute render
    output path inside the save folder is stored relative (//loop.mp4), so the folder can be moved."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    r = bpy.context.scene.render
    keep = r.filepath
    folder = os.path.dirname(os.path.abspath(path))
    if os.path.isabs(keep) and os.path.dirname(os.path.abspath(keep)).startswith(folder):
        r.filepath = "//" + os.path.relpath(keep, folder)
    try:
        bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
    finally:
        r.filepath = keep
    return {"file": path}
