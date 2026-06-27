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

# XPT2046 calibration from the on-device 5-point calibration.
# The panel reports swapped axes in landscape rotation 0x28.
TOUCH_X_MIN = 374
TOUCH_X_MAX = 3895
TOUCH_Y_MIN = 273
TOUCH_Y_MAX = 3857
TOUCH_SWAP_XY = True
TOUCH_INVERT_X = True
TOUCH_INVERT_Y = True

# Optional display backlight pin. Set to the real BL pin when wired.
PIN_BACKLIGHT = None

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
ENABLE_BACKEND_ACTIONS = False
ADMIN_TOKEN = ""

# TCP bridge demo path for the current SmartBinDemo test network.
ENABLE_TCP_BRIDGE = True
WLAN_SSID = "SmartBinDemo"
WLAN_PASSWORD = "SmartBin2026!"
BRIDGE_HOST = "192.168.50.10"
BRIDGE_PORT = 50002
TCP_STATUS_MS = 2000

# Local maintenance PIN. The on-screen keypad supports digits plus * and #.
MAINTENANCE_PIN = "12#"


def make_output(pin_no, value=1):
    pin = Pin(pin_no, Pin.OUT)
    pin.value(value)
    return pin
