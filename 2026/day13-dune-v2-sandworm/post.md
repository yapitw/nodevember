# Nodevember 2026 · Day 13 · Dune

Date: 2026-11-13

## Idea
- Reading of the prompt (literal / lateral / personal): literal: a giant sandworm standing out of a desert dune.
- One-sentence concept: the worm holds above its hole, maw open at the camera, swaying, its mouth drawing in and
  letting go, sand pouring off its rings and dust breathing out of the sand.
- Constraint I'm stating in the caption: every ring, needle, grain and dune comes from Geometry Nodes sliders; no
  image textures, no simulation, no imported assets.
- Technique to learn or show off: a body that follows its own track (the hole stays put while the worm slides out of
  it); one closed tube for head and body, with the relief pushed along the head profile's normal; sand that leaves the
  body where it was τ seconds ago (the spine Speed·τ further back); Points to Volume dust.
- Output: animation, 6 s seamless loop, 24 fps, 1:1 1080².

## Build log
- Mouth proportions: a thin rim (~0.12 R), needles from the rim's inner edge down a funnel throat, tips stopping short
  of a dark centre (~¼ of the diameter).
- Hide: telescoping rings (each rear edge overhangs the next), slabs, terraced crust, creases; crust octaves capped
  at the mesh spacing (finer ones aliased into radial streaks), micro detail in the shader bump.
- Dust: every on/off is a soft ramp (no popping), built from the full point set before any Delete; warm sand colour,
  paler than the sand, not grey-white.
- Light: low warm side sun, pale yellow ground fog in a finite box (a world volume swallows the sun), an orange-yellow
  dusty sky.
- Motion: five sliders keyed on every frame (Sway, Nod, Squeeze, Phase, Time), every periodic part with a whole number
  of periods in 6 s, so the loop has no seam. Checked as a white-clay preview before the final render.
- Final render: Cycles on a Mac (Metal), 64 samples + OpenImageDenoise, 144 frames in 51 min (~21 s each).
- Tutorial: the big inline sections moved into node groups (`PA_Baleen`, `PA_Sand`, `PA_Puffs`, `PA_Spine At`,
  `PA_Outline`, `PA_Smooth Min`), every group split into lettered sections; the main tree went from 411 nodes to 50.
  The evaluated worm, needles, grains, dust points and dune are bit-identical at frames 1, 48 and 97, so the video
  still matches the file.

## Files
- [x] loop.mp4 (6 s, 24 fps, 1080²) + loop_720.mp4 (720²)
- [x] render.png (hero still, frame 66) + render-113.png (frame 113)
- [x] nodes/main.png + nodes/skin.png + nodes/head.png + nodes/hide.png
- [x] audit: strict_procedural, no issues
- [x] tutorial/README.md (node-by-node walkthrough: the track, the spine, the one-tube skin, the head profile, hide
      layers, baleen, falling sand and dust, the dune)

## Caption
Nodevember 2026 · Day 13: Dune | Sandworm

A colossal worm holds above its hole, maw open at the camera. It rides a track it never leaves: the body is just the
stretch of path behind the head, so the hole stays put, and the sand pours off where the hide was a moment ago.

Rules: Geometry Nodes sliders only; no image textures, no simulation, no imported assets

Made with Blender Geometry Nodes.

#nodevember #nodevember2026 #GeometryNodes #b3d
(Bluesky / X: drop the middle paragraph to fit.)

## Alt text
- A giant ringed worm of rocky, sand-coloured hide stands out of an orange dune and bends over toward the camera. Its
  round mouth is lined with thousands of fine pale needles around a dark throat. The neck sways slowly, the mouth draws
  in and opens again, thin streams of sand pour off its rings, and dust drifts round its base under a hazy orange sky.

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted
