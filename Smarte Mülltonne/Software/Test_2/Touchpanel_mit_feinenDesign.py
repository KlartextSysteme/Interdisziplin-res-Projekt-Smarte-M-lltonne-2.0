from machine import Pin, SPI
from time import sleep_ms

# =========================
# DISPLAY KONFIGURATION
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


# =========================
# DISPLAY FUNKTIONEN
# =========================

def cmd(value):
    cs.off()
    dc.off()
    spi.write(bytearray([value]))
    cs.on()


def data(values):
    cs.off()
    dc.on()
    spi.write(bytearray(values))
    cs.on()


def reset():
    rst.on()
    sleep_ms(50)
    rst.off()
    sleep_ms(100)
    rst.on()
    sleep_ms(150)


def init():
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


def rect(x, y, w, h, color, thickness=2):
    fill_rect(x, y, w, thickness, color)
    fill_rect(x, y + h - thickness, w, thickness, color)
    fill_rect(x, y, thickness, h, color)
    fill_rect(x + w - thickness, y, thickness, h, color)


# =========================
# LINIEN TEST
# =========================

print("Starte Linientest")

init()

fill_screen(WHITE)

# Außenrahmen
x0 = 20
y0 = 20
w = 280
h = 200

rect(x0, y0, w, h, BLACK, 2)

# -------------------------
# Bereich 1: horizontale 1px
# -------------------------
for y in range(35, 65, 2):
    line(40, y, 280, y, BLACK, 1)

# -------------------------
# Bereich 2: horizontale 2px
# -------------------------
for y in range(80, 110, 4):
    line(40, y, 280, y, BLACK, 2)

# -------------------------
# Bereich 3: horizontale 3px
# -------------------------
for y in range(125, 155, 6):
    line(40, y, 280, y, BLACK, 3)

# -------------------------
# Bereich 4: vertikale 1px
# -------------------------
for x in range(40, 280, 6):
    line(x, 165, x, 210, BLACK, 1)

# -------------------------
# Diagonalen drüber
# -------------------------
line(40, 35, 280, 210, BLACK, 1)
line(280, 35, 40, 210, BLACK, 1)

print("Linientest fertig")