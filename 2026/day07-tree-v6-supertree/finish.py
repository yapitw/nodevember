"""Encode and validate the completed 192-frame awakening. Standard Python only."""
import json
import re
import shutil
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FFMPEG = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'
FFPROBE = shutil.which('ffprobe') or '/opt/homebrew/bin/ffprobe'
EXPECTED = 192


def run(args):
    return subprocess.run(args, cwd=HERE, check=True, capture_output=True, text=True)


for f in range(1, EXPECTED+1):
    path = HERE/'frames'/f'{f:04}.png'
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f'Missing or unfinished frame: {f}')
    with path.open('rb') as handle:
        header = handle.read(24)
    if header[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', header[16:24]) != (960, 960):
        raise RuntimeError(f'Unexpected PNG header: {f}')

run([FFMPEG, '-y', '-v', 'error', '-xerror', '-framerate', '24', '-start_number', '1', '-i', 'frames/%04d.png',
     '-frames:v', str(EXPECTED), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17',
     '-movflags', '+faststart', 'awakening.mp4'])
probe = json.loads(run([FFPROBE, '-v', 'error', '-count_frames', '-select_streams', 'v:0',
    '-show_entries', 'stream=codec_name,width,height,nb_read_frames,r_frame_rate,duration',
    '-of', 'json', 'awakening.mp4']).stdout)['streams'][0]
assert int(probe['nb_read_frames']) == EXPECTED, probe
assert (probe['width'], probe['height']) == (960, 960), probe
assert abs(float(probe['duration'])-8.) < .01, probe

# Full decode, including a record of frame-to-frame luminance for flash inspection.
run([FFMPEG, '-v', 'error', '-xerror', '-i', 'awakening.mp4', '-vf',
     'signalstats,metadata=print:file=checks/video-signalstats.txt', '-f', 'null', '-'])
stats = (HERE/'checks'/'video-signalstats.txt').read_text()
means = [float(x) for x in re.findall(r'lavfi\.signalstats\.YAVG=([0-9.]+)', stats)]
assert len(means) == EXPECTED, len(means)

run([FFMPEG, '-y', '-v', 'error', '-i', 'awakening.mp4', '-vf',
     'fps=12,scale=480:480:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a',
     '-loop', '0', 'awakening.gif'])

report = {'passed': True, 'video': probe, 'sequence_frames': EXPECTED, 'full_decode_passed': True,
          'luminance': {'first': means[0], 'last': means[-1],
                        'max_adjacent_change': max(abs(b-a) for a, b in zip(means, means[1:]))},
          'bytes': {name: (HERE/name).stat().st_size for name in ('awakening.mp4', 'awakening.gif', 'render.png', 'piece.blend')}}
(HERE/'checks'/'video-verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
