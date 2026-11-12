# Nodevember

My entries for [Nodevember](https://nodevember.com), the November challenge for node-based art. One prompt a day.

Every piece is procedural, built with Blender 5.2 Geometry Nodes and shader nodes, with no image textures and no
hand modelling. Days 1–8 come with the `.blend` file and the Python build script that generates it, so you can read
exactly how it is made and build it again yourself. From Day 9 on, a day folder holds a node-by-node tutorial and the
finished renders.

## 2026

| Day | Prompt | Piece | |
|---|---|---|---|
| 01 | Origami | **Paper plane.** A sheet of washi paper folds itself into a paper plane and glides off the stack. The sheet underneath is already waiting, so the 8-second loop is seamless. | [files](2026/day01-origami) · [loop](2026/day01-origami/loop.mp4) · [**node-by-node tutorial**](2026/day01-origami/tutorial/README.md) |
| 02 | Furniture | **A day in the corner.** A reading corner lit by one window, out of frame. In 10 seconds the sun crosses the room from raking morning light to a golden window on the wall, the lamp clicks on at blue hour, the moon comes through, and morning returns. Bouclé, walnut, travertine, pleated linen, knit, wool and glaze are all shader nodes. | [files](2026/day02-furniture-v3-corner) · [loop](2026/day02-furniture-v3-corner/loop.mp4) · [**node-by-node tutorial**](2026/day02-furniture-v3-corner/tutorial/README.md) |
| 03 | Stitch | **Kintsugi.** An old cream tea bowl breaks along its gold seams. The shards are glued back one by one with black urushi lacquer, which squeezes out of each seam, and then gold flows down every crack from the rim until the bowl is whole again. | [files](2026/day03-stitch-v3-kintsugi) · [loop](2026/day03-stitch-v3-kintsugi/loop.mp4) · [**node-by-node tutorial**](2026/day03-stitch-v3-kintsugi/tutorial/README.md) |
| 04 | Brass | **Chladni.** Sand on a brass plate finds the nodal lines of four rising tones: an X of arcs, a rounded square round a ring, a ring of loops, then lace. At each new tone the grains leap off the parts that shake and settle on the lines that stand still. One standing-wave formula, with Newton steps in a Repeat Zone. | [files](2026/day04-brass-v2-chladni) · [loop](2026/day04-brass-v2-chladni/loop.mp4) · [**node-by-node tutorial**](2026/day04-brass-v2-chladni/tutorial/README.md) |
| 05 | Clockwork | **Four-season music box.** A wind-up music box whose stage makes one turn per loop, and that turn is one year. The tree on it goes from snow through blossom, leaf and fruit to leaf-fall and back, and behind a wall of translucent enamel a pinned cylinder plucks a steel comb, one bar of the tune per season. The sound is synthesised from the same score as the pins, so picture and tune loop together. | [files](2026/day05-clockwork-v3-musicbox) · [loop with sound](2026/day05-clockwork-v3-musicbox/loop_sound.mp4) · [**node-by-node tutorial**](2026/day05-clockwork-v3-musicbox/tutorial/README.md) |
| 06 | Vault | **Rouen nave.** You lie on the floor of the nave of Rouen Cathedral and look up as you walk towards the rose window: four storeys of stone, pointed arches and a quadripartite rib vault, with every ochre stone of the cells laid course by course. The nave slides back one bay per loop, so the 10-second walk never ends. Rendered in Cycles, and again in EEVEE. | [files](2026/day06-vault-v5-rouen) · [loop](2026/day06-vault-v5-rouen/color/loop.mp4) · [EEVEE loop](2026/day06-vault-v5-rouen/eevee/loop.mp4) · [**node-by-node tutorial**](2026/day06-vault-v5-rouen/tutorial/README.md) |
| 07 | Tree | **After the rain — Supertree.** Eleven steel trees in an imagined Singapore garden at blue hour, inspired by the Supertree Grove at Gardens by the Bay. After the rain the garden wakes: violet-white light rises tree by tree through curved, flaring canopies, and a suspended skyway lights up between the two nearest trees. The crown framework is one connected graph of ribs, branches and ties, all in Geometry Nodes. A one-shot 8-second event, not a loop. Rendered in EEVEE. | [files](2026/day07-tree-v6-supertree) · [video](2026/day07-tree-v6-supertree/awakening.mp4) · [**node-by-node tutorial**](2026/day07-tree-v6-supertree/tutorial/README.md) |
| 08 | Mycelium | **Fingertip.** A weathered stone hand stands in fern moss on a forest floor and points one finger at the sky, with a low sun behind it. White hyphae leave the soil and climb the stone, cords gather up the raised finger, a hyphal knot swells on its tip, and a bonnet mushroom grows there, opens and sheds spores into the light. The hand is a skeleton of bones melted into stone by a signed distance field, and the mycelium is shortest paths over its mesh. A one-shot 15-second growth, not a loop. Rendered in Cycles. | [files](2026/day08-mycelium-v5-fingertip) · [video](2026/day08-mycelium-v5-fingertip/loop.mp4) · [**node-by-node tutorial**](2026/day08-mycelium-v5-fingertip/tutorial/README.md) |
| 09 | Winged | **Solo.** One silver maple key spins down through low sun, and the camera falls with it; the dark wood far below is only green and gold bokeh. The key is one closed surface, a sphere laid out over a single (s, v) field: the ribbed nut, the papery wing and its raised veins all come from that field, so the raking sun draws real shadow lines along the veins. It autorotates with a real key's numbers (an 18° cone, the spin axis through the centre of mass, about 6 cm of fall per turn), here about 30 times slower. Mid-loop a gust tips the spin over, and the key rights itself. A 12-second seamless loop, rendered in Cycles, plus a white clay video of its nine modifier sliders. | [files](2026/day09-winged-v5-solo) · [loop](2026/day09-winged-v5-solo/loop.mp4) · [sliders](2026/day09-winged-v5-solo/sliders/sliders.mp4) · [**node-by-node tutorial**](2026/day09-winged-v5-solo/tutorial/README.md) |
| 10 | Geode | **Geode generator.** A sawn geode on a black studio floor, and the one Geometry Nodes group that grows it. The whole stone is one implicit field on a voxel grid: its depth into the wall paints the agate bands on the polished face, and 10 242 fixed rays cast from the centre stand the crystals on the cavity wall, so when a slider moves every crystal glides instead of jumping. The 27-second video moves seven sliders one at a time (shape, wall thickness, bands, crystal size, tip, blade, colour zoning), then morphs through six classic kinds: amethyst, citrine, celestine, dogtooth calcite, druzy quartz and a solid agate. Rendered in Cycles, with a clean version and one with the slider readout. | [files](2026/day10-geode-v2-generator) · [video](2026/day10-geode-v2-generator/sweep/loop.mp4) · [with readout](2026/day10-geode-v2-generator/sweep/sweep.mp4) · [**node-by-node tutorial**](2026/day10-geode-v2-generator/tutorial/README.md) |
| 11 | Cavernous | **Flooded geode canal.** A small boat with a lantern drifts down a chain of giant flooded geodes: an amethyst hall, a hall of water-clear quartz with milky roots, a citrine dome, and on into pale blue celestine. Every hall is the Day 10 geode generator's own field and crystal groups, scaled 150 times. A chamber is a function of its number alone, and every point asks only the two nearest chambers, so the chain could run on for ever at the same cost per point. In the passages between the halls the crystals change kind one by one, with odds that slide across the bore, and the boat's Kelvin wake breaks the reflections behind it. The lantern is the only light. A 34-second video, rendered in Cycles. | [files](2026/day11-cavernous-v8-canal) · [video](2026/day11-cavernous-v8-canal/loop.mp4) · [**node-by-node tutorial**](2026/day11-cavernous-v8-canal/tutorial/README.md) |

<p>
  <img src="2026/day01-origami/_still_086.png" width="49%" alt="The washi sheet folded into a dart on a stack of paper">
  <img src="2026/day01-origami/_still_160.png" width="49%" alt="The paper plane standing on its keel, lifting off the stack">
</p>

<p>
  <img src="2026/day02-furniture-v3-corner/_still_076.png" width="49%" alt="A reading corner at noon: sun through an unseen window falls across a cream bouclé barrel chair, a walnut side table with a travertine lamp, and a vase of pampas grass">
  <img src="2026/day02-furniture-v3-corner/_still_211.png" width="49%" alt="The same corner at night: the pleated linen lamp is on and warms the room, and moonlight draws the window faintly on the wall">
</p>

<p>
  <img src="2026/day03-stitch-v3-kintsugi/_still_001.png" width="49%" alt="A cream tea bowl with fine crazing, its cracks mended with flat gold lines">
  <img src="2026/day03-stitch-v3-kintsugi/_still_128.png" width="49%" alt="The same bowl with every shard back in place, the seams still black urushi lacquer before the gold">
</p>

<p>
  <img src="2026/day04-brass-v2-chladni/render.png" width="49%" alt="A square brass plate on a thin shaft in a black void, white sand drawn into a rounded square around a ring at the centre bolt">
  <img src="2026/day04-brass-v2-chladni/_still_220.png" width="49%" alt="The same plate on the highest tone: the sand has settled into dense nested loops like lace">
</p>

<p>
  <img src="2026/day05-clockwork-v3-musicbox/_still_090.png" width="49%" alt="A brass music box with a pierced band of green and amber enamel under a tall glass cloche; on its grass stage a small twisted tree is a cloud of pink blossom">
  <img src="2026/day05-clockwork-v3-musicbox/_still_240.png" width="49%" alt="The same music box in autumn: the tree has turned orange and red apples lie fallen on the grass">
</p>

<p>
  <img src="2026/day06-vault-v5-rouen/render.png" width="49%" alt="Looking up the nave of Rouen Cathedral: grey four-storey walls lit by patches of low sun climb into an ochre rib vault with a rosette boss in every bay, and the rose window far ahead">
  <img src="2026/day06-vault-v5-rouen/masonry_detail_square.png" width="49%" alt="Close-up of the upper vault: ochre stones laid in courses in each cell end cleanly on the moulded diagonal ribs at a carved rosette boss">
</p>

<p>
  <img src="2026/day07-tree-v6-supertree/_still_001.png" width="49%" alt="Blue hour in a garden of tall steel trees before the lights: dark violet crowns, planted trunks lit green from below, a skyway between the two nearest trees">
  <img src="2026/day07-tree-v6-supertree/render_1080.png" width="49%" alt="The same garden awake: every crown glows violet-white through black radial ribs, the skyway glows pink and gold, and wet paths reflect the light">
</p>

<p>
  <img src="2026/day08-mycelium-v5-fingertip/render-wide.png" width="49%" alt="A stone hand in fern moss points one finger at the sky, its stone laced with white mycelium; a small pale mushroom stands on the fingertip, its cap glowing in the backlight against a dark forest">
  <img src="2026/day08-mycelium-v5-fingertip/render.png" width="49%" alt="Close-up of the pale bonnet mushroom on its thin pink stem, the gills lit from behind by a low golden sun and spores drifting through the light, above the fingertip wrapped in white threads">
</p>

<p>
  <img src="2026/day09-winged-v5-solo/render.png" width="49%" alt="A pale silver maple key, a ribbed brown nut flowing into one papery wing, tipped over by a gust against a near-black background; low sun from the right rakes across its raised veins, and green and gold bokeh drifts behind it">
  <img src="2026/day09-winged-v5-solo/_still_173.png" width="49%" alt="The same key half a second later, its wing turned broadside with the veins fanning from the nut, as specks of dust float past">
</p>

<p>
  <img src="2026/day10-geode-v2-generator/render.png" width="49%" alt="Two halves of a sawn amethyst geode on a black studio floor: a rough reddish rind, lavender and blue-grey agate bands, white quartz, and a hollow lined with glassy purple points that catch small white highlights">
  <img src="2026/day10-geode-v2-generator/_still_494.png" width="49%" alt="The same generator set to celestine: a pale white rind and a hollow packed with pale blue, flat bladed crystals with chisel ends, on black">
</p>

<p>
  <img src="2026/day11-cavernous-v8-canal/render.png" width="49%" alt="A small boat with a hooded figure and a hanging lantern on black water inside a giant amethyst geode; purple points line the walls, and ahead a passage lined with clear quartz opens into the next hall">
  <img src="2026/day11-cavernous-v8-canal/render-600.png" width="49%" alt="The boat in an orange citrine dome, the passage ahead ringed in pale blue celestine, and its V-shaped wake breaking the reflections of the crystals into slanted strips">
</p>

## What is in a day folder

Days 1–8 hold all of these. From Day 9 on, a folder holds `tutorial/`, the renders, the node screenshots and `post.md`.

| File | |
|---|---|
| `build.py` | builds the whole scene: node trees, materials, lights, camera, render settings |
| `*.blend` | the result of `build.py`; open it to explore the node trees |
| `loop.mp4` | the render, 1080 × 1080 (`loop_sound.mp4` adds the sound, where there is one) |
| `_still_*.png` | full-quality stills |
| `nodes*.png`, `nodes/` | node-tree screenshots |
| `nodes_layout.json` | node positions and frames, tidied by hand; `build.py` restores them |
| `post.md` | idea, build log, captions and alt text |
| `tutorial/` | a walkthrough of the node tree, where there is one |
| `sliders/` | a second video: the piece's modifier sliders moved one by one, where there is one |
| `color/`, `eevee/`, `clay/` | a render copy and its loop per engine, where a piece was rendered more than one way |

## Rebuild a piece

Days 1–8 can be rebuilt. You need Blender 5.2 and, for the video, ffmpeg.

```sh
cd 2026/day01-origami
blender -b --factory-startup --python build.py     # writes origami.blend
../../lib/render_frames.sh origami.blend 30         # PNG frames → loop.mp4
```

`lib/proc_blender.py` is a small helper library that every build script uses. It is a builder for node graphs, plus
layout, a seamless loop clock, a studio setup and render helpers. `lib/render_frames.sh` renders a frame sequence and
retries if Blender crashes, then encodes the MP4.

## License

All rights reserved. This is a private project, shared for learning and study only. You may view, download and run
the pieces to learn how they are made, but not redistribute them, use them commercially, present them as your own or
use them to train models. See [LICENSE](LICENSE).
