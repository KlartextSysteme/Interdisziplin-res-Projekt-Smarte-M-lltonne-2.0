"""Rendert confirm_report.png ("Meldung gesendet") im Stil von confirm_generic.

Werte aus confirm_generic.rle abgeleitet:
BG (66,65,66), Gelb (255,199,33), Text weiss, dunkles Haekchen im gelben Quadrat.
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 320, 240
BG = (66, 65, 66)
YELLOW = (255, 199, 33)
WHITE = (255, 255, 255)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# Gelbes abgerundetes Quadrat, zentriert (wie Referenz: ~96px, oben mittig)
sq = 96
sx = (W - sq) // 2
sy = 44
d.rounded_rectangle([sx, sy, sx + sq, sy + sq], radius=20, fill=YELLOW)

# Dunkles Haekchen (BG-Farbe) im Quadrat
d.line(
    [(sx + 26, sy + 50), (sx + 42, sy + 66), (sx + 72, sy + 32)],
    fill=BG, width=11, joint="curve",
)

# Text "Meldung gesendet", weiss, fett, zentriert darunter
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
]
text = "Meldung gesendet"


def _load_font(size):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


size = 30
font = _load_font(size)
while d.textlength(text, font=font) > W - 40 and size > 12:
    size -= 1
    font = _load_font(size)

tw = d.textlength(text, font=font)
d.text(((W - tw) // 2, 170), text, fill=WHITE, font=font)

img.save("confirm_report.png")
print("OK size", size)
