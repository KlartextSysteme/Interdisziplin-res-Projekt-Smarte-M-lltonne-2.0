# # from machine import Pin, SPI
# # from time import sleep_ms

# # # SPI0 Pico 2 W
# # spi = SPI(
# #     0,
# #     baudrate=20_000_000,
# #     polarity=0,
# #     phase=0,
# #     sck=Pin(18),
# #     mosi=Pin(19),
# #     miso=Pin(16)
# # )

# # # Display-Pins
# # cs = Pin(17, Pin.OUT)
# # dc = Pin(20, Pin.OUT)
# # rst = Pin(21, Pin.OUT)

# # # Touch-Pins
# # t_cs = Pin(22, Pin.OUT)
# # t_irq = Pin(26, Pin.IN, Pin.PULL_UP)

# # WIDTH = 320
# # HEIGHT = 240

# # # Button
# # BUTTON_X = 80
# # BUTTON_Y = 80
# # BUTTON_W = 160
# # BUTTON_H = 70


# # def write_cmd(cmd):
# #     cs.off()
# #     dc.off()
# #     spi.write(bytearray([cmd]))
# #     cs.on()


# # def write_data(data):
# #     cs.off()
# #     dc.on()
# #     spi.write(bytearray(data))
# #     cs.on()


# # def reset_display():
# #     rst.off()
# #     sleep_ms(100)
# #     rst.on()
# #     sleep_ms(100)


# # def init_display():
# #     reset_display()

# #     write_cmd(0x01)
# #     sleep_ms(100)

# #     write_cmd(0x28)

# #     write_cmd(0x3A)
# #     write_data([0x55])

# #     write_cmd(0x36)
# #     write_data([0x28])

# #     write_cmd(0x11)
# #     sleep_ms(120)

# #     write_cmd(0x29)


# # def set_window(x0, y0, x1, y1):
# #     write_cmd(0x2A)
# #     write_data([x0 >> 8, x0 & 255, x1 >> 8, x1 & 255])

# #     write_cmd(0x2B)
# #     write_data([y0 >> 8, y0 & 255, y1 >> 8, y1 & 255])

# #     write_cmd(0x2C)


# # def color565(r, g, b):
# #     return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


# # def fill_rect(x, y, w, h, color):
# #     set_window(x, y, x + w - 1, y + h - 1)

# #     high = color >> 8
# #     low = color & 255
# #     data = bytearray([high, low] * w)

# #     cs.off()
# #     dc.on()

# #     for _ in range(h):
# #         spi.write(data)

# #     cs.on()


# # def fill_screen(color):
# #     fill_rect(0, 0, WIDTH, HEIGHT, color)


# # def draw_button(active=False):
# #     if active:
# #         color = color565(0, 180, 0)      # grün
# #     else:
# #         color = color565(0, 80, 255)     # blau

# #     white = color565(255, 255, 255)

# #     fill_rect(BUTTON_X, BUTTON_Y, BUTTON_W, BUTTON_H, color)

# #     # Rand
# #     fill_rect(BUTTON_X, BUTTON_Y, BUTTON_W, 3, white)
# #     fill_rect(BUTTON_X, BUTTON_Y + BUTTON_H - 3, BUTTON_W, 3, white)
# #     fill_rect(BUTTON_X, BUTTON_Y, 3, BUTTON_H, white)
# #     fill_rect(BUTTON_X + BUTTON_W - 3, BUTTON_Y, 3, BUTTON_H, white)


# # def read_touch_raw(cmd):
# #     tx = bytearray([cmd, 0x00, 0x00])
# #     rx = bytearray(3)

# #     t_cs.off()
# #     spi.write_readinto(tx, rx)
# #     t_cs.on()

# #     return ((rx[1] << 8) | rx[2]) >> 3


# # def read_touch():
# #     x_raw = read_touch_raw(0xD0)
# #     y_raw = read_touch_raw(0x90)

# #     # ungültige Werte herausfiltern
# #     if x_raw <= 20 or y_raw <= 20 or x_raw >= 4075 or y_raw >= 4075:
# #         return None

# #     return x_raw, y_raw


# # def map_value(value, in_min, in_max, out_min, out_max):
# #     return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)


# # def raw_to_screen(x_raw, y_raw):
# #     # Diese Werte ggf. nach Kalibrierung anpassen
# #     x = map_value(x_raw, 300, 3800, 0, WIDTH)
# #     y = map_value(y_raw, 300, 3800, 0, HEIGHT)

# #     # Begrenzen
# #     if x < 0:
# #         x = 0
# #     if x >= WIDTH:
# #         x = WIDTH - 1

# #     if y < 0:
# #         y = 0
# #     if y >= HEIGHT:
# #         y = HEIGHT - 1

# #     return x, y


# # def button_pressed(x, y):
# #     return (
# #         BUTTON_X <= x <= BUTTON_X + BUTTON_W and
# #         BUTTON_Y <= y <= BUTTON_Y + BUTTON_H
# #     )


# # # Start
# # print("Starte Display + Touch Test...")

# # cs.on()
# # t_cs.on()

# # init_display()

# # black = color565(0, 0, 0)
# # fill_screen(black)

# # draw_button(False)

# # last_state = False

# # while True:
# #     touch = read_touch()

# #     if touch is not None:
# #         x_raw, y_raw = touch
# #         x, y = raw_to_screen(x_raw, y_raw)

# #         print("Touch:", x, y, "| Raw:", x_raw, y_raw)

# #         if button_pressed(x, y):
# #             if not last_state:
# #                 print("Button gedrückt")
# #                 draw_button(True)
# #                 last_state = True
# #         else:
# #             if last_state:
# #                 draw_button(False)
# #                 last_state = False

# #     else:
# #         if last_state:
# #             draw_button(False)
# #             last_state = False

# #     sleep_ms(100)
# from machine import Pin, SPI
# from time import sleep_ms

# # SPI0 initialisieren
# spi = SPI(
#     0,
#     baudrate=20_000_000,
#     polarity=0,
#     phase=0,
#     sck=Pin(18),
#     mosi=Pin(19),
#     miso=Pin(16)
# )

# # Display Pins
# cs = Pin(17, Pin.OUT)
# dc = Pin(20, Pin.OUT)
# rst = Pin(21, Pin.OUT)

# WIDTH = 320
# HEIGHT = 240


# def write_cmd(cmd):
#     cs.off()
#     dc.off()
#     spi.write(bytearray([cmd]))
#     cs.on()


# def write_data(data):
#     cs.off()
#     dc.on()
#     spi.write(bytearray(data))
#     cs.on()


# def reset_display():
#     rst.off()
#     sleep_ms(100)
#     rst.on()
#     sleep_ms(100)


# def init_display():
#     reset_display()

#     write_cmd(0x01)  # Software Reset
#     sleep_ms(150)

#     write_cmd(0x28)  # Display OFF

#     write_cmd(0x3A)  # Pixel Format
#     write_data([0x55])  # RGB565

#     write_cmd(0x36)  # Rotation
#     write_data([0x28])

#     write_cmd(0x11)  # Sleep Out
#     sleep_ms(150)

#     write_cmd(0x29)  # Display ON


# def set_window(x0, y0, x1, y1):
#     write_cmd(0x2A)
#     write_data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])

#     write_cmd(0x2B)
#     write_data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])

#     write_cmd(0x2C)


# def color565(r, g, b):
#     return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


# def fill_screen(color):
#     set_window(0, 0, WIDTH - 1, HEIGHT - 1)

#     high = color >> 8
#     low = color & 0xFF

#     line = bytearray([high, low] * WIDTH)

#     cs.off()
#     dc.on()

#     for _ in range(HEIGHT):
#         spi.write(line)

#     cs.on()


# def fill_rect(x, y, w, h, color):
#     set_window(x, y, x + w - 1, y + h - 1)

#     high = color >> 8
#     low = color & 0xFF

#     line = bytearray([high, low] * w)

#     cs.off()
#     dc.on()

#     for _ in range(h):
#         spi.write(line)

#     cs.on()


# # Start
# print("Initialisiere Display...")

# init_display()

# # Hintergrund schwarz
# black = color565(0, 0, 0)
# fill_screen(black)

# # Rotes Rechteck
# red = color565(255, 0, 0)
# fill_rect(50, 50, 220, 100, red)

# print("Anzeige erfolgreich")

from machine import Pin, SPI
from time import sleep

# SPI
spi = SPI(
    0,
    baudrate=10000000,
    polarity=0,
    phase=0,
    sck=Pin(18),
    mosi=Pin(19)
)

# Pins
cs = Pin(17, Pin.OUT)
dc = Pin(20, Pin.OUT)
rst = Pin(21, Pin.OUT)

def write_cmd(cmd):
    cs.value(0)
    dc.value(0)
    spi.write(bytearray([cmd]))
    cs.value(1)

def write_data(data):
    cs.value(0)
    dc.value(1)
    spi.write(bytearray(data))
    cs.value(1)

def reset():
    rst.value(1)
    sleep(0.1)

    rst.value(0)
    sleep(0.1)

    rst.value(1)
    sleep(0.1)

def init():
    reset()

    write_cmd(0x01)
    sleep(0.1)

    write_cmd(0x11)
    sleep(0.12)

    write_cmd(0x3A)
    write_data([0x55])

    write_cmd(0x29)

def fill_screen(color):
    write_cmd(0x2A)
    write_data([0x00, 0x00, 0x00, 0xEF])

    write_cmd(0x2B)
    write_data([0x00, 0x00, 0x01, 0x3F])

    write_cmd(0x2C)

    hi = color >> 8
    lo = color & 0xFF

    cs.value(0)
    dc.value(1)

    for _ in range(320 * 240):
        spi.write(bytearray([hi, lo]))

    cs.value(1)

print("Init Display")

init()

RED = 0xF800

fill_screen(RED)

print("Fertig")