from time import sleep_ms

from display import ILI9341
from ui import TouchUi


display = None
ui = None


def main():
    global display, ui

    display = ILI9341()
    display.init()

    ui = TouchUi(display)
    ui.draw()

    # Temporary demo loop until XPT2046 touch is wired and calibrated.
    # In Thonny/REPL call:
    #   ui.handle_touch(280, 120)  -> next
    #   ui.handle_touch(160, 190)  -> open/confirm action
    print("Touchpanel UI started")
    print("Use ui.handle_touch(x, y) in the REPL for first screen tests.")

    while True:
        sleep_ms(1000)


main()
