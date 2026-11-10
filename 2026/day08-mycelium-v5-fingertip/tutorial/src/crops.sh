#!/bin/bash
# Inputs for tutorial/figs.json: crops of the final frames and of the concept renders.
#   tutorial/src/crops.sh RENDER_DIR [FIRST_FRAMES FRONT_FRAMES [UNSEATED_FRAMES]]   (RENDER_DIR holds the output of hand_stages.py,
#   cost_fields.py, sun_link.py (run on the first render's .blend); FIRST_FRAMES the frames of the first render, sun from the left and a little behind,
#   SUN_DIR (0.86, -0.22, -0.46); FRONT_FRAMES those of the second, sun from the left-front, (0.86, 0.22, -0.40);
#   UNSEATED_FRAMES the backlit frames from before the stem was seated on the stone)
# Run from the piece folder. Writes tutorial/images/_*.jpg.
set -euo pipefail
R=${1:?render dir}
I=tutorial/images
HAND="crop=540:720:350:200"           # the hand in the opening camera (1080² frame)
jpg() { ffmpeg -v error -y -i "$1" -vf "$2" -q:v 3 "$3"; }

for f in 0001 0049 0097 0133 0165 0205 0245 0360; do          # storyboard
  jpg frames/$f.png "scale=540:540" $I/_f$f.jpg
done
for f in 0020 0050 0075 0099; do                                # colony at a fixed camera (it starts to move at frame 100)
  jpg frames/$f.png "$HAND" $I/_myc_$f.jpg
done
for s in 1_spheres 2_raw_sdf 3_smoothed 4_weathered; do
  jpg $R/_hand_$s.png "$HAND" $I/_hand_$s.jpg
done
jpg frames/0001.png "$HAND" $I/_hand_5_final.jpg
jpg $R/_field_d.png "$HAND" $I/_field_d.jpg
jpg $R/_field_dt.png "$HAND" $I/_field_dt.jpg
jpg $R/_sun_skips.png "crop=540:250:0:0" $I/_sun_skips.jpg     # the top of a half-size frame 1: the far trunks
jpg $R/_sun_hits.png "crop=540:250:0:0" $I/_sun_hits.jpg
jpg frames/0360.png "crop=600:400:240:680" $I/stem-foot.jpg   # the last frame: fibrils over the fingertip, curled fuzz
FIST="crop=600:760:280:220"           # the fist at frame 133 (the camera has started to move in)
jpg frames/0133.png "$FIST" $I/_sun_back.jpg
SEAT="crop=500:330:290:750"           # the stem's foot in the last frame
jpg frames/0360.png "$SEAT" $I/_seat_after.jpg
if [ -n "${4:-}" ]; then              # optional: frames rendered before the stem was seated on the stone
  jpg "$4/0360.png" "$SEAT" $I/_seat_before.jpg
fi
if [ -n "${3:-}" ]; then              # optional: the two earlier renders, for the sun-direction figure
  jpg "$2/0133.png" "$FIST" $I/_sun_side.jpg
  jpg "$3/0133.png" "$FIST" $I/_sun_front.jpg
fi
echo CROPS_OK
