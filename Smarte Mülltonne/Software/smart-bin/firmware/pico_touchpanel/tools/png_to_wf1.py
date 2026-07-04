"""PNG -> WF1 (Touchpanel-RLE) Encoder + Decoder.

WF1: b'WF1' | w(2B BE) | h(2B BE) | palette_len(1B) | palette(palette_len * 2B RGB565)
     | pro Zeile: row_len(2B BE) + row_len Bytes als (run 1B, palette_index 1B)-Paare.
run 1..255; sum(runs) je Zeile == w; palette <= 256 Farben (RGB565).

Muss exakt zum Decoder in smart-bin/firmware/pico_touchpanel/wireframe.py passen.
"""
from PIL import Image


def _rgb_to_565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def _565_to_rgb(c):
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return (r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)


def encode_png_to_wf1(png_path, rle_path):
    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    px = img.load()

    cells = [[_rgb_to_565(*px[x, y]) for x in range(w)] for y in range(h)]
    uniq = sorted({c for row in cells for c in row})
    if len(uniq) > 256:
        q = img.convert("P", palette=Image.ADAPTIVE, colors=256).convert("RGB")
        qpx = q.load()
        cells = [[_rgb_to_565(*qpx[x, y]) for x in range(w)] for y in range(h)]
        uniq = sorted({c for row in cells for c in row})
    index_of = {c: i for i, c in enumerate(uniq)}

    out = bytearray(b"WF1")
    out += w.to_bytes(2, "big") + h.to_bytes(2, "big")
    out += bytes([len(uniq)])
    for c in uniq:
        out += c.to_bytes(2, "big")

    for y in range(h):
        row = bytearray()
        x = 0
        while x < w:
            c = cells[y][x]
            run = 1
            while x + run < w and cells[y][x + run] == c and run < 255:
                run += 1
            row += bytes([run, index_of[c]])
            x += run
        out += len(row).to_bytes(2, "big") + row

    with open(rle_path, "wb") as f:
        f.write(out)


def decode_wf1(rle_path):
    with open(rle_path, "rb") as f:
        assert f.read(3) == b"WF1"
        w = int.from_bytes(f.read(2), "big")
        h = int.from_bytes(f.read(2), "big")
        n = f.read(1)[0]
        pal = [_565_to_rgb(int.from_bytes(f.read(2), "big")) for _ in range(n)]
        rows = []
        for _ in range(h):
            row_len = int.from_bytes(f.read(2), "big")
            data = f.read(row_len)
            row = []
            for i in range(0, row_len, 2):
                row += [pal[data[i + 1]]] * data[i]
            rows.append(row)
    return w, h, rows
