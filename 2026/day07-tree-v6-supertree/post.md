# Nodevember 2026 · Day 07 · Tree

## Concept

**雨後甦醒 / After the Rain — Supertree**

Eleven living steel trees fill an imagined Singapore garden at blue hour. Violet-white light rises through curved, flaring canopies; a suspended skyway ascends from the complete tree on the left to a much nearer tree cropped at the right edge.

- Reading: lateral — a human-built tree becomes a living vertical garden.
- References: a user-supplied photo (not included here), and [Gardens by the Bay — Supertree Grove](https://www.gardensbythebay.com.sg/en/things-to-do/attractions/supertree-grove.html). The structural engineer’s [project page](https://www.atelierone.com/gardens-by-the-bay/) was also consulted for context. This is an artistic interpretation, not a measured site reconstruction.
- Constraint: every visible mesh is generated in Geometry Nodes from an empty base mesh. No imported models, image textures, simulation or keyframes. The reference images are not loaded into the scene.
- Outputs: square 1440² hero and an editable scene containing a one-shot light awakening, 8 seconds / 24 fps / 192 frames, with a final hold.

## Shape

The luminous skin is a quarter-ellipse surface of revolution. Its neck has a vertical tangent and its upper lip opens almost horizontally. Above it is a wide, three-level dark cap; an open metal branch fringe extends well beyond the light bowl.

- Light bowl diameter: approximately 51% of the full outer crown diameter.
- Dark cap diameter: approximately 57% of the full crown diameter.
- Main light bowl: approximately 20 m wide and 10 m high; the full branch crown is approximately 39 m wide.
- A short exposed neck separates the light bowl from the larger circular visitor platform.

The skin has 64 meridian samples and 193 circumferential samples, parameterised from the flat grid's actual X/Y coordinates to avoid erroneous long bridge faces. `inspect/shape-side.png` isolates the light skin; `inspect/crown-side.png` shows the complete crown and dark cap. The saved `.blend` retains the full perspective scene.

## Build

- Eleven towers share one six-input architecture group: Height, Crown Radius, Ribs, Plant Density, Lighting Delay, Seed.
- One shared profile group (`PA_CrownProfile`) places the light skin, its rim, the curved ribs and every branch station, so the steel and the light always stay together. The outer branching of each rib is one `PA_RibModule`, used as a module and its mirror image.
- Each tree has 32 curved primary ribs, splitting into 64 long outer members, with 64 L/Y side branches and 64 short, staggered cross-members. The bars use flat box-like sections. There are no complete outer circumferential rings and no material-only fake rib stripes on the light skin. Seven visual review rounds are preserved in `review/structure/`.
- Fern leaflets become paired fronds and seeded plant clusters around the trunks. Layered procedural tree masses fill the garden below.
- The skyway follows an analytic cubic curve, with a continuous deck, rails, pickets, suspension cables and five small visitors.
- Stored `flow` and `delay` attributes drive the ascending light front. Area-light drivers supply matching coloured spill.
- Distant buildings, triangular conservatory domes, wet pavers, low mist and blue-hour clouds are generated with nodes and procedural shaders. A continuous distant ground extends from y=125 to 1200 m; tower foundations sample the same height field and sit 0.35 m into it, with a low irregular tree belt in front. Distant land fades into blue-hour haze; the camera far clip extends to 1600 m so that the terrain is not visibly cut off.
- The 24 mm perspective camera is elevated 10 m to show the layers of the garden. The right foreground canopy deliberately extends outside the frame.
- Renderer: Blender 5.2.3 / EEVEE. Hero: 1440², 96 samples. Animation: 960², 64 samples, 192 frames, rendered on the LAN renderfarm from the current scene.

## Files

| Path | What it is |
|---|---|
| `piece.blend` | complete editable scene; opens on hero frame 168 |
| `render.png` | 1440² hero, 96 samples |
| `awakening.mp4` · `awakening.gif` | 960², 192 frames / 24 fps / 8 s, 64 EEVEE samples on the LAN renderfarm; 480² / 12 fps GIF preview |
| `storyboard.jpg` | nine checkpoints from the final frames |
| `nodes.png` | `PA_SupertreeArchitecture`, the tree group (the main node screenshot for posts) |
| `nodes-profile.png` · `nodes-frame.png` · `nodes-module.png` | crown profile, crown framework and rib module groups |
| `nodes-plants.png` · `nodes-skyline.png` | fern rosette group; garden, land and skyline tree |
| `tutorial/` | node-by-node walkthrough (`README.md`, 50 images, `figs.json`, `src/concept_figs.py`) |
| `build.py` · `render.py` · `verify.py` · `finish.py` | build the scene · render hero / storyboard / frames · check the saved file · encode and check the video |
| `checks/` | `audit.json`, `verification.json`, `verification-smallest.json`, `skyline-inspection.json`, `video-verification.json`, `video-signalstats.txt`, render manifest and progress |
| `inspect/` | isolated inspection renders (`shape-side`, `crown-side`, `structure`, `structure-bay`) and review sheets (`iteration-sheet`, `skyline-before-after`) |
| `tools/` | `make_storyboard.py` (Pillow), `inspect_skyline.py` (Blender) |
| `review/` | nine storyboard frames and `structure/`: seven structural review rounds with `review.md` |
| `frames/` | the 192 rendered PNGs (not included) |

## Validation

The saved scene passes the procedural audit: empty, node-driven mesh bases; no simulation nodes, keyframe actions or external image files. Evaluated structural coordinates are finite. Crown-light drivers are checked at five timeline positions.

The actual evaluated light skin is also checked separately. Its vertices must match the quarter-ellipse relation within 0.0001, and no mesh edge may exceed 1 m; this rules out erroneous long neck-to-rim bridge faces. Measured values are recorded in `checks/verification.json` and `checks/video-verification.json`. The orthographic side render is visually checked before the full scene render.

The final framework centreline is one connected graph: 1,984 vertices, 2,048 edges, 128 terminal tips and 256 three-way joints. It contains 32 primary ribs, 64 long outer members, 64 short side branches and 64 short cross-members. A conservative outer-member intersection check, excluding the joined neighbourhoods, detects no unintended intersections. This is visual topology and clearance validation, not an engineering load assessment.

Seven rounds of reference comparison, including rejected regular-grid variants, are documented in `review/structure/review.md`. The smallest background preset is also checked in `checks/verification-smallest.json`; section sizes reduce with crown size and rib density to retain clearance. Both saved presets pass.

The skyline is checked against the evaluated terrain mesh at the centre and four footprint corners of each of the 36 buildings. `checks/skyline-inspection.json` records these 180 surface samples.

The animation is a one-shot event; no seamless-loop claim is made. Video decoding and frame-count results are recorded in `checks/video-verification.json`.

## Caption

雨後甦醒 / After the Rain

雨停了，花園開始呼吸。

Violet-white light opens through curved steel canopies and travels across a suspended skyway.
An imagined Supertree Grove, inspired by Singapore's Gardens by the Bay.

Nodevember 2026 · Day 07 — Tree
Blender Geometry Nodes / EEVEE. All geometry is node-generated; no imported models, image textures, simulation or keyframes.

#nodevember #nodevember2026 #b3d #geometrynodes

## Alt text

At blue hour, eleven tree-shaped towers rise above a dark tropical garden. Their planted trunks flare into broad curved canopies, with black radial ribs silhouetted against violet-white light panels. A complete large tree stands on the left, while a nearer tree is cropped along the right and top edges. A pink-and-gold skyway climbs diagonally between them. Smaller trees, a distant skyline and triangular glass domes form the background; wet paths reflect the coloured light below.

藍調時刻，十一棵擎天樹從深色花園中升起。包覆植栽的樹幹向外彎展成寬闊傘冠，黑色肋條沿著紫白色發光弧面延伸。左側主樹完整入鏡，右側近景大樹被畫面裁切；粉紫與暖金色步道斜向連接兩者。較小的樹群、城市天際線與三角格網玻璃穹頂在後方展開，雨後地面反射燈光。

## Rebuild

Run from the repository root:

```sh
B=/Applications/Blender.app/Contents/MacOS/Blender
D=2026/day07-tree-v6-supertree
$B -b --factory-startup --python $D/build.py -- --preview --shape --structure   # piece.blend, checks/audit.json, preview, inspect/
$B -b --factory-startup --python $D/build.py -- --hero                           # render.png, 1440², 96 samples
$B -b $D/piece.blend --python $D/verify.py                                       # checks/verification.json
$B -b $D/piece.blend --python $D/tools/inspect_skyline.py                        # checks/skyline-inspection.json
$B -b $D/piece.blend --python $D/render.py -- --animation                        # frames/ (local, resumable)
python3 $D/finish.py                                                             # awakening.mp4 / .gif, checks/video-verification.json
uv run --with pillow python $D/tools/make_storyboard.py                          # storyboard.jpg, review/
```

The skyway is composed for the saved tree positions and dimensions: its ends sit on the balconies of trees 01 and 02 (0.58 × Height). If changing those dimensions or positions, update `BRIDGE` as well. The renderer skips completed sequence frames and refuses frames from a different scene; move the previous `frames/` folder aside before rendering a changed scene.

## Posting

- [ ] Posted by the user.
