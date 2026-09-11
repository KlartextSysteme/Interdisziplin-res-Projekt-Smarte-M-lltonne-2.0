from time import sleep_ms

from display import BLACK, GREEN, RED, WHITE, YELLOW, ILI9341
from touch import XPT2046


TARGETS = (
    ("TOP LEFT", 24, 24),
    ("TOP RIGHT", 295, 24),
    ("BOTTOM RIGHT", 295, 215),
    ("BOTTOM LEFT", 24, 215),
    ("CENTER", 160, 120),
)


def draw_cross(display, x, y, color):
    display.line(x - 12, y, x + 12, y, color, 2)
    display.line(x, y - 12, x, y + 12, color, 2)
    display.rect(x - 18, y - 18, 36, 36, color, 1)


def draw_screen(display, step):
    display.fill_screen(BLACK)
    display.text("TOUCH KALIBRIERUNG", 28, 10, YELLOW, 2)
    display.text("RAW WERTE WERDEN", 38, 42, WHITE, 1)
    display.text("IN DER KONSOLE GEDRUCKT", 24, 58, WHITE, 1)

    for i, (label, x, y) in enumerate(TARGETS):
        draw_cross(display, x, y, GREEN if i == step else WHITE)

    label, x, y = TARGETS[step]
    display.text(label, 82, 104, YELLOW, 2)
    display.text("TOUCH ZIEL", 102, 142, WHITE, 1)
    display.text(str(step + 1) + "/" + str(len(TARGETS)), 142, 160, WHITE, 2)


def main():
    display = ILI9341()
    display.init()
    touch = XPT2046(display)

    step = 0
    last_touch = False
    samples = []
    draw_screen(display, step)

    print("CALIBRATION_START")
    print("Touch targets in order: TOP_LEFT, TOP_RIGHT, BOTTOM_RIGHT, BOTTOM_LEFT, CENTER")
    print("Output format: SAMPLE label screen_x screen_y raw_x raw_y")

    while True:
        raw = touch.read_raw()
        if raw is None:
            last_touch = False
            sleep_ms(40)
            continue

        if last_touch:
            sleep_ms(40)
            continue

        x_raw, y_raw = raw
        mapped = touch.read_screen()
        if mapped is None:
            last_touch = True
            continue

        x, y, _rx, _ry = mapped
        label, tx, ty = TARGETS[step]
        samples.append((label, tx, ty, x, y, x_raw, y_raw))

        print("SAMPLE", label, "target=", tx, ty, "mapped=", x, y, "raw=", x_raw, y_raw)

        step += 1
        if step >= len(TARGETS):
            print("CALIBRATION_DONE")
            for item in samples:
                label, tx, ty, x, y, rx, ry = item
                print("RESULT", label, "target=", tx, ty, "mapped=", x, y, "raw=", rx, ry)
            display.fill_screen(BLACK)
            display.text("FERTIG", 118, 74, GREEN, 3)
            display.text("WERTE IN KONSOLE", 54, 126, WHITE, 1)
            while True:
                sleep_ms(1000)

        draw_screen(display, step)
        last_touch = True
        sleep_ms(250)


main()
