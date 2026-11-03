# Nodevember 2026 · Day 01 · Origami

Date: 2026-11-01  ·  Folder: 2026/day01-origami

## Idea
- Reading of the prompt (literal / lateral / personal): Literal, but as a story: the most universal origami there is, folded by itself.
- One-sentence concept: A washi sheet on a stack folds itself into a paper plane and flies out of frame; the identical sheet underneath makes the loop seamless.
- Constraint I'm stating in the caption: Geometry Nodes + shader nodes only, no image textures, no hand modelling, seamless loop
- Technique to learn or show off: Sequential flat folds: each fold rotates the points on one side of a crease (current desk coordinates) about that line; vertices near the crease snap onto it for clean edges; flap height = (max z + flap max z + gap)/2. Seigaiha print + M/V backside in one shader from a stored 'flat' attribute.
- Output: loop, 240 frames @ 30 fps (8 s), 1:1 1080×1080, Cycles

## Build log
- v1 (v1-miura/): Miura-ori tessellation breathing open and shut. Read as a tech demo, little artistic value, so it was kept and replaced.
- v2: paper plane. Crease snapping + 0.05 mm layer gap + flat shading removed the sawtooth fold edges.
- Cycles ignores a stored attribute named 'uv' (reserved); renamed to 'flat'.
- Metal kernel specialisation crashed mid-render; render_frames.sh (PNG sequence, retries, kernel optimisation OFF) fixed it.

## Files
- [x] build.py → origami.blend
- [x] hero still: _still_086.png (dart with arrow) or _still_160.png (lift-off)
- [x] loop.mp4 (1:1, 240 frames, seamless)
- [x] nodes.png + nodes_fold.png (framed layout, kept in nodes_layout.json)
- [x] tutorial/README.md: node-by-node walkthrough with screenshots and diagrams

## Caption
```
──── mastodon 421/500 chars
Nodevember 2026 · Day 01: Origami | Paper plane

A sheet of washi folds itself into a plane and flies off the stack; the next sheet is already waiting. Seven folds, each one rotation about a crease line.

Rules: Geometry Nodes + shader nodes only, no image textures, no hand modelling, seamless loop

Made with Blender Geometry Nodes, Cycles.

@Nodevember@graphics.social

#nodevember #nodevember2026 #GeometryNodes #b3d

──── bluesky 261/300 chars
Nodevember 2026 · Day 01: Origami | Paper plane

Rules: Geometry Nodes + shader nodes only, no image textures, no hand modelling, seamless loop

Made with Blender Geometry Nodes, Cycles.

@nodevember.bsky.social

#nodevember #nodevember2026 #GeometryNodes #b3d

──── x 249/280 chars
Nodevember 2026 · Day 01: Origami | Paper plane

Rules: Geometry Nodes + shader nodes only, no image textures, no hand modelling, seamless loop

Made with Blender Geometry Nodes, Cycles.

@Nodevember

#nodevember #nodevember2026 #GeometryNodes #b3d

──── instagram 407/2200 chars
Nodevember 2026 · Day 01: Origami | Paper plane

A sheet of washi folds itself into a plane and flies off the stack; the next sheet is already waiting. Seven folds, each one rotation about a crease line.

Rules: Geometry Nodes + shader nodes only, no image textures, no hand modelling, seamless loop

Made with Blender Geometry Nodes, Cycles.

@nodevemberio

#nodevember #nodevember2026 #GeometryNodes #b3d

──── ba 
TITLE: Nodevember 2026 · Day 01 · Origami | Paper plane
TAGS: nodevember, geometry-nodes, procedural

A sheet of washi folds itself into a plane and flies off the stack; the next sheet is already waiting. Seven folds, each one rotation about a crease line.

Rules: Geometry Nodes + shader nodes only, no image textures, no hand modelling, seamless loop

Made with Blender Geometry Nodes, Cycles.

(render / loop here)

Node tree:

(nodes.png here)

Breakdown: (2–4 bullets on the key trick)
```

## Alt text
- Top-down view of a cream washi sheet printed with indigo wave (seigaiha) pattern on a small stack of sheets on a walnut desk. It folds corners and edges into a dart, folds in half, the wings drop, it stands up and flies away toward the top of the frame, revealing the next sheet.

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted
