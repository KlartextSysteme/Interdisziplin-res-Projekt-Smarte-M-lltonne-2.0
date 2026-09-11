# # # from machine import Pin, SPI
# # # from time import sleep

# # # # SPI0 initialisieren
# # # spi = SPI(
# # #     0,
# # #     baudrate=1000000,
# # #     polarity=0,
# # #     phase=0,
# # #     sck=Pin(18),
# # #     mosi=Pin(19),
# # #     miso=Pin(16)
# # # )

# # # # Touch Pins
# # # touch_cs = Pin(22, Pin.OUT)
# # # touch_irq = Pin(26, Pin.IN, Pin.PULL_UP)

# # # touch_cs.on()


# # # def read_touch_channel(command):
# # #     tx = bytearray([command, 0x00, 0x00])
# # #     rx = bytearray(3)

# # #     touch_cs.off()

# # #     spi.write_readinto(tx, rx)

# # #     touch_cs.on()

# # #     value = ((rx[1] << 8) | rx[2]) >> 3
# # #     return value


# # # def read_touch():
# # #     x = read_touch_channel(0xD0)
# # #     y = read_touch_channel(0x90)
# # #     return x, y


# # # print("Starte Touchpanel-Test...")

# # # while True:

# # #     if touch_irq.value() == 0:
# # #         x, y = read_touch()
# # #         print("Touch erkannt | X:", x, "| Y:", y)
# # #     else:
# # #         print("Kein Touch")

# # #     sleep(0.2)

# # from machine import Pin, SPI
# # from time import sleep

# # spi = SPI(
# #     0,
# #     baudrate=500_000,
# #     polarity=0,
# #     phase=0,
# #     sck=Pin(18),
# #     mosi=Pin(19),
# #     miso=Pin(16)
# # )

# # t_cs = Pin(22, Pin.OUT)
# # t_irq = Pin(26, Pin.IN, Pin.PULL_UP)

# # t_cs.on()

# # def read_raw(cmd):
# #     tx = bytearray([cmd, 0x00, 0x00])
# #     rx = bytearray(3)

# #     t_cs.off()
# #     sleep(0.001)

# #     spi.write_readinto(tx, rx)

# #     t_cs.on()

# #     print("TX:", list(tx), "RX:", list(rx))

# #     value = ((rx[1] << 8) | rx[2]) >> 3
# #     return value


# # print("Touchpanel Diagnose gestartet")

# # while True:
# #     print("IRQ:", t_irq.value())

# #     x = read_raw(0xD0)
# #     y = read_raw(0x90)

# #     print("X:", x, "Y:", y)
# #     print("--------------------")

# #     sleep(1)

from machine import Pin, SPI
from time import sleep

spi = SPI(
    0,
    baudrate=500_000,
    polarity=0,
    phase=0,
    sck=Pin(18),
    mosi=Pin(19),
    miso=Pin(16)
)

t_cs = Pin(22, Pin.OUT)
t_irq = Pin(26, Pin.IN, Pin.PULL_UP)

t_cs.on()

def read_raw(cmd):
    tx = bytearray([cmd, 0x00, 0x00])
    rx = bytearray(3)

    t_cs.off()
    spi.write_readinto(tx, rx)
    t_cs.on()

    return ((rx[1] << 8) | rx[2]) >> 3

def read_touch():
    x = read_raw(0xD0)
    y = read_raw(0x90)

    # ungültige/leere Werte herausfiltern
    if x <= 20 or y <= 20 or x >= 4075 or y >= 4075:
        return None

    return x, y

print("Touchpanel-Test gestartet")
def map_value(value, in_min, in_max, out_min, out_max):
    return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)
while True:
    touch = read_touch()

    if touch is not None:
        x, y = touch
        print("Touch erkannt | X:", x, "| Y:", y)
    else:
        print("Kein gültiger Touch")

    sleep(0.2)

# Beispiel:
# Rohwerte:  X ca. 300 bis 3800
#            Y ca. 300 bis 3800
# Display:   320 x 240 Pixel

from machine import Pin, SPI
from time import sleep_ms

# SPI0 Pico 2 W
spi = SPI(
    0,
    baudrate=40_000_000,
    polarity=0,
    phase=0,
    sck=Pin(18),
    mosi=Pin(19),
    miso=Pin(16)
)

# Display-Pins
cs = Pin(17, Pin.OUT)
dc = Pin(20, Pin.OUT)
rst = Pin(21, Pin.OUT)

# Touch-Pins
t_cs = Pin(22, Pin.OUT)
t_irq = Pin(26, Pin.IN, Pin.PULL_UP)

WIDTH = 320
HEIGHT = 240

def write_cmd(cmd):
    cs.off()
    dc.off()
    spi.write(bytearray([cmd]))
    cs.on()

def write_data(data):
    cs.off()
    dc.on()
    spi.write(bytearray(data))
    cs.on()

def reset_display():
    rst.off()
    sleep_ms(100)
    rst.on()
    sleep_ms(100)

def init_display():
    reset_display()

    write_cmd(0x01)      # Software Reset
    sleep_ms(100)

    write_cmd(0x28)      # Display OFF

    write_cmd(0x3A)      # Pixel Format
    write_data([0x55])   # 16 Bit Farbe

    write_cmd(0x36)      # Memory Access Control
    write_data([0x28])   # Landscape

    write_cmd(0x11)      # Sleep OUT
    sleep_ms(120)

    write_cmd(0x29)      # Display ON

def set_window(x0, y0, x1, y1):
    write_cmd(0x2A)
    write_data([x0 >> 8, x0 & 255, x1 >> 8, x1 & 255])

    write_cmd(0x2B)
    write_data([y0 >> 8, y0 & 255, y1 >> 8, y1 & 255])

    write_cmd(0x2C)

def color565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def fill_rect(x, y, w, h, color):
    set_window(x, y, x + w - 1, y + h - 1)

    high = color >> 8
    low = color & 255
    data = bytearray([high, low] * w)

    cs.off()
    dc.on()

    for _ in range(h):
        spi.write(data)

    cs.on()

def fill_screen(color):
    fill_rect(0, 0, WIDTH, HEIGHT, color)

def draw_button(x, y, w, h):
    blue = color565(0, 80, 255)
    white = color565(255, 255, 255)

    fill_rect(x, y, w, h, blue)

    # einfacher weißer Rand
    fill_rect(x, y, w, 3, white)
    fill_rect(x, y + h - 3, w, 3, white)
    fill_rect(x, y, 3, h, white)
    fill_rect(x + w - 3, y, 3, h, white)

# Hauptprogramm
print("Starte Display-Test...")

t_cs.on()
cs.on()

init_display()

black = color565(0, 0, 0)
fill_screen(black)

# Button zeichnen
draw_button(80, 80, 160, 70)

print("Button wurde angezeigt")

while True:
    sleep_ms(500)