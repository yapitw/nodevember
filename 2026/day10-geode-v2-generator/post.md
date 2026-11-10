# Nodevember 2026 · Day 10 · Geode

Date: 2026-11-10

## Idea
- Reading of the prompt (literal / lateral / personal): literal, asked for directly by the user after two rounds of
  ideas ("直接一點"): "做一組可以生成多種晶洞的 geometry node，影片就展示參數變換", based on a reference photo of
  two amethyst geode halves on a lavender backdrop (rusty rind, blue-grey/lavender agate bands, a thin orange line,
  white quartz, amethyst points).
- One-sentence concept: one Geometry Nodes group that grows many real kinds of geode; the video moves its sliders
  one at a time, then morphs through eight kinds (amethyst, citrine, celestine, calcite, onyx, agate, druzy, smoky).
- Constraint I'm stating in the caption: every geode, crystal, band and colour comes from one node group's sliders;
  no image textures, simulation or imported assets.
- Technique to learn or show off: Blender 5.2 grids: one implicit field (4D-noise ellipsoid, rough rind, cavity as a
  deeper level set, a flat onyx floor, the saw kerf) → Cube Grid Topology → Field to Grid → Grid to Mesh; the same
  field evaluated on the vertices stores depth-into-the-wall for the agate bands; crystal sites are a fixed ico
  sphere ray-cast onto the cavity wall, so nothing re-scatters while sliders move; one 6-sided, 3-ring template per
  crystal, placed vertex by vertex (root, shoulder, point or chisel ridge, blade flattening), flattened at the cut.
- Output: animation, 27 s (646 frames), 24 fps, 1080² (1:1), Cycles; a clean version (sweep/loop.mp4) and one with
  the slider readout composited after (hud.py → sweep/sweep.mp4).

## Research (what varies in real geodes)
- Structure, outside in: rind (basalt / limestone skin) → chalcedony/agate bands → white quartz palisade → crystal
  points → hollow. Amethyst crystals are often white at the root and purple towards the tip (iron rises as the
  cavity fills); Texas celestine is likewise white at the base, blue at the tips.
- Banding: wall-parallel "fortification" bands, or gravity-levelled horizontal "water-level" (onyx, Uruguay-type)
  bands that fill the cavity floor; both can occur in one stone.
- Kinds: amethyst (Uruguay/Rio Grande do Sul basalt), citrine (mostly heat-treated amethyst), celestine (blue,
  tabular/bladed), calcite (dogtooth spar, often fluorescent; Keokuk geodes from the Warsaw Formation), clear and
  druzy quartz, smoky quartz, solid agate nodules (no cavity).
- Sources: geology.com/articles/geodes, rockchasing.com/types-of-geodes, Wikipedia "Agate" (level banding),
  fossilera.com amethyst notes (colour zoning), tpwd.texas.gov young naturalist "Geodes" (celestite tips, dogtooth).

## Build log
- 2026-11-10: Field to Grid needs Threshold 0 on Grid to Mesh (default 0.1 gave no mesh) and treats values above the
  threshold as inside, with normals pointing towards lower values: so the field is "positive = solid", and the
  cavity grid's normals point into the rock (grow = −normal).
- Crystals first read as gummy candy: subsurface on thin pyramids rounds the facets. The body is now an opaque
  glossy layer mixed with clear glass (light tint per crossing: crossing many crystals went black).
- Druzy needed denser sites (ico subdivision 6: 10 242 sites; Blender counts the icosahedron as level 1, which build.py first miscounted as 40 962) and a milky share; a fixed ray source at the centre keeps
  every site still while the onyx level and wall change (sites under the onyx are scaled to zero, not moved).
- Black studio (user: "黑色背景，水晶的高光和折射感看不太出來"): black seamless sweep with a faint sheen, gem
  lighting (thin strip boxes for long facet highlights, three tiny point lights for glints, two rims), clear
  glass share up (Clarity 0.8, milky share cut), per-crystal depth variation.
- Onyx first read as ruled paper (hairline level bands, all one width). Real Uruguay (level) banding sits only at the
  cavity floor and is a stack of flat strata of uneven thickness, each one tone, granular. Now: ~a dozen strata per
  fill, tone per stratum by a golden-ratio walk (neighbours always differ: dark / grey / milky), fine laminae, grain,
  and a slight meniscus at the wall.
- Crystals still read opaque (user). Glass tests on a 2× crop (A–K): a milky root band and black-behind-glass were
  the culprits. Now: no milky root (milky only from Clarity and the druzy), closed prisms, 60 % tinted shadow rays
  through the glass (the cavity is lit through the crystals; caustics stay off), three glossy-only reflection cards
  light-linked to the geode (facets flash, the black sweep stays black), and a light from high behind into the bowls.
- Cut to six classic kinds (user): amethyst, citrine, celestine, calcite, druzy, agate. Onyx and smoky left out, and
  the Level sweep with them (it read oddly); the Level slider stays in the generator. Sheet: _sheet_six.png.
- 2026-11-11, flicker (user: "影片中間有一些閃爍"). A tile-wise temporal check (how far a frame sticks out from the
  midpoint of its neighbours, beyond their own motion) found four causes: (1) Seed ran through the 4D noise at up to
  1.9 a frame in the finale (preset seeds −5 … 33) and 0.35 in the seed sweep, so outline and cavity boiled: presets
  now sit on a chain −2.0 … 1.2 (neighbours ≤ 1.2 apart, ≤ 0.1 a frame) and the seed sweep is one slow trip out and
  back; (2) crystal axes came from the raycast's flat triangle normal and snapped as the wall moved: now the wall's
  vertex normals read back interpolated at the hit; (3) big ↔ druzy switched within ±0.03 of `keep`, abrupt when keep
  is large: now over a ratio (0.6–1.6 × keep); (4) random values were by index after dropping missed sites, so a
  miss reshuffled every later crystal: sites store a stable `id` first. The crystal sliders also reshuffle a dense
  palisade at 13-frame legs: Shell/Crystal/Point/Blade now get 18-frame legs and narrower ends (64 frames each).
  Low-res test of the whole sweep: frames over 15 went 92 → 2, worst 88 → 19, mean 7.1 → 2.4. Final render (1080²,
  646 frames): 3 over 15, worst 17.8, mean 1.77; the three left are specular flashes as a facet turns through the
  seed and shell legs (frames 40/68 mirror each other at the same seed value), not boiling.
- Framing for the clean version (user: "空白顯得有點大"): option sheet A–D; A chosen (same angle and light, lens 70 →
  79.4 mm, centred; fitted to the projected extent of every 6th frame, 92 % of the width). The readout still fits
  over the frame, so both versions come from one render.

## Files
- [x] render.png (hero still, 2160², amethyst at rest = the video's last frame, framing A, 160 spp + denoise)
- [x] sweep/loop.mp4 (clean, no text) + sweep/sweep.mp4 (with the slider readout): 1080², 24 fps, 646 frames (26.9 s), Mac only (farm worker down), 64 spp + denoise, 2026-11-11 00:54–04:46
- [x] nodes/main.png (main tree: 4 sections, one slider input per section) + nodes/field.png (the implicit field,
  sections a–d)
- [x] tutorial/README.md (node-by-node walkthrough)
- [x] extra: _sheet_six.png (the six kinds with the new seeds, framing A); _still_494.png (frame 494, celestine)
- Audit: strict_procedural True, no issues (15 Geometry Nodes trees, 403 nodes not counting frames, after the
  tutorial grouped the helper maths into PA_Smoothstep / PA_Clamp / PA_Mix / PA_ByRing; the evaluated meshes of all
  six presets and the sweep's frames hash the same as before the regrouping).

## Caption
Mastodon / Bluesky (300/300):
> Nodevember 2026 · Day 10: Geode | Geode generator
>
> Rules: every stone, crystal, band and colour comes from one Geometry Nodes group's sliders; no image textures, simulation or imported assets
>
> Made with Blender Geometry Nodes.
>
> @Nodevember@graphics.social (Bluesky: @nodevember.bsky.social)
>
> #nodevember #nodevember2026 #GeometryNodes #b3d

Instagram / Blender Artists, add after the title:
> One implicit field on a voxel grid (Field to Grid → Grid to Mesh) gives the rind, the agate wall and the hollow;
> crystal sites are a fixed ico sphere ray-cast onto the cavity wall, so nothing re-scatters while the sliders move.
> The video moves seven sliders, then morphs through six classic kinds: amethyst, citrine, celestine, calcite,
> druzy quartz, agate.

X (146/280): title line, "Made with Blender Geometry Nodes.", @Nodevember, tags.

## Alt text
- Video: Two halves of a sawn geode on a black studio floor: a rough reddish rind, lavender and blue-grey agate
  bands, and a hollow lined with glassy purple amethyst points. A slider readout along the bottom moves as the
  stone changes shape, wall thickness, banding and crystal size, then morphs into orange citrine, pale blue
  celestine blades, honey dogtooth calcite, sparkling white druzy quartz and a solid banded agate, and back to amethyst.
  (Clean version, sweep/loop.mp4: the same without the readout and the kind names.)
- Node screenshot: Blender Geometry Nodes editor with four coloured frames, Grid, Rock, Crystals and Two halves,
  each a short chain of node groups fed by its own slider input.

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted
