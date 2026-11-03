#!/bin/zsh
# Crash-tolerant loop render: PNG sequence → H.264 MP4.
#   render_frames.sh <file.blend> [fps=30] [crf=16]
# Writes <blend dir>/frames/####.png and <blend dir>/loop.mp4.
# - Cycles Metal kernel specialisation is turned off: its background compile thread crashed
#   Blender 5.2.3 mid-render (MetalKernelPipeline::compile → MTLBinaryArchive serialize).
# - Frames already on disk are skipped, so a crash costs one frame: placeholders left by the
#   crash (0-byte files) are deleted and Blender is re-run, up to 3 times.
set -u
B=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
blend=${1:?usage: render_frames.sh file.blend [fps] [crf]}
fps=${2:-30}
crf=${3:-16}
dir=$(cd "$(dirname "$blend")" && pwd)
mkdir -p "$dir/frames"
setup="import bpy
bpy.context.preferences.addons['cycles'].preferences.kernel_optimization_level = 'OFF'
sc = bpy.context.scene
im = sc.render.image_settings
im.media_type = 'IMAGE'; im.file_format = 'PNG'
sc.render.filepath = '//frames/'
sc.render.use_overwrite = False
sc.render.use_placeholder = True
print('FRAMES_EXPECTED', sc.frame_end - sc.frame_start + 1)"
for attempt in 1 2 3; do
  find "$dir/frames" -name '*.png' -size 0 -delete
  out=$("$B" -b "$blend" --python-expr "$setup" -a 2>&1)
  want=$(print -r -- "$out" | sed -n 's/^FRAMES_EXPECTED //p' | head -1)
  find "$dir/frames" -name '*.png' -size 0 -delete
  have=$(find "$dir/frames" -name '*.png' | wc -l | tr -d ' ')
  echo "attempt $attempt: $have/${want:-?} frames"
  [[ -n "$want" && "$have" -ge "$want" ]] && break
done
first=$(ls "$dir/frames" | head -1)
start=${first%.png}
ffmpeg -y -loglevel error -framerate "$fps" -start_number "$((10#$start))" -i "$dir/frames/%04d.png" \
  -c:v libx264 -pix_fmt yuv420p -crf "$crf" -movflags +faststart "$dir/loop.mp4" && echo "MP4 $dir/loop.mp4"
