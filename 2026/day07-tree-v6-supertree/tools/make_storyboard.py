"""Contact sheet from the actual rendered sequence; requires Pillow.

uv run --with pillow python tools/make_storyboard.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parents[1]  # the piece folder
CHECKPOINTS = (1, 25, 49, 73, 97, 121, 145, 168, 192)
SIZE, GAP, LABEL = 408, 14, 34
out = Image.new('RGB', (SIZE*3+GAP*4, (SIZE+LABEL)*3+GAP*4), (12,18,30))
draw = ImageDraw.Draw(out)
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 19)
review = HERE/'review'
review.mkdir(exist_ok=True)
for j, frame in enumerate(CHECKPOINTS):
    source = HERE/'frames'/f'{frame:04}.png'
    with Image.open(source) as im:
        im = im.convert('RGB')
        im.resize((624,624), Image.Resampling.LANCZOS).save(review/f'{frame:04}.png')
        tile = im.resize((SIZE,SIZE), Image.Resampling.LANCZOS)
    x = GAP+(j%3)*(SIZE+GAP)
    y = GAP+(j//3)*(SIZE+LABEL+GAP)
    out.paste(tile, (x,y))
    draw.text((x+9,y+SIZE+7), f'{(frame-1)/24:.2f} s', font=font, fill=(213,219,231))
out.save(HERE/'storyboard.jpg', quality=94)
print('STORYBOARD_OK', HERE/'storyboard.jpg')
