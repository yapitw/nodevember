# Nodevember 2026 · Day 02 · Furniture (v3) · A day in the corner

Date: 2026-11-04  ·  Folder: 2026/day02-furniture-v3-corner

## Idea
- Reading of the prompt: literal, as interior styling. Furniture is how it sits in a room and how light moves across it. The piece is about materials and home decor.
- One-sentence concept: A reading corner on a seamless limewash set. One window, out of frame, is the only sun. Over 10 seconds it crosses the corner from morning raking light to a golden window on the wall. The lamp clicks on at blue hour, the moon comes through the same window, and the morning comes back.
- Constraint I'm stating in the caption: Geometry Nodes + shader nodes only, no image textures, no hand modelling, seamless loop.
- Technique to learn or show off:
  - Eight procedural materials under changing light (see Materials below).
  - One sweep for the chair shell.
  - Lathes with per-corner fillets.
  - A knit pillow inflated from a grid.
  - About 13 000 pampas fibres instanced on Bézier stems.
- Output: loop, 300 frames @ 30 fps (10 s), 1:1 1080×1080, Cycles 96 samples.

## Materials (all shader nodes)
| object | material | how |
|---|---|---|
| barrel chair | bouclé | `PA_Boucle` pushes a dense mesh out into loops (Voronoi cells, noise-jittered, 2 mm). The shader repeats the same cells for bump, adds smaller loops and fuzz, darkens between loops, sheen 0.9. |
| lumbar pillow | chunky knit | stockinette Vs built from `|fract(u·9) − ½|` and `v·8`, pushed 9 mm out of an inflated grid, mirrored and merged at the seam. |
| side table, legs | walnut | growth rings around a vertical tree axis just off centre: end grain on the top, straight grain down the turned column. Noise-warped, with latewood and pores, satin coat. |
| lamp base | travertine | bedding layers (noise squashed in z) and vugs (Voronoi masked by noise), honed. |
| lamp shade | pleated linen | 40 pleats from a zigzag ring swept up a tapering line. Diffuse outside, translucent through, with thick weft slubs letting less light through. |
| rug | wool | Beni Ourain-style: a wobbly, broken diamond lattice, rust dots picked by a cell hash, a rust band, dye-lot streaks, pile bump. Fringe is curves. |
| floor vase | sage glaze | drips from vertically stretched noise, a glaze line with a bare clay foot, glossy coat. |
| set | limewash | cloudy noise plus brush strokes, one sweep from floor to wall (no horizon line). |

## The day
- The lighting is functions of the frame, not keyframes. Every light property has a driver whose expression is written in `build.py`. They are Blender "simple expressions", so a plain `Blender -b` render evaluates them without enabling Python auto-run, and frame 301 = frame 1.
  - Sun: heading `lerp(-15°, 55°, u^1.3)`, elevation `24°·sin(πu)^0.85`, where `u` = sun progress from rise to set. Strength fades at the horizon, and colour temperature follows elevation.
  - Lamp: on at t = 0.565, off at 0.935.
  - Moon: a faint 9000 K sun through the same window.
  - Camera: exposure +1 EV and white balance 6500 → 3900 K at night, so it re-meters like a phone camera.
- The sky is world shader nodes. One driven Value node (`fmod(frame-1, 300)/300`) feeds nine smoothstep Map Ranges and chained Mix nodes, which give the colour and strength through 10 keys. A single driver expression cannot hold that curve, because drivers are limited to 256 characters.
- Open the Drivers editor to read or change any of them. Scrubbing the timeline evaluates them live.
- The window is a wall with a 2 × 3 pane opening at x = −2.7 m. It is invisible to camera and reflections but blocks the sun, so the sun can only reach the corner through it.

## Build log
- The first previews had the camera on the right. Light from the left meant we saw only the shadow sides of everything, so the camera moved to the window side.
- Cycles does not render GN curves on a mesh object. Pampas and fringe are Curves (hair) objects.
- Curve to Mesh no longer uses the curve radius (5.x has a Scale input). The lamp shade first came out 2 m wide.
- A sweep profile's y maps to −z. The first chair shell was under the floor.
- The bulb mesh blocked the point light. The point light (a visible sphere since 4.0) is now the bulb.
- The lights were first keyed on every frame from Python. They are now drivers (functions of the frame). Values match the keyed version to float precision (sun direction within 0.02°), and two re-rendered frames compare at 54–56 dB PSNR, so frames rendered before the switch were kept.

## Files
- [x] build.py → corner.blend
- [x] hero stills: _still_076.png (noon) and _still_211.png (night)
- [x] loop.mp4 (300 frames, 10 s; seam 300 → 1 checked)
- [x] nodes.png (the whole PA_Corner_GN tree in frames; layout in nodes_layout.json)
- [x] tutorial/README.md: a node-by-node walkthrough with diagrams and material close-ups

## Caption
```
──── mastodon (≤500)
Nodevember 2026 · Day 02: Furniture | A day in the corner

One window, out of frame, is the only sun. Ten seconds of a day cross a reading corner; the lamp takes over at blue hour. Bouclé, walnut, travertine, linen, knit, wool, glaze: all shader nodes.

Rules: Geometry Nodes + shader nodes only, no image textures, no hand modelling, seamless loop

Made with Blender Geometry Nodes, Cycles.

@Nodevember@graphics.social

#nodevember #nodevember2026 #GeometryNodes #b3d

──── bluesky (≤300)
Nodevember 2026 · Day 02: Furniture | A day in the corner

Rules: Geometry Nodes + shader nodes only, no image textures, no hand modelling, seamless loop

Made with Blender Geometry Nodes, Cycles.

@nodevember.bsky.social

#nodevember #nodevember2026 #GeometryNodes #b3d

──── instagram
Nodevember 2026 · Day 02: Furniture | A day in the corner

One window, out of frame, is the only sun. Ten seconds of a day cross a reading corner: raking morning light, noon through the bouclé, a golden window on the wall, the lamp at blue hour, the moon, then morning again. Bouclé, walnut, travertine, pleated linen, chunky knit, wool, glaze and limewash, all shader nodes.

Rules: Geometry Nodes + shader nodes only, no image textures, no hand modelling, seamless loop

Made with Blender Geometry Nodes, Cycles.

@nodevemberio

#nodevember #nodevember2026 #GeometryNodes #b3d
```

## Alt text
- A reading corner against a seamless warm white limewash wall: a cream bouclé barrel chair with a rust chunky-knit pillow, a turned walnut side table with a travertine ball lamp and a pleated linen shade, a sage glazed vase of pampas grass, and a cream rug with a charcoal diamond lattice. Over ten seconds, sunlight from an unseen window rakes across the floor, falls across the chair, and climbs the wall as an orange window shape with pampas shadows. Then the room turns blue, the lamp switches on, moonlight shows the window faintly on the wall, and morning returns.

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted
