from machine import Pin


# Display wiring from the working ILI9341 test.
SPI_ID = 0
SPI_BAUDRATE = 20_000_000
PIN_SCK = 18
PIN_MOSI = 19
PIN_MISO = 16
PIN_DISPLAY_CS = 17
PIN_DISPLAY_DC = 20
PIN_DISPLAY_RST = 21

# XPT2046 touch wiring. Adjust T_CS/T_IRQ after checking the real module.
# Keep CS separate from MISO; 22 is a safe placeholder, not a confirmed wire.
PIN_TOUCH_CS = 22
PIN_TOUCH_IRQ = None

# Landscape UI target.
WIDTH = 320
HEIGHT = 240

# ILI9341 MADCTL rotation value. If the UI is mirrored/rotated on hardware,
# try 0x28, 0x88 or 0xE8 and keep WIDTH/HEIGHT at 320x240.
DISPLAY_ROTATION = 0x28

# Backend settings for later integration.
BIN_ID = 1
BACKEND_URL = "http://192.168.0.10:8000"
POLL_COMMAND_MS = 2000
POST_STATUS_MS = 8000

# Local maintenance PIN. Keep numeric for the on-screen keypad.
MAINTENANCE_PIN = "1234"


def make_output(pin_no, value=1):
    pin = Pin(pin_no, Pin.OUT)
    pin.value(value)
    return pin
