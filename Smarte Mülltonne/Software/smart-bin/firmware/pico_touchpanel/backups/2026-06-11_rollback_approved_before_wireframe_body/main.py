from machine import Pin
from time import sleep_ms

from config import PIN_BACKLIGHT
from display import ILI9341
from touch import XPT2046
from ui import TouchUi


display = None
touch = None
ui = None
_backlight = None


def set_backlight(enabled):
    global _backlight
    if PIN_BACKLIGHT is None:
        return
    if _backlight is None:
        _backlight = Pin(PIN_BACKLIGHT, Pin.OUT, value=1)
    _backlight.value(1 if enabled else 0)


def handle_action(action):
    # First stage: keep hardware/backend side effects observable but safe.
    # These names are the stable contract for later integration.
    print("Touch action:", action)
    if action == "eco":
        set_backlight(False)
    elif action in ("connect", "disconnect"):
        # Network control will be wired to the final Pico/bridge integration.
        pass
    elif action == "shutdown":
        set_backlight(False)


def main():
    global display, touch, ui

    set_backlight(True)

    display = ILI9341()
    display.init()

    touch = XPT2046(display)
    ui = TouchUi(display, action_handler=handle_action)
    ui.draw()

    print("Touchpanel UI started")
    print("PIN: 1234")

    last_touch = False

    while True:
        ui.tick()
        data = touch.read_screen()

        if data is not None:
            x, y, x_raw, y_raw = data
            if not last_touch:
                print("Touch:", x, y, "| Raw:", x_raw, y_raw)
                ui.handle_touch(x, y)
                last_touch = True
        else:
            last_touch = False

        sleep_ms(60)


main()
