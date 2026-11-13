# Nodevember 2026 · Day 12 · Erosion

Date: 2026-11-12

## Idea
- Reading of the prompt (literal / lateral / personal): lateral, at table scale: erosion by dissolving. Hot tea drips on a sugar cube.
- One-sentence concept: the first drops soak in, the next drill a funnel through the cube, the corners go, it slumps, and a ragged ring of crystals is left in a pool of tea.
- Constraint I'm stating in the caption: one Age slider drives everything; no image textures, no simulation, no imported assets.
- Technique to learn or show off: the cube is an implicit field (rounded box whose corner radius grows, minus a funnel); the crystals are a fixed 3D lattice shown only in a thin shell at the surface, so they are uncovered and lost without flicker.
- Output: animation, 8 s, 24 fps, 1080², holds on the fresh cube and on the island.

## Build log
- clay motion pass first, then lighting options, then Cycles.
- lighting: four options (sun backlight / window / black stage + small rim / grazing sun) → C, black stage. A rough glossy black saucer spreads the rim light's reflection over the whole backdrop; keep it glossy and drop Specular IOR Level to 0.1 instead.
- tea colour from depth: clear surface + Volume Absorption (amber, density 900/m), so thin edges are pale and the middle dark.
- the smooth body showed between the grains: crystal shell thickened to ~1.1 mm (about three layers), body sunk 0.3 mm under it, grains 0.9–1.4 × pitch.
- grains looked like grey cement: clear glass grains (Transmission 0.85) only read as sugar once shadow rays pass through them (Light Path · Is Shadow Ray × 0.75 → Transparent), so the lower layers are lit.
- final stage E: C's rim + kick on a white glazed saucer, which shows the tea amber by depth (Volume Absorption 0.84/0.52/0.16, 1800/m). Pool: flat top, round meniscus edge (z^0.35); a thin strip light seen only in reflections gives the liquid line.
- the cube now wicks tea up from the pool as well as down from the drip (bottom goes brown first), as real sugar does.
- warm white: grain tint alone did nothing (the shadow pass-through Transparent was pure white, and the look is mostly glints); tint the Transparent too. Grains 0.985/0.95/0.87, body 0.95/0.87/0.74.
- more SSS made it worse both ways: SSS in 0.4 mm grains leaks out grey; a 3 mm body radius made dark specks between grains. Kept clear grains over a 1 mm-radius SSS body (compared neutral / warm / warm + deep SSS side by side).
- edge translucency (the user circled the top-front ridge and the two upright edges): a 'Light through' group walks from each surface point five ways into the lit side (toward the rim light, ±55°, up, level), adds up how much of each walk is sugar, averages exp(−t / 0.9 mm), only on faces turned away from the light (normal from the field gradient) and only for walks going inward. Stored as `glow`, used as a warm emission (0.45 × glow); a Glow slider scales it. The first version (one ray toward the light) lit only the top ridge; counting walks that leave the face lit a whole side.
- lighting kept as E after testing the key from the right (F: pure side, G: right-behind).
- loose grains: they floated (centre at a fixed 0.16 mm, random tumble) and let 75 % of shadow rays through. Now they lie on their broad face, lifted by half their height, with their own material passing only 30 %; sizes 0.9–1.5 × pitch, plus 8 clumps of 4. Their shadows are still only 2–3 px: with the rim straight behind at 42° and the camera at 37°, a grain's shadow (≈ its own height long) points at the camera and hides under it. Lowering the rim (30°) or swinging it 30° (preset I) barely helps; kept E.
- final render: Cycles on the Mac (M4 Pro), 192 frames in 72 min (~23 s each), no flicker (frame-to-frame difference steady, hold frames static). Hero still = frame 100: funnel open, white corners still standing, tea wicking up from a first puddle, so the whole story is in one frame. The held end frame is render-end.png.
- node shots retaken from the final file; section 2 had been reopened after 2b, which drew a second '2 · The cube as a field' frame. Moved Set Shade Smooth before the glow store; the evaluated mesh (positions, smooth flags, wet, glow) hashes the same at frames 60 and 140.
- tutorial: made the trees readable first. The light-through group had 29 inline field calls (~250 nodes); each walk is now `PA_Walk`, and the rounded box, the crystal lattice and the crumbs are groups too; `PA_Clock` is built once and shared by both trees. Every object's evaluated mesh (positions, smooth flags, wet, glow) hashes the same at frames 60, 100 and 140, so the rendered video still matches piece.blend.
- caption fix: with Drops = 10 only nine drops fall (the clock's last cycle has no drop, so the ninth bite can finish); counted in the tea object, frames 17–25 … 145–153. Caption says nine now; the Drops tooltip says so too.

## Files
- [x] loop.mp4 (8 s, 24 fps, 1080²; no GIF)
- [x] render.png (hero still, frame 100) + render-end.png (held end, frame 192)
- [x] nodes/main.png (main tree) + nodes/field.png (sugar field) + nodes/glow.png (light through)
- [x] audit: strict_procedural, no issues
- [x] tutorial/README.md (node-by-node walkthrough: cross-sections of the field, clock, glow pass, body vs crystals)

## Caption
Nodevember 2026 · Day 12: Erosion | Sugar cube

Nine drops of tea drill through a sugar cube. The grains are a fixed 3D lattice: only the ones at the surface show, so the same crystals are uncovered and then lost as the cube dissolves.

Rules: one Age slider drives it all; no image textures, no simulation, no imported assets

Made with Blender Geometry Nodes.

#nodevember #nodevember2026 #GeometryNodes #b3d
(Bluesky / X: drop the middle paragraph to fit.)

## Alt text
- A white sugar cube sits on a white saucer, lit from behind. Drops of amber tea fall onto it one by one: a brown funnel opens in the top, tea pools around the base and creeps up the sides, the corners crumble, and the cube sinks into a ragged ring of brown crystals in a puddle of tea.

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted
