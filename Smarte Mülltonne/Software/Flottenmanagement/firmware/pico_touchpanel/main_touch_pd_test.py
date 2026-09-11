from machine import Pin
from time import sleep_ms

from config import PIN_BACKLIGHT
from display import BLACK, BLUE, GREEN, ORANGE, RED, WHITE, ILI9341
from pd_motor_linien_touch import create_motors, run_to_street
from touch import XPT2046
from ui import TouchUi


display = None
touch = None
ui = None
motors = None
_backlight = None


def set_backlight(enabled):
    global _backlight
    if PIN_BACKLIGHT is None:
        return
    if _backlight is None:
        _backlight = Pin(PIN_BACKLIGHT, Pin.OUT, value=1)
    _backlight.value(1 if enabled else 0)


def center_text(text, y, color=BLACK, scale=2):
    x = (display.width - display.text_width(text, scale)) // 2
    display.text(text, x, y, color, scale)


def draw_drive_screen(title, subtitle="", color=BLUE):
    display.fill_screen(WHITE)
    display.rect(4, 4, 312, 232, BLACK, 2)
    center_text(title, 82, color, 3)
    if subtitle:
        center_text(subtitle, 142, BLACK, 2)


def draw_result(result):
    if result == "street":
        draw_drive_screen("ZIEL ERREICHT", "STRASSE", GREEN)
        ui.set_status(location="truck", status_kind="full_home")
    elif result == "obstacle":
        draw_drive_screen("STOPP", "HINDERNIS", ORANGE)
        ui.set_status(status_kind="obstacle", obstacle_cm=0)
    elif result == "line_lost":
        draw_drive_screen("STOPP", "LINIE VERLOREN", RED)
        ui.set_status(status_kind="line_lost", line_ok=False)
    else:
        draw_drive_screen("STOPP", result.upper(), RED)
    sleep_ms(1800)


def handle_action(action):
    global motors

    print("Touch action:", action)

    if action == "eco":
        set_backlight(False)
        return

    if action == "shutdown":
        set_backlight(False)
        return

    if action in ("connect", "disconnect"):
        return

    if action == "goto_home":
        # Fuer diesen Test wird nur die Fahrt zur Strasse aktiv gestartet.
        draw_drive_screen("TEST", "HEIMFAHRT NOCH NICHT AKTIV", ORANGE)
        sleep_ms(1500)
        return

    if action == "goto_street":
        if motors is None:
            motors = create_motors(debug=False)

        draw_drive_screen("FAEHRT", "PD REGLER AKTIV", BLUE)
        result = run_to_street(motors)
        draw_result(result)
        return


def main():
    global display, touch, ui

    set_backlight(True)

    display = ILI9341()
    display.init()

    touch = XPT2046(display)
    ui = TouchUi(display, action_handler=handle_action)
    ui.draw()

    print("Touchpanel UI + PD-Motor-Test gestartet")
    print("Start: PIN -> Fahren -> Abholung")

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
