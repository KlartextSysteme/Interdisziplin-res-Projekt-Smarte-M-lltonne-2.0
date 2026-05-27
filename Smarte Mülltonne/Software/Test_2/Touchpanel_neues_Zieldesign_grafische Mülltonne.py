from machine import Pin, SPI
from time import sleep_ms

SPI_ID = 0
PIN_SCK = 18
PIN_MOSI = 19
PIN_MISO = 16
PIN_DISPLAY_CS = 17
PIN_DISPLAY_DC = 20
PIN_DISPLAY_RST = 21
PIN_TOUCH_CS = 22

WIDTH = 320
HEIGHT = 240
ROTATION = 0x28

spi = SPI(SPI_ID, baudrate=20_000_000, polarity=0, phase=0,
          sck=Pin(PIN_SCK), mosi=Pin(PIN_MOSI), miso=Pin(PIN_MISO))

cs = Pin(PIN_DISPLAY_CS, Pin.OUT, value=1)
dc = Pin(PIN_DISPLAY_DC, Pin.OUT, value=1)
rst = Pin(PIN_DISPLAY_RST, Pin.OUT, value=1)
touch_cs = Pin(PIN_TOUCH_CS, Pin.OUT, value=1)

def color565(r, g, b):
    return ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)

WHITE = color565(255, 255, 255)
BLACK = color565(20, 20, 20)
DARK = color565(55, 55, 55)
MID = color565(95, 95, 95)
GRAY = color565(135, 135, 135)

def cmd(c):
    touch_cs.on()
    cs.off()
    dc.off()
    spi.write(bytearray([c]))
    cs.on()

def data(d):
    touch_cs.on()
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
    data([ROTATION])
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

def fill_polygon(points, color):
    ys = [p[1] for p in points]
    y_min = max(0, min(ys))
    y_max = min(HEIGHT - 1, max(ys))

    for y in range(y_min, y_max + 1):
        nodes = []
        j = len(points) - 1

        for i in range(len(points)):
            xi, yi = points[i]
            xj, yj = points[j]

            if (yi < y and yj >= y) or (yj < y and yi >= y):
                x = int(xi + (y - yi) / (yj - yi) * (xj - xi))
                nodes.append(x)

            j = i

        nodes.sort()

        for i in range(0, len(nodes), 2):
            if i + 1 < len(nodes):
                x0 = max(0, nodes[i])
                x1 = min(WIDTH - 1, nodes[i + 1])
                fill_rect(x0, y, x1 - x0 + 1, 1, color)

def circle(cx, cy, r, color):
    x = r
    y = 0
    err = 0

    while x >= y:
        for px, py in (
            (cx + x, cy + y), (cx + y, cy + x),
            (cx - y, cy + x), (cx - x, cy + y),
            (cx - x, cy - y), (cx - y, cy - x),
            (cx + y, cy - x), (cx + x, cy - y)
        ):
            fill_rect(px, py, 1, 1, color)

        y += 1
        if err <= 0:
            err += 2 * y + 1
        if err > 0:
            x -= 1
            err -= 2 * x + 1

def draw_bin():
    fill_screen(WHITE)

    # zentrierter Iconbereich
    x = 97
    y = 12

    # Griff oben
    fill_polygon([
        (x + 47, y + 4), (x + 79, y + 4),
        (x + 86, y + 22), (x + 40, y + 22)
    ], DARK)
    rect(x + 48, y + 7, 30, 8, BLACK, 1)

    # Deckel
    fill_polygon([
        (x + 15, y + 30), (x + 113, y + 30),
        (x + 120, y + 46), (x + 8, y + 46)
    ], BLACK)
    line(x + 18, y + 35, x + 110, y + 35, GRAY, 1)

    # oberer Rand / Kragen
    fill_polygon([
        (x + 24, y + 48), (x + 104, y + 48),
        (x + 98, y + 68), (x + 30, y + 68)
    ], DARK)

    # Hauptkörper
    fill_polygon([
        (x + 34, y + 66),
        (x + 94, y + 66),
        (x + 106, y + 196),
        (x + 22, y + 196)
    ], DARK)

    # Körper-Highlight
    fill_polygon([
        (x + 43, y + 76),
        (x + 62, y + 72),
        (x + 59, y + 188),
        (x + 36, y + 188)
    ], MID)

    fill_polygon([
        (x + 70, y + 72),
        (x + 87, y + 76),
        (x + 94, y + 188),
        (x + 72, y + 188)
    ], BLACK)

    # feine Konturen
    line(x + 34, y + 66, x + 22, y + 196, GRAY, 1)
    line(x + 94, y + 66, x + 106, y + 196, GRAY, 1)
    line(x + 22, y + 196, x + 106, y + 196, GRAY, 1)

    # Vertikale Details
    line(x + 50, y + 76, x + 47, y + 188, BLACK, 1)
    line(x + 78, y + 76, x + 81, y + 188, GRAY, 1)

    # untere Achse / Füße
    fill_rect(x + 18, y + 198, 24, 10, BLACK)
    fill_rect(x + 86, y + 198, 24, 10, BLACK)

    # Räder
    circle(x + 41, y + 209, 13, BLACK)
    circle(x + 87, y + 209, 13, BLACK)
    circle(x + 41, y + 209, 6, GRAY)
    circle(x + 87, y + 209, 6, GRAY)

    # seitliche Stützen
    fill_rect(x + 21, y + 177, 8, 25, BLACK)
    fill_rect(x + 99, y + 177, 8, 25, BLACK)

    # feine Bodenlinie
    line(x + 20, y + 222, x + 108, y + 222, GRAY, 1)

print("Starte Mülltonnen-Icon")

init_display()
draw_bin()

while True:
    sleep_ms(1000)