from machine import Pin, PWM
from time import sleep, sleep_ms, sleep_us, ticks_diff, ticks_ms, ticks_us


# ============================================================
# Linienfolger mit PD-Regler
# Pico + CD74HC4067 Multiplexer + 2 Schrittmotoren per STEP/DIR
#
# Motoransteuerung passend zu eurem PWM-Testcode:
# links:  DIR GP10, STEP GP11, ENABLE GP12
# rechts: DIR GP13, STEP GP8,  ENABLE GP9
#
# Wichtig:
# Bei Schrittmotoren wird die Geschwindigkeit ueber die STEP-Frequenz
# geregelt. Der PD-Regler veraendert deshalb links/rechts die Frequenz.
# ============================================================


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

# Vorderer Ultraschallsensor:
# Trigger direkt an GP6, Echo ueber Multiplexer C5.
US_TRIGGER_PIN = 6
US_FRONT_CHANNEL = 5
US_LEFT_CHANNEL = 6
US_RIGHT_CHANNEL = 7
US_STOP_CM = 30
US_SIDE_CLEAR_CM = 35
US_INTERVAL_MS = 120
US_TIMEOUT_US = 30000

us_trigger = Pin(US_TRIGGER_PIN, Pin.OUT)
us_trigger.value(0)

# C0-C4: Liniensensoren von rechts nach links.
LINE_CHANNELS = [0, 1, 2, 3, 4]
LINE_WEIGHTS = [2, 1, 0, -1, -2]

# Falls eure Sensoren auf schwarzer Linie 0 statt 1 liefern, hier 0 eintragen.
LINE_DETECTED_VALUE = 1


# ---------------- MOTOREN ----------------
LEFT_DIR_PIN = 10
LEFT_STEP_PIN = 11
LEFT_ENABLE_PIN = 12

RIGHT_DIR_PIN = 13
RIGHT_STEP_PIN = 8
RIGHT_ENABLE_PIN = 9

ENABLE_ACTIVE_VALUE = 1

# Richtungen eurer Vorwaertsfahrt:
# forward: links DIR=0, rechts DIR=1
LEFT_FORWARD_DIR = 1
RIGHT_FORWARD_DIR = 0


# ---------------- PARAMETER ZUM EINSTELLEN ----------------
# Werte aus eurem Motortest.
MIN_FREQ = 2000
MAX_FREQ = 4500
LEFT_TRIM_FACTOR = 1.0
RIGHT_TRIM_FACTOR = 1.0

# Grundgeschwindigkeit in Prozent. Zum ersten Test eher niedrig starten.
BASE_SPEED = 45
MIN_SPEED = 0
MAX_SPEED = 95

# PD-Regler:
# Sensorposition liegt grob zwischen -2 und +2.
# Korrektur wird in Prozentpunkten auf links/rechts addiert/subtrahiert.
KP = 32
KD = 2
MAX_CORRECTION = 60
MAX_DERIVATIVE_PER_S = 45

CONTROL_INTERVAL_MS = 25
PRINT_INTERVAL_MS = 250

# Wenn die Linie verloren geht, faehrt der Roboter kurz mit der zuletzt
# berechneten Geschwindigkeit weiter. Danach stoppt er.
LOST_LINE_STOP_MS = 10000

# Zeitbasierte Hindernisumfahrung. Diese Werte muessen am Fahrzeug
# praktisch kalibriert werden.
OBSTACLE_WAIT_MS = 10000
AVOID_SPEED = 35
AVOID_TURN_SPEED = 35
AVOID_TURN_90_MS = 850
AVOID_FORWARD_EXTRA_MS = 900
AVOID_SIDE_MAX_MS = 5000
AVOID_LINE_SEARCH_MAX_MS = 6000


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
    """
    Ansteuerung fuer zwei Schrittmotoren mit STEP/DIR/ENABLE-Treibern.
    Die STEP-Signale werden per PWM erzeugt.
    """

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

    def _drive_with_dirs(self, left_speed, right_speed, left_dir, right_dir):
        left_speed = clamp(left_speed, 0, 100)
        right_speed = clamp(right_speed, 0, 100)

        if left_speed <= 0 and right_speed <= 0:
            self.stop()
            return

        left_freq = self._speed_to_frequency(left_speed, self.left_trim_factor)
        right_freq = self._speed_to_frequency(right_speed, self.right_trim_factor)

        self.enable()
        self.left_dir.value(left_dir)
        self.right_dir.value(right_dir)

        # Kleine Pause, damit Richtung/Enable sicher gesetzt sind.
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

    def drive_forward_differential(self, left_speed, right_speed):
        self._drive_with_dirs(
            left_speed,
            right_speed,
            LEFT_FORWARD_DIR,
            RIGHT_FORWARD_DIR,
        )

    def forward(self, speed):
        self.drive_forward_differential(speed, speed)

    def backward(self, speed):
        self._drive_with_dirs(
            speed,
            speed,
            1 - LEFT_FORWARD_DIR,
            1 - RIGHT_FORWARD_DIR,
        )

    def turn_left(self, speed):
        self._drive_with_dirs(
            speed,
            speed,
            1 - LEFT_FORWARD_DIR,
            RIGHT_FORWARD_DIR,
        )

    def turn_right(self, speed):
        self._drive_with_dirs(
            speed,
            speed,
            LEFT_FORWARD_DIR,
            1 - RIGHT_FORWARD_DIR,
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
    # Symmetrische PD-Korrektur:
    # Ein Motor wird langsamer, der andere wird im gleichen Mass schneller.
    left_speed = BASE_SPEED - correction
    right_speed = BASE_SPEED + correction

    left_speed = clamp(left_speed, MIN_SPEED, MAX_SPEED)
    right_speed = clamp(right_speed, MIN_SPEED, MAX_SPEED)

    return left_speed, right_speed


def side_is_clear(distance_cm):
    return distance_cm is None or distance_cm > US_SIDE_CLEAR_CM


def any_line_detected():
    values = read_line_sensors()
    position = calculate_line_position(values)
    return position is not None


def drive_timed(mode, duration_ms, speed=AVOID_SPEED, stop_on_line=False):
    start_ms = ticks_ms()

    if mode == "forward":
        motors.forward(speed)
    elif mode == "backward":
        motors.backward(speed)
    elif mode == "left":
        motors.turn_left(speed)
    elif mode == "right":
        motors.turn_right(speed)
    else:
        motors.stop()
        return False

    while ticks_diff(ticks_ms(), start_ms) < duration_ms:
        if stop_on_line and any_line_detected():
            motors.stop()
            return True
        sleep_ms(25)

    motors.stop()
    return False


def drive_until_side_clear(side_channel, max_ms):
    start_ms = ticks_ms()
    motors.forward(AVOID_SPEED)

    while ticks_diff(ticks_ms(), start_ms) < max_ms:
        distance = measure_ultrasonic(side_channel)
        if side_is_clear(distance):
            motors.stop()
            return True
        sleep_ms(25)

    motors.stop()
    return False


def choose_avoidance_side():
    left_distance = measure_ultrasonic(US_LEFT_CHANNEL)
    right_distance = measure_ultrasonic(US_RIGHT_CHANNEL)

    left_clear = side_is_clear(left_distance)
    right_clear = side_is_clear(right_distance)

    print(
        "Umfahrung pruefen - US links:",
        left_distance,
        "US rechts:",
        right_distance,
    )

    if right_clear and (not left_clear or right_distance is None):
        return "right"
    if right_clear and left_clear and left_distance is not None and right_distance is not None:
        if right_distance >= left_distance:
            return "right"
        return "left"
    if right_clear:
        return "right"
    if left_clear:
        return "left"

    return None


def avoid_obstacle(side):
    print("Starte Hindernisumfahrung:", side)

    if side == "right":
        first_turn = "right"
        second_turn = "left"
        third_turn = "left"
        final_turn = "right"
        side_channel = US_LEFT_CHANNEL
    else:
        first_turn = "left"
        second_turn = "right"
        third_turn = "right"
        final_turn = "left"
        side_channel = US_RIGHT_CHANNEL

    drive_timed(first_turn, AVOID_TURN_90_MS, AVOID_TURN_SPEED)
    drive_until_side_clear(side_channel, AVOID_SIDE_MAX_MS)
    drive_timed("forward", AVOID_FORWARD_EXTRA_MS, AVOID_SPEED)
    drive_timed(second_turn, AVOID_TURN_90_MS, AVOID_TURN_SPEED)
    drive_timed("forward", AVOID_FORWARD_EXTRA_MS, AVOID_SPEED)
    drive_timed(third_turn, AVOID_TURN_90_MS, AVOID_TURN_SPEED)
    line_found = drive_timed(
        "forward",
        AVOID_LINE_SEARCH_MAX_MS,
        AVOID_SPEED,
        stop_on_line=True,
    )

    if line_found:
        drive_timed(final_turn, AVOID_TURN_90_MS, AVOID_TURN_SPEED)
        print("Linie nach Umfahrung wiedergefunden")
        return True

    print("Linie nach Umfahrung nicht gefunden")
    return False


motors = DualStepperMotorPWM(
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
    debug=False,
)

controller = PDController(KP, KD, MAX_CORRECTION, MAX_DERIVATIVE_PER_S)

last_control_ms = ticks_ms()
last_print_ms = ticks_ms()
last_us_ms = ticks_ms()
last_line_seen_ms = ticks_ms()
last_position = 0
last_left_speed = BASE_SPEED
last_right_speed = BASE_SPEED
front_distance_cm = None
obstacle_wait_start_ms = None

print("Starte Linienfolger mit PD-Regler und PWM-Schrittmotorsteuerung")
print("MUX: S0 GP2, S1 GP3, S2 GP4, S3 GP5, SIG GP28")
print("Liniensensoren: C0-C4")
print("Ultraschall vorne: Trigger GP6, Echo C5")
print("Ultraschall links/rechts: Echo C6/C7, nur bei Umfahrung aktiv")
print("Motor links:  DIR GP10, STEP GP11, ENABLE GP12")
print("Motor rechts: DIR GP13, STEP GP8,  ENABLE GP9")
print("Zum Stoppen: Strg+C / Reset")
print("----------------------------------------")

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
                controller.reset()
                correction = 0
                left_speed = 0
                right_speed = 0
                motors.stop()

                if obstacle_wait_start_ms is None:
                    obstacle_wait_start_ms = now_ms
                    print("Hindernis vorne erkannt - warte 10 Sekunden")

                elif ticks_diff(now_ms, obstacle_wait_start_ms) >= OBSTACLE_WAIT_MS:
                    avoidance_side = choose_avoidance_side()

                    if avoidance_side is None:
                        print("Hindernis nicht umfahrbar")
                        obstacle_wait_start_ms = now_ms
                    else:
                        avoid_obstacle(avoidance_side)
                        obstacle_wait_start_ms = None
                        front_distance_cm = None
                        last_line_seen_ms = ticks_ms()
                        last_left_speed = BASE_SPEED
                        last_right_speed = BASE_SPEED

            elif position == "street":
                obstacle_wait_start_ms = None
                controller.reset()
                correction = 0
                left_speed = 0
                right_speed = 0
                motors.stop()

            elif position is not None:
                obstacle_wait_start_ms = None
                last_position = position
                last_line_seen_ms = now_ms

                correction = controller.calculate(position, 0, now_ms)
                left_speed, right_speed = speeds_from_correction(correction)
                last_left_speed = left_speed
                last_right_speed = right_speed
                motors.drive_forward_differential(left_speed, right_speed)

            else:
                obstacle_wait_start_ms = None
                controller.reset()
                correction = 0

                if ticks_diff(now_ms, last_line_seen_ms) < LOST_LINE_STOP_MS:
                    left_speed = last_left_speed
                    right_speed = last_right_speed
                    motors.drive_forward_differential(left_speed, right_speed)
                else:
                    left_speed = 0
                    right_speed = 0
                    motors.stop()

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
    pass
finally:
    motors.stop()
    print("Linienfolger gestoppt")
