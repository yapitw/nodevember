# Nodevember 2026 · Day 03 · Stitch

Date: 2026-11-03  ·  Folder: 2026/day03-stitch-v3-kintsugi

## Idea
- Reading of the prompt (literal / lateral / personal): lateral, kintsugi: a break mended so the seams are stitched together with gold.
- One-sentence concept: A cream tea bowl veined with gold breaks along exactly those veins (gold dust puffs off, raw biscuit shows), the shards hover, come home one by one — urushi wiped along each broken edge, the shard pressed home and the lacquer squeezing out of the seam — and then gold flows down the seams from the rim until the bowl is whole again.
- Constraint I'm stating in the caption: Geometry Nodes + shader nodes only, no image textures, no simulation, seamless loop
- Technique to learn or show off: a fracture by 3D Voronoi cells on a chawan (Cylinder grid laid on a filleted profile curve; low cells merged into the foot piece); shard id per face → Split to Instances; crack vertices snapped onto the cell bisector (3 Newton steps through the noise warp) so the shards have smooth edges; Extrude (offset 0) + move the top to the inner skin = inner glaze + raw crack walls; the seams are the grid edges between different ids (variance of the face id on the edge domain), snapped the same way, and become lacquer and gold beads.
- Output: loop, 240 frames @ 30 fps (8 s), 1:1 1080×1080, Cycles

## Build log
- Loop (phase): whole, gold-veined → break 0.05–0.10 (gold leaves the seams by 0.075 as dust) → hover → for each shard in turn around the bowl (first ones slowest and widest apart): a bead of urushi is brushed along its broken edge over 0.06 (real tube on the mid-wall, riding with the shard), the shard flies home over 0.16 → 0.08 easing to a crawl ((1−x)^4(1+4x)), presses a little past home and settles; as the faces meet the seam lacquer swells to 3.5× (squeeze-out) and settles to a slim bead over 0.07 → gold flows from the rim down 0.62–0.89 (2.2 s) → rest. One turn per loop. Frame 1 == frame 241 (max diff 0).
- Rejected the first take (gold sutures): kintsugi isn't stitched with thread.
- Materials from the reference: warm cream glaze inside and out with sparse iron speckles (two thresholded Voronoi layers on the rest position), thinning to brown at the lip; gold lip; satin gold (roughness 0.24–0.36, brushed noise, anisotropic); urushi lacquer under the gold, showing as a dark edge where the gold is a hairline; a lost chip at the lip (makienaoshi), raw biscuit while broken, gilt once the gold has flowed.
- Gold width: hairline → wide from a noise along the seam (0.35–1.25 × r) plus a modest pool (+1.0 × r, exp falloff 0.07, none on the lip) where seams meet. The round bead is then squashed along the surface normal to 10 % of its height (stored centre + normal per curve point, offset = n·(dot(P−c0, n)·(k−1))), so the gold lies flat on the glaze like lacquer and powder; the urushi squeeze-out is round while swelling and flattens to 12 % as it sets. Blender 5.2's Curve to Mesh ignores the curve radius, so thickness goes in through its Scale input.
- Profile: one cubic NURBS cage (end points tripled) from the lip round the foot ring, so tangent and curvature are continuous; the inner skin is a second NURBS (same cage, turning into the well) pushed in by the wall thickness along its normal and sampled by the same arc length from the lip, so crack walls stay square; the two skins close in a round nose at the lip. Aged glaze, all in the shader: warm/cool mottling, two scales of Voronoi distance-to-edge crazing stained with tea (darker inside and toward the well), a faint tea ring, pinholes, an iron-brown worn lip (rougher coat), and a raw-clay foot ring with grime at the body. The urushi line shows only during glue and set; it shrinks to nothing as the gold arrives.
- Bugs fixed: Extrude Mesh defaults to Individual (per-face walls); the inner profile sampled by the same factor as the outer one sheared the crack walls (inner skin is now the outer pushed in by the wall thickness, rounding into the well below s = 0.62); a 1-ulp difference in the face→point averaged site changed the White Noise hash, so one vertex per face tumbled differently (snap the site before hashing).
- Clay pass (Workbench): clay/kintsugi_clay.blend → clay/loop.mp4.

## Files
- [x] build.py → kintsugi.blend (framed node layout kept in nodes_layout.json)
- [x] _still_001.png (gilt, whole) · _still_128.png (lacquer setting): full-quality stills
- [x] loop.mp4: final Cycles render, 1080², 240 frames, Metal GPU, 84 min
- [x] nodes: tutorial/images/nodes-0-overview.png (whole tree, 12 labelled frames) + per-section cut-outs
- [x] tutorial/README.md: node-by-node walkthrough with screenshots and diagrams
- [x] tutorial/images/storyboard.jpg: from final frames 1, 16, 36, 62, 75, 128, 175, 215

## Caption
(generate with: python3 nodevember.py caption 3 --tools "Blender Geometry Nodes" --constraint "...")

## Alt text
-

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted
