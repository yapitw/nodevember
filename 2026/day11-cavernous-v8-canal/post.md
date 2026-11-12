# Nodevember 2026 · Day 11 · Cavernous

Date: 2026-11-11

## Idea
- Reading of the prompt (literal / lateral / personal): the user's brief, "利用 day 10 geode generator 做一個無限晶洞探索";
  idea A of six ("淹水的晶洞運河"): Day 10's Level slider (water-level onyx) read as real water.
- One-sentence concept: a small boat with a lantern drifts down an endless chain of giant flooded geodes, each
  chamber a different kind, joined by crystal-lined passages where one kind fades into the next.
- Constraint I'm stating in the caption: every chamber is the Day 10 generator's own field and crystal groups,
  scaled ×150; no image textures, simulation or imported assets.
- Technique to learn or show off: reuse a node-group library across days (build.py imports Day 10's build.py);
  per-voxel "two nearest chambers" evaluation, so chamber n is a function of n alone (no end to the chain);
  per-chamber presets via Index Switch on n mod 5; sites ray-cast from each chamber's centre.
- Output: animation, 34 s (816 frames), 24 fps, 1080² (1:1), Cycles.

## Build log
- 2026-11-11: first build. A 6-chamber chain on a 2.5 mm (Day 10 units) grid: 985k verts, evaluates in 0.5 s.
  K = 100 felt cramped (boat 2.3 m in a 12 m hall, crystals as big as the boat) → K = 150, Crystal Scale 0.45,
  a standing hooded figure with a hooked staff and lantern (the seated cone read as a chess pawn).
- Camera options A/B/C: B, 8 m behind and 2.8 m up, 18 mm.
- Clay v1 (30 s): the boat was still in the third arch at the end → 34 s, so it drifts on into chamber 3 (druzy)
  after the camera stops.
- Look: the first Cycles stills were black: the point light sat inside the lantern's emissive glass, which blocked
  its shadow rays (now transparent to shadow rays). Light options A–D (600 W / 2000 W / + world
  ambient / + haze): the world ambient does nothing in a closed cave; haze 0.004 gives the lantern a halo that
  backlights the figure. Chosen: 2000 W, a less orange flame (amethyst and celestine kept their colour), haze.
- Day 10's crystal cover (≈ 67 % of the wall under big crystals) read as a camouflage pattern at ×150 → cover 2.6;
  celestine's 7 mm blades capped at 5 mm (they crowded the lens).

- Figure (user: "人的比例太大了", then "船不用縮"): the figure, its staff and lantern scaled about its feet, the boat
  kept; options ×0.75 / ×0.6 / ×0.45 → ×0.6 (1.05 m). The lantern now hangs lower and lights the
  boat and the water round it.
- Wake (user: "正式版加上船的 V 形尾波，讓倒影在船後碎開"): the water became a 10 cm grid (476k verts) displaced in
  the boat's frame, read each frame with Object Info: two Kelvin arms at 19.5°, divergent crests at 35° to the track
  (λ 1 m), weak transverse waves inside the V (λ 2.8 m), fading out 10–22 m behind. Slow 4D-noise ripples in the
  shader (W = frame / 300).
- Final: 1080², 64 spp + OIDN, haze 0.004; Mac (Metal, ~30 s/frame) took 1–351 and a second PC with an RTX 4060
  (OptiX, ~23 s) 352–816. Same frame on both devices: equal brightness (+0.26 %) but PSNR only 40 dB, with single crystal
  facets up to 2× brighter on OptiX, so instead of interleaving there is one hand-off, crossfaded over frames 344–359
  from renders of both devices; no change spike in a consecutive-frame scan. The lantern glass's emission now rises
  with the light (it glowed at full strength in the dark first frames); frames 1–40 re-rendered.
- Hero still (v1): frame 120 at 2160², 256 spp (amethyst hall, agate arch, celestine beyond).
  Alternative: render-600.png (citrine dome, wake breaking the reflections). Node layout tidied for the screenshots (one Group Input per section, unused ChamberKind
  outputs hidden); the evaluated canal, water and boat hash the same before and after.
- Audit (v1): strict_procedural True, no issues; 18 Geometry Nodes trees, 609 nodes.

### v2 (2026-11-12)
- Passages (user: "晶洞的連結過渡怪怪的，岩壁是亮面"): the arch's cut face was Day 10's polished agate slab
  (roughness 0.1, coat 0.35, no bump), which reads as glossy plastic at ×150. Options A–D (polished / matte /
  scalloped and wet / broken blocks), then the user: "可以直接用不同的晶石壁嗎？… 兩種晶石漸變過去".
  So the passages grow crystals too: PassageSites scatters sites on the cut face at its chamber's own density, and
  KindBlend gives each site chamber n or n + 1, with smoothstep odds across the passage (new slider Blend 0.03, about
  ±4.5 m). Amethyst points thin out as the next kind takes over. The cut is joined to the hollows with a smooth max
  (0.006), and the rock's druzy glitter is twice as fine (3600 cells per unit).
- Hall order (user: "白色晶洞換到第二幕，藍色這個看起來有點暗淡"): amethyst → white quartz → citrine → celestine →
  calcite.
- Clear quartz (user: "白色的晶石 應該是要透明才對"): options A–D (milky / clarity 0.8 / clear
  tips with milky roots / the same with more light through the roots) → D: clarity 1.0, crystals ×3 and ×1.8 longer,
  milky only over the bottom third of each crystal (fading out by 0.65 of its length), and the roots pass more
  shadow rays (0.6 + 0.42 × root), so the hall stays bright behind the points.
- Final v2: same split and settings as v1. Mac (Metal, ~36 s/frame) 1–360, the RTX 4060 PC (OptiX, ~26 s) 361–816,
  crossfaded over 345–360 from renders of both devices; the consecutive-frame difference stays 9.6–11.1 through
  340–366 (no step at either end of the blend).
- Hero stills (v2, 2160², 256 spp): render.png = frame 120 (amethyst hall, the quartz-lined passage
  ahead); render-600.png = frame 600 (citrine dome, the passage to celestine ringed in pale blue, the wake breaking
  the reflections).
- Audit (v2): strict_procedural True, no issues; 20 Geometry Nodes trees (new: PA_PassageSites, PA_KindBlend,
  PA_Mix), 696 nodes (not counting frames). Note: the water's Object Info reads the boat, itself a Geometry Nodes
  object.
- Tutorial (2026-11-12): tutorial/README.md. For readable cut-outs, KindBlend and PassageSites got section frames,
  the wake and the hull were split in two, the water's and boat's sections are lettered, and a few values that cross
  sections got labels. The evaluated canal, water and boat hash the same as the rendered scene (frames 120 and
  300). build.py's notes and slider tips said ×100 (from before K = 150): now ×150.

## Files
- [x] loop.mp4 (816 frames, 34 s, 1080², 24 fps, H.264 CRF 16, 41.2 MB)
- [x] render.png (hero still, frame 120, 2160², 256 spp) + render-600.png (alternative, frame 600)
- [x] nodes/main.png (main tree, 5 sections) + nodes/field.png (PA_CaveField) + nodes/PA_*.png (ChamberKind,
  CanalSites, PassageSites, KindBlend, Water, Boat)
- [x] tutorial/README.md (node-by-node walkthrough)

## Caption
Mastodon (315/500):
> Nodevember 2026 · Day 11: Cavernous | Flooded geode canal
>
> Rules: every chamber is my Day 10 geode generator's own field and crystal groups, scaled ×150; no image textures,
> simulation or imported assets
>
> Made with Blender Geometry Nodes.
>
> @Nodevember@graphics.social
>
> #nodevember #nodevember2026 #GeometryNodes #b3d

Bluesky (166/300) / X (154/280): title line, "Made with Blender Geometry Nodes.", the handle, tags.

Instagram / Blender Artists, add after the title:
> A lantern boat drifts down an endless chain of giant flooded geodes. Chamber n's kind, seed and size come from n
> alone, so the canal has no end; in the passages between halls, one crystal fades into the next.

## Alt text
- Video: A small wooden boat with a hooded figure and a hanging lantern drifts across dark still water inside a giant
  geode. Lantern light catches walls of purple amethyst points; through a crystal-lined passage where the purple
  thins out, it enters a hall of large clear quartz points with milky white roots, then an orange citrine hall; a
  V-shaped wake breaks the reflections behind the boat. The camera stops and the boat drifts on alone through the
  next passage towards pale blue celestine.
- Node screenshot: Blender Geometry Nodes editor with five coloured frames (Grid, Rock, Crystal sites, Crystals, Canal);
  the crystal steps are node groups reused from the Day 10 geode generator, and the crystal-sites frame adds sites on
  the passage walls that mix the two neighbouring kinds.

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted
