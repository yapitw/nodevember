# Nodevember 2026 · Day 06 · Vault

Date: 2026-11-06

## Idea
- Reading of the prompt (literal / lateral / personal): literal, the high vault of Rouen Cathedral's nave, detailed after a user photo (looking straight up, rose window end at the top) plus Wikimedia Commons photos of the same nave from other angles (`_refs_rouen_commons.jpg`).
- One-sentence concept: lying on the floor of an endless Rouen nave, head towards the west end, looking up: four storeys of stone climb into a quadripartite vault that runs on to the rose window.
- Constraint I'm stating in the caption: 100 % Geometry Nodes, no keyframes, no simulation, no image textures; one wall bay built once and instanced on both sides of every bay.
- Technique to learn or show off: four-storey elevation as one Mesh Boolean (slab minus stepped orders of equilateral lancets), roll mouldings as curves along each arris; moulded rib sections as multi-spline profiles for Curve to Mesh; v3's cell parametrisation for ashlar courses in herringbone.
- Output: 1:1 2160² color still; white-model loop at 1080², one bay per 10 s at 30 fps.

## Build log
- Reference facts (Commons photos): four storeys (arcade on compound piers, a false tribune opening into the tall aisle without a floor, a triforium of small lancets, a deep clerestory with an inner passage and rail); vaulting shafts in bundles from floor to springing, ringed at every storey; quadripartite vault with no ridge rib, rosette bosses, heavy transverse arches.
- The user's photo has the vanishing point at the top: the camera is pitched ~60° and rolled 180° (head towards the far end). 14 mm let the near pier capitals fill the corners; 26 mm (a 1:1 crop of the portrait photo's view) frames walls and vault like the reference.
- Mesh Boolean (Exact) with overlapping cutters joined into one mesh left half-cylinders standing in the nave; link each cutter into the multi-input and turn on Self Intersection.
- Clerestory glass set at the outer face of a 1.6 m wall is invisible from the floor (the reveal hides it at 75° elevation); the glass moved to 0.9 m and the roof narrowed to the walls' outer faces (it was shading the windows).
- Vault first read as brick: larger stones (0.78 m), 8 mm joints, a light mortar bed, less tone variance, large water-stain noise; walls cooler grey.
- Polish pass (user: exposure, blocky corner capitals, small windows; grey walls + cream vault as in the photo):
  - capitals are smooth bells whose rims curl out into n leaves (cos(nθ)³ plus a little noise); each of the pier's 16 shafts gets its own, the drum a 12-leaf bell, under a chamfered abacus.
  - clerestory glass and tracery moved to 0.5–0.6 m from the inner face, lights widened to 0.8 m: the windows now read from the floor.
  - every course is split at its cell ridge (a = 0): a course that ran across the ridge had a kink there, and the stone on the kink stood proud (a column of steps along both ridges).
  - at least 2 stones per course: one-point courses next to the bosses had no tangent and their stones lay at random angles.
  - palette: walls 0.50 grey, vault cells (0.88, 0.72, 0.46), ribs a paler ochre; fill and sun near-white so the walls stay grey; AgX High Contrast, exposure 0.8. ~50 s per 1080² frame at 160 spp (Metal).

## Files
- [x] rouen.blend (colored procedural scene)
- [x] clay/rouen_clay.blend (white-model scene)
- [x] masonry_direction_v1.png (2160² raking still)
- [x] masonry_direction_detail_v1.png (native-resolution upper-vault detail)
- [x] clay/loop_masonry_v4.mp4 (10 s loop)
- [x] clay/loop_masonry_v4_3x.mp4 (30 s playback review)
- [x] color/loop.mp4 (colored 10 s loop, final directional light)
- [x] color/loop_3x.mp4 (30 s playback review)
- [x] render.png (poster: frame 1, final light, 1080²)
- [x] nodes.png → tutorial/images/nodes-main.png + per-group cut-outs (tutorial/README.md)
- [x] extra: breakdown → tutorial/ (node-by-node walkthrough, concept figures, storyboard)

## Caption
(generate with: python3 nodevember.py caption 6 --tools "Blender Geometry Nodes" --constraint "...")

## Alt text
-

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted

### Pass 3: "像水管，不像牆飾" (pipes, not carving)
- Arch rolls ran down the jambs as free tubes parallel to the colonnettes: a bundle of pipes. Now each order's roll is only on
  the arch, sunk 0.85 r into the arris, and springs from a leaf capital on an engaged colonnette in the angle of the step;
  the three colonnettes of a jamb share one abacus. The outer order has a slighter roll than the inner two.
- The arcade has no jamb colonnettes: all three orders land on the pier abacus (a colonnette there stood loose in front of the pier).
- Vaulting shafts are half sunk into a stepped pilaster (three steps) instead of standing clear of a flat one.
- Orders of the tribune and clerestory stop on one sill; the string course under the tribune is gone (from below it read as a
  loose bar crossing the arcade); the other string courses are stepped corbels, not a fillet plus a free roll.
- Trim grime (AO) up to 0.7 so the hollows between shafts and orders go dark.
- Raking views for checking (`_cycles_001_rake*.png`) look good on their own: a possible second image.

### Pass 4: flat wall between the arcade and tribune
- Fixed the lancet cutter: the circle intersection was a full lens, whose lower tip extended below high
  sills and carved an inverted arch into the spandrel. Clip the lens at its springing before joining the
  jamb box; the wall band is now actually planar rather than hiding the cut behind a projecting sill.
- Removed the separate projecting tribune sill. The uncut wall under the opening supports the jamb bases,
  with all three opening orders ending at the same height, so the spandrel stays in the wall plane.
- Raised the tribune sill from 11.7 to 12.2 m, leaving about 1.26 m of clear wall above the arcade's outer
  moulding. This matches the flat, separated tiers indicated in the user's reference, rather than stacked shelves.
- Updated the saved scene, raking still and straight-up hero render; retained the previous build and images
  as `_before_flat_spandrel_*` for comparison.
- Validation: 18 horizontal ray casts across the band, on both sides and at three heights, hit the wall
  face at x = ±5.5 m; the Geometry Nodes procedural audit reports no issues.

### Pass 5: recessed jambs and one carved vaulting pilaster
- Tribune and clerestory jambs now have shallow profiles inside their reveals. Flattened shafts and small
  neckings stay behind each order's face; separate leaf capitals, square abaci and projecting foot rings are removed.
- Replaced the five long round vaulting shafts and their stepped backing with one closed cross-section
  extruded as solid stone. Five shallow rolls share a continuous face and rounded shoulders into the wall.
  Each storey has one continuous band, and the top has one shared capital, rather than separate pipe collars.
- Previous scene, source and stills retained as `_before_recessed_jambs_*`.
- Validation: the new pilaster is one connected, closed mesh at the intended 20.32 m height; the previous
  flat-spandrel checks still pass. The procedural audit has no issues. Both 1080² stills are updated.

### Pass 6: compare every moulding with the full reference
- The previous connected pilaster still had five smooth, equal round waves. Replaced them with a broad
  central flat, narrower side fillets, chamfered shoulders and narrow recesses. Sharp cross-section edges
  retain their normals instead of shading into rounded tubes.
- Window arches now have shallow, flat stepped mouldings inside the wall face, replacing circular tubes.
- Vault ribs use one closed, stepped polygon section with a flat soffit, replacing several overlapping
  circles. Reduced transverse and diagonal rib depth to match the reference's lighter ribs. Corrected
  half-arch frames so the carved soffits consistently face the nave on both sides.
- Retained the previous scene and stills as `_before_stone_profiles_*`.
- Validation: isolated pilaster and rib sections are closed meshes with a single connected surface;
  all 18 flat-spandrel ray checks and the procedural audit pass. Raking and straight-up stills updated.

### Pass 7: articulated mouldings from the larger reference
- The large reference clarified that flat chamfers alone were an overcorrection. The stone has convex
  rolls of different sizes, concave hollows, narrow fillets and stepped transitions in one continuous core.
- Rebuilt the pilaster with a broad partial central roll, smaller side rolls and outer beads, separated by
  sampled concave hollows and fine fillets. The rolls are unequal and embedded in a shared solid section.
- Rib sections now combine a rounded soffit, hollowed shoulders and small beads. Window arch sections use
  the same convex / concave / fillet vocabulary, recessed behind their respective wall faces.
- Fine 5–6 mm joints at roughly 0.62 m intervals and subtle per-block tones break up the uninterrupted
  extruded appearance. Shaft coursing follows height; arch and rib joints follow curve length. These are
  shader details on the solid sections, with no additional collars or raised bands.
- The triforium's small colonnettes are more deeply engaged in their stone piers.
- Retained the flatter version as `_before_articulated_mouldings_*`; added a closer material-and-profile
  view as `detail_mouldings.png` alongside the two full nave views.

### Pass 8: lower compound pier and capital cleanup
- Replaced sixteen separate round shafts and individual leaf capitals with one eight-lobed compound drum,
  a continuous smooth bell, and a chamfered octagonal abacus. A notch keeps the arcade capital behind the
  uninterrupted vaulting service instead of letting a plate intersect its front.
- The capital and main service are joined with Manifold booleans. The Exact solver produced overlapping
  faces at the complex junction; the revised core is one connected, closed surface with no nonmanifold edges.
- The white-model copy uses a single neutral material, cavity shading, no specular highlight, white
  background and removed glazing faces so openings remain readable. The color scene is preserved.
- User requested two comparison rounds before rendering the white-model animation.
- The first white-model comparison exposed small dark wedges beneath the fluted abacus. Replaced that
  scalloped capital rim with a smooth bell and a clean octagonal bearing surface, then repeated both rounds.
- Round 1 passed after the revision: front / reverse capital close-ups, full raking view and straight-up
  view. The joined pier core has 3,354 vertices, 2,445 faces, one connected surface and zero nonmanifold edges.
- Round 2 passed: white-model capital close-up and frames 1, 2, 151, 299, 300, 301. Frames 1 and 301 are
  pixel-identical. Mean RGB changes are 6.014 (1→2), 6.005 (299→300), and 6.011 (300→1), confirming the
  loop transition has the same movement scale as ordinary adjacent frames. Metrics: `clay/review_round2/loop_metrics.json`.
- `prepare_clay_video.py` separates the stationary west end from the procedural nave and drives the
  nave object's translation by the same loop expression. Geometry remains generated in nodes, with no
  baked mesh or keyframes. Six comparison frames differ from the original export by mean RGB values
  of only 0.0001–0.0159 on a 0–255 scale. This enables mesh caching during the white-model render.
- Completed `clay/loop.mp4`: 300 frames, 10.000 s, 1080 × 1080, 30 fps, H.264 / yuv420p, about 13.2 MB.
  Full decode passed; decoded first / middle / final frames were visually checked. The encoded loop-step
  mean RGB change is 6.61 versus 6.12 for ordinary adjacent frames. Review details: `clay/review_report.json`.
  White model: `clay/rouen_clay.blend`; poster: `clay/preview.png`.

### Pass 9: a shared capital around the whole shaft bundle
- The marked photo clarified the remaining structural mismatch: the reference capital follows all the
  smaller shafts as a continuous crown. Cutting the previous circular capital around the front service
  left two large corbels and an unnatural junction.
- Removed the notch and generic octagonal bracket. The drum and front shaft profiles now rise into
  matching flared capital sections, with continuous necking and a shallow abacus following the whole profile.
- Leaf-like relief is deformed directly into the capital surface, aligned with the individual shafts;
  separate overlaid leaf sheets produced small intersections and were removed. The capital is one joined
  solid, with small degenerate boolean islands discarded. Stone joints stop across the carved capital.
- Review explicitly includes frame 61 (about 2 s), matching the user's marked playback angle, as well as
  front and reverse capital close-ups. Previous scene, source, frames and video are in `_before_shared_capital/`.
- References: `_refs_shared_capital_photo.png` and `_refs_shared_capital_issue.png`.
- Both final comparison rounds passed: front / reverse close-ups, the marked frame-61 angle, full nave
  views, white-model close-up and frames 1, 2, 61, 151, 299, 300, 301. The core is one closed connected
  surface (28,268 vertices, 22,640 faces, zero nonmanifold edges). Frames 1 and 301 remain identical.
- Updated `clay/loop_capital_v2.mp4` (10 s, 300 frames, 1080², 30 fps) and
  `clay/loop_capital_v2_3x.mp4` (30 s). Full decode and encoded first / 2-second / middle / final frame
  checks passed. The previous `loop.mp4` and `loop_3x_review.mp4` aliases also contain the new render.
- Direct frame-61 comparison: `clay/capital_before_after_v2.png` (old at left, new at right).
  Detailed white model: `clay/capital_detail_v2.png`. Updated checks are in `clay/review_report.json`.

### Pass 10: rebuild the junction as shared mesh rings
- Replaced the stacked 3D capital solids with one continuous loft from the compound shaft through the
  neck, bell and abacus. The compound section is derived once in 2D; all vertical transitions share vertices.
- The upper service starts on an explicit annular bearing. Its bottom loop is the bearing's inner loop;
  the capital top is the outer loop. A containment check keeps the full upper footprint inside the bearing,
  including the narrow concave mouldings. This removes overlapping joint faces and mismatched corners.
- Added a restrained necking and bevelled abacus in the same loft. Leaf-like relief remains integral to
  the surface; obsolete capital booleans and island cleanup are removed from the build.
- Previous source, model, video and close-ups are retained in `_before_continuous_junction/`.

- Both comparison rounds were repeated after the final bearing correction: colored front / reverse
  close-ups, frame 61, full raking / straight-up views, and white-model close-up and seven loop frames.
  The core has 6,585 vertices and 6,587 faces, one connected component, no nonmanifold edges,
  no inconsistent winding and positive signed volume. Frame 1 and 301 match exactly.
- Cached versus original white-model frames differ by at most 0.0151 mean RGB on a 0–255 scale.
  Final `clay/loop_junction_v3.mp4` is 10 s, 300 frames, 1080² at 30 fps;
  `clay/loop_junction_v3_3x.mp4` repeats it three times for playback review. Full decode passed;
  encoded first / 2-second / middle / final frames were visually inspected. Encoded loop movement
  is 6.62 mean RGB versus 6.13 for adjacent frames. Report: `clay/review_report.json`.
- Close-up comparison: `junction_comparison_v3.png` (old left / new right).
  White detail: `clay/junction_detail_v3.png`. The public loop aliases now contain this revision.

### Pass 11: aged limestone and warm vault from the material reference
- User material reference retained as `_refs_material.png`. The walls and carved shafts now use
  grey-taupe limestone, the vault cells use warm ochre, and the rib stone has a restrained sandy tint.
  Crown glass shows pale cyan daylight instead of uniform white emission.
- Added long umber mineral streaks, broader stone mottling, fine granular color and pores, roughness
  variation and dirt in recesses. Narrow masonry joints have softer contrast so they read as stone
  joints rather than applied shaft collars. The shader uses procedural nodes throughout.
- Stone coordinates are stored before the nave translates. Four-dimensional noise follows a periodic
  embedding over the 6.3 m bay, so texture stays attached to the moving architecture and repeats at
  the loop boundary. No image textures are used.
- A first low-resolution comparison was too dark. Increased skylight and warm indirect fill and used
  a gentler AgX contrast before rendering the final raking view, vault view and capital close-up.
  The neutral white-model scene and completed video are retained separately in `clay/`.
- The full-resolution vault comparison exposed a pale checker pattern where the mortar backing
  appeared between end stones. Matched the backing to warm aged mortar instead of pale beige,
  then rerendered the raking and straight-up views. Final previews: `material_preview_v2.png`,
  `material_vault_v2.png`; carved-stone close-up: `material_junction_v1.png`.
  The updated colored scene remains `rouen.blend`; procedural audit passes with no issues.

### Pass 12: crisp rendering and brighter clerestory bounce
- User reported a soft-looking render and pointed out that the vault beside the high windows should
  receive more daylight. Inspection confirmed that depth of field and motion blur were already off.
  The previous render used a 1.5 px pixel filter, 128-sample stills, 0.02 adaptive threshold,
  denoising, and two glow passes (Bloom and Fog Glow). Settings are recorded in
  `sharpness_review/before_settings.json`.
- Removed the glow compositor, narrowed the pixel filter to 0.9 px, raised the output to 2160²
  and 512 maximum samples, and tightened adaptive sampling to 0.005 with 64 minimum samples.
  Accurate-prefilter, high-quality denoising follows the higher-sample render.
- Added broad soft daylight at each clerestory opening, aimed across the adjacent vault webs.
  A first 650 W trial washed out the stone, so the final window fill is 180 W per opening.
  This lifts the upper vault locally while preserving the lower nave's shadow and warm stone color.
- At the user's request, removed 685 obsolete preview PNGs and archived render frames (about 1.1 GiB).
  Reference photos, current deliverables, current comparison rounds, source and blend backups,
  and the active white-video frame sequence were preserved. Manifest: `screenshot_cleanup.json`.
  Historic image filenames in earlier pass notes describe removed iterations.
- Final 2160² render completed with the METAL device and passed visual review at native crop size.
  `material_daylight_sharp_v1.png` is the current hero image; `render.png` and `_still_001_rake.png`
  point to the same image. The brighter vault detail is `vault_daylight_detail.png`.
  `sharpness_comparison.png` shows the old 1080 crop enlarged on the left and the new native
  2160 crop on the right. Final settings and audit: `sharpness_review/after_settings.json`.
  Superseded material preview PNGs and window-light tests were removed after final verification.

### Pass 13: masonry direction follows the user's red lines
- Reference annotation: `_refs_masonry_direction.png`. The previous stones ran around each barrel
  section. The marked courses run along the barrel axis, perpendicular to the old long edges.
- Replaced the old box-on-tangent layout with axial running bond. Courses step over each curved
  section, alternate rows start with half stones, and the first / last stones are mapped to the
  diagonal rib boundary. All faces follow the exact vault surface; stones no longer stand proud
  in a line at the cell ridge. Fine corner slivers entirely covered by ribs are omitted.
- Each brick is generated from a subdivided parameter box, mapped to the barrel with a continuous
  outward thickness. Mirrored quarters explicitly reverse face winding where needed.
- Isolated one-bay checks pass for 432 transverse-cell bricks and 504 wall-cell bricks:
  every brick is closed and consistently wound, all volumes are positive, and there are no
  zero-area faces. Maximum soffit height error is less than 0.008 mm. Report: `masonry_review.json`.
- A same-view 1080² color preview confirmed the red-line directions on both cell families, before
  the final 2160² / 512-sample render and the second white-model comparison. Previous source and
  scenes are retained in `_before_masonry_direction/`; old preview screenshots are not duplicated.
- The user approved the corrected masonry and requested animation. Prepared a colored loop with
  the same cached procedural-nave method as the white-model scene. The clerestory fill lights
  now follow the moving window openings; stored stone coordinates keep weathering attached.
  Animation target: 10 s, 300 frames, 1080², 30 fps, 256 maximum samples, 0.01 adaptive threshold,
  64 minimum samples, accurate / high-quality denoising, 0.9 px filter, no glow, no depth of field
  or motion blur. Source: `prepare_color_video.py`; saved animation scene: `color/rouen_color.blend`.
- Reduced the animation materials' AO node samples from 16 to 4 while retaining 256 path samples.
  First two full-frame comparisons differ by only 0.237 mean RGB on a 0–255 scale, with fewer than
  0.00006 % of channels differing by more than 8; the same grime appearance and sharp detail remain.
  This removes redundant shading work. Comparison: `color/review/ao_comparison.json`.
- The updated white-model loop passed the seven-frame review and full video decode. Frame 1 and
  301 match exactly; mean RGB changes are 5.329 (1→2), 5.322 (299→300), and 5.327 (300→1).
  White video: `clay/loop_masonry_v4.mp4`; three-repeat review: `clay/loop_masonry_v4_3x.mp4`.
  Report: `clay/review_masonry/review_report.json`.
- The first colored seam review caught a larger-than-normal color change at the wrap: per-stone
  random IDs were global across all nave bays. Changed them to local course / quarter / brick IDs,
  preserving varied stone tones while repeating the same palette pattern in every bay. Two-bay
  checks confirm identical tone values and repeated geometry within 0.002 mm. Repeated the
  colored seam review before allowing the full render to start. Report: `masonry_periodicity.json`.
- A second seam check isolated the remaining luminance jump to changing skylight through the
  open rear end of the finite nave. Added a stationary rear closure behind the camera, which
  blocks this varying contribution. Raised skylight strength to 4.2 to balance the approved look.
  In the 540² / 64-sample check the seam's RGB change is 3.758, versus 3.739 and 3.696 for
  ordinary adjacent frames (ratio 1.011); frame 1 and 301 differ by only 0.000262 mean RGB.
  Report: `color/review_daylight_balance/loop_metrics.json`. Final-quality seam review precedes
  the resumable 300-frame render. The render job prevents idle sleep for its duration.
- Final 1080² / 256-sample seam review passed: mean RGB changes 4.238 (1→2),
  4.238 (299→300), and 4.248 (300→1), with a seam-step ratio of 1.0024.
  Frame 1 and 301 differ by only 0.000187 mean RGB (maximum channel difference 1).
  The full 300-frame color sequence is rendering with the validated settings.
  Current poster: `color/preview.png`; `render.png` and `_still_001_rake.png` now use that poster.
  `masonry_direction_v1.png` remains the 2160² geometry-review still from before the rear light closure.

### Paused at the user's request · 2026-11-07
- Stopped the color renderer, its automatic-retry controller and this job's idle-sleep inhibitor.
- Moved all 67 complete sequence PNGs into `color/paused_2026-11-07/frames/`.
  Frames 1–65 form a continuous 2.167 s segment; frames 299 and 300 are completed ending checks.
- Preserved the animation scene, render logs, loop-review metrics and exact progress manifest in
  the same folder. Next frame is 66; 233 frames remain. See `resume_info.json` and `README.txt`.
- `preview_partial.mp4` plays only the continuous completed segment, with no jump to the ending tests.
  The full colored animation remains unfinished and paused. White-model v4 is complete.

### Expired-file cleanup · 2026-11-07
- Removed superseded build / blend backups, automatic blend backups, old comparison images,
  obsolete review directories and logs, duplicate / superseded white videos, Python bytecode,
  and the completed white video's intermediate PNG sequence. The latest white-model proof
  report is consolidated as `clay/review_report.json`.
- Kept the latest scene and source, reference images, current poster, the high-resolution
  masonry geometry-review stills, the final white videos and their source scene.
- All files in `color/paused_2026-11-07/` were checked by SHA-256 before and after cleanup
  and are unchanged, including 67 complete PNGs, the partial movie, scene and resume manifest.
- Earlier log entries describe historical backups / tests that have now been removed.
  Deletion manifest: `cleanup_manifest.json`. Rendering remains paused.

### Symmetric composition trial · 2026-11-07
- User asked to try a left–right symmetric composition for the animation. Camera moved onto the
  nave axis: (0, −1, 2), no yaw or roll, pitched 42° above the horizon, 22 mm lens. The two
  elevations mirror each other and the west rose window sits whole on the vertical centre line.
  Colour tests at 540² / 64 spp compared 48° / 42° / 40° pitch, a steeper 62° / 18 mm, straight up
  (shows the stationary rear closure, rejected) and the 180°-rolled photo view; 42° / 22 mm chosen.
- White-model loop: `clay_symmetric/loop.mp4` (10 s, 300 frames, 1080², 30 fps) and
  `clay_symmetric/loop_3x.mp4`. Seam step 300→1 is 4.548 mean RGB versus 4.522–5.101 for ordinary
  adjacent frames (`clay_symmetric/review_loop.json`). Workbench's studio light falls from one side,
  so the clay shading is not mirrored even though the geometry is.
- Camera script: `clay_symmetric/set_symmetric_camera.py` (also applies to `color/rouen_color.blend`).
  The paused colour render keeps the original 3/4 view; nothing in `color/` was changed.

### Directional light trial · 2026-11-07
- User kept the original 3/4 camera and asked for more directional light. Tested at 540² / 64 spp,
  then frame 1 at 1080² / 256 spp: `lighting_directional_v1.png`; old/new: `lighting_before_after_v1.png`.
- Chosen candidate V4: sun from the far (+x) side through the clerestory, 30° elevation, Z rotation
  75°, energy 10, colour (1.0, 0.88, 0.74); floor fill 2500 → 1100, clerestory fills 180 → 95 each,
  sky 4.2 → 2.9, exposure 0.85 → 0.92. Sunlit patches fall bay by bay on the near triforium and
  clerestory. Rejected: backlit sun (patches only in the aisle) and a darker, lower-fill version.
- Not yet applied to `color/rouen_color.blend`; the paused render is unchanged.
- User: the vault should be a little darker under side sun. The 48 clerestory fills aim at the vault
  webs, so only they were lowered: 95 → 35 each (tested 60 / 35 / 20 with sky 2.6). Everything else as V4.
  Mean luminance of an upper-vault crop: 150.6 (paused render) → 117.1 (v1) → 81.0 (v2); the brightest
  wall sun patch stays at 234. Frame 1 at 1080² / 256 spp: `lighting_directional_v2.png`;
  v1/v2 side by side: `lighting_vault_v1_v2.png`. Still not applied to `color/rouen_color.blend`.

### Final light and cleanup · 2026-11-07
- User approved lighting v2 as final. `build.py` now holds it as constants (SKY 2.9, FILL 1100,
  WINDOW_FILL 35, SUN_ELEVATION 30, SUN_HEADING 75, SUN_ENERGY 10, SUN_COLOR, EXPOSURE 0.92);
  `prepare_color_video.py` gained `apply_lighting()`, which copies them onto an existing scene.
  Applied to `rouen.blend` and `color/rouen_color.blend`; camera unchanged (original 3/4 view).
- Seam check at 540² / 64 spp: 300→301 step 3.375 versus 3.374–3.676 for ordinary adjacent frames
  (ratio 0.997); frame 1 and 301 differ by 0.0002 mean RGB. `color/seam_check.json`.
- `render.png` is the v2 frame 1 (1080² / 256 spp).
- Cleanup: removed the symmetric-camera trial (`clay_symmetric/`, parameters kept in the note above),
  the paused old-light colour frames and their folder, `color/PAUSED.json`, `color/progress.json`,
  lighting comparison images and `.blend1` backups: 388 files, 671 MB. Recorded as the second
  round in `cleanup_manifest.json`. Earlier notes naming these files describe removed iterations.
- Final colour loop rendering from frame 1 with `render_frames.sh` (Metal, 1080², 256 spp, 30 fps)
  into `color/frames/` → `color/loop.mp4`; log `color/render.log`.
- Split the final render with the LAN Flamenco farm (NUC12, RTX 4060, OptiX). The farm job
  `day06-rouen-v2` (id df4c65ed-6ada-4827-9a1c-5fe0811f646f) renders frames 1 and 111–300 in chunks of 4
  from a byte-identical copy of `color/rouen_color.blend`.
  The Mac (Metal) keeps rendering upward from frame 5. `color/farm_sync.py` copies each settled farm frame
  into `color/frames/`; the local render skips existing files, so whichever machine is first takes a frame.
  Farm frame 1 is kept as `color/farm_0001.png` to compare Metal and OptiX output. Both use
  OpenImageDenoise on the CPU with the same seed. Sync log: `color/farm_sync.log`.
- Final colour loop complete (01:02–03:08): `color/loop.mp4`, 300 frames, 10.000 s, 1080², 30 fps,
  H.264 / yuv420p, 12.0 MB; full decode passed. Farm rendered 167 sequence frames (~33 s each),
  the Mac 133 (~53 s each). Metal vs OptiX on frame 1: 0.256 mean RGB, mean level 65.49 on both
  (`color/device_check.json`). All 300 frame steps lie between 3.66 and 4.11 (median 3.79), with none
  above 1.3× the median; the 18 Mac/farm hand-overs measure 3.67–3.88 and the loop seam 300→1 is 3.66
  (ratio 0.97). `color/loop_review.json`. `render.png` is frame 1 of the final sequence.
