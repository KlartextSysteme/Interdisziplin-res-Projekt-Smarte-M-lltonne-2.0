from machine import Pin, PWM
from time import sleep_ms

from config import PIN_BACKLIGHT
from display import BLACK, BLUE, GREEN, ILI9341, ORANGE, RED, WHITE
from touch import XPT2046
from ui import TouchUi


class Touchpanel:
    """
    Kapselt Display, Touch-Auswertung und die vorhandene TouchUi.

    Diese Klasse enthaelt bewusst keine Motor-, Sensor- oder State-Machine-
    Logik. Touch-Aktionen werden nur an den uebergebenen action_handler
    weitergegeben.
    """

    def __init__(self, action_handler=None):
        self.action_handler = action_handler
        self.display = None
        self.touch = None
        self.ui = None
        self.backlight = None
        self.eco = False
        self.last_touch = False

    def init(self):
        self.set_backlight(True)

        self.display = ILI9341()
        self.display.init()

        self.touch = XPT2046(self.display)
        self.ui = TouchUi(self.display, action_handler=self._handle_action)
        self.ui.draw()

    # Backlight ueber PWM (dimmbar): volle Helligkeit = DUTY_NORMAL, Eco = DUTY_ECO.
    BACKLIGHT_FREQ = 1000
    DUTY_NORMAL = 65535
    DUTY_ECO = 26214       # ~40 % Helligkeit

    def _ensure_backlight(self):
        if PIN_BACKLIGHT is None:
            return
        if self.backlight is None:
            self.backlight = PWM(Pin(PIN_BACKLIGHT))
            self.backlight.freq(self.BACKLIGHT_FREQ)

    def _target_duty(self):
        return self.DUTY_ECO if self.eco else self.DUTY_NORMAL

    def set_backlight(self, enabled):
        # enabled=True -> aktuelle Helligkeit (normal/eco), False -> aus.
        self._ensure_backlight()
        if self.backlight is None:
            return
        self.backlight.duty_u16(self._target_duty() if enabled else 0)

    def set_eco(self, enabled):
        self.eco = bool(enabled)
        self._ensure_backlight()
        if self.backlight is not None:
            self.backlight.duty_u16(self._target_duty())

    def toggle_eco(self):
        self.set_eco(not self.eco)

    def _handle_action(self, action):
        if self.action_handler:
            self.action_handler(action)

    def tick(self):
        """
        Muss zyklisch in der Main-Loop aufgerufen werden.
        """
        if self.ui is None or self.touch is None:
            return

        self.ui.tick()
        data = self.touch.read_screen()

        if data is not None:
            x, y, x_raw, y_raw = data
            if not self.last_touch:
                print("Touch:", x, y, "| Raw:", x_raw, y_raw)
                self.ui.handle_touch(x, y)
                self.last_touch = True
        else:
            self.last_touch = False

    def set_status(self, **kwargs):
        if self.ui is not None:
            self.ui.set_status(**kwargs)

    def center_text(self, text, y, color=BLACK, scale=2):
        x = (self.display.width - self.display.text_width(text, scale)) // 2
        self.display.text(text, x, y, color, scale)

    def draw_drive_screen(self, title, subtitle="", color=BLUE):
        self.display.fill_screen(WHITE)
        self.display.rect(4, 4, 312, 232, BLACK, 2)
        self.center_text(title, 78, color, 3)
        if subtitle:
            self.center_text(subtitle, 142, BLACK, 2)

    def draw_result_screen(self, result):
        if result == "street":
            self.draw_drive_screen("ZIEL", "STRASSE ERREICHT", GREEN)
            self.set_status(location="truck", status_kind="full_home", line_ok=True)
        elif result == "obstacle":
            self.draw_drive_screen("STOPP", "HINDERNIS", ORANGE)
            self.set_status(status_kind="obstacle", obstacle_cm=0)
        elif result == "line_lost":
            self.draw_drive_screen("STOPP", "LINIE VERLOREN", RED)
            self.set_status(status_kind="line_lost", line_ok=False)
        elif result == "aborted":
            self.draw_drive_screen("STOPP", "ABBRUCH", RED)
        else:
            self.draw_drive_screen("STOPP", "UNBEKANNT", RED)

        sleep_ms(1800)
        if self.ui is not None:
            self.ui.draw()
