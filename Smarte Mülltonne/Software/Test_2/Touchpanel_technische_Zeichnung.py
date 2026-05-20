from machine import Pin, SPI
from time import sleep_ms

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


def color565(r, g, b):
    return ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)


BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)
GRAY = color565(180, 180, 180)


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


def circle(cx, cy, r, color):
    x = r
    y = 0
    err = 0

    while x >= y:
        for px, py in [
            (cx + x, cy + y), (cx + y, cy + x),
            (cx - y, cy + x), (cx - x, cy + y),
            (cx - x, cy - y), (cx - y, cy - x),
            (cx + y, cy - x), (cx + x, cy - y)
        ]:
            fill_rect(px, py, 1, 1, color)

        y += 1
        if err <= 0:
            err += 2 * y + 1
        if err > 0:
            x -= 1
            err -= 2 * x + 1


def draw_bin_drawing():
    fill_screen(WHITE)

    # Außenrahmen
    rect(5, 5, 310, 230, BLACK, 1)

    # =====================
    # Vorderansicht links
    # =====================
    line(35, 55, 95, 55, BLACK, 2)      # Deckel
    line(42, 65, 88, 65, BLACK, 1)
    line(45, 65, 55, 170, BLACK, 1)
    line(85, 65, 75, 170, BLACK, 1)
    line(55, 170, 75, 170, BLACK, 1)

    # Räder
    circle(45, 180, 8, BLACK)
    circle(85, 180, 8, BLACK)
    line(45, 180, 85, 180, BLACK, 1)

    # Maße links
    line(30, 45, 100, 45, GRAY, 1)
    line(30, 42, 30, 48, GRAY, 1)
    line(100, 42, 100, 48, GRAY, 1)

    # =====================
    # Seitenansicht Mitte
    # =====================
    line(130, 55, 230, 55, BLACK, 2)    # Deckel
    line(145, 65, 220, 65, BLACK, 1)
    line(145, 65, 150, 180, BLACK, 1)
    line(220, 65, 205, 180, BLACK, 1)
    line(150, 180, 205, 180, BLACK, 1)

    # Griff / Deckelkreis
    circle(150, 45, 30, GRAY)
    line(150, 45, 180, 55, GRAY, 1)

    # Rad
    circle(158, 185, 12, BLACK)
    circle(158, 185, 5, BLACK)

    # Diagonalstrebe / Kante
    line(150, 65, 205, 180, GRAY, 1)

    # Maßlinien
    line(125, 55, 125, 185, GRAY, 1)
    line(120, 55, 130, 55, GRAY, 1)
    line(120, 185, 130, 185, GRAY, 1)

    line(145, 200, 205, 200, GRAY, 1)
    line(145, 195, 145, 205, GRAY, 1)
    line(205, 195, 205, 205, GRAY, 1)

    # =====================
    # Draufsicht rechts
    # =====================
    rect(250, 60, 45, 90, BLACK, 2)
    rect(258, 75, 29, 18, BLACK, 1)
    rect(262, 95, 21, 12, GRAY, 1)

    # seitliche Formen
    line(250, 70, 240, 95, BLACK, 1)
    line(240, 95, 250, 140, BLACK, 1)
    line(295, 70, 305, 95, BLACK, 1)
    line(305, 95, 295, 140, BLACK, 1)

    # Maße rechts
    line(245, 50, 300, 50, GRAY, 1)
    line(245, 47, 245, 53, GRAY, 1)
    line(300, 47, 300, 53, GRAY, 1)

    line(310, 60, 310, 150, GRAY, 1)
    line(307, 60, 313, 60, GRAY, 1)
    line(307, 150, 313, 150, GRAY, 1)

    print("Muelltonnen-Zeichnung angezeigt")


# =====================
# START
# =====================

init_display()
draw_bin_drawing()

while True:
    sleep_ms(1000)