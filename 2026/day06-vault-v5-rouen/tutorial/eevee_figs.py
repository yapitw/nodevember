"""Figure for the EEVEE chapter of the tutorial.

    uv run --with pillow python tutorial/eevee_figs.py

Run from the piece folder after eevee/crossfade.py. Writes
  images/cycles-vs-eevee.jpg   Cycles frame 1 beside the EEVEE loop's frame 1
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PIECE = os.path.dirname(HERE)
EEVEE = os.path.join(PIECE, "eevee")
OUT = os.path.join(HERE, "images")


def side_by_side():
    a = Image.open(os.path.join(PIECE, "color", "frames", "0001.png")).convert("RGB")
    b = Image.open(os.path.join(EEVEE, "frames_loop", "0001.png")).convert("RGB")
    c = Image.new("RGB", (2 * a.width + 12, a.height), "white")
    c.paste(a, (0, 0))
    c.paste(b, (a.width + 12, 0))
    d = ImageDraw.Draw(c)
    font = ImageFont.load_default(size=40)
    for x, text in ((30, "Cycles · 256 samples · 53 s a frame"), (a.width + 42, "EEVEE · 128 samples · 23-27 s a frame")):
        box = d.textbbox((x, 30), text, font=font)
        d.rectangle((box[0] - 14, box[1] - 10, box[2] + 14, box[3] + 10), fill=(0, 0, 0))
        d.text((x, 30), text, fill=(255, 255, 255), font=font)
    c.resize((c.width // 2, c.height // 2), Image.LANCZOS).save(os.path.join(OUT, "cycles-vs-eevee.jpg"), quality=90)


if __name__ == "__main__":
    side_by_side()
