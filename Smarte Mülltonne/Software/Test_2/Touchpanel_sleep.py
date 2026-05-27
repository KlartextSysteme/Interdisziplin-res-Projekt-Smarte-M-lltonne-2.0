from machine import Pin, SPI
from time import sleep_ms

# Pins wie in eurem funktionierenden Skript
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

spi = SPI(
    SPI_ID,
    baudrate=20_000_000,
    polarity=0,
    phase=0,
    sck=Pin(PIN_SCK),
    mosi=Pin(PIN_MOSI),
    miso=Pin(PIN_MISO)
)

lcd_cs = Pin(PIN_DISPLAY_CS, Pin.OUT, value=1)
lcd_dc = Pin(PIN_DISPLAY_DC, Pin.OUT, value=1)
lcd_rst = Pin(PIN_DISPLAY_RST, Pin.OUT, value=1)
touch_cs = Pin(PIN_TOUCH_CS, Pin.OUT, value=1)

def color565(r, g, b):
    return ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)

BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)
GRAY = color565(120, 120, 120)
GREEN = color565(0, 200, 80)

def spi_display():
    spi.init(baudrate=20_000_000, polarity=0, phase=0)

def spi_touch():
    spi.init(baudrate=500_000, polarity=0, phase=0)

def cmd(c):
    spi_display()
    touch_cs.on()
    lcd_cs.off()
    lcd_dc.off()
    spi.write(bytearray([c]))
    lcd_cs.on()

def data(d):
    spi_display()
    touch_cs.on()
    lcd_cs.off()
    lcd_dc.on()
    spi.write(bytearray(d))
    lcd_cs.on()

def reset():
    lcd_rst.on()
    sleep_ms(50)
    lcd_rst.off()
    sleep_ms(100)
    lcd_rst.on()
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

    spi_display()
    touch_cs.on()
    lcd_cs.off()
    lcd_dc.on()

    for _ in range(h):
        spi.write(line)

    lcd_cs.on()

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

def read_touch_raw(command):
    spi_touch()

    lcd_cs.on()
    touch_cs.off()

    tx = bytearray([command, 0x00, 0x00])
    rx = bytearray(3)

    spi.write_readinto(tx, rx)

    touch_cs.on()

    return ((rx[1] << 8) | rx[2]) >> 3

def touch_detected():
    x_raw = read_touch_raw(0xD0)
    y_raw = read_touch_raw(0x90)

    print("Touch Raw:", x_raw, y_raw)

    if x_raw <= 20 or y_raw <= 20:
        return False

    if x_raw >= 4075 or y_raw >= 4075:
        return False

    return True

def gray_sleep_screen():
    fill_screen(GRAY)
    print("Grauer Schlafmodus aktiv")

def draw_wakeup_symbol():
    fill_screen(WHITE)

    # grüner Haken
    line(120, 125, 150, 155, GREEN, 8)
    line(150, 155, 205, 85, GREEN, 8)

print("Starte Graumodus-Test")

init_display()

fill_screen(WHITE)
sleep_ms(2000)

gray_sleep_screen()

while True:
    if touch_detected():
        print("Touch erkannt - Display wacht auf")
        draw_wakeup_symbol()
        break

    sleep_ms(200)

while True:
    sleep_ms(1000)