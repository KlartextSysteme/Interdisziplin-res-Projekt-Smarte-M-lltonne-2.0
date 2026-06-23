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
from ui import TouchUi


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


def center_text(text, y, color=BLACK, scale=2):
    x = (display.width - display.text_width(text, scale)) // 2
    display.text(text, x, y, color, scale)


def draw_drive_screen(title, subtitle="", color=BLUE):
    display.fill_screen(WHITE)
    display.rect(4, 4, 312, 232, BLACK, 2)
    center_text(title, 78, color, 3)
    if subtitle:
        center_text(subtitle, 142, BLACK, 2)


def draw_result_screen(result):
    if result == "street":
        draw_drive_screen("ZIEL", "STRASSE ERREICHT", GREEN)
        ui.set_status(location="truck", status_kind="full_home", line_ok=True)
    elif result == "obstacle":
        draw_drive_screen("STOPP", "HINDERNIS", ORANGE)
        ui.set_status(status_kind="obstacle", obstacle_cm=0)
    elif result == "line_lost":
        draw_drive_screen("STOPP", "LINIE VERLOREN", RED)
        ui.set_status(status_kind="line_lost", line_ok=False)
    elif result == "aborted":
        draw_drive_screen("STOPP", "ABBRUCH", RED)
    else:
        draw_drive_screen("STOPP", "UNBEKANNT", RED)
    sleep_ms(1800)


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


def start_goto_street(source):
    if source == "bridge":
        send_bridge_line("ACK " + CMD_GOTO_STREET)
    else:
        send_bridge_line("STATUS:MANUAL_GOTO_STREET_REQUEST")

    set_pico_state("LINE_FOLLOWING")
    draw_drive_screen("FAEHRT", "PD REGLER AKTIV", BLUE)
    result = run_to_street()
    finish_drive_result(result)
    draw_result_screen(result)


def handle_bridge_command(cmd):
    print("Bridge command:", cmd)

    if cmd == CMD_GOTO_STREET:
        start_goto_street("bridge")
        return

    if cmd == CMD_RETURN_HOME:
        send_bridge_line("ACK " + CMD_RETURN_HOME)
        draw_drive_screen("TEST", "HEIMFAHRT NICHT AKTIV", ORANGE)
        set_pico_state("STANDBY")
        send_bridge_line("ARRIVED: HOME")
        sleep_ms(1400)
        return

    if cmd == CMD_STOP:
        send_bridge_line("ACK " + CMD_STOP)
        if motors is not None:
            motors.stop()
        set_pico_state("USER_PAUSED")
        draw_drive_screen("STOPP", "PAUSIERT", ORANGE)
        sleep_ms(900)
        if ui is not None:
            ui.draw()
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
MAX_CORRECTION = 60
MAX_DERIVATIVE_PER_S = 45

CONTROL_INTERVAL_MS = 25
PRINT_INTERVAL_MS = 250
LOST_LINE_STOP_MS = 10000


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


def run_to_street():
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

    line_values = [0, 0, 0, 0, 0]
    position = None
    correction = 0
    left_speed = 0
    right_speed = 0

    print("Starte Linienfolger per Touchpanel")

    try:
        while True:
            now_ms = ticks_ms()

            if ticks_diff(now_ms, last_us_ms) >= US_INTERVAL_MS:
                last_us_ms = now_ms
                front_distance_cm = measure_ultrasonic(US_FRONT_CHANNEL)

            if ticks_diff(now_ms, last_control_ms) >= CONTROL_INTERVAL_MS:
                last_control_ms = now_ms
                line_values = read_line_sensors()
                position = calculate_line_position(line_values)

                if obstacle_detected(front_distance_cm):
                    motors.stop()
                    print("Stopp: Hindernis", front_distance_cm, "cm")
                    return "obstacle"

                if position == "street":
                    motors.stop()
                    print("Stopp: Strasse erkannt")
                    return "street"

                if position is not None:
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
                    left_freq = motors._speed_to_frequency(
                        left_speed,
                        motors.left_trim_factor,
                    )
                    right_freq = motors._speed_to_frequency(
                        right_speed,
                        motors.right_trim_factor,
                    )
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
                        "Frequenz L/R:",
                        left_freq,
                        right_freq,
                        "US vorne:",
                        front_distance_cm,
                    )

    except KeyboardInterrupt:
        return "aborted"
    finally:
        motors.stop()
        print("Linienfolger gestoppt")


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
        draw_drive_screen("TEST", "HEIMFAHRT NICHT AKTIV", ORANGE)
        send_bridge_line("STATUS:MANUAL_RETURN_HOME_REQUEST")
        sleep_ms(1400)
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

    while True:
        ui.tick()
        if bridge_client is not None:
            bridge_client.tick()
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
