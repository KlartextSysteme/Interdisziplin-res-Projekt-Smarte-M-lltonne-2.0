from machine import Pin, SPI
from time import sleep_ms

from config import (
    DISPLAY_ROTATION,
    HEIGHT,
    PIN_DISPLAY_CS,
    PIN_DISPLAY_DC,
    PIN_DISPLAY_RST,
    PIN_MISO,
    PIN_MOSI,
    PIN_SCK,
    SPI_BAUDRATE,
    SPI_ID,
    WIDTH,
)


def color565(r, g, b):
    return ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)


BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)
GRAY = color565(170, 170, 170)
DARK = color565(35, 35, 35)
BG_TOP = color565(57, 57, 57)
BG_BOTTOM = color565(107, 107, 107)
PANEL = color565(96, 96, 96)
PANEL_DARK = color565(70, 70, 70)
YELLOW = color565(248, 196, 35)
GREEN = color565(46, 125, 50)
ORANGE = color565(230, 126, 0)
RED = color565(198, 40, 40)
BLUE = color565(0, 120, 255)


FONT = {
    " ": (0, 0, 0, 0, 0),
    "%": (17, 2, 4, 8, 17),
    "/": (1, 2, 4, 8, 16),
    "-": (0, 0, 14, 0, 0),
    ":": (0, 4, 0, 0, 4),
    "*": (0, 21, 14, 21, 0),
    "#": (10, 31, 10, 31, 10),
    ".": (0, 0, 0, 0, 4),
    "0": (14, 17, 19, 21, 14),
    "1": (4, 12, 4, 4, 14),
    "2": (14, 17, 2, 4, 31),
    "3": (30, 1, 14, 1, 30),
    "4": (18, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 30),
    "6": (14, 16, 30, 17, 14),
    "7": (31, 1, 2, 4, 8),
    "8": (14, 17, 14, 17, 14),
    "9": (14, 17, 15, 1, 14),
    "A": (14, 17, 31, 17, 17),
    "B": (30, 17, 30, 17, 30),
    "C": (15, 16, 16, 16, 15),
    "D": (30, 17, 17, 17, 30),
    "E": (31, 16, 30, 16, 31),
    "F": (31, 16, 30, 16, 16),
    "G": (15, 16, 19, 17, 15),
    "H": (17, 17, 31, 17, 17),
    "I": (14, 4, 4, 4, 14),
    "J": (7, 2, 2, 18, 12),
    "K": (17, 18, 28, 18, 17),
    "L": (16, 16, 16, 16, 31),
    "M": (17, 27, 21, 17, 17),
    "N": (17, 25, 21, 19, 17),
    "O": (14, 17, 17, 17, 14),
    "P": (30, 17, 30, 16, 16),
    "R": (30, 17, 30, 18, 17),
    "S": (15, 16, 14, 1, 30),
    "T": (31, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 14),
    "V": (17, 17, 17, 10, 4),
    "W": (17, 17, 21, 27, 17),
    "X": (17, 10, 4, 10, 17),
    "Y": (17, 10, 4, 4, 4),
    "Z": (31, 2, 4, 8, 31),
}


class ILI9341:
    def __init__(self):
        self.spi = SPI(
            SPI_ID,
            baudrate=SPI_BAUDRATE,
            polarity=0,
            phase=0,
            sck=Pin(PIN_SCK),
            mosi=Pin(PIN_MOSI),
            miso=Pin(PIN_MISO),
        )
        self.cs = Pin(PIN_DISPLAY_CS, Pin.OUT, value=1)
        self.dc = Pin(PIN_DISPLAY_DC, Pin.OUT, value=1)
        self.rst = Pin(PIN_DISPLAY_RST, Pin.OUT, value=1)
        self.width = WIDTH
        self.height = HEIGHT

    def cmd(self, value):
        self.cs.off()
        self.dc.off()
        self.spi.write(bytearray([value]))
        self.cs.on()

    def data(self, values):
        self.cs.off()
        self.dc.on()
        self.spi.write(bytearray(values))
        self.cs.on()

    def reset(self):
        self.rst.on()
        sleep_ms(50)
        self.rst.off()
        sleep_ms(100)
        self.rst.on()
        sleep_ms(150)

    def init(self):
        self.reset()
        self.cmd(0x01)
        sleep_ms(120)
        self.cmd(0x11)
        sleep_ms(120)
        self.cmd(0x3A)
        self.data([0x55])
        self.cmd(0x36)
        self.data([DISPLAY_ROTATION])
        self.cmd(0x29)
        sleep_ms(50)

    def set_window(self, x0, y0, x1, y1):
        self.cmd(0x2A)
        self.data([x0 >> 8, x0 & 255, x1 >> 8, x1 & 255])
        self.cmd(0x2B)
        self.data([y0 >> 8, y0 & 255, y1 >> 8, y1 & 255])
        self.cmd(0x2C)

    def fill_rect(self, x, y, w, h, color):
        if w <= 0 or h <= 0:
            return
        x = max(0, min(self.width - 1, x))
        y = max(0, min(self.height - 1, y))
        w = min(w, self.width - x)
        h = min(h, self.height - y)
        self.set_window(x, y, x + w - 1, y + h - 1)
        hi = color >> 8
        lo = color & 255
        line = bytearray([hi, lo] * w)
        self.cs.off()
        self.dc.on()
        for _ in range(h):
            self.spi.write(line)
        self.cs.on()

    def fill_screen(self, color):
        self.fill_rect(0, 0, self.width, self.height, color)

    def pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.fill_rect(x, y, 1, 1, color)

    def line(self, x0, y0, x1, y1, color, thickness=1):
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.fill_rect(x0, y0, thickness, thickness, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def rect(self, x, y, w, h, color, thickness=2):
        self.fill_rect(x, y, w, thickness, color)
        self.fill_rect(x, y + h - thickness, w, thickness, color)
        self.fill_rect(x, y, thickness, h, color)
        self.fill_rect(x + w - thickness, y, thickness, h, color)

    def text(self, text, x, y, color=BLACK, scale=2, spacing=1):
        cx = x
        for ch in text.upper():
            glyph = FONT.get(ch, FONT[" "])
            for col, bits in enumerate(glyph):
                for row in range(7):
                    if bits & (1 << row):
                        self.fill_rect(
                            cx + col * scale,
                            y + row * scale,
                            scale,
                            scale,
                            color,
                        )
            cx += (5 + spacing) * scale

    def text_width(self, text, scale=2, spacing=1):
        return len(text) * (5 + spacing) * scale
