import time

from config import MAINTENANCE_PIN
from display import color565
from wireframe import WireframeRenderer


SCREEN_STATUS = "status"
SCREEN_PIN = "pin"
SCREEN_MENU_1 = "menu_1"
SCREEN_MENU_2 = "menu_2"
SCREEN_SUBMENU = "submenu"
SCREEN_DIAGNOSE = "diagnose"
SCREEN_CONFIRM = "confirm"

CONFIRM_MS = 1_500
SCREEN_W = 320
SCREEN_H = 240

BIN_BODY = color565(104, 106, 102)
BIN_LABEL = color565(204, 204, 200)
ASSET_KEY = color565(255, 0, 255)

# Dynamische Diagnose-Werte (Fuellstand %, Hindernis cm) im Mockup-Look.
# Ziffern-Assets dv_* (weiss auf Panel-Grau) werden rechtsbuendig in die Slots
# geblittet. Panel-Grau exakt aus diagnose_ok.rle gemessen.
DIAG_PANEL_BG = color565(66, 65, 66)
DIAG_VALUE_RIGHT_X = 289
DIAG_FILL_Y = 88
DIAG_OBST_Y = 63
# Zeichen -> (Asset-Name, Breite px), Breiten aus tools/render_diag_digits.py
DIAG_GLYPHS = {
    "0": ("dv_0", 10), "1": ("dv_1", 10), "2": ("dv_2", 10), "3": ("dv_3", 10),
    "4": ("dv_4", 10), "5": ("dv_5", 10), "6": ("dv_6", 10), "7": ("dv_7", 10),
    "8": ("dv_8", 10), "9": ("dv_9", 10),
    "%": ("dv_pct", 14), "-": ("dv_dash", 7),
    "C": ("dv_c", 12), "M": ("dv_m", 14), " ": ("dv_sp", 6),
}

# Sentinel: erlaubt set_status(obstacle_cm=None) als "kein Hindernis" zu setzen,
# waehrend weggelassene Parameter den bisherigen Wert behalten.
_UNSET = object()


class Button:
    def __init__(self, x, y, w, h, action):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.action = action

    def contains(self, x, y):
        return self.x <= x < self.x + self.w and self.y <= y < self.y + self.h


class TouchUi:
    def __init__(self, display, action_handler=None):
        self.d = display
        self.r = WireframeRenderer(display)
        self.action_handler = action_handler
        self.buttons = []

        self.screen = SCREEN_STATUS
        self.pin = ""
        self.menu_page = 1
        self.submenu = None
        self.confirm_asset = "confirm_generic"
        self.confirm_return = SCREEN_MENU_1
        self.confirm_until = 0

        self.status_kind = "full_home"
        self.location = "home"
        self.connected = True
        self.locked = False
        self.fill_level = 54
        self.line_ok = True
        self.obstacle_cm = None
        self.light_mode = False
        # Zuletzt gezeichnete Diagnose-Werte (fuer partielles Live-Refresh).
        self._diag_last_fill = None
        self._diag_last_obstacle = None

    def set_status(
        self,
        fill_level=None,
        connected=None,
        location=None,
        locked=None,
        line_ok=None,
        obstacle_cm=_UNSET,
        status_kind=None,
        light_mode=None,
        **_unused
    ):
        if fill_level is not None:
            self.fill_level = max(0, min(100, int(fill_level)))
        if connected is not None:
            self.connected = bool(connected)
        if location is not None:
            self.location = location
        if locked is not None:
            self.locked = bool(locked)
        if line_ok is not None:
            self.line_ok = bool(line_ok)
        if obstacle_cm is not _UNSET:
            self.obstacle_cm = obstacle_cm
        if status_kind is not None:
            self.status_kind = status_kind
        if light_mode is not None:
            self.light_mode = bool(light_mode)

        # Diagnose wird nicht voll neu gemalt (Flackern); tick() macht das
        # partielle Refresh der beiden Wert-Slots.
        if self.screen == SCREEN_STATUS:
            self.draw()

    def go(self, screen):
        self.screen = screen
        if screen != SCREEN_PIN:
            self.pin = ""
        self.draw()

    def tick(self):
        if self.screen == SCREEN_CONFIRM and self.confirm_until:
            if time.ticks_diff(time.ticks_ms(), self.confirm_until) >= 0:
                self.confirm_until = 0
                self.go(self.confirm_return)

        if self.screen == SCREEN_DIAGNOSE:
            if (self.fill_level != self._diag_last_fill
                    or self.obstacle_cm != self._diag_last_obstacle):
                self._draw_diag_values()

    def handle_touch(self, x, y):
        if self.screen == SCREEN_CONFIRM:
            self.confirm_until = 0
            self.go(self.confirm_return)
            return True

        for button in self.buttons:
            if button.contains(x, y):
                self.handle_action(button.action)
                return True
        return False

    def handle_action(self, action):
        if action == "pin":
            self.go(SCREEN_PIN)
        elif action == "status":
            self.go(SCREEN_STATUS)
        elif action == "toggle_theme":
            self.light_mode = not self.light_mode
            self.draw()
        elif action == "menu_1":
            self.menu_page = 1
            self.go(SCREEN_MENU_1)
        elif action == "menu_2":
            self.menu_page = 2
            self.go(SCREEN_MENU_2)
        elif action == "diag":
            self.go(SCREEN_DIAGNOSE)
        elif action.startswith("submenu:"):
            self.submenu = action.split(":", 1)[1]
            self.go(SCREEN_SUBMENU)
        elif action.startswith("pin_"):
            self._handle_pin_action(action[4:])
        elif action.startswith("do:"):
            self._perform_action(action.split(":", 1)[1])

    def _handle_pin_action(self, key):
        if key == "back":
            self.go(SCREEN_STATUS)
            return
        if key == "clear":
            self.pin = ""
            self.draw_pin()
            return
        if key == "ok":
            if self.pin == MAINTENANCE_PIN:
                self.menu_page = 1
                self.go(SCREEN_MENU_1)
            elif self.pin == "***":
                # Easter-Egg: Party-Modus
                self.pin = ""
                self.go(SCREEN_STATUS)
                if self.action_handler:
                    self.action_handler("party")
            else:
                self.pin = ""
                self.draw_pin()
            return
        if len(self.pin) < len(MAINTENANCE_PIN) and key in "0123456789*#":
            self.pin += key
            self.draw_pin()

    def _perform_action(self, action):
        if action == "lock":
            self.locked = True
            asset = "confirm_locked"
        elif action == "unlock":
            self.locked = False
            asset = "confirm_unlocked"
        elif action == "connect":
            self.connected = True
            asset = "confirm_connected"
        elif action == "disconnect":
            self.connected = False
            asset = "confirm_disconnected"
        elif action in ("report_damage", "report_hygiene"):
            asset = "confirm_report"
        else:
            asset = "confirm_generic"

        if self.action_handler:
            try:
                self.action_handler(action)
            except Exception as exc:
                print("Action failed:", action, exc)

        if action in ("goto_street", "goto_home"):
            self.show_confirm(asset, return_screen=SCREEN_STATUS)
        else:
            self.show_confirm(asset)

    def show_confirm(self, asset="confirm_generic", return_screen=None):
        self.confirm_asset = asset
        self.confirm_return = return_screen or self._return_after_action()
        self.confirm_until = time.ticks_add(time.ticks_ms(), CONFIRM_MS)
        self.go(SCREEN_CONFIRM)

    def _return_after_action(self):
        if self.submenu in ("deckel", "fahren", "problem", "power"):
            return SCREEN_MENU_1
        if self.submenu in ("sicherheit", "verbindung", "energy"):
            return SCREEN_MENU_2
        return SCREEN_STATUS

    def draw(self):
        if self.screen == SCREEN_STATUS:
            self.draw_status()
        elif self.screen == SCREEN_PIN:
            self.draw_pin()
        elif self.screen == SCREEN_MENU_1:
            self.draw_menu(1)
        elif self.screen == SCREEN_MENU_2:
            self.draw_menu(2)
        elif self.screen == SCREEN_SUBMENU:
            self.draw_submenu()
        elif self.screen == SCREEN_DIAGNOSE:
            self.draw_diagnose()
        elif self.screen == SCREEN_CONFIRM:
            self.draw_confirm()

    def draw_status(self):
        self.buttons = [
            Button(256, 176, 64, 64, "pin"),
            Button(0, 176, 64, 64, "toggle_theme"),
        ]
        asset = "status_full_home_clean"
        if self.status_kind == "obstacle":
            asset = "status_obstacle"
        elif self.status_kind == "help":
            asset = "status_help"
        elif self.status_kind == "line_ok":
            asset = "status_line_ok"
        elif self.status_kind == "line_lost":
            asset = "status_line_lost"
        elif self.location == "truck":
            asset = "status_full_truck_clean"
        # Positions-Symbol in der oberen Leiste an die Fahrtrichtung anpassen:
        # unterwegs zur Abholpos (truck) -> Muellwagen statt Haus auf den Fahr-Screens.
        if self.location == "truck" and asset in (
            "status_obstacle",
            "status_line_ok",
            "status_line_lost",
        ):
            asset += "_truck"
        show_fill = asset in ("status_full_home_clean", "status_full_truck_clean")
        if self.light_mode:
            asset += "_light"
        self.r.draw(asset)
        self.draw_theme_toggle()
        if show_fill:
            self.draw_fill_overlay()

    def draw_theme_toggle(self):
        asset = "theme_to_dark" if self.light_mode else "theme_to_light"
        self.r.draw_at_keyed(asset, 10, 190, ASSET_KEY)

    def draw_fill_overlay(self):
        body_asset = "fillbody_base_light" if self.light_mode else "fillbody_base"
        self.r.draw_at_keyed(body_asset, 120, 96, ASSET_KEY)
        self.r.draw_at_keyed("fillbar_" + str(self.fill_level), 120, 96, ASSET_KEY)

        # Repaint the small label field above the fill area in a 4:3 ratio.
        self.d.fill_rect(148, 99, 35, 26, BIN_BODY)
        self.d.fill_rect(151, 101, 28, 21, BIN_LABEL)

        self.r.draw_at_keyed("fill_" + str(self.fill_level), 131, 141, BIN_BODY)

    def draw_pin(self):
        self.buttons = []
        labels = (("1", "2", "3"), ("4", "5", "6"), ("7", "8", "9"), ("*", "0", "#"))
        for row in range(4):
            for col in range(3):
                x = 21 + col * 56
                y = 43 + row * 49
                self.buttons.append(Button(x, y, 44, 38, "pin_" + labels[row][col]))
        self.buttons.append(Button(187, 91, 110, 38, "pin_clear"))
        self.buttons.append(Button(187, 140, 110, 38, "pin_ok"))
        self.buttons.append(Button(187, 189, 110, 35, "pin_back"))
        self.r.draw("pin_" + str(min(len(MAINTENANCE_PIN), len(self.pin))))

    def draw_menu(self, page):
        self.menu_page = page
        self.buttons = [Button(0, 0, 36, 36, "status")]
        items = self._menu_items(page)
        positions = ((40, 36), (166, 36), (40, 126), (166, 126))
        for i, key in enumerate(items):
            x, y = positions[i]
            action = "diag" if key == "diagnose" else "submenu:" + key
            self.buttons.append(Button(x, y, 114, 72, action))
        if page == 1:
            self.buttons.append(Button(290, 82, 30, 76, "menu_2"))
            self.r.draw("menu_1")
        else:
            self.buttons.append(Button(0, 82, 30, 76, "menu_1"))
            self.r.draw("menu_2")

    def draw_submenu(self):
        self.buttons = []
        defs = self._submenu_defs(self.submenu)
        for i, (_label, action) in enumerate(defs):
            self.buttons.append(Button(40 + i * 126, 58, 114, 72, "do:" + action))
        back = "menu_1" if self.submenu in ("deckel", "fahren", "problem", "power") else "menu_2"
        self.buttons.append(Button(92, 188, 136, 46, back))
        self.r.draw(self._submenu_asset(self.submenu))

    def _diag_fill_text(self):
        if self.fill_level is None:
            return "-"
        return str(self.fill_level) + "%"

    def _diag_obstacle_text(self):
        if self.obstacle_cm is None:
            return "-"
        return str(int(self.obstacle_cm)) + " CM"

    def _draw_diag_value(self, text, right_x, top_y):
        # Slot leeren (rechts vom Label, x>=200) und Wert rechtsbuendig blitten.
        self.d.fill_rect(200, top_y - 1, right_x - 200 + 1, 12, DIAG_PANEL_BG)
        total = 0
        for ch in text:
            g = DIAG_GLYPHS.get(ch)
            if g:
                total += g[1]
        x = right_x - total
        for ch in text:
            g = DIAG_GLYPHS.get(ch)
            if not g:
                continue
            self.r.draw_at(g[0], x, top_y)
            x += g[1]

    def _draw_diag_values(self):
        self._draw_diag_value(self._diag_obstacle_text(), DIAG_VALUE_RIGHT_X, DIAG_OBST_Y)
        self._draw_diag_value(self._diag_fill_text(), DIAG_VALUE_RIGHT_X, DIAG_FILL_Y)
        self._diag_last_fill = self.fill_level
        self._diag_last_obstacle = self.obstacle_cm

    def draw_diagnose(self):
        self.buttons = [Button(92, 188, 136, 46, "menu_2")]
        self.r.draw("diagnose_ok" if self.connected and self.line_ok else "diagnose_alert")
        self._draw_diag_values()

    def draw_confirm(self):
        self.buttons = [Button(0, 0, 320, 240, "confirm_back")]
        self.r.draw(self.confirm_asset)

    def _menu_items(self, page):
        if page == 1:
            return ("deckel", "fahren", "problem", "power")
        return ("sicherheit", "verbindung", "energy", "diagnose")

    def _submenu_defs(self, key):
        if key == "deckel":
            return (("OEFFNEN", "lid_open"), ("SCHLIESSEN", "lid_close"))
        if key == "fahren":
            return (("HEIM", "goto_home"), ("ABHOLUNG", "goto_street"))
        if key == "problem":
            return (("SCHADEN", "report_damage"), ("HYGIENE", "report_hygiene"))
        if key == "power":
            return (("AUS", "shutdown"), ("RESET", "factory_reset"))
        if key == "sicherheit":
            return (("ENTSPERREN", "unlock"), ("SPERREN", "lock"))
        if key == "verbindung":
            return (("VERBINDEN", "connect"), ("TRENNEN", "disconnect"))
        if key == "energy":
            return (("ECO", "eco"), ("DOCK", "goto_dock"))
        return (("OK", "noop"), ("OK", "noop"))

    def _submenu_asset(self, key):
        if key == "deckel":
            return "submenu_lid"
        if key == "fahren":
            return "submenu_drive"
        if key == "problem":
            return "submenu_problem"
        if key == "power":
            return "submenu_power"
        if key == "sicherheit":
            return "submenu_security"
        if key == "verbindung":
            return "submenu_connection"
        if key == "energy":
            return "submenu_energy"
        return "menu_1"
