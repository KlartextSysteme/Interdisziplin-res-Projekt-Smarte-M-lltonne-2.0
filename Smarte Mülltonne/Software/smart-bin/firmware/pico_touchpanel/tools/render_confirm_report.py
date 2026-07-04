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

# Gelbes abgerundetes Quadrat, zentriert (Referenz: 87x88 bei y=50)
sq = 87
sx = (W - sq) // 2
sy = 50
d.rounded_rectangle([sx, sy, sx + sq, sy + sq], radius=18, fill=YELLOW)

# Dunkles Haekchen (BG-Farbe) im Quadrat, proportional zum 87er-Quadrat.
# joint="curve" rundet die Ecke; zusaetzlich runde Endkappen (Kreise) an den
# beiden Haken-Enden, damit es zu den anderen Icons passt (keine flachen Enden).
CHK = [(sx + 22, sy + 46), (sx + 37, sy + 61), (sx + 65, sy + 28)]
CW = 8
d.line(CHK, fill=BG, width=CW, joint="curve")
_r = CW / 2
for (cx, cy) in (CHK[0], CHK[-1]):
    d.ellipse([cx - _r, cy - _r, cx + _r, cy + _r], fill=BG)

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


def _text_h(f):
    bb = d.textbbox((0, 0), text, font=f)
    return bb[3] - bb[1]


TARGET_H = 17            # Texthoehe wie Referenz "Auswahl bestaetigt"
TEXT_CENTER_Y = 178      # vertikale Text-Mitte wie Referenz
size = 24
font = _load_font(size)
while _text_h(font) > TARGET_H and size > 8:
    size -= 1
    font = _load_font(size)

bb = d.textbbox((0, 0), text, font=font)
tw, th = bb[2] - bb[0], bb[3] - bb[1]
tx = (W - tw) // 2 - bb[0]
ty = TEXT_CENTER_Y - th // 2 - bb[1]
d.text((tx, ty), text, fill=WHITE, font=font)

img.save("confirm_report.png")
print("OK size", size, "text_h", th)
