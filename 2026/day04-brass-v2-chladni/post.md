# Nodevember 2026 · Day 04 · Brass

Date: 2026-11-04  ·  Folder: 2026/day04-brass-v2-chladni

## Idea
- Reading of the prompt (literal / lateral / personal): lateral, brass as sound. A brass Chladni plate driven at
  its centre sings four rising tones, and sand draws each one.
- One-sentence concept: sand on a brass plate is thrown off the antinodes and settles on the nodal lines of four
  tones, X → rounded square → ring of loops → lace, and then drops back to the first.
- Constraint I'm stating in the caption: 100 % Geometry Nodes, no keyframes, no image textures. The sand's
  only rule is one standing-wave family, cos(nπu)cos(mπv) + cos(mπu)cos(nπv), with two modes mixed per tone.
- Technique to learn or show off: Newton projection onto a field's zero set inside a Repeat Zone
  (p ← p − f∇f/|∇f|²), and amplitude-driven grain hops.
- Output: loop, 8 s, 30 fps, 1:1 1080², Cycles. Final frames rendered on the LAN GPU farm (NUC12, RTX 4060, OptiX).

## Build log
- Picked the modes from numpy contact sheets first (scratch only; no data goes into the .blend).
- v-a: odd-odd modes with a bow on the edge. Dropped: every odd-odd mode has the "+" cross through the centre,
  which centre-driven plates don't show.
- v-b: even-even modes (centre = antinode, the driven point) and no bow; the plate itself ripples with the tone.
- v-c, after comparing with real photos: two modes mixed per tone (curved lines, no straight diamond), a static
  noise warp (the plate is not perfectly even), line width ∝ 1/|∇f| plus a soft halo, 3 % strays, and a clamp
  ring of sand at the bolt.
- Hops scale with the new tone's |f| under the grain: grains on antinodes bounce longest and highest, grains
  already near a new line barely move.
- The camera went low (30°), 100 mm, f/1.4, ±6° swing per loop. Sand radius was halved and count raised to
  300k, because the bigger grains looked like rice.
- v-d: the plate no longer bends. The slow 3 Hz bend (0.0016 × f) made the brass read as soft, like jelly. The plate is
  rigid now, and the tone shows only as extra roughness on the antinodes (a `ring` attribute → brass roughness +0.16),
  plus the sand jumping.

## Files
- [x] chladni.blend (+ build.py, which builds it: `Blender -b --factory-startup --python build.py`)
- [x] render.png (hero still = frame 100)
- [x] loop.mp4 (8 s, 30 fps, 1080², Cycles 128 spp, rendered on NUC12 / RTX 4060 OptiX via Flamenco)
- [x] nodes.png (PA_Sand_GN) + nodes_nodal.png (PA_ToNodalLines, the Newton projection)
- [x] clay/loop.mp4 (Workbench motion check)
- [x] tutorial/README.md (node-by-node walkthrough, images in tutorial/images) + nodes_layout.json

## Caption
Nodevember 2026 · Day 04: Brass | Chladni

Sand on a brass plate finds the nodal lines of four rising tones. One standing-wave family, two modes mixed per tone, Newton steps in a Repeat Zone.

Rules: 100% Geometry Nodes, no keyframes, no image textures

Made with Blender Geometry Nodes.

#nodevember #nodevember2026 #GeometryNodes #b3d
(Bluesky/X: drop the description line; per-platform handles from `nodevember.py caption 4 ...`)

## Alt text
- A square brass plate on a thin shaft in a black void, seen low and close. White sand on it forms curving
  Chladni figures: an X of four arcs, then a rounded square around a ring, then a ring of loops, then dense lace.
  At each new tone the sand jumps off the vibrating parts and settles onto new lines while the brass reflection blurs on the parts that shake.

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted
