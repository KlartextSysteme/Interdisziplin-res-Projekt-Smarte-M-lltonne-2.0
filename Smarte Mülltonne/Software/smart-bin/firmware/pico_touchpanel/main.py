# =============================================================================
# >>> LIVE-FIRMWARE  ·  Smarte Mülltonne 2.0  ·  Pico (Touchpanel + Fahrlogik) <<<
#
# DAS IST DER PRODUKTIVE, ZULETZT GETESTETE STAND (Inline-Stack).
# GENAU DIESE DATEI WIRD AUF DEN PICO GEFLASHT.
#
# Pfad: Smarte Mülltonne/Software/smart-bin/firmware/pico_touchpanel/main.py
#
# Enthält self-contained: Touchpanel-UI, Liniensensor-PD-Regelung, Motor-
# steuerung, echte Heimfahrt (run_to_home: 180° → zurück → 180°), Sofort-Stopp
# während der Fahrt und den TCP-Bridge-Client (Web-App-Steuerung, Tonne 22).
#
# NICHT verwechseln mit dem MODULAREN Stack unter Quellcode/Client/main.py –
# der läuft NICHT auf dem Pico. Vollständige Einordnung:
# smart-bin/docs/handoff_fahrlogik_2026-06-27.md  (§1 „Welcher Code läuft wirklich")
# =============================================================================

from machine import Pin, PWM
from time import sleep_ms, sleep_us, ticks_diff, ticks_ms, ticks_us

from config import (
    BRIDGE_HOST,
    BRIDGE_PORT,
    ENABLE_TCP_BRIDGE,
    PIN_BACKLIGHT,
    TCP_STATUS_MS,
    WLAN_PASSWORD,
    WLAN_SSID,
)
from display import BLACK, BLUE, GREEN, ILI9341, ORANGE, RED, WHITE
from touch import XPT2046
from ui import SCREEN_STATUS, TouchUi


# ============================================================
# Touchpanel + PD-Schrittmotor-Regelung in einer main.py
#
# Start ueber Touchpanel:
# PIN -> Fahren -> Abholung
#
# Die Motorlogik ist absichtlich direkt in dieser Datei enthalten,
# damit kein zusaetzliches pd_motor_linien_touch.py importiert werden muss.
# ============================================================


display = None
touch = None
ui = None
motors = None
_backlight = None
bridge_client = None
pico_state = "STANDBY"

# Fahr-/Abbruch-Steuerung: erlaubt Stopp per Bridge MITTEN in einer Fahrt.
_driving = False
_abort_drive = False

CMD_GOTO_STREET = "CMD_GOTO_STREET"
CMD_RETURN_HOME = "CMD_RETURN_HOME"
CMD_STOP = "CMD_STOP"


# ---------------- TOUCHPANEL / ANZEIGE ----------------
def set_backlight(enabled):
    global _backlight
    if PIN_BACKLIGHT is None:
        return
    if _backlight is None:
        _backlight = Pin(PIN_BACKLIGHT, Pin.OUT, value=1)
    _backlight.value(1 if enabled else 0)


def show_status(location=None, status_kind=None, **kw):
    """Zeigt den echten Wireframe-Status-Screen (ersetzt die alten Text-Screens).

    location="home" -> Haus-Symbol oben, location="truck" -> Muellwagen-Symbol.
    status_kind="position" laesst draw_status auf das Positions-Vollbild fallen.
    """
    if ui is None:
        return
    if ui.screen != SCREEN_STATUS:
        ui.go(SCREEN_STATUS)
    ui.set_status(location=location, status_kind=status_kind, **kw)


def show_drive_result(result):
    if result == "street":
        # an der Abholposition angekommen -> Muellwagen-Symbol
        show_status(location="truck", status_kind="position")
    elif result == "obstacle":
        show_status(status_kind="obstacle")
    elif result == "line_lost":
        show_status(status_kind="line_lost", line_ok=False)
    else:
        # aborted / unbekannt -> zurueck auf den Positions-Screen
        show_status(status_kind="position")


def send_bridge_line(line):
    if bridge_client is None:
        return
    try:
        bridge_client.send_line(line)
    except Exception as exc:
        print("Bridge send failed:", exc)


def set_pico_state(state, notify=True):
    global pico_state
    pico_state = state
    if notify:
        send_bridge_line("STATUS:" + state)


def get_pico_state():
    return pico_state


def finish_drive_result(result):
    if result == "street":
        set_pico_state("WAIT_AT_STREET", notify=False)
        send_bridge_line("ARRIVED: STREET")
    elif result == "obstacle":
        set_pico_state("OBSTACLE")
    elif result == "line_lost":
        set_pico_state("LINE_LOST")
    elif result == "aborted":
        set_pico_state("USER_PAUSED")
    else:
        set_pico_state("USER_PAUSED")


def _drive_pump():
    # Waehrend einer (blockierenden) Fahrt die Bridge weiter bedienen:
    # eingehende Befehle lesen (z.B. Stopp) + Status senden.
    # Rueckgabe True, wenn die Fahrt abgebrochen werden soll.
    if bridge_client is not None:
        try:
            bridge_client.tick()
        except Exception as exc:
            print("bridge tick failed:", exc)
    return _abort_drive


def start_goto_street(source):
    global _driving, _abort_drive
    _abort_drive = False
    _driving = True
    try:
        _run_goto_street(source)
    finally:
        _driving = False


def _run_goto_street(source):
    if source == "bridge":
        send_bridge_line("ACK " + CMD_GOTO_STREET)
    else:
        send_bridge_line("STATUS:MANUAL_GOTO_STREET_REQUEST")

    set_pico_state("LINE_FOLLOWING")
    # Waehrend der Fahrt zur Abholpos: "Linie erkannt"-Screen mit Muellwagen-Symbol oben
    show_status(location="truck", status_kind="line_ok")
    result = follow_line(leave_pad_first=False)
    finish_drive_result(result)
    show_drive_result(result)


def start_return_home(source):
    global _driving, _abort_drive
    _abort_drive = False
    _driving = True
    try:
        _run_return_home(source)
    finally:
        _driving = False


def _run_return_home(source):
    if source == "bridge":
        send_bridge_line("ACK " + CMD_RETURN_HOME)
    else:
        send_bridge_line("STATUS:MANUAL_RETURN_HOME_REQUEST")

    set_pico_state("LINE_FOLLOWING")
    # Heimwaerts: Haus-Symbol oben + "Linie erkannt"
    show_status(location="home", status_kind="line_ok")
    result = run_to_home()

    if result == "home":
        send_bridge_line("ARRIVED: HOME")
        set_pico_state("STANDBY")
        show_status(location="home", status_kind="position")
    else:
        # obstacle / line_lost / aborted -> bestehende Ergebnis-Behandlung
        finish_drive_result(result)
        show_drive_result(result)


def handle_bridge_command(cmd):
    global _abort_drive
    print("Bridge command:", cmd)

    if _driving:
        # Mitten in einer Fahrt: nur Stopp wird sofort beachtet -> Abbruch.
        if cmd == CMD_STOP:
            send_bridge_line("ACK " + CMD_STOP)
            _abort_drive = True
            if motors is not None:
                motors.stop()
        else:
            print("Befehl waehrend Fahrt ignoriert:", cmd)
        return

    if cmd == CMD_GOTO_STREET:
        start_goto_street("bridge")
        return

    if cmd == CMD_RETURN_HOME:
        start_return_home("bridge")
        return

    if cmd == CMD_STOP:
        send_bridge_line("ACK " + CMD_STOP)
        if motors is not None:
            motors.stop()
        set_pico_state("USER_PAUSED")
        # aktuellen Positions-Screen zeigen (kein Text-Screen)
        show_status()
        return

    print("Unknown bridge command:", cmd)


def create_bridge_client():
    if not ENABLE_TCP_BRIDGE:
        return None
    try:
        from tcp_bridge_client import TcpBridgeClient
    except Exception as exc:
        print("TCP bridge client import failed:", exc)
        return None

    return TcpBridgeClient(
        WLAN_SSID,
        WLAN_PASSWORD,
        BRIDGE_HOST,
        BRIDGE_PORT,
        handle_bridge_command,
        status_provider=get_pico_state,
        status_interval_ms=TCP_STATUS_MS,
    )


# ---------------- MULTIPLEXER CD74HC4067 ----------------
MUX_S0_PIN = 2
MUX_S1_PIN = 3
MUX_S2_PIN = 4
MUX_S3_PIN = 5
MUX_SIGNAL_PIN = 28

s0 = Pin(MUX_S0_PIN, Pin.OUT)
s1 = Pin(MUX_S1_PIN, Pin.OUT)
s2 = Pin(MUX_S2_PIN, Pin.OUT)
s3 = Pin(MUX_S3_PIN, Pin.OUT)
mux_signal = Pin(MUX_SIGNAL_PIN, Pin.IN)

US_TRIGGER_PIN = 6
US_FRONT_CHANNEL = 5
US_STOP_CM = 15
US_INTERVAL_MS = 120
US_TIMEOUT_US = 30000

# Füllstandsanzeige über den vorderen Ultraschallsensor (portiert aus dem
# modularen FuellstandSensor): leerer Abstand -> 0 %, voller Abstand -> 100 %.
FUELLSTAND_LEER_CM = 40.0
FUELLSTAND_VOLL_CM = 5.0
FILL_MEASURE_INTERVAL_MS = 2000

us_trigger = Pin(US_TRIGGER_PIN, Pin.OUT)
us_trigger.value(0)

LINE_CHANNELS = [0, 1, 2, 3, 4]
LINE_WEIGHTS = [2, 1, 0, -1, -2]
LINE_DETECTED_VALUE = 1


# ---------------- MOTOREN ----------------
LEFT_DIR_PIN = 10
LEFT_STEP_PIN = 11
LEFT_ENABLE_PIN = 12

RIGHT_DIR_PIN = 13
RIGHT_STEP_PIN = 8
RIGHT_ENABLE_PIN = 9

ENABLE_ACTIVE_VALUE = 1
LEFT_FORWARD_DIR = 1
RIGHT_FORWARD_DIR = 0

MIN_FREQ = 2000
MAX_FREQ = 4500
LEFT_TRIM_FACTOR = 1.0
RIGHT_TRIM_FACTOR = 1.0

BASE_SPEED = 45
MIN_SPEED = 0
MAX_SPEED = 95

KP = 32
KD = 2
MAX_CORRECTION = 80
MAX_DERIVATIVE_PER_S = 45

CONTROL_INTERVAL_MS = 25
PRINT_INTERVAL_MS = 250
LOST_LINE_STOP_MS = 10000

# 180-Grad-Drehung auf der Stelle (aus dem Handtest kalibriert).
TURN_SPEED = 35
TURN_180_STEPS = 43000
# Kurze Pause (Motoren aus) vor jeder 180-Grad-Drehung, damit sichtbar ist,
# dass das 5-Sensor-End-Pad erkannt wurde.
PIVOT_PAUSE_MS = 1000


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


class PDController:
    def __init__(self, kp, kd, max_correction, max_derivative_per_s):
        self.kp = kp
        self.kd = kd
        self.max_correction = max_correction
        self.max_derivative_per_s = max_derivative_per_s
        self.last_error = 0
        self.last_ms = None

    def calculate(self, current_position, target_position=0, now_ms=None):
        if current_position is None:
            self.reset()
            return 0

        if now_ms is None:
            now_ms = ticks_ms()

        error = current_position - target_position

        if self.last_ms is None:
            dt_s = CONTROL_INTERVAL_MS / 1000.0
        else:
            dt_s = max(0.001, ticks_diff(now_ms, self.last_ms) / 1000.0)

        derivative_per_s = (error - self.last_error) / dt_s
        derivative_per_s = clamp(
            derivative_per_s,
            -self.max_derivative_per_s,
            self.max_derivative_per_s,
        )

        self.last_error = error
        self.last_ms = now_ms

        correction = error * self.kp + derivative_per_s * self.kd
        return clamp(correction, -self.max_correction, self.max_correction)

    def reset(self):
        self.last_error = 0
        self.last_ms = None


class DualStepperMotorPWM:
    def __init__(
        self,
        left_dir_pin,
        left_step_pin,
        left_enable_pin,
        right_dir_pin,
        right_step_pin,
        right_enable_pin,
        min_freq=2000,
        max_freq=4500,
        left_trim_factor=1.0,
        right_trim_factor=1.0,
        enable_active_value=1,
        name="DUAL_STEPPER",
        debug=False,
    ):
        self.left_dir = Pin(left_dir_pin, Pin.OUT)
        self.right_dir = Pin(right_dir_pin, Pin.OUT)
        self.left_step = PWM(Pin(left_step_pin))
        self.right_step = PWM(Pin(right_step_pin))
        self.left_enable = Pin(left_enable_pin, Pin.OUT)
        self.right_enable = Pin(right_enable_pin, Pin.OUT)
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.left_trim_factor = left_trim_factor
        self.right_trim_factor = right_trim_factor
        self.enable_active_value = enable_active_value
        self.disable_value = 0 if enable_active_value == 1 else 1
        self.name = name
        self.debug = debug
        self.last_left_speed = None
        self.last_right_speed = None
        self.stop()

    def enable(self):
        self.left_enable.value(self.enable_active_value)
        self.right_enable.value(self.enable_active_value)

    def disable(self):
        self.left_enable.value(self.disable_value)
        self.right_enable.value(self.disable_value)

    def stop(self):
        self.left_step.duty_u16(0)
        self.right_step.duty_u16(0)
        self.disable()
        self.last_left_speed = 0
        self.last_right_speed = 0
        if self.debug:
            print(self.name, "STOP")

    def _speed_to_frequency(self, speed, trim_factor):
        speed = clamp(speed, 0, 100)
        adjusted_speed = clamp(speed * trim_factor, 0, 100)
        if adjusted_speed <= 0:
            return 0
        return int(
            self.min_freq
            + (self.max_freq - self.min_freq) * (adjusted_speed / 100)
        )

    def drive_forward_differential(self, left_speed, right_speed):
        left_speed = clamp(left_speed, 0, 100)
        right_speed = clamp(right_speed, 0, 100)

        if left_speed <= 0 and right_speed <= 0:
            self.stop()
            return

        left_freq = self._speed_to_frequency(left_speed, self.left_trim_factor)
        right_freq = self._speed_to_frequency(right_speed, self.right_trim_factor)

        self.enable()
        self.left_dir.value(LEFT_FORWARD_DIR)
        self.right_dir.value(RIGHT_FORWARD_DIR)
        sleep_ms(2)

        if left_freq > 0:
            self.left_step.freq(left_freq)
            self.left_step.duty_u16(32768)
        else:
            self.left_step.duty_u16(0)

        if right_freq > 0:
            self.right_step.freq(right_freq)
            self.right_step.duty_u16(32768)
        else:
            self.right_step.duty_u16(0)

        self.last_left_speed = left_speed
        self.last_right_speed = right_speed

        if self.debug:
            print(
                self.name,
                "L",
                round(left_speed, 1),
                left_freq,
                "R",
                round(right_speed, 1),
                right_freq,
            )

    def turn_in_place(self, speed, clockwise=True):
        # Drehung auf der Stelle: eine Kette vorwaerts, die andere rueckwaerts.
        speed = clamp(speed, 0, 100)
        if speed <= 0:
            self.stop()
            return

        left_freq = self._speed_to_frequency(speed, self.left_trim_factor)
        right_freq = self._speed_to_frequency(speed, self.right_trim_factor)

        self.enable()
        if clockwise:
            # Rechtsdrehung: linke Kette vorwaerts, rechte rueckwaerts
            self.left_dir.value(LEFT_FORWARD_DIR)
            self.right_dir.value(1 - RIGHT_FORWARD_DIR)
        else:
            self.left_dir.value(1 - LEFT_FORWARD_DIR)
            self.right_dir.value(RIGHT_FORWARD_DIR)
        sleep_ms(2)

        if left_freq > 0:
            self.left_step.freq(left_freq)
            self.left_step.duty_u16(32768)
        if right_freq > 0:
            self.right_step.freq(right_freq)
            self.right_step.duty_u16(32768)

        self.last_left_speed = speed
        self.last_right_speed = speed

    def steps_to_ms(self, steps, speed):
        freq = self._speed_to_frequency(speed, 1.0)
        if freq <= 0:
            return 0
        return int((steps * 1000) / freq)


def create_motors(debug=False):
    return DualStepperMotorPWM(
        left_dir_pin=LEFT_DIR_PIN,
        left_step_pin=LEFT_STEP_PIN,
        left_enable_pin=LEFT_ENABLE_PIN,
        right_dir_pin=RIGHT_DIR_PIN,
        right_step_pin=RIGHT_STEP_PIN,
        right_enable_pin=RIGHT_ENABLE_PIN,
        min_freq=MIN_FREQ,
        max_freq=MAX_FREQ,
        left_trim_factor=LEFT_TRIM_FACTOR,
        right_trim_factor=RIGHT_TRIM_FACTOR,
        enable_active_value=ENABLE_ACTIVE_VALUE,
        name="Muelltonne",
        debug=debug,
    )


def select_channel(channel):
    s0.value(channel & 1)
    s1.value((channel >> 1) & 1)
    s2.value((channel >> 2) & 1)
    s3.value((channel >> 3) & 1)
    sleep_us(500)


def read_line_sensor(channel):
    select_channel(channel)
    sleep_us(300)
    return mux_signal.value()


def read_line_sensors():
    values = []
    for channel in LINE_CHANNELS:
        values.append(read_line_sensor(channel))
    return values


def measure_ultrasonic(channel):
    select_channel(channel)

    us_trigger.value(0)
    sleep_us(2)
    us_trigger.value(1)
    sleep_us(10)
    us_trigger.value(0)

    start_timeout = ticks_us()
    while mux_signal.value() == 0:
        if ticks_diff(ticks_us(), start_timeout) > US_TIMEOUT_US:
            return None

    start = ticks_us()
    while mux_signal.value() == 1:
        if ticks_diff(ticks_us(), start) > US_TIMEOUT_US:
            return None

    end = ticks_us()
    duration = ticks_diff(end, start)
    return duration / 58.0


def obstacle_detected(distance_cm):
    return distance_cm is not None and distance_cm <= US_STOP_CM


def measure_fill_percent():
    # Füllstand aus dem vorderen Ultraschallsensor: leer -> 0 %, voll -> 100 %.
    # Rueckgabe None bei fehlendem Echo (z.B. Deckel offen / kein Reflex).
    distance = measure_ultrasonic(US_FRONT_CHANNEL)
    if distance is None:
        return None
    if distance >= FUELLSTAND_LEER_CM:
        return 0
    if distance <= FUELLSTAND_VOLL_CM:
        return 100
    span = FUELLSTAND_LEER_CM - FUELLSTAND_VOLL_CM
    ratio = (FUELLSTAND_LEER_CM - distance) / span
    if ratio < 0.0:
        ratio = 0.0
    if ratio > 1.0:
        ratio = 1.0
    return int(round(ratio * 100))


def calculate_line_position(values):
    if all(value == LINE_DETECTED_VALUE for value in values):
        return "street"

    weighted_sum = 0
    active_count = 0

    for index, value in enumerate(values):
        if value == LINE_DETECTED_VALUE:
            weighted_sum += LINE_WEIGHTS[index]
            active_count += 1

    if active_count == 0:
        return None

    return weighted_sum / active_count


def speeds_from_correction(correction):
    left_speed = BASE_SPEED - correction
    right_speed = BASE_SPEED + correction
    left_speed = clamp(left_speed, MIN_SPEED, MAX_SPEED)
    right_speed = clamp(right_speed, MIN_SPEED, MAX_SPEED)
    return left_speed, right_speed


def follow_line(leave_pad_first=False):
    global motors

    if motors is None:
        motors = create_motors(debug=False)

    controller = PDController(KP, KD, MAX_CORRECTION, MAX_DERIVATIVE_PER_S)
    last_control_ms = ticks_ms()
    last_print_ms = ticks_ms()
    last_us_ms = ticks_ms()
    last_line_seen_ms = ticks_ms()
    last_left_speed = BASE_SPEED
    last_right_speed = BASE_SPEED
    front_distance_cm = None

    # Leave-Pad-Guard: Das End-T-Pad zaehlt erst als Ziel, nachdem das
    # Start-Pad einmal verlassen wurde (Linie gesehen). Wichtig fuer die
    # Rueckfahrt, weil die Tonne nach der 180-Grad-Drehung noch auf dem Pad steht.
    armed = not leave_pad_first

    line_values = [0, 0, 0, 0, 0]
    position = None
    correction = 0
    left_speed = 0
    right_speed = 0

    print("Starte Linienfolger (leave_pad_first=" + str(leave_pad_first) + ")")

    try:
        while True:
            now_ms = ticks_ms()

            if ticks_diff(now_ms, last_us_ms) >= US_INTERVAL_MS:
                last_us_ms = now_ms
                front_distance_cm = measure_ultrasonic(US_FRONT_CHANNEL)

            if ticks_diff(now_ms, last_control_ms) >= CONTROL_INTERVAL_MS:
                last_control_ms = now_ms

                # Bridge bedienen (Stopp mitten in der Fahrt moeglich)
                if _drive_pump():
                    motors.stop()
                    print("Fahrt per Stopp abgebrochen")
                    return "aborted"

                line_values = read_line_sensors()
                position = calculate_line_position(line_values)

                if obstacle_detected(front_distance_cm):
                    motors.stop()
                    print("Stopp: Hindernis", front_distance_cm, "cm")
                    return "obstacle"

                if position == "street":
                    if armed:
                        motors.stop()
                        print("Stopp: T-Pad erkannt")
                        return "street"
                    # Noch auf dem Start-Pad -> geradeaus, bis verlassen
                    last_line_seen_ms = now_ms
                    correction = 0
                    left_speed = BASE_SPEED
                    right_speed = BASE_SPEED
                    last_left_speed = left_speed
                    last_right_speed = right_speed
                    motors.drive_forward_differential(BASE_SPEED, BASE_SPEED)
                elif position is not None:
                    armed = True
                    last_line_seen_ms = now_ms
                    correction = controller.calculate(position, 0, now_ms)
                    left_speed, right_speed = speeds_from_correction(correction)
                    last_left_speed = left_speed
                    last_right_speed = right_speed
                    motors.drive_forward_differential(left_speed, right_speed)
                else:
                    controller.reset()
                    correction = 0
                    if ticks_diff(now_ms, last_line_seen_ms) < LOST_LINE_STOP_MS:
                        left_speed = last_left_speed
                        right_speed = last_right_speed
                        motors.drive_forward_differential(left_speed, right_speed)
                    else:
                        motors.stop()
                        print("Stopp: Linie verloren")
                        return "line_lost"

                if ticks_diff(now_ms, last_print_ms) >= PRINT_INTERVAL_MS:
                    last_print_ms = now_ms
                    print(
                        "Sensoren:",
                        line_values,
                        "Position:",
                        position,
                        "Korrektur:",
                        round(correction, 1),
                        "Speed L/R:",
                        round(left_speed, 1),
                        round(right_speed, 1),
                        "armed:",
                        armed,
                        "US vorne:",
                        front_distance_cm,
                    )

    except KeyboardInterrupt:
        return "aborted"
    finally:
        motors.stop()
        print("Linienfolger gestoppt")


def pivot_180():
    # 180-Grad-Drehung auf der Stelle, Dauer aus TURN_180_STEPS kalibriert.
    global motors

    if motors is None:
        motors = create_motors(debug=False)

    # Kurz mit gestoppten Motoren stehen bleiben -> sichtbares Zeichen, dass
    # das 5-Sensor-End-Pad erkannt wurde, bevor sich die Tonne dreht.
    motors.stop()
    pause_start = ticks_ms()
    while ticks_diff(ticks_ms(), pause_start) < PIVOT_PAUSE_MS:
        if _drive_pump():
            print("Drehung per Stopp abgebrochen (Pause)")
            return
        sleep_ms(20)

    duration_ms = motors.steps_to_ms(TURN_180_STEPS, TURN_SPEED)
    print("Starte 180-Grad-Drehung:", duration_ms, "ms")
    start = ticks_ms()
    motors.turn_in_place(TURN_SPEED, clockwise=True)
    try:
        while ticks_diff(ticks_ms(), start) < duration_ms:
            if _drive_pump():
                print("Drehung per Stopp abgebrochen")
                break
            sleep_ms(20)
    except KeyboardInterrupt:
        pass
    finally:
        motors.stop()
    print("180-Grad-Drehung fertig")


def run_to_home():
    # Gegenstueck zu follow_line(goto_street):
    # 1) an der Abholpos 180 Grad drehen
    # 2) der Linie zurueck folgen bis zum Heim-T-Pad
    # 3) am Heim-T-Pad nochmal 180 Grad drehen
    pivot_180()
    if _abort_drive:
        return "aborted"
    result = follow_line(leave_pad_first=True)
    if result != "street":
        return result
    pivot_180()
    if _abort_drive:
        return "aborted"
    return "home"


def handle_action(action):
    print("Touch action:", action)

    if action == "eco":
        set_backlight(False)
        return

    if action in ("connect", "disconnect"):
        return

    if action == "shutdown":
        set_backlight(False)
        return

    if action == "goto_home":
        start_return_home("touchpanel")
        return

    if action == "goto_street":
        start_goto_street("touchpanel")
        return


def main():
    global bridge_client, display, touch, ui

    set_backlight(True)

    display = ILI9341()
    display.init()

    touch = XPT2046(display)
    ui = TouchUi(display, action_handler=handle_action)
    ui.draw()
    bridge_client = create_bridge_client()
    if bridge_client is not None:
        bridge_client.start()

    print("Touchpanel UI + PD-Regler gestartet")
    print("Start der Fahrt: PIN -> Fahren -> Abholung")
    if bridge_client is not None:
        print("TCP bridge client aktiv:", BRIDGE_HOST, BRIDGE_PORT)

    last_touch = False
    last_fill_ms = ticks_ms()
    last_fill_shown = None

    while True:
        ui.tick()
        if bridge_client is not None:
            bridge_client.tick()

        # Füllstand periodisch messen und im Status-Screen anzeigen. Laeuft nur
        # im Leerlauf (waehrend einer Fahrt blockiert diese Schleife ohnehin) und
        # zeichnet nur bei Aenderung neu (kein Flackern).
        if ticks_diff(ticks_ms(), last_fill_ms) >= FILL_MEASURE_INTERVAL_MS:
            last_fill_ms = ticks_ms()
            fill = measure_fill_percent()
            if fill is not None and fill != last_fill_shown and ui is not None:
                last_fill_shown = fill
                ui.set_status(fill_level=fill)

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
