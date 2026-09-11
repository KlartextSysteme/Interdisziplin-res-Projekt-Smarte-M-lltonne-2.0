from machine import Pin

from config import (
    HEIGHT,
    PIN_TOUCH_CS,
    SPI_BAUDRATE,
    TOUCH_INVERT_X,
    TOUCH_INVERT_Y,
    TOUCH_SWAP_XY,
    TOUCH_X_MAX,
    TOUCH_X_MIN,
    TOUCH_Y_MAX,
    TOUCH_Y_MIN,
    WIDTH,
)


class XPT2046:
    def __init__(self, display, touch_baudrate=500_000):
        self.d = display
        self.touch_baudrate = touch_baudrate
        self.cs = Pin(PIN_TOUCH_CS, Pin.OUT, value=1)

    def _spi_touch(self):
        self.d.spi.init(baudrate=self.touch_baudrate, polarity=0, phase=0)

    def _spi_display(self):
        self.d.spi.init(baudrate=SPI_BAUDRATE, polarity=0, phase=0)

    def read_raw_channel(self, command):
        self._spi_touch()
        self.d.cs.on()
        self.cs.off()

        tx = bytearray([command, 0x00, 0x00])
        rx = bytearray(3)
        self.d.spi.write_readinto(tx, rx)

        self.cs.on()
        self._spi_display()
        return ((rx[1] << 8) | rx[2]) >> 3

    def read_raw(self):
        x_raw = self.read_raw_channel(0xD0)
        y_raw = self.read_raw_channel(0x90)

        if x_raw <= 20 or y_raw <= 20:
            return None
        if x_raw >= 4075 or y_raw >= 4075:
            return None

        return x_raw, y_raw

    def _map(self, value, in_min, in_max, out_min, out_max):
        if in_max == in_min:
            return out_min
        return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

    def read_screen(self):
        raw = self.read_raw()
        if raw is None:
            return None

        x_raw, y_raw = raw
        if TOUCH_SWAP_XY:
            x_source = y_raw
            y_source = x_raw
        else:
            x_source = x_raw
            y_source = y_raw

        x = self._map(x_source, TOUCH_X_MIN, TOUCH_X_MAX, 0, WIDTH)
        y = self._map(y_source, TOUCH_Y_MIN, TOUCH_Y_MAX, 0, HEIGHT)

        if TOUCH_INVERT_X:
            x = WIDTH - 1 - x
        if TOUCH_INVERT_Y:
            y = HEIGHT - 1 - y

        x = max(0, min(WIDTH - 1, x))
        y = max(0, min(HEIGHT - 1, y))
        return x, y, x_raw, y_raw
