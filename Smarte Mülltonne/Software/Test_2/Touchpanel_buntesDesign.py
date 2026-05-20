from machine import Pin, SPI
from time import sleep_ms
import math

# =========================
# DISPLAY SETUP
# =========================

spi = SPI(
    0,
    baudrate=20_000_000,
    polarity=0,
    phase=0,
    sck=Pin(18),
    mosi=Pin(19),
    miso=Pin(16)
)

cs = Pin(17, Pin.OUT, value=1)
dc = Pin(20, Pin.OUT, value=1)
rst = Pin(21, Pin.OUT, value=1)

WIDTH = 320
HEIGHT = 240


# =========================
# FARBEN
# =========================

def color565(r, g, b):
    return ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)


BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)
GRAY = color565(180, 180, 180)
PINK = color565(245, 200, 240)
GREEN = color565(160, 245, 210)


# =========================
# DISPLAY BASIS
# =========================

def cmd(c):
    cs.off()
    dc.off()
    spi.write(bytearray([c]))
    cs.on()


def data(d):
    cs.off()
    dc.on()
    spi.write(bytearray(d))
    cs.on()


def reset():
    rst.on()
    sleep_ms(50)
    rst.off()
    sleep_ms(100)
    rst.on()
    sleep_ms(150)


def init_display():
    reset()

    cmd(0x01)
    sleep_ms(120)

    cmd(0x11)
    sleep_ms(120)

    cmd(0x3A)
    data([0x55])

    cmd(0x36)
    data([0x28])

    cmd(0x29)
    sleep_ms(50)


def set_window(x0, y0, x1, y1):
    cmd(0x2A)
    data([x0 >> 8, x0 & 255, x1 >> 8, x1 & 255])

    cmd(0x2B)
    data([y0 >> 8, y0 & 255, y1 >> 8, y1 & 255])

    cmd(0x2C)


def fill_rect(x, y, w, h, color):
    if w <= 0 or h <= 0:
        return

    if x < 0:
        w += x
        x = 0
    if y < 0:
        h += y
        y = 0
    if x + w > WIDTH:
        w = WIDTH - x
    if y + h > HEIGHT:
        h = HEIGHT - y

    if w <= 0 or h <= 0:
        return

    set_window(x, y, x + w - 1, y + h - 1)

    hi = color >> 8
    lo = color & 255
    line = bytearray([hi, lo] * w)

    cs.off()
    dc.on()

    for _ in range(h):
        spi.write(line)

    cs.on()


def fill_screen(color):
    fill_rect(0, 0, WIDTH, HEIGHT, color)


def line(x0, y0, x1, y1, color, thickness=1):
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy

    while True:
        fill_rect(x0, y0, thickness, thickness, color)

        if x0 == x1 and y0 == y1:
            break

        e2 = 2 * err

        if e2 >= dy:
            err += dy
            x0 += sx

        if e2 <= dx:
            err += dx
            y0 += sy


def rect(x, y, w, h, color, thickness=1):
    fill_rect(x, y, w, thickness, color)
    fill_rect(x, y + h - thickness, w, thickness, color)
    fill_rect(x, y, thickness, h, color)
    fill_rect(x + w - thickness, y, thickness, h, color)


def rounded_rect(x, y, w, h, color, thickness=1):
    # einfache abgerundete Wirkung durch kurze Linien + Eckpixel
    line(x + 12, y, x + w - 12, y, color, thickness)
    line(x + 12, y + h, x + w - 12, y + h, color, thickness)
    line(x, y + 12, x, y + h - 12, color, thickness)
    line(x + w, y + 12, x + w, y + h - 12, color, thickness)

    line(x + 3, y + 8, x + 8, y + 3, color, thickness)
    line(x + w - 3, y + 8, x + w - 8, y + 3, color, thickness)
    line(x + 3, y + h - 8, x + 8, y + h - 3, color, thickness)
    line(x + w - 3, y + h - 8, x + w - 8, y + h - 3, color, thickness)


def circle(cx, cy, r, color, thickness=1):
    for angle in range(0, 360):
        rad = math.radians(angle)
        x = int(cx + r * math.cos(rad))
        y = int(cy + r * math.sin(rad))
        fill_rect(x, y, thickness, thickness, color)


def fill_circle(cx, cy, r, color):
    for yy in range(-r, r + 1):
        for xx in range(-r, r + 1):
            if xx * xx + yy * yy <= r * r:
                fill_rect(cx + xx, cy + yy, 1, 1, color)


def arc(cx, cy, r, start_deg, end_deg, color, thickness=2):
    for angle in range(start_deg, end_deg + 1):
        rad = math.radians(angle)
        x = int(cx + r * math.cos(rad))
        y = int(cy + r * math.sin(rad))
        fill_rect(x, y, thickness, thickness, color)


# =========================
# MINI FONT
# =========================

FONT = {
    "A": (14, 17, 31, 17, 17),
    "B": (30, 17, 30, 17, 30),
    "D": (30, 17, 17, 17, 30),
    "E": (31, 16, 30, 16, 31),
    "N": (17, 25, 21, 19, 17),
    "R": (30, 17, 30, 18, 17),
    "S": (15, 16, 14, 1, 30),
    "U": (17, 17, 17, 17, 14),
    "V": (17, 17, 17, 10, 4),
    " ": (0, 0, 0, 0, 0),
}


def text(txt, x, y, color=BLACK, scale=2):
    cx = x

    for ch in txt.upper():
        glyph = FONT.get(ch, FONT[" "])

        for col, bits in enumerate(glyph):
            for row in range(7):
                if bits & (1 << row):
                    fill_rect(
                        cx + col * scale,
                        y + row * scale,
                        scale,
                        scale,
                        color
                    )

        cx += 6 * scale


# =========================
# SCREEN ELEMENTE
# =========================

def draw_cloud():
    # Wolke als Linien/Bögen, nicht als volle Kreise

    # linke Wölbung
    arc(118, 92, 24, 180, 300, BLACK, 2)

    # große obere Wölbung
    arc(158, 68, 34, 190, 350, BLACK, 2)

    # rechte Wölbung
    arc(200, 91, 25, 220, 360, BLACK, 2)

    # Verbindende Linien
    line(97, 92, 97, 112, BLACK, 2)
    line(97, 112, 224, 112, BLACK, 2)
    line(224, 91, 224, 112, BLACK, 2)


def draw_status_box():
    # rosa Kasten
    fill_rect(76, 105, 150, 62, PINK)
    rect(76, 105, 150, 62, GRAY, 1)

    # Trennlinie im Kasten
    line(76, 137, 226, 137, GRAY, 1)

    text("SERVER", 104, 118, BLACK, 2)
    text("VERBUNDEN", 88, 145, BLACK, 2)


def draw_check_icon():
    fill_circle(232, 155, 28, GREEN)
    circle(232, 155, 28, GRAY, 2)

    # Haken
    line(218, 154, 229, 166, BLACK, 4)
    line(229, 166, 248, 132, BLACK, 4)


def draw_screen():
    fill_screen(WHITE)

    # äußerer Rahmen
    rounded_rect(12, 14, 296, 210, GRAY, 2)

    draw_cloud()
    draw_status_box()
    draw_check_icon()


# =========================
# START
# =========================

print("Starte Server verbunden Screen")

init_display()
draw_screen()

while True:
    sleep_ms(1000)