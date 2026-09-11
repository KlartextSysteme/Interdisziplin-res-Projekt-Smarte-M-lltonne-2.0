ASSET_DIR = "/assets"


class WireframeRenderer:
    def __init__(self, display):
        self.d = display
        self._line = bytearray(self.d.width * 2)

    def draw(self, name):
        self.draw_at(name, 0, 0)

    def draw_at(self, name, x0, y0):
        self._draw(name, x0, y0, None)

    def draw_at_keyed(self, name, x0, y0, transparent_color):
        self._draw(name, x0, y0, transparent_color)

    def _draw(self, name, x0, y0, transparent_color):
        path = ASSET_DIR + "/" + name + ".rle"
        with open(path, "rb") as f:
            if f.read(3) != b"WF1":
                raise ValueError("bad wireframe asset: " + path)

            w = int.from_bytes(f.read(2), "big")
            h = int.from_bytes(f.read(2), "big")
            palette_len = f.read(1)[0]
            palette = []
            for _ in range(palette_len):
                color = int.from_bytes(f.read(2), "big")
                palette.append((color >> 8, color & 255))

            needed = w * 2
            if len(self._line) < needed:
                self._line = bytearray(needed)

            if transparent_color is None:
                self.d.set_window(x0, y0, x0 + w - 1, y0 + h - 1)
                self.d.cs.off()
                self.d.dc.on()

            transparent = None
            if transparent_color is not None:
                transparent = (transparent_color >> 8, transparent_color & 255)

            for y in range(h):
                row_len = int.from_bytes(f.read(2), "big")
                row = f.read(row_len)
                x = 0
                for i in range(0, row_len, 2):
                    run = row[i]
                    hi, lo = palette[row[i + 1]]
                    if transparent is not None:
                        if (hi, lo) != transparent:
                            self._write_run(x0 + x, y0 + y, run, hi, lo)
                        x += run
                    else:
                        stop = x + run
                        while x < stop:
                            off = x * 2
                            self._line[off] = hi
                            self._line[off + 1] = lo
                            x += 1
                if transparent is None:
                    self.d.spi.write(self._line[:needed])

            if transparent_color is None:
                self.d.cs.on()

    def _write_run(self, x, y, run, hi, lo):
        needed = run * 2
        if len(self._line) < needed:
            self._line = bytearray(needed)
        for i in range(run):
            off = i * 2
            self._line[off] = hi
            self._line[off + 1] = lo

        self.d.set_window(x, y, x + run - 1, y)
        self.d.cs.off()
        self.d.dc.on()
        self.d.spi.write(self._line[:needed])
        self.d.cs.on()
