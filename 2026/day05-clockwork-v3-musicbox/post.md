# Nodevember 2026 · Day 05 · Clockwork

Date: 2026-11-05  ·  Folder: 2026/day05-clockwork-v3-musicbox

## Idea
- Reading of the prompt (literal / lateral / personal): clockwork as a calendar. A music box whose turning stage is one year (the user's idea: 圓形的發條音樂盒，轉動時上面發生四季變換).
- One-sentence concept: a round wind-up music box; one turn of its stage is one year, and the tree on it goes from snow through blossom, leaf and fruit to leaf-fall and back. A brass index at the front points at the season emblem passing under it.
- Constraint I'm stating in the caption: 100 % Geometry Nodes, no keyframes, no simulation, no image textures. Every leaf, petal and snowflake is a function of one loop clock.
- Technique to learn or show off: an analytic tree (trunk → branches → twigs as closed-form curves, Points to Curves); a season time u = 4·Phase with every change a window inside (0, 4), so the year loops; things that let go fall along a drift curve to the mound and lie there until the snow covers them; a pinned cylinder whose pins pluck a comb (each tooth's deflection is a sum over its pin slots); gears in mesh (pinion on the stage rim, cylinder gear on the spring barrel).
- Output: loop, 12 s, 30 fps, 1:1, Cycles.

## Build log
- Blender 5.2: Curve to Mesh no longer reads the radius attribute by itself; pass Radius into its Scale input (first pass: branches came out as huge ribbons).
- First framing: the tree was too small and the box read as a cake tin. Tree scaled ×1.35, 9 branches × 7 twigs, camera closer.
- Season emblems were too small to read; mound radius 0.82 → 0.78 to make room, emblems 0.075 → 0.10, and a flat kite-shaped index hand instead of a cone on a post.
- Sound: the cylinder is pinned from a score (an original 4-bar tune, one bar per season, 80 bpm), and the comb is tuned diatonically A3 … C7. GN reads the score through two Index Switches (pin → tooth, pin → angle); each tooth's bend is the per-tooth sum of its pins' plucks (Accumulate Field by tooth, then Sample Index). The same score is synthesised in Python with Blender's audio engine (aud): cantilever-beam partials 1 : 6.27 : 17.55, tails wrapped round the loop and a circular (FFT) reverb, so the sound loops as seamlessly as the picture.

- Tree pass 2 (after looking at the first renders): twigs only between 25 % and 75 % of a branch and shorter/thinner towards its tip, so the branch stays the leader (a twig on the very tip made branches look cut short); the trunk's first point sunk straight down into the mound (the leaning S cut its end square to the curve and lifted one side off the grass); whole tree × 1.15 (`TREE_S`) and branches × 1.3 to make up for the shorter twigs; leaves anchored on the wood with Curve to Points (they used to sit up to ±7.5 cm off it and hung in the air at the tips); tips taper with tip + (1 − tip)(1 − f)^k (a linear taper left blunt ends, a taper to 0 left spikes); crooks from two Ping-Pong triangle waves with corners on the control points, so twigs computed from the formula still land on the wood; leaves and blossom turned by the curve tangent (to one side of their twig) instead of away from the trunk, which made every branch look like a feather; cloche wall 0.95 → 1.10 (`DOME_H`).
- The limb formula became a node group, `PA_MB_Limb`: the twig section had grown to 198 nodes because every twig re-derives its branch; now it is 85 and the tree 552 (was 586). Same geometry to the vertex.

## Files
- [x] musicbox.blend (+ build.py, which builds it: `Blender -b --factory-startup --python build.py`)
- [x] _still_090.png (blossom) + _still_240.png (leaf-fall), full-quality frames from the loop
- [x] loop.mp4 + loop_sound.mp4 (12 s, 30 fps, 1080², Cycles 128 spp; frames 1–160 on the Mac, 161–360 on NUC12 / RTX 4060 via Flamenco)
- [x] musicbox.wav (the tune, `build.py -- --sound`, from the same score as the pins)
- [x] tutorial/README.md (node-by-node walkthrough, node shots in tutorial/images)

## Caption
Nodevember 2026 · Day 05: Clockwork | Music box

A wind-up music box: one turn of its stage is one year. The tree goes from snow through blossom, leaf and fruit to leaf-fall and back, and the pinned cylinder plays one bar per season.

Rules: 100% Geometry Nodes, no keyframes, no simulation, no image textures

Made with Blender Geometry Nodes.

#nodevember #nodevember2026 #GeometryNodes #b3d
(Bluesky/X: drop the description line; per-platform handles from `nodevember.py caption 5 ...`)

## Alt text
- A round brass music box with a pierced band of translucent green and amber enamel, under a tall glass cloche on a
  black background. On its grass stage a small twisted tree passes through a year as the stage turns: bare and
  snow-covered, then a cloud of pink blossom, full green leaf, red apples, orange leaves that fall onto the grass, and
  snow again. A butterfly key on the side slowly turns.

## Posting
- [ ] Mastodon (mention @Nodevember@graphics.social)
- [ ] Bluesky (@nodevember.bsky.social)
- [ ] X (@Nodevember)
- [ ] Instagram (@nodevemberio)
- [ ] Blender Artists (tag: nodevember)
- [ ] Posted
