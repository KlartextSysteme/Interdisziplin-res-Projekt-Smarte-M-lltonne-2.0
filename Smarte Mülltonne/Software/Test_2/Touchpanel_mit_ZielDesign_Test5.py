from machine import Pin, SPI
from time import sleep_ms


# =========================
# KONFIGURATION
# =========================

SPI_ID = 0

PIN_SCK = 18
PIN_MOSI = 19
PIN_MISO = 16

PIN_DISPLAY_CS = 17
PIN_DISPLAY_DC = 20
PIN_DISPLAY_RST = 21

PIN_TOUCH_CS = 22

WIDTH = 320
HEIGHT = 240

DISPLAY_ROTATION = 0x28

MAINTENANCE_PIN = "1234"


# Touch-Kalibrierung ggf. anpassen
TOUCH_X_MIN = 467
TOUCH_X_MAX = 3606
TOUCH_Y_MIN = 475
TOUCH_Y_MAX = 3789


# =========================
# DISPLAY
# =========================

def color565(r, g, b):
    return ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)


BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)
GRAY = color565(170, 170, 170)
DARK = color565(35, 35, 35)
GREEN = color565(46, 125, 50)
ORANGE = color565(230, 126, 0)
RED = color565(198, 40, 40)
BLUE = color565(0, 120, 255)


FONT = {
    " ": (0, 0, 0, 0, 0),
    "%": (17, 2, 4, 8, 17),
    "/": (1, 2, 4, 8, 16),
    "-": (0, 0, 14, 0, 0),
    ".": (0, 0, 0, 0, 4),
    "0": (14, 17, 19, 21, 14),
    "1": (4, 12, 4, 4, 14),
    "2": (14, 17, 2, 4, 31),
    "3": (30, 1, 14, 1, 30),
    "4": (18, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 30),
    "6": (14, 16, 30, 17, 14),
    "7": (31, 1, 2, 4, 8),
    "8": (14, 17, 14, 17, 14),
    "9": (14, 17, 15, 1, 14),
    "A": (14, 17, 31, 17, 17),
    "B": (30, 17, 30, 17, 30),
    "C": (15, 16, 16, 16, 15),
    "D": (30, 17, 17, 17, 30),
    "E": (31, 16, 30, 16, 31),
    "F": (31, 16, 30, 16, 16),
    "G": (15, 16, 19, 17, 15),
    "H": (17, 17, 31, 17, 17),
    "I": (14, 4, 4, 4, 14),
    "J": (7, 2, 2, 18, 12),
    "K": (17, 18, 28, 18, 17),
    "L": (16, 16, 16, 16, 31),
    "M": (17, 27, 21, 17, 17),
    "N": (17, 25, 21, 19, 17),
    "O": (14, 17, 17, 17, 14),
    "P": (30, 17, 30, 16, 16),
    "R": (30, 17, 30, 18, 17),
    "S": (15, 16, 14, 1, 30),
    "T": (31, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 14),
    "V": (17, 17, 17, 10, 4),
    "W": (17, 17, 21, 27, 17),
    "Y": (17, 10, 4, 4, 4),
    "Z": (31, 2, 4, 8, 31),
}


class ILI9341:
    def __init__(self):
        self.spi = SPI(
            SPI_ID,
            baudrate=20_000_000,
            polarity=0,
            phase=0,
            sck=Pin(PIN_SCK),
            mosi=Pin(PIN_MOSI),
            miso=Pin(PIN_MISO),
        )

        self.cs = Pin(PIN_DISPLAY_CS, Pin.OUT, value=1)
        self.dc = Pin(PIN_DISPLAY_DC, Pin.OUT, value=1)
        self.rst = Pin(PIN_DISPLAY_RST, Pin.OUT, value=1)
        self.touch_cs = Pin(PIN_TOUCH_CS, Pin.OUT, value=1)

        self.width = WIDTH
        self.height = HEIGHT

    def spi_display(self):
        self.spi.init(baudrate=20_000_000, polarity=0, phase=0)

    def spi_touch(self):
        self.spi.init(baudrate=500_000, polarity=0, phase=0)

    def cmd(self, value):
        self.spi_display()
        self.touch_cs.on()
        self.cs.off()
        self.dc.off()
        self.spi.write(bytearray([value]))
        self.cs.on()

    def data(self, values):
        self.spi_display()
        self.touch_cs.on()
        self.cs.off()
        self.dc.on()
        self.spi.write(bytearray(values))
        self.cs.on()

    def reset(self):
        self.rst.on()
        sleep_ms(50)
        self.rst.off()
        sleep_ms(100)
        self.rst.on()
        sleep_ms(150)

    def init(self):
        self.reset()

        self.cmd(0x01)
        sleep_ms(120)

        self.cmd(0x11)
        sleep_ms(120)

        self.cmd(0x3A)
        self.data([0x55])

        self.cmd(0x36)
        self.data([DISPLAY_ROTATION])

        self.cmd(0x29)
        sleep_ms(50)

    def set_window(self, x0, y0, x1, y1):
        self.cmd(0x2A)
        self.data([x0 >> 8, x0 & 255, x1 >> 8, x1 & 255])

        self.cmd(0x2B)
        self.data([y0 >> 8, y0 & 255, y1 >> 8, y1 & 255])

        self.cmd(0x2C)

    def fill_rect(self, x, y, w, h, color):
        if w <= 0 or h <= 0:
            return

        x = max(0, min(self.width - 1, x))
        y = max(0, min(self.height - 1, y))
        w = min(w, self.width - x)
        h = min(h, self.height - y)

        self.set_window(x, y, x + w - 1, y + h - 1)

        hi = color >> 8
        lo = color & 255
        line = bytearray([hi, lo] * w)

        self.spi_display()
        self.touch_cs.on()
        self.cs.off()
        self.dc.on()

        for _ in range(h):
            self.spi.write(line)

        self.cs.on()

    def fill_screen(self, color):
        self.fill_rect(0, 0, self.width, self.height, color)

    def line(self, x0, y0, x1, y1, color, thickness=1):
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        while True:
            self.fill_rect(x0, y0, thickness, thickness, color)

            if x0 == x1 and y0 == y1:
                break

            e2 = 2 * err

            if e2 >= dy:
                err += dy
                x0 += sx

            if e2 <= dx:
                err += dx
                y0 += sy

    def rect(self, x, y, w, h, color, thickness=2):
        self.fill_rect(x, y, w, thickness, color)
        self.fill_rect(x, y + h - thickness, w, thickness, color)
        self.fill_rect(x, y, thickness, h, color)
        self.fill_rect(x + w - thickness, y, thickness, h, color)

    def text(self, text, x, y, color=BLACK, scale=2, spacing=1):
        cx = x

        for ch in text.upper():
            glyph = FONT.get(ch, FONT[" "])

            for col, bits in enumerate(glyph):
                for row in range(7):
                    if bits & (1 << row):
                        self.fill_rect(
                            cx + (6 - row) * scale,
                            y + col * scale,
                            scale,
                            scale,
                            color,
                        )

            cx += (5 + spacing) * scale

    def text_width(self, text, scale=2, spacing=1):
        return len(text) * (5 + spacing) * scale


# =========================
# TOUCH
# =========================

class XPT2046:
    def __init__(self, display):
        self.d = display

    def read_raw_channel(self, command):
        self.d.spi_touch()

        self.d.cs.on()
        self.d.touch_cs.off()

        tx = bytearray([command, 0x00, 0x00])
        rx = bytearray(3)

        self.d.spi.write_readinto(tx, rx)

        self.d.touch_cs.on()

        return ((rx[1] << 8) | rx[2]) >> 3

    def read_raw(self):
        x_raw = self.read_raw_channel(0xD0)
        y_raw = self.read_raw_channel(0x90)

        if x_raw <= 20 or y_raw <= 20:
            return None

        if x_raw >= 4075 or y_raw >= 4075:
            return None

        return x_raw, y_raw

    def map_value(self, value, in_min, in_max, out_min, out_max):
        return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

    def read_screen(self):
        raw = self.read_raw()

        if raw is None:
            return None

        x_raw, y_raw = raw

        x = self.map_value(x_raw, TOUCH_X_MIN, TOUCH_X_MAX, 0, WIDTH)
        y = self.map_value(y_raw, TOUCH_Y_MIN, TOUCH_Y_MAX, 0, HEIGHT)

        x = max(0, min(WIDTH - 1, x))
        y = max(0, min(HEIGHT - 1, y))

        return x, y, x_raw, y_raw


# =========================
# UI / ZIELDESIGN
# =========================

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

    def go(self, screen):
        self.screen = screen

        if screen != SCREEN_PIN:
            self.pin = ""

        self.draw()

    def handle_touch(self, x, y):
        print("Touch UI:", x, y, "Screen:", self.screen)

        # STARTSEITE
        if self.screen == SCREEN_STATUS:
            if 130 <= x <= 210 and 0 <= y <= 60:
                print("STATUS -> OPEN")
                self.go(SCREEN_OPEN)
                return True

        # DECKEL OEFFNEN
        elif self.screen == SCREEN_OPEN:
            # linker Pfeil
            if 100 <= x <= 230 and 180 <= y <= 239:
                print("OPEN -> STATUS")
                self.go(SCREEN_STATUS)
                return True

            # rechter Pfeil
            if 130 <= x <= 210 and 0 <= y <= 60:
                print("OPEN -> REPORT")
                self.go(SCREEN_REPORT)
                return True

            # großer Deckel-Button
            if 0 <= x <= 90 and 60 <= y <= 130:
                print("OPEN -> LID_OPEN")
                self.go(SCREEN_LID_OPEN)
                return True

        # PROBLEM MELDEN
        elif self.screen == SCREEN_REPORT:
            # linker Pfeil
            if 100 <= x <= 230 and 180 <= y <= 239:
                print("REPORT -> OPEN")
                self.go(SCREEN_OPEN)
                return True

            # rechter Pfeil
            if 130 <= x <= 210 and 0 <= y <= 60:
                print("REPORT -> PIN")
                self.go(SCREEN_PIN)
                return True

            # großer Melden-Button
            if 0 <= x <= 90 and 60 <= y <= 130:
                print("REPORT -> REPORTED")
                self.go(SCREEN_REPORTED)
                return True

        elif self.screen == SCREEN_LID_OPEN:
            # Schließen-Button
            if 0 <= x <= 90 and 60 <= y <= 130:
                print("LID_OPEN -> STATUS")
                self.go(SCREEN_STATUS)
                return True

        elif self.screen == SCREEN_REPORTED:
                # Schließen-Button
            if 0 <= x <= 90 and 60 <= y <= 130:
                print("REPORTED -> STATUS")
                self.go(SCREEN_STATUS)
                return True
            
        elif self.screen == SCREEN_PIN:
            # OK-Button
            if 20 <= x <= 60 and 0 <= y <= 40:
                print("PIN -> OK")
                self.handle_action("pin_ok")
                return True

            # linker Pfeil zurück zu Problem melden
            if 100 <= x <= 230 and 180 <= y <= 239:
                print("PIN -> REPORT")
                self.go(SCREEN_REPORT)
                return True

            # Zahlen 1 bis 5 - rechte Touch-Spalte
            if 155 <= x <= 210:
                if 140 <= y <= 175:
                    print("PIN -> 1")
                    self.handle_action("pin_1")
                    return True
                elif 105 <= y <= 139:
                    print("PIN -> 2")
                    self.handle_action("pin_2")
                    return True
                elif 70 <= y <= 104:
                    print("PIN -> 3")
                    self.handle_action("pin_3")
                    return True
                elif 35 <= y <= 69:
                    print("PIN -> 4")
                    self.handle_action("pin_4")
                    return True
                elif 0 <= y <= 34:
                    print("PIN -> 5")
                    self.handle_action("pin_5")
                    return True

            # Zahlen 6 bis 0 - linke Touch-Spalte
            if 75 <= x <= 125:
                if 140 <= y <= 175:
                    print("PIN -> 6")
                    self.handle_action("pin_6")
                    return True
                elif 105 <= y <= 139:
                    print("PIN -> 7")
                    self.handle_action("pin_7")
                    return True
                elif 70 <= y <= 104:
                    print("PIN -> 8")
                    self.handle_action("pin_8")
                    return True
                elif 35 <= y <= 69:
                    print("PIN -> 9")
                    self.handle_action("pin_9")
                    return True
                elif 0 <= y <= 34:
                    print("PIN -> 0")
                    self.handle_action("pin_0")
                    return True
                
        elif self.screen == SCREEN_MAINTENANCE:

            # Zurück-Pfeil / START links unten
            if 210 <= x <= 270 and 180 <= y <= 239:
                print("MAINTENANCE -> STATUS")
                self.go(SCREEN_STATUS)
                return True

            # BESCHAEDIGT oben/rechts
            if 200 <= x <= 300 and 50 <= y <= 110:
                print("MAINTENANCE -> BESCHAEDIGT")
                self.go(SCREEN_REPORTED)
                return True

            # HYGIENE mittig/links
            if 40 <= x <= 130 and 50 <= y <= 110:
                print("MAINTENANCE -> HYGIENE")
                self.go(SCREEN_REPORTED)
                return True

        print("Kein Bereich getroffen")
        return False
    
    def draw_blue_page(self):
        self.buttons = []

        self.d.fill_screen(WHITE)
        self.d.rect(4, 4, 312, 232, BLACK, 2)

        # Blaues Rechteck in der Mitte
        self.d.fill_rect(80, 70, 160, 90, BLUE)

        # Zurück-Pfeil
        self.draw_arrow_button(14, 92, "left", "back_status")

    def handle_action(self, action):
        if action == "next_from_status":
            self.go(SCREEN_OPEN)

        elif action == "next_from_open":
            self.go(SCREEN_REPORT)

        elif action == "next_from_report":
            self.go(SCREEN_PIN)

        elif action == "back_from_open":
            self.go(SCREEN_STATUS)

        elif action == "back_from_report":
            self.go(SCREEN_OPEN)

        elif action == "back_from_pin":
            self.go(SCREEN_REPORT)
        
        elif action == "pin_back":
            self.go(SCREEN_REPORT)

        elif action == "open_lid":
            self.go(SCREEN_LID_OPEN)

        elif action == "close_lid_confirm":
            self.go(SCREEN_STATUS)

        elif action == "report_damaged":
            self.go(SCREEN_REPORTED)

        elif action == "report_hygiene":
            self.go(SCREEN_REPORTED)

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

        self.draw_arrow_button(14, 92, "left", "back_from_open")
        self.buttons.append(Button(0, 60, 100, 140, "back_big", "back_from_open"))

        self.draw_arrow_button(252, 92, "right", "next_from_open")
        self.buttons.append(Button(220, 60, 100, 140, "next_big", "next_from_open"))

        # Testfläche oben, weil deine Touchwerte dort liegen
        self.buttons.append(Button(80, 0, 180, 70, "top_next", "next_from_open"))

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

        self.d.text("PIN", 145, 18, BLACK, 2)

        if error:
            self.d.text("FALSCH", 132, 205, RED, 1)

        # PIN-Felder etwas weiter rechts
        for i in range(4):
            color = BLACK if i < len(self.pin) else GRAY
            self.d.rect(112 + i * 34, 52, 20, 20, color, 2)

            if i < len(self.pin):
                self.d.fill_rect(117 + i * 34, 57, 10, 10, color)

        # Zahlenfeld weiter nach rechts verschoben
        labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
        self.buttons = []

        for i, label in enumerate(labels):
            col = i % 5
            row = i // 5

            x = 92 + col * 44
            y = 92 + row * 48

            self.buttons.append(Button(x, y, 34, 34, label, "pin_" + label))
            self.d.rect(x, y, 34, 34, BLUE, 2)
            self.d.text(label, x + 11, y + 8, BLACK, 2)

        # OK-Button rechts
        self.draw_big_button(240, 178, 72, 42, "OK", "pin_ok", 2)

        # Zurückpfeil jetzt links
        self.draw_arrow_button(14, 92, "left", "pin_back")

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


# =========================
# HAUPTPROGRAMM
# =========================

display = ILI9341()
touch = XPT2046(display)
ui = TouchUi(display)

print("Starte Display + Touch + Zieldesign")

display.init()
ui.draw()

last_touch = False

while True:
    touch_data = touch.read_screen()

    if touch_data is not None:
        x, y, x_raw, y_raw = touch_data

        if not last_touch:
            print("Touch:", x, y, "| Raw:", x_raw, y_raw)
            ui.handle_touch(x, y)
            last_touch = True

    else:
        last_touch = False

    sleep_ms(80)