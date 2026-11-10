# Nodevember 2026 · Day 09 · Winged

Date: 2026-11-09

## Idea
- Reading of the prompt (literal / lateral / personal): lateral-natural, follow-up to v4. User brief: "改用 Samara，
  做一個新的版本 focus 在一個種子的掉落，背景深色虛化，近景陽光照射對比強烈 … single winged samara".
- One-sentence concept: the camera falls with one silver maple samara, a little above it; the key spins in place
  in hard low sun while the dark wood below drifts up as soft bokeh and dust motes stream past; mid-loop a gust
  tips the spin disc, the sun rakes across the corrugated wing, and it rights itself.
- Constraint I'm stating in the caption: same samara generator as v4 (wing = a field over (s, v); veins fanned
  from the root, now also corrugating the membrane); all geometry from Geometry Nodes on empty objects; no
  simulation, image textures or imported assets.
- Technique to learn or show off: tracking-shot autorotation with real keys' numbers (cone 18°, spin axis through
  the centre of mass at the wing root, pitch −2.5° leading edge down, 6 cm per turn: a silver maple key slowed about
  30 times, in spin and in fall alike); sliding-world loop (world slides up one tile per loop, motes shrink away and
  grow back around the wrap, bokeh flecks fade over their drift); light linking keeps the wood in shade (sun + fill light only the key
  and the motes).
- Output: 12 s seamless loop, 24 fps, 1080² (1:1), Cycles, motion blur 0.15.

## Build log
- Camera 38° down showed the wing edge-on and small → 55° down, 33 cm; sun 28° up, ~63° off the camera axis.
- 150 bright flecks read as polka dots → 70, brightness rand², size 0.002·6^rand × distance, round aperture.
- Close up the wing read as clay; voronoi nut cells read as a turtle shell → nut gets lengthwise ribs + wrinkles;
  veins sparser (ln a × 4.2) and darker; the membrane is corrugated along the same vein field in GN, so the
  raking sun draws real light/shadow ribs (biggest single gain).
- 1 rev/s with a 0.3 shutter smeared the wing → 9 turns per loop (0.75 rev/s), shutter 0.15.
- Clay pass: clay/loop.mp4; seam PSNR 288→1 = 28.3 dB vs 28.1 between neighbours.
- (Superseded by the one-piece rebuild below.) Nut/wing joint clipped (user: "種子和羽翼的接合處很容易穿模"): the wing starts halfway along the nut, and the cup,
  wave and wrinkles lifted its root edge through the nut surface (a jagged cut line; at Wave 2.6 or Cup 0.5 whole
  flaps poked out). KeyShape § d "Root inside the nut": over the nut length the membrane is flattened onto the
  nut's mid-plane (z × smoothstep(0.55 LN, 1.3 LN, x)) and squeezed inside 0.75 × its half-width
  (fading out over 0.62–0.95 LN), so the wing grows out of the nut's end and side seam. Checked with red-nut
  Workbench close-ups from five angles at the rest values and the extremes.
- Tutorial (user: "製做 tutorial"): before the shots, the helper math became node groups (PA_Smoothstep, PA_Mix,
  PA_Clamp, PA_Harmonic, PA_InFrustum; shader copies for the wing), group sections are lettered (a · …), values that
  cross sections are labelled, and the nut and the corrugation sections are split in two. 611 → 505 nodes. The rebuilt
  scene is the rendered one: evaluated vertices identical at frames 1, 161 and 300 (main and sliders), hud.json
  identical, a 30 % Cycles preview differs in 5–6 pixels by one level, the same as two renders of the old file.
  No re-render needed.
- One-piece samara (user: "不是很滿意，有辦法讓種子一體成型嗎？", reference: Fig. 1 of "Maple samara flight is robust to
  morphological perturbation", Communications Biology 2024, A. saccharum / A. saccharinum): the three meshes
  (membrane grid, leading-edge vein tube, squashed-sphere nut) and the "root inside the nut" fix are gone. One UV
  sphere (160 × 320) stores s = arccos(z)/π and φ; PA_KeyShape gives a mid-surface over (s, v = (1 − cos φ)/2) whose
  outline is a smooth union (k = 1 mm) of a stalk-and-nut plan curve and the wing; every point moves to
  mid-surface + normal × (sin φ × (nut bulge + 0.05 mm) + sign(sin φ) × leading-edge vein). The upper face is always on
  the +normal side and the lower on the −normal side, so nothing can clip, by construction. The nut gets eight ribs
  and a raised net of veins (Voronoi) in GN; one material, PA_Pericarp, blends paper → nut shell by a `nut` mask, so
  the colour runs through the neck as the surface does. Mesh 51 042 verts, closed, outward; sliders extremes
  (frames 42, 95, 201, 230, 363, 420, 526, 556) render intact.
- Tutorial rewritten for the one-piece key (§ 2 a–f, § 3 a–i, § 4 a–f; sphere → samara and outline figures). Before
  the shots the busiest sections were split (KeyShape outline 34 → 18 + 16 nodes, Samara corrugation and nut relief,
  Pericarp vein lines); the evaluated geometry is identical to the rendered build (max difference 0 at frames 1, 161,
  300 for key, motes and flecks).

- Rotation and veins (user: "研究一下旋轉方式 … 羽翼上大的葉脈好像有點平面", with a strobe photo of a falling key and
  Ezra, Levavi & Bar-On, "The load-bearing mechanism of plant wings", Acta Biomaterialia 158 (2023) 423–434;
  kinematics from Jung & Rezgui 2024, Royal Society Open Science (PMC11441657), and Nave et al., arXiv 2010.12553):
  pitch −4° → −2.5° (real: −0.7 to −2.6°), cone 13° → 18° (5–15° best thrust; a little steeper to read on screen),
  spin axis 1.05 → 1.4 cm from the nut tip (centre of mass at 24–30 % of the length; 26 % here), 10 → 6 cm per turn
  (silver maple 6.2 cm), so the world slides 54 cm per loop instead of 90. At 54 cm about 127 far motes per loop
  would shrink on screen at the wrap (50 at 90 cm), so the motes' fade widened from 1 % to 10 % of u (1.2 s).
  Veins: the paper's cross-sections show vein bundles bulging both skins and a thick marginal vein at the free edge,
  so PA_Samara § f–g raise the veins on both faces (0.11 mm × size 0.25 + 2·rand³, the same width, end and per-vein
  value as the painted veins) and adds a 0.15 mm marginal vein along the trailing edge; corrugation 0.09 → 0.06 mm;
  the sphere 160 × 320 → 400 × 640 (255 602 verts) so ridges resolve. Option sheets: side-view strobes A–D against
  the photo, vein close-ups A–D in the real shot, and a clay comparison; user chose D and the full rotation set
  ("D", "用整套建議"). Render time per frame unchanged (≈ 7 s).

## Second post: Sliders (controllability reel)
- sliders.py imports build.py's scene and changes three things: the key's eight shape inputs (Length, Width, Sweep,
  Cup, Bend, Twist, Wave, Seed) and its coning angle (Cone) become sliders on the Key object's GN modifier and are
  keyframed; the key does not turn (user: "可調整性的影片不要轉動"): no spin, precession, drift or gust, one fixed
  pose (heading 18°, tip up-right); the background is plain black (user: "背景全黑就好": flecks and motes removed,
  world strength 0; sun and fill unchanged); the camera comes in to 25 cm.
- Timeline (26 s, seamless): 1 s at rest, then each slider in turn goes to both ends of its range
  and back (2.25 s each), then all of them move together through three other keys and back to the hero.
- Readout: hud.py draws the modifier's values from hud.json (each slider's F-curve, evaluated per frame), so the
  numbers on screen are the inputs that made that frame; the slider being moved lights up warm.
- Fit check: the key's projected extent over every frame stays within NDC x 0.17–0.87, y 0.45–0.77, clear of the
  readout band (bottom 0.21).
- Rendered as white clay (user: "不要渲染 slider 了", "slider 的影片用白模就好"): `sliders.py --clay` →
  sliders/clay/clay.blend (Workbench, 1080², studio light, no DOF) → sliders/clay/frames → hud.py →
  sliders/sliders.mp4. Cone now rests at 18° and goes
  to 30° and 4°; the pose uses the new pitch and spin axis.

## Files
- [x] render.png (hero still = frame 161, the gust: sun raking across the raised veins);
  _still_173.png (frame 173, the wing broadside, still tipped as the gust passes)
- [x] loop.mp4 (re-rendered with raised veins and the new autorotation: 288 frames, Cycles 128 spp, Metal, 39 min;
  seam PSNR 288→1 = 20.45 dB vs 18.23–22.05 between neighbours)
- [x] nodes/ (samara.png overview, key-shape.png, material.png = PA_Pericarp, flight.png, key.png; sliders-key.png for the reel)
- [x] tutorial/README.md (node-by-node walkthrough)
- [x] extra: sliders/sliders.mp4 (controllability reel: 624 frames, 26 s, 1080², white clay in Workbench, 4 min on the
  Mac, readout by hud.py; 624→1 identical). (An earlier Cycles version of the reel
  was retired with this change.)
- Audit: strict procedural, no issues; 625 nodes in GN + PA_ materials, PA_KeyShape 80, PA_Samara 181,
  PA_Pericarp 116 (without frames and group I/O).

## Caption
Mastodon / Instagram / Blender Artists:

> Nodevember 2026 · Day 09: Winged | Solo
>
> One silver maple key, autorotating like the real thing (18° cone, ~6 cm per turn, here about 30× slower). The
> camera falls with it through low sun; the dark wood below is only bokeh. 12 s seamless loop.
>
> Rules: every mesh from Geometry Nodes on empty objects: no simulation, image textures or imported assets
>
> Made with Blender Geometry Nodes, Cycles.
>
> @Nodevember@graphics.social (IG: @nodevemberio)
>
> #nodevember #nodevember2026 #GeometryNodes #b3d

Bluesky / X: the same without the middle paragraph (262 / 250 chars), handle @nodevember.bsky.social / @Nodevember.

Sliders reel (second post, sliders/sliders.mp4):

> Nodevember 2026 · Day 09: Winged | Solo, the sliders
>
> The same maple key is one Geometry Nodes group with nine inputs. Each goes to both ends of its range and back,
> then all move together through three other keys. The numbers are the modifier values that made each frame.
>
> #nodevember #nodevember2026 #GeometryNodes #b3d

Bluesky / X: drop the last sentence of the middle paragraph (320 → 262 chars).

## Alt text
- A single pale silver-maple seed, a ribbed brown nut flowing into one papery wing, spins in place against a near-black background. A warm,
  low sun from the right picks out raised veins fanning across the wing; out-of-focus green and gold dots of light drift
  upward behind it and specks of dust float past.
- Sliders reel: a white clay model of a maple seed, a ribbed nut flowing into one veined wing, hangs still against black. Below it, a
  readout of nine sliders (Length, Width, Sweep, Cup, Bend, Twist, Wave, Cone, Seed); as each slider lights up and
  moves, the wing grows longer or wider, cups, bends, twists, ripples or changes its vein pattern, then all change
  at once into three other seed shapes and back.

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted
