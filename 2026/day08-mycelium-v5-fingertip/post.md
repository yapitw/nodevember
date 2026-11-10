# Nodevember 2026 · Day 08 · Mycelium

Date: 2026-11-08

## Idea
- Reading of the prompt (literal / lateral / personal): literal growth on a lateral stage. The user asked for a new
  take on the v4 Bonnet: "菌絲長在一個立体的手型的石頭上，石頭比著 1 拾指指著上面，最後在拾指指尖長出蘑菇".
- One-sentence concept: a weathered stone hand on a mossy forest floor points one finger at the sky; white hyphae
  climb the stone out of the soil, cords gather up the raised finger, and a bonnet mushroom grows on its fingertip.
- Title: Fingertip / 指尖.
- Constraint I'm stating in the caption: all geometry from Geometry Nodes on empty objects (hand, moss, litter,
  mycelium, mushroom, forest); the hand is a skeleton of points turned into stone by an SDF grid. No simulation,
  image textures or assets.
- Technique to learn or show off: a hand from bones (three bones and three curls per finger) → Points to SDF Grid →
  Fillet → Mean → Grid to Mesh; shortest-path mycelium on that mesh (paths down to the soil for the colony, paths up
  to the fingertip for the cords), smoothed into flowing threads; the v4 mushroom on the fingertip.
- Output: one-shot growth, 15 s, 24 fps, 1080² (1:1), Cycles. Not a loop. Ends on a close-up of the mushroom.

## Growth schedule (T = growth clock 0..1, reaches 1 at frame 300, then hold to 360)
| T | stage | geometry |
|---|---|---|
| 0.02 – 0.40 | colonisation | hyphae leave the soil in a few patches and spread over the stone; cost-from-soil < reach(T) |
| 0.30 – 0.50 | cords | shortest paths to the fingertip thicken |
| 0.40 – 0.60 | hyphal knot | a white knot swells on the fingertip |
| 0.46 – 0.56 | pin | the whole body plan in miniature |
| 0.53 – 0.92 | expansion | stem stretches, cap inflates: cone → bell → parasol |
| 0.70 – 0.92 | maturation | cap opens, gills deepen |
| 0.88 – 1 + hold | sporulation | spores drift from under the cap (unclamped clock in the hold) |

## Build log
- Started from v4 Bonnet's build.py: growth clock, Float Curve schedule, Cap group, mushroom, moss, litter, canopy light.
- Hand v1 (spheres along each finger, palm slab, back of the hand to the camera) read as a ☝ but looked tubular and
  boxy. User note: "手的型狀可以再優化一下". Hand v2:
  - Finger group: three bones with an oval section, slimmer mid-bone, a pad shifted to the palm side, and a bony
    knuckle wherever a joint bends (out of sight on a straight joint).
  - Thumb posed by its four joints (`fit_chain`), its last bone lying across the curled middle finger.
  - Muscle as long capsules (ball of the thumb, edge of the little finger, the web between thumb and index) instead
    of spheres; the inside of the fist filled, as a carving would be.
  - Nails as a raised plate in a groove, displaced in the hand's own frame (index and thumb).
  - Palm to the camera: the fist, the thumb and the raised finger read at once.
- Mycelium on the stone: triangulated hand mesh → edge cost (wander noise, cheaper in the hollows) → shortest paths
  down to the soil (start chance falls with height: dense low, sparse high) and up to the fingertip (cords). The
  edge paths run straight with sharp turns, so each curve is blurred along itself (ends pinned) and snapped back onto
  the stone with Sample Nearest Surface.
- Stone: mottled sandstone, iron stains, grime in the hollows (surface vs a blurred copy of itself), patchy crustose
  lichen from Voronoi rosettes, damp near the soil.
- Mushroom 1.3 × the Bonnet's so it holds its own on a stone finger.
- Forest: far crowns close the sky behind the cap; trunks are their own object that the sun skips (light linking),
  since sunlit trunks read as stone columns. Shade blobs have no specular (a grazing-sun sheen showed as grey planes).
- Moss: no bare corridor; fronds creep low (they stood up like grass at this scale).
- Clay pass 1 (Workbench, 14 s). User note: "可以最後特寫蘑菇嗎". Camera now in three moves: wide on the hand →
  the finger and its mushroom (T 0.33–0.73) → a close-up of the whole mushroom from a little below the cap, gills
  showing (T 0.74–0.98, while the cap opens), then a slow 1.2 cm creep through a 2.5 s hold of falling spores.
  Aperture ≈ f/11 → f/5 → f/16 (fstop 0.11 → 0.05 → 0.16 in this cm scene).
- In close-up the cottony fuzz read as stiff bristles: wisps now curl (a hook and a kink, spun at random), lie low on
  the stone, shorter and thinner.
- Clay pass 2: clay/loop.mp4 (15 s).
- Render: timed, a full-res frame is 17–21 s on the Mac (128 spp, persistent data on; the per-frame cost is mostly the
  mycelium and mushroom re-evaluating, so 64 spp saves little). User chose the farm for the whole shot (one device,
  so no OptiX/Metal hand-off): a LAN render node (RTX 4060, OptiX, Flamenco), ≈ 10 s/frame + 30 s per 20-frame chunk, about 1 h.
  Farm frame 40 vs the Mac's: SSIM 0.994, PSNR 45.7 dB; the sun's light linking works under OptiX.
  The frames are copied home and encoded into loop.mp4 / render.png with vignette and grain.
- Farm run: 360 frames in 67 min, all from the farm node. Mean luma has no step over 1 level anywhere, and the hold drifts
  by at most 0.04 a frame (no flicker).
- The last frame is a close-up without the hand, so the hand is missing from the story there. `still_wide.py` renders
  a second still from piece.blend at frame 360 on the opening shot's line, camera lower so the cap meets the dark
  wood above the foliage: render-wide.png (Mac, 35 s).
- Sun (2026-11-10, "陽光的感覺不夠強烈"): the sun came from behind-left, so the camera saw only the hand's shadow
  side (N · L ≈ −0.2 on camera-facing stone) and the shot read as overcast. A stronger sun with a dimmer sky and fill
  alone changed nothing on the hand (tests A–J). Now SUN_DIR (0.86, 0.22, −0.40): left-front, 23° up; sun 16,
  (1.0, 0.72, 0.42); fill 9 → 2.5 kW; sky (0.30, 0.42, 0.40) × 0.35; compositor bloom 0.3. The low sun lit the
  forest's dark masses as flat facets and then as pale smooth slabs: Set Shade Smooth and a near-black base. The first
  render's frames are kept outside the repo; render-wide.png and the tutorial figures redone.
- Farm run 2 (new sun): 360 frames in 69 min, all from the farm node. Largest mean-luma step 0.32 (frames 144–155, while
  the camera moves in), mean 0.07: no flicker. Light link, bloom and the dark forest hold in every frame.
- Sun, round 2 ("感覺新的沒有比較好"): side by side, the front-lit render read darker and duller, not sunnier.
  Four readings as a sheet (P bright day, Q backlit, R backlit + compositor sun beams, S the first look, brighter);
  the user chose Q. SUN_DIR (0.45, −0.78, −0.43): behind the hand, a little left, 25° up; sun 25,
  (1.0, 0.66, 0.36); fill 5 kW; sky × 0.5, sky gaps × 1.0; exposure 0.4; bloom 0.5. Moss tips, the hand's rim,
  the stem and the cap edge glow; shadows run towards the camera. The farm node was offline, so all 360 frames went on
  the Mac (Metal, one device). The front-lit render is kept outside the repo; render-wide.png redone; the
  tutorial trick is now "put the sun behind the subject" with a three-way figure.
- Mac run (backlit): 360 frames in 99 min (render_frames.sh, one attempt, no crash). Largest mean-luma step 0.6
  (frames 140–160, the camera moving in off the bright moss), mean 0.11, hold ≤ 0.12: no flicker. Under the backlight
  the trunks face the camera in shadow, so the light-link figure is rendered from the first render's .blend.
- Tutorial: the repeated hand helpers became node groups (PA_Bone, PA_Knuckle, PA_Capsule, PA_Nail, PA_Rosettes), and
  every frame got a "N · Title" or "a · Title" label. Proven unchanged: evaluated vertex counts and coordinate sums at
  frames 120 and 300 match (the mycelium differs by 0.001 summed over 286 705 points, float noise), and the stone
  material renders at 54.8 dB PSNR against the old one. The farm frames stay valid. tutorial/README.md walks through
  the hand, finger, mycelium, stone, light link and camera; the mushroom, moss and clock link to the v4 tutorial.

## Files
- [x] piece.blend (Cycles 128 spp, 1080², persistent data; `save_final.py` writes it from build.py)
- [x] render.png (frame 360: the close-up, vignette + grain)
- [x] render-wide.png (the whole hand with the grown mushroom, frame 360; `still_wide.py`)
- [x] loop.mp4 (15 s, 24 fps, 1080², vignette + temporal grain; 360 frames on the Mac, backlit)
- [ ] nodes.png (node tree screenshot, readable)
- [x] tutorial/README.md (node-by-node walkthrough; node cut-outs in tutorial/images, figure scripts in tutorial/src)
- [ ] extra: hand sweep / breakdown

## Caption
Mastodon (357/500):

> Nodevember 2026 · Day 08: Mycelium | Fingertip / 指尖
>
> A stone hand points at the sky; hyphae climb it out of the moss and a bonnet mushroom grows on the fingertip,
> backlit by a low sun. Node-by-node tutorial: github.com/yapitw/nodevember
>
> Made with Blender Geometry Nodes, Cycles.
>
> @Nodevember@graphics.social
>
> #nodevember #nodevember2026 #GeometryNodes #b3d

Bluesky / X: the same without the middle paragraph (handles @nodevember.bsky.social / @Nodevember). Instagram and
Blender Artists add: "Rules: all geometry from Geometry Nodes on empty objects: the stone hand is a skeleton of bones
melted by an SDF grid, the mycelium is shortest paths on its mesh. No simulation, image textures or assets."
(`nodevember.py caption 8 --tools "Blender Geometry Nodes, Cycles" --title "Fingertip / 指尖" --constraint … --note …`)

## Alt text
- loop.mp4: A weathered stone hand stands in sunlit fern moss on a dark forest floor, one finger pointing up, with a
  low sun behind it. White threads creep out of the moss and lace the stone, thicken into cords up the raised finger
  and gather in a white knot on its tip. The camera moves in as a thin pink stem rises from the knot under a closed
  cap, then comes close as the cap opens into a pale, backlit parasol and spores drift down into the light.
- render.png: Close-up of a pale bonnet mushroom on a thin pink stem, its gills lit from behind by a low golden sun,
  spores drifting through the light; below, the tip of a stone finger wrapped in white mycelium threads, and out of
  focus behind, green leaves on a dark forest.
- render-wide.png: A stone hand in fern moss points one finger at the sky, its stone laced with white mycelium; a
  small pale mushroom stands on the fingertip, its cap glowing in the backlight against a dark forest.

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted
