#!/bin/zsh
# Crash-tolerant loop render: PNG sequence → H.264 MP4.
#   render_frames.sh <file.blend> [fps=30] [crf=16]
# Writes <blend dir>/frames/####.png and <blend dir>/loop.mp4.
# - Cycles Metal kernel specialisation is turned off: its background compile thread crashed
#   Blender 5.2.3 mid-render (MetalKernelPipeline::compile → MTLBinaryArchive serialize).
# - Frames already on disk are skipped, so a crash costs one frame: placeholders left by the
#   crash (0-byte files) are deleted and Blender is re-run, up to 3 times.
# - The GPU is picked here (METAL → OPTIX → CUDA → HIP → ONEAPI, else CPU), not left to the
#   user preferences, which reset or --factory-startup would silently drop back to CPU.
set -u
B=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
blend=${1:?usage: render_frames.sh file.blend [fps] [crf]}
fps=${2:-30}
crf=${3:-16}
dir=$(cd "$(dirname "$blend")" && pwd)
mkdir -p "$dir/frames"
setup="import bpy
p = bpy.context.preferences.addons['cycles'].preferences
p.kernel_optimization_level = 'OFF'
sc = bpy.context.scene
dev = 'CPU'
if sc.render.engine == 'CYCLES':
    for t in ('METAL', 'OPTIX', 'CUDA', 'HIP', 'ONEAPI'):
        try:
            p.compute_device_type = t
            p.get_devices()
        except TypeError:
            continue
        if any(d.type == t for d in p.devices):
            for d in p.devices:
                d.use = True
            sc.cycles.device = 'GPU'
            dev = t
            break
    else:
        sc.cycles.device = 'CPU'
print('RENDER_DEVICE', sc.render.engine, dev)
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
  device=$(print -r -- "$out" | sed -n 's/^RENDER_DEVICE //p' | head -1)
  echo "attempt $attempt: $have/${want:-?} frames (device: ${device:-?})"
  [[ -n "$want" && "$have" -ge "$want" ]] && break
done
first=$(ls "$dir/frames" | head -1)
start=${first%.png}
ffmpeg -y -loglevel error -framerate "$fps" -start_number "$((10#$start))" -i "$dir/frames/%04d.png" \
  -c:v libx264 -pix_fmt yuv420p -crf "$crf" -movflags +faststart "$dir/loop.mp4" && echo "MP4 $dir/loop.mp4"
