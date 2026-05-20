from machine import Pin, SPI
from time import sleep_ms

# SPI0 Pico 2 W
spi = SPI(
    0,
    baudrate=5_000_000,
    polarity=0,
    phase=0,
    sck=Pin(18),
    mosi=Pin(19),
    miso=Pin(16)
)

# Display ILI9341
lcd_cs = Pin(17, Pin.OUT)
lcd_dc = Pin(20, Pin.OUT)
lcd_rst = Pin(21, Pin.OUT)

# Touch XPT2046
touch_cs = Pin(22, Pin.OUT)

WIDTH = 240
HEIGHT = 320

BTN_X = 60
BTN_Y = 120
BTN_W = 120
BTN_H = 60

lcd_cs.on()
touch_cs.on()


def spi_display():
    spi.init(baudrate=5_000_000, polarity=0, phase=0)


def spi_touch():
    spi.init(baudrate=500_000, polarity=0, phase=0)


def color565(r, g, b):
    return ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)


def lcd_cmd(cmd):
    spi_display()
    touch_cs.on()
    lcd_cs.off()
    lcd_dc.off()
    spi.write(bytes([cmd]))
    lcd_cs.on()


def lcd_data(data):
    spi_display()
    touch_cs.on()
    lcd_cs.off()
    lcd_dc.on()
    spi.write(bytes(data))
    lcd_cs.on()


def lcd_reset():
    lcd_rst.on()
    sleep_ms(50)
    lcd_rst.off()
    sleep_ms(100)
    lcd_rst.on()
    sleep_ms(150)


def lcd_init():
    lcd_reset()

    lcd_cmd(0x01)  # Software Reset
    sleep_ms(150)

    lcd_cmd(0x11)  # Sleep Out
    sleep_ms(150)

    lcd_cmd(0x3A)  # Pixel Format
    lcd_data([0x55])  # 16 Bit RGB565

    lcd_cmd(0x36)  # Memory Access Control
    lcd_data([0x48])  # Hochformat

    lcd_cmd(0x29)  # Display ON
    sleep_ms(100)


def set_window(x0, y0, x1, y1):
    lcd_cmd(0x2A)
    lcd_data([x0 >> 8, x0 & 255, x1 >> 8, x1 & 255])

    lcd_cmd(0x2B)
    lcd_data([y0 >> 8, y0 & 255, y1 >> 8, y1 & 255])

    lcd_cmd(0x2C)


def fill_rect(x, y, w, h, color):
    spi_display()
    set_window(x, y, x + w - 1, y + h - 1)

    high = color >> 8
    low = color & 255
    line = bytes([high, low] * w)

    touch_cs.on()
    lcd_cs.off()
    lcd_dc.on()

    for _ in range(h):
        spi.write(line)

    lcd_cs.on()


def fill_screen(color):
    fill_rect(0, 0, WIDTH, HEIGHT, color)


def draw_button(pressed=False):
    if pressed:
        bg = color565(0, 180, 0)      # grün
    else:
        bg = color565(0, 120, 255)    # blau

    white = color565(255, 255, 255)

    fill_rect(BTN_X, BTN_Y, BTN_W, BTN_H, bg)

    # Rahmen
    fill_rect(BTN_X, BTN_Y, BTN_W, 4, white)
    fill_rect(BTN_X, BTN_Y + BTN_H - 4, BTN_W, 4, white)
    fill_rect(BTN_X, BTN_Y, 4, BTN_H, white)
    fill_rect(BTN_X + BTN_W - 4, BTN_Y, 4, BTN_H, white)


def read_touch_raw(command):
    spi_touch()

    lcd_cs.on()
    touch_cs.off()

    tx = bytearray([command, 0x00, 0x00])
    rx = bytearray(3)

    spi.write_readinto(tx, rx)

    touch_cs.on()

    return ((rx[1] << 8) | rx[2]) >> 3


def read_touch():
    x_raw = read_touch_raw(0xD0)
    y_raw = read_touch_raw(0x90)

    if x_raw <= 20 or y_raw <= 20:
        return None

    if x_raw >= 4075 or y_raw >= 4075:
        return None

    return x_raw, y_raw


def map_value(value, in_min, in_max, out_min, out_max):
    return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)


def touch_to_screen(x_raw, y_raw):
    x = map_value(x_raw, 300, 3800, 0, WIDTH)
    y = map_value(y_raw, 300, 3800, 0, HEIGHT)

    x = max(0, min(WIDTH - 1, x))
    y = max(0, min(HEIGHT - 1, y))

    return x, y


def button_hit(x, y):
    return (
        BTN_X <= x <= BTN_X + BTN_W and
        BTN_Y <= y <= BTN_Y + BTN_H
    )


print("Starte Display und Touch Button")

lcd_init()

fill_screen(color565(0, 0, 0))
draw_button(False)

last_pressed = False

while True:
    touch = read_touch()

    if touch is not None:
        x_raw, y_raw = touch
        x, y = touch_to_screen(x_raw, y_raw)

        print("Touch:", x, y, "| Raw:", x_raw, y_raw)

        pressed = button_hit(x, y)

        if pressed != last_pressed:
            draw_button(pressed)
            last_pressed = pressed

    else:
        if last_pressed:
            draw_button(False)
            last_pressed = False

    sleep_ms(100)