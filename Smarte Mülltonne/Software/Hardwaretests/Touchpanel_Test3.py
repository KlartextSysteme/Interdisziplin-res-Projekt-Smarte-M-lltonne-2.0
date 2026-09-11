# from machine import Pin, SPI
# from time import sleep_ms

# spi = SPI(
#     0,
#     baudrate=5_000_000,
#     polarity=0,
#     phase=0,
#     sck=Pin(18),
#     mosi=Pin(19)
# )

# cs = Pin(17, Pin.OUT)
# dc = Pin(20, Pin.OUT)
# rst = Pin(21, Pin.OUT)

# cs.value(1)
# dc.value(1)
# rst.value(1)

# def write_cmd(cmd):
#     cs.value(0)
#     dc.value(0)
#     spi.write(bytes([cmd]))
#     cs.value(1)

# def write_data(data):
#     cs.value(0)
#     dc.value(1)
#     spi.write(bytes(data))
#     cs.value(1)

# def reset_display():
#     rst.value(1)
#     sleep_ms(50)
#     rst.value(0)
#     sleep_ms(100)
#     rst.value(1)
#     sleep_ms(150)

# def init_display():
#     reset_display()

#     write_cmd(0x01)
#     sleep_ms(150)

#     write_cmd(0x11)
#     sleep_ms(150)

#     write_cmd(0x3A)
#     write_data([0x55])

#     write_cmd(0x36)
#     write_data([0x48])

#     write_cmd(0x29)
#     sleep_ms(100)

# def set_window(x0, y0, x1, y1):
#     write_cmd(0x2A)
#     write_data([x0 >> 8, x0 & 255, x1 >> 8, x1 & 255])

#     write_cmd(0x2B)
#     write_data([y0 >> 8, y0 & 255, y1 >> 8, y1 & 255])

#     write_cmd(0x2C)

# def fill_screen(color):
#     set_window(0, 0, 239, 319)

#     hi = color >> 8
#     lo = color & 255
#     line = bytes([hi, lo] * 240)

#     cs.value(0)
#     dc.value(1)

#     for _ in range(320):
#         spi.write(line)

#     cs.value(1)

# print("Starte ILI9341 Test")

# init_display()

# while True:
#     print("ROT")
#     fill_screen(0xF800)
#     sleep_ms(1000)

#     print("GRUEN")
#     fill_screen(0x07E0)
#     sleep_ms(1000)

#     print("BLAU")
#     fill_screen(0x001F)
#     sleep_ms(1000)

from machine import Pin, SPI
from time import sleep_ms

# SPI
spi = SPI(
    0,
    baudrate=20_000_000,
    polarity=0,
    phase=0,
    sck=Pin(18),
    mosi=Pin(19)
)

# Display Pins
cs = Pin(17, Pin.OUT)
dc = Pin(20, Pin.OUT)
rst = Pin(21, Pin.OUT)

WIDTH = 240
HEIGHT = 320


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


def init():
    reset()

    cmd(0x01)
    sleep_ms(120)

    cmd(0x11)
    sleep_ms(120)

    cmd(0x3A)
    data([0x55])

    cmd(0x36)
    data([0x48])

    cmd(0x29)
    sleep_ms(50)


def set_window(x0, y0, x1, y1):
    cmd(0x2A)
    data([x0 >> 8, x0 & 255, x1 >> 8, x1 & 255])

    cmd(0x2B)
    data([y0 >> 8, y0 & 255, y1 >> 8, y1 & 255])

    cmd(0x2C)


def color565(r, g, b):
    return ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)


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


def draw_button(x, y, w, h):

    blue = color565(0, 120, 255)
    white = color565(255, 255, 255)

    # Buttonfläche
    fill_rect(x, y, w, h, blue)

    # Rahmen
    fill_rect(x, y, w, 4, white)
    fill_rect(x, y + h - 4, w, 4, white)
    fill_rect(x, y, 4, h, white)
    fill_rect(x + w - 4, y, 4, h, white)


print("Starte Display")

init()

black = color565(0, 0, 0)

fill_screen(black)

# Button mittig
draw_button(60, 120, 120, 60)

print("Button gezeichnet")