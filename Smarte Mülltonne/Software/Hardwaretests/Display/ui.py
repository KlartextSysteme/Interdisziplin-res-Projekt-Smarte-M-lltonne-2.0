from config import MAINTENANCE_PIN
from display import BLACK, BLUE, DARK, GRAY, GREEN, ORANGE, RED, WHITE


SCREEN_STATUS = "status"
SCREEN_OPEN = "open"
SCREEN_LID_OPEN = "lid_open"
SCREEN_REPORT = "report"
SCREEN_MAINTENANCE = "maintenance"
SCREEN_REPORTED = "reported"
SCREEN_PIN = "pin"
SCREEN_LOCKED = "locked"


class Button:
    def __init__(self, x, y, w, h, label, action):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.label = label
        self.action = action

    def contains(self, x, y):
        return self.x <= x < self.x + self.w and self.y <= y < self.y + self.h


class TouchUi:
    def __init__(self, display):
        self.d = display
        self.screen = SCREEN_STATUS
        self.fill_level = 68
        self.battery = 92
        self.locked = False
        self.pin = ""
        self.buttons = []

    def set_status(self, fill_level=None, battery=None, locked=None):
        if fill_level is not None:
            self.fill_level = max(0, min(100, int(fill_level)))
        if battery is not None:
            self.battery = max(0, min(100, int(battery)))
        if locked is not None:
            self.locked = bool(locked)
        if self.locked:
            self.screen = SCREEN_LOCKED

    def go(self, screen):
        self.screen = screen
        if screen != SCREEN_PIN:
            self.pin = ""
        self.draw()

    def handle_touch(self, x, y):
        for button in self.buttons:
            if button.contains(x, y):
                self.handle_action(button.action)
                return True
        return False

    def handle_action(self, action):
        if action == "next_from_status":
            self.go(SCREEN_OPEN)
        elif action == "back_status":
            self.go(SCREEN_STATUS)
        elif action == "open_lid":
            # Servo action will be connected in main.py.
            self.go(SCREEN_LID_OPEN)
        elif action == "close_lid_confirm":
            self.go(SCREEN_STATUS)
        elif action == "report":
            self.go(SCREEN_REPORT)
        elif action == "maintenance":
            self.go(SCREEN_PIN)
        elif action == "report_damaged":
            self.go(SCREEN_REPORTED)
        elif action == "report_hygiene":
            self.go(SCREEN_REPORTED)
        elif action == "pin_back":
            self.go(SCREEN_OPEN)
        elif action == "pin_ok":
            if self.pin == MAINTENANCE_PIN:
                self.go(SCREEN_MAINTENANCE)
            else:
                self.pin = ""
                self.draw_pin(error=True)
        elif action.startswith("pin_"):
            if len(self.pin) < 4:
                self.pin += action[-1]
            self.draw_pin()

    def draw(self):
        if self.locked:
            self.draw_locked()
        elif self.screen == SCREEN_STATUS:
            self.draw_status()
        elif self.screen == SCREEN_OPEN:
            self.draw_open()
        elif self.screen == SCREEN_LID_OPEN:
            self.draw_success("DECKEL GEOEFFNET", "SCHLIESSEN", "close_lid_confirm")
        elif self.screen == SCREEN_REPORT:
            self.draw_report()
        elif self.screen == SCREEN_MAINTENANCE:
            self.draw_maintenance()
        elif self.screen == SCREEN_REPORTED:
            self.draw_success("PROBLEM GEMELDET", "SCHLIESSEN", "close_lid_confirm")
        elif self.screen == SCREEN_PIN:
            self.draw_pin()

    def base(self, left="", right=""):
        self.buttons = []
        self.d.fill_screen(WHITE)
        self.d.rect(4, 4, 312, 232, BLACK, 2)
        if left:
            self.d.text(left, 12, 12, BLACK, 1)
            self.d.line(12, 25, 98, 25, BLACK, 1)
        if right:
            tx = 308 - self.d.text_width(right, 1)
            self.d.text(right, tx, 12, BLACK, 1)
            self.d.line(tx, 25, 308, 25, BLACK, 1)

    def draw_arrow_button(self, x, y, direction, action):
        self.buttons.append(Button(x, y, 58, 56, direction, action))
        self.d.rect(x, y, 58, 56, BLACK, 2)
        cy = y + 28
        if direction == "left":
            self.d.line(x + 38, cy, x + 18, cy, BLACK, 4)
            self.d.line(x + 18, cy, x + 30, cy - 12, BLACK, 4)
            self.d.line(x + 18, cy, x + 30, cy + 12, BLACK, 4)
        else:
            self.d.line(x + 20, cy, x + 40, cy, BLACK, 4)
            self.d.line(x + 40, cy, x + 28, cy - 12, BLACK, 4)
            self.d.line(x + 40, cy, x + 28, cy + 12, BLACK, 4)

    def draw_big_button(self, x, y, w, h, label, action, scale=3):
        self.buttons.append(Button(x, y, w, h, label, action))
        self.d.rect(x, y, w, h, BLACK, 2)
        tw = self.d.text_width(label, scale)
        self.d.text(label, x + (w - tw) // 2, y + (h - 7 * scale) // 2, BLACK, scale)

    def draw_status(self):
        self.base()
        self.draw_bin_icon(46, 56, 96, 92)
        self.d.text(str(self.fill_level) + "%", 76, 91, BLACK, 3)
        self.d.text("FUELLSTAND", 54, 128, DARK, 1)
        self.d.line(174, 55, 174, 152, GRAY, 1)
        self.draw_battery_icon(210, 58, self.battery)
        self.d.text(str(self.battery) + "%", 211, 128, BLACK, 2)
        self.d.text("AKKU", 222, 150, DARK, 1)
        self.d.text("FUELLSTAND / AKKU", 54, 190, BLACK, 2)
        self.draw_arrow_button(252, 92, "right", "next_from_status")

    def draw_open(self):
        self.base("FUELLSTAND", "PROBLEM MELDEN")
        self.draw_arrow_button(14, 92, "left", "back_status")
        self.draw_arrow_button(248, 92, "right", "report")
        self.draw_open_bin_icon(112, 58)
        self.draw_big_button(86, 176, 148, 48, "DECKEL", "open_lid", 2)
        self.d.text("OEFFNEN", 116, 202, BLACK, 2)

    def draw_report(self):
        self.base("PROBLEM", "WARTUNG")
        self.draw_arrow_button(14, 92, "left", "back_status")
        self.draw_arrow_button(248, 92, "right", "maintenance")
        self.draw_warning_icon(112, 55)
        self.draw_big_button(72, 176, 176, 48, "PROBLEM", "report_damaged", 2)
        self.d.text("MELDEN", 124, 202, BLACK, 2)

    def draw_maintenance(self):
        self.base("WARTUNG")
        self.draw_arrow_button(14, 42, "left", "back_status")
        self.draw_big_button(108, 38, 190, 62, "BESCHAEDIGT", "report_damaged", 2)
        self.draw_big_button(108, 136, 190, 62, "HYGIENE", "report_hygiene", 2)
        self.draw_big_button(14, 148, 72, 44, "START", "back_status", 1)

    def draw_success(self, message, button_label, action):
        self.base()
        self.draw_check_icon(136, 24, 58)
        tw = self.d.text_width(message, 2)
        self.d.text(message, (320 - tw) // 2, 106, GREEN, 2)
        self.draw_big_button(44, 156, 232, 58, button_label, action, 3)

    def draw_locked(self):
        self.base()
        self.draw_warning_icon(112, 36, RED)
        self.d.text("TONNE GESPERRT", 70, 132, RED, 2)
        self.d.text("BITTE PERSONAL RUFEN", 54, 164, BLACK, 1)

    def draw_pin(self, error=False):
        self.base()
        self.d.text("PIN", 140, 18, BLACK, 2)
        if error:
            self.d.text("FALSCH", 132, 205, RED, 1)
        for i in range(4):
            color = BLACK if i < len(self.pin) else GRAY
            self.d.rect(94 + i * 34, 52, 20, 20, color, 2)
            if i < len(self.pin):
                self.d.fill_rect(99 + i * 34, 57, 10, 10, color)
        labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
        self.buttons = []
        for i, label in enumerate(labels):
            col = i % 5
            row = i // 5
            x = 36 + col * 44
            y = 92 + row * 48
            self.buttons.append(Button(x, y, 34, 34, label, "pin_" + label))
            self.d.rect(x, y, 34, 34, BLUE, 2)
            self.d.text(label, x + 11, y + 8, BLACK, 2)
        self.draw_big_button(242, 54, 58, 42, "OK", "pin_ok", 2)
        self.draw_arrow_button(242, 124, "left", "pin_back")

    def draw_bin_icon(self, x, y, w, h):
        self.d.rect(x + 8, y + 18, w - 16, h - 18, BLACK, 3)
        self.d.line(x + 2, y + 18, x + w - 2, y + 18, BLACK, 3)
        self.d.line(x + 28, y + 4, x + w - 28, y + 4, BLACK, 3)
        self.d.line(x + 28, y + 4, x + 18, y + 18, BLACK, 3)
        self.d.line(x + w - 28, y + 4, x + w - 18, y + 18, BLACK, 3)

    def draw_battery_icon(self, x, y, percent):
        self.d.rect(x, y, 38, 62, BLACK, 3)
        self.d.rect(x + 11, y - 8, 16, 8, BLACK, 2)
        fill_h = int(52 * percent / 100)
        self.d.fill_rect(x + 6, y + 56 - fill_h, 26, fill_h, GRAY)
        self.d.line(x + 6, y + 20, x + 32, y + 20, BLACK, 1)
        self.d.line(x + 6, y + 38, x + 32, y + 38, BLACK, 1)

    def draw_open_bin_icon(self, x, y):
        self.d.rect(x + 20, y + 52, 96, 58, BLACK, 3)
        self.d.line(x + 10, y + 50, x + 126, y + 50, BLACK, 4)
        self.d.line(x + 48, y + 26, x + 88, y + 26, BLACK, 3)
        self.d.line(x + 48, y + 26, x + 36, y + 50, BLACK, 3)
        self.d.line(x + 88, y + 26, x + 100, y + 50, BLACK, 3)
        self.d.line(x + 68, y + 12, x + 68, y - 18, BLACK, 4)
        self.d.line(x + 68, y - 18, x + 54, y - 4, BLACK, 4)
        self.d.line(x + 68, y - 18, x + 82, y - 4, BLACK, 4)

    def draw_warning_icon(self, x, y, color=ORANGE):
        self.d.line(x + 52, y, x, y + 92, color, 4)
        self.d.line(x + 52, y, x + 104, y + 92, color, 4)
        self.d.line(x, y + 92, x + 104, y + 92, color, 4)
        self.d.line(x + 52, y + 28, x + 52, y + 58, BLACK, 5)
        self.d.fill_rect(x + 49, y + 72, 7, 7, BLACK)

    def draw_check_icon(self, x, y, size):
        self.d.rect(x, y, size, size, GREEN, 3)
        self.d.line(x + 14, y + 31, x + 25, y + 43, GREEN, 5)
        self.d.line(x + 25, y + 43, x + 45, y + 16, GREEN, 5)
