from machine import Pin, SPI
from time import sleep_ms


SPI_ID = 0
SPI_BAUDRATE = 20_000_000
PIN_SCK = 18
PIN_MOSI = 19
PIN_MISO = 16
PIN_DISPLAY_CS = 17
PIN_DISPLAY_DC = 20
PIN_DISPLAY_RST = 21
PIN_TOUCH_CS = 22

WIDTH = 320
HEIGHT = 240
DISPLAY_ROTATION = 0x28

TOUCH_X_MIN = 467
TOUCH_X_MAX = 3606
TOUCH_Y_MIN = 475
TOUCH_Y_MAX = 3789

VIEW_X = 20
VIEW_Y = 34
VIEW_W = 280
VIEW_H = 180
ROW_H = 34
ROW_COUNT = 12

# Bei gedrehtem Display liefert eine Hoch/Runter-Fingerbewegung die X-Achse.
# Wenn die Richtung falsch herum wirkt, diesen Wert auf -1 setzen.
TOUCH_SCROLL_SIGN = 1


def color565(r, g, b):
    return ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)


BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)
BLUE = color565(0, 120, 255)
GREEN = color565(46, 125, 50)
GRAY = color565(180, 180, 180)
YELLOW = color565(248, 196, 35)
RED = color565(198, 40, 40)


FONT = {
    " ": (0, 0, 0, 0, 0),
    "-": (0, 0, 14, 0, 0),
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
    "C": (15, 16, 16, 16, 15),
    "E": (31, 16, 30, 16, 31),
    "L": (16, 16, 16, 16, 31),
    "N": (17, 25, 21, 19, 17),
    "O": (14, 17, 17, 17, 14),
    "R": (30, 17, 30, 18, 17),
    "S": (15, 16, 14, 1, 30),
    "T": (31, 4, 4, 4, 4),
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
        self.touch_cs = Pin(PIN_TOUCH_CS, Pin.OUT, value=1)

    def spi_display(self):
        self.spi.init(baudrate=SPI_BAUDRATE, polarity=0, phase=0)

    def spi_touch(self):
        self.spi.init(baudrate=500_000, polarity=0, phase=0)

    def cmd(self, value):
        self.spi_display()
        self.touch_cs.on()
        self.cs.off()
        self.dc.off()
        self.spi.write(bytearray([value]))
        self.cs.on()

    def data(self, values):
        self.spi_display()
        self.touch_cs.on()
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
        x = max(0, min(WIDTH - 1, x))
        y = max(0, min(HEIGHT - 1, y))
        w = min(w, WIDTH - x)
        h = min(h, HEIGHT - y)
        self.set_window(x, y, x + w - 1, y + h - 1)
        hi = color >> 8
        lo = color & 255
        line = bytearray([hi, lo] * w)
        self.spi_display()
        self.touch_cs.on()
        self.cs.off()
        self.dc.on()
        for _ in range(h):
            self.spi.write(line)
        self.cs.on()

    def fill_screen(self, color):
        self.fill_rect(0, 0, WIDTH, HEIGHT, color)

    def blit_buffer(self, x, y, w, h, buffer):
        self.set_window(x, y, x + w - 1, y + h - 1)
        self.spi_display()
        self.touch_cs.on()
        self.cs.off()
        self.dc.on()
        self.spi.write(buffer)
        self.cs.on()

    def text(self, text, x, y, color=BLACK, scale=3, spacing=1):
        cx = x
        for ch in text.upper():
            glyph = FONT.get(ch, FONT[" "])
            for col, bits in enumerate(glyph):
                for row in range(7):
                    if bits & (1 << row):
                        self.fill_rect(
                            cx + (6 - row) * scale,
                            y + col * scale,
                            scale,
                            scale,
                            color,
                        )
            cx += (5 + spacing) * scale


class XPT2046:
    def __init__(self, display):
        self.d = display

    def read_raw_channel(self, command):
        self.d.spi_touch()
        self.d.cs.on()
        self.d.touch_cs.off()

        tx = bytearray([command, 0, 0])
        rx = bytearray(3)
        self.d.spi.write_readinto(tx, rx)

        self.d.touch_cs.on()
        return ((rx[1] << 8) | rx[2]) >> 3

    def read_raw(self):
        x_raw = self.read_raw_channel(0xD0)
        y_raw = self.read_raw_channel(0x90)

        if x_raw <= 20 or y_raw <= 20:
            return None
        if x_raw >= 4075 or y_raw >= 4075:
            return None

        return x_raw, y_raw

    def map_value(self, value, in_min, in_max, out_min, out_max):
        return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

    def read_screen(self):
        raw = self.read_raw()
        if raw is None:
            return None

        x_raw, y_raw = raw
        x = self.map_value(x_raw, TOUCH_X_MIN, TOUCH_X_MAX, 0, WIDTH)
        y = self.map_value(y_raw, TOUCH_Y_MIN, TOUCH_Y_MAX, 0, HEIGHT)

        x = max(0, min(WIDTH - 1, x))
        y = max(0, min(HEIGHT - 1, y))
        return x, y, x_raw, y_raw


def draw_static_background(display):
    display.fill_screen(WHITE)
    display.fill_rect(0, 0, WIDTH, 26, BLUE)
    display.text("TOUCH SCROLL", 56, 7, WHITE, 2)
    display.text("HOCH RUNTER", 64, 220, RED, 2)

    for y in range(44, 220, 28):
        display.fill_rect(20, y, 280, 1, GRAY)


def fill_buffer(buffer, color):
    hi = color >> 8
    lo = color & 255
    line = bytes([hi, lo]) * VIEW_W

    for y in range(VIEW_H):
        start = y * VIEW_W * 2
        buffer[start:start + VIEW_W * 2] = line


def fill_buffer_rect(buffer, x, y, w, h, color):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(VIEW_W, x + w)
    y1 = min(VIEW_H, y + h)

    if x0 >= x1 or y0 >= y1:
        return

    hi = color >> 8
    lo = color & 255
    line = bytes([hi, lo]) * (x1 - x0)

    for py in range(y0, y1):
        start = (py * VIEW_W + x0) * 2
        buffer[start:start + len(line)] = line


def draw_buffer_text(buffer, text, x, y, color=BLACK, scale=2, spacing=1):
    cx = x

    for ch in text.upper():
        glyph = FONT.get(ch, FONT[" "])
        for col, bits in enumerate(glyph):
            for row in range(7):
                if bits & (1 << row):
                    fill_buffer_rect(
                        buffer,
                        cx + (6 - row) * scale,
                        y + col * scale,
                        scale,
                        scale,
                        color,
                    )
        cx += (5 + spacing) * scale


def draw_list(display, scroll, buffer):
    fill_buffer(buffer, WHITE)

    for i in range(ROW_COUNT):
        y = 4 + i * ROW_H - scroll
        if y < -30 or y > VIEW_H:
            continue

        color = GREEN if i % 2 == 0 else GRAY
        fill_buffer_rect(buffer, 10, y, 260, 28, color)
        fill_buffer_rect(buffer, 10, y, 10, 28, YELLOW)
        draw_buffer_text(buffer, "ZEILE " + str(i + 1), 38, y + 7, BLACK, 2)

    display.blit_buffer(VIEW_X, VIEW_Y, VIEW_W, VIEW_H, buffer)


def main():
    display = ILI9341()
    touch = XPT2046(display)
    display.init()
    draw_static_background(display)

    list_buffer = bytearray(VIEW_W * VIEW_H * 2)
    scroll = 0
    last_touch_axis = None
    max_scroll = ROW_COUNT * ROW_H - VIEW_H
    draw_list(display, scroll, list_buffer)

    while True:
        data = touch.read_screen()

        if data is None:
            last_touch_axis = None
            sleep_ms(20)
            continue

        x, _y, _x_raw, _y_raw = data

        if last_touch_axis is not None:
            delta = x - last_touch_axis
            if delta > 1 or delta < -1:
                scroll += delta * TOUCH_SCROLL_SIGN
                scroll = max(0, min(max_scroll, scroll))
                draw_list(display, scroll, list_buffer)

        last_touch_axis = x
        sleep_ms(20)


main()
