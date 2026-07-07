"""Rendert Ziffern/Symbole fuer die dynamischen Diagnose-Werte (Fuellstand %, Hindernis cm)
im selben Look wie das diagnose_ok-Mockup: weiss, fett, Panel-Grau-Hintergrund.

Erzeugt je Zeichen ein WF1-Asset dv_<key>.rle (opak blitbar, BG == Panel-Grau)
und druckt die Breiten-Tabelle fuer ui.py.

Aufruf:  python3 render_diag_digits.py
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.abspath(os.path.join(HERE, "..", "assets"))
sys.path.insert(0, HERE)
from png_to_wf1 import encode_png_to_wf1  # noqa: E402

PANEL_BG = (66, 65, 66)      # gemessen aus diagnose_ok.rle
VALUE_FG = (255, 255, 255)   # Werte sind weiss
FONT_SIZE = 14               # -> Cap-Height ~9px (matcht Mockup)
PAD_X = 1                    # 1px Luft je Seite pro Glyph

# key -> darzustellendes Zeichen
CHARS = {
    "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
    "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
    "pct": "%", "dash": "-", "c": "C", "m": "M", "sp": " ",
}

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
]


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main():
    font = load_font(FONT_SIZE)
    probe = Image.new("RGB", (60, 40), PANEL_BG)
    pd = ImageDraw.Draw(probe)

    # Gemeinsame vertikale Zelle aus "0123456789%" (volle Ziffernhoehe).
    tops, bots = [], []
    for ch in "0123456789%":
        bb = pd.textbbox((0, 0), ch, font=font)
        tops.append(bb[1]); bots.append(bb[3])
    cell_top = min(tops)
    cell_h = max(bots) - cell_top

    widths = {}
    for key, ch in CHARS.items():
        bb = pd.textbbox((0, 0), ch, font=font)
        glyph_w = max(1, bb[2] - bb[0])
        w = glyph_w + 2 * PAD_X
        img = Image.new("RGB", (w, cell_h), PANEL_BG)
        d = ImageDraw.Draw(img)
        # so zeichnen, dass Glyph-Left bei PAD_X und Zellen-Top passt
        d.text((PAD_X - bb[0], -cell_top), ch, fill=VALUE_FG, font=font)
        png = os.path.join(ASSETS, "dv_%s.png" % key)
        rle = os.path.join(ASSETS, "dv_%s.rle" % key)
        img.save(png)
        encode_png_to_wf1(png, rle)
        os.remove(png)
        widths[ch] = w

    print("cell_h =", cell_h)
    print("# fuer ui.py DIAG_GLYPH_W (Zeichen -> Breite px):")
    print("DIAG_GLYPH_W =", widths)


if __name__ == "__main__":
    main()
