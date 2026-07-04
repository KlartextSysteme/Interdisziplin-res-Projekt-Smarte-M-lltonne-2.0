import os
import tempfile

from PIL import Image

from png_to_wf1 import encode_png_to_wf1, decode_wf1, _rgb_to_565, _565_to_rgb


def test_roundtrip_matches_source_in_565():
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "src.png")
    rle = os.path.join(tmp, "out.rle")
    img = Image.new("RGB", (12, 5), (30, 30, 34))
    for x in range(12):
        img.putpixel((x, 2), (242, 201, 76))   # gelbe Linie
    img.putpixel((0, 0), (248, 250, 252))       # ein heller Pixel
    img.save(src)

    encode_png_to_wf1(src, rle)
    w, h, rows = decode_wf1(rle)
    assert (w, h) == (12, 5)

    spx = img.load()
    for y in range(h):
        for x in range(w):
            assert rows[y][x] == _565_to_rgb(_rgb_to_565(*spx[x, y]))


def test_decoder_reads_existing_confirm_generic():
    # Beweist, dass unser Decoder das echte Asset-Format liest (320x240).
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "confirm_generic.rle")
    w, h, rows = decode_wf1(path)
    assert (w, h) == (320, 240)
    assert len(rows) == 240 and len(rows[0]) == 320
