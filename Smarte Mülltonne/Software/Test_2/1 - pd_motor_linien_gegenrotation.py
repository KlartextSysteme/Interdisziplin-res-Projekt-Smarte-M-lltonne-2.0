from machine import Pin, PWM
from time import sleep, sleep_ms, sleep_us, ticks_diff, ticks_ms, ticks_us


# ============================================================
# Linienfolger mit PD-Regler  --  KOPIE mit Gegenrotation
#
# Aenderung ggue. Original:
# - Verkabelung auf den AKTUELLEN Aufbau angepasst (Post-Blast):
#     MUX: S0-S3 = GP1-4, SIG = GP5
#     Motor LINKS  = DIR 13 / STEP 8  / ENABLE 9   (fwd = 0)
#     Motor RECHTS = DIR 10 / STEP 11 / ENABLE 12  (fwd = 1)
# - PD-Vorzeichen +/- (verifiziert korrekt fuer diese Verkabelung).
# - GEGENROTATION im "nur linker Motor"-Fall: Wenn die Korrektur so gross ist,
#   dass NUR das linke Rad fahren wuerde (rechtes Rad = 0), bleibt das LINKE Rad
#   stehen und das RECHTE Rad dreht RUECKWAERTS -> gleiche Drehrichtung, aber
#   ueber den funktionierenden rechten Motor (der linke Treiber schafft das
#   Pivot alleine nicht, auch nicht mit hoeherem Vref).
#   ALLE anderen Korrekturen bleiben unveraendert.
# ============================================================


# ---------------- MULTIPLEXER CD74HC4067 (aktuell) ----------------
MUX_S0_PIN = 1
MUX_S1_PIN = 2
MUX_S2_PIN = 3
MUX_S3_PIN = 4
MUX_SIGNAL_PIN = 5

s0 = Pin(MUX_S0_PIN, Pin.OUT)
s1 = Pin(MUX_S1_PIN, Pin.OUT)
s2 = Pin(MUX_S2_PIN, Pin.OUT)
s3 = Pin(MUX_S3_PIN, Pin.OUT)
mux_signal = Pin(MUX_SIGNAL_PIN, Pin.IN)

US_TRIGGER_PIN = 6
US_FRONT_CHANNEL = 5
US_STOP_CM = 15
US_INTERVAL_MS = 120
US_TIMEOUT_US = 8000

us_trigger = Pin(US_TRIGGER_PIN, Pin.OUT)
us_trigger.value(0)

# C0-C4: Liniensensoren von rechts nach links.
LINE_CHANNELS = [0, 1, 2, 3, 4]
LINE_WEIGHTS = [2, 1, 0, -1, -2]
LINE_DETECTED_VALUE = 1


# ---------------- MOTOREN (aktuell) ----------------
LEFT_DIR_PIN = 13
LEFT_STEP_PIN = 8
LEFT_ENABLE_PIN = 9

RIGHT_DIR_PIN = 10
RIGHT_STEP_PIN = 11
RIGHT_ENABLE_PIN = 12

ENABLE_ACTIVE_VALUE = 1

# Richtungen der Vorwaertsfahrt (aktuell):
LEFT_FORWARD_DIR = 0
RIGHT_FORWARD_DIR = 1


# ---------------- PARAMETER ZUM EINSTELLEN ----------------
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

# Rueckwaerts-Geschwindigkeit des rechten Rads im "nur linker Motor"-Fall.
RIGHT_BACK_SPEED = 55

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
            derivative_per_s, -self.max_derivative_per_s, self.max_derivative_per_s
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
    Zwei Schrittmotoren mit STEP/DIR/ENABLE.
    drive_signed() akzeptiert VORZEICHENBEHAFTETE Speeds: negativ -> Rad
    rueckwaerts (fuer die Gegenrotation).
    """

    def __init__(self):
        self.left_dir = Pin(LEFT_DIR_PIN, Pin.OUT)
        self.right_dir = Pin(RIGHT_DIR_PIN, Pin.OUT)
        self.left_step = PWM(Pin(LEFT_STEP_PIN))
        self.right_step = PWM(Pin(RIGHT_STEP_PIN))
        self.left_enable = Pin(LEFT_ENABLE_PIN, Pin.OUT)
        self.right_enable = Pin(RIGHT_ENABLE_PIN, Pin.OUT)
        self.disable_value = 0 if ENABLE_ACTIVE_VALUE == 1 else 1
        self.stop()

    def enable(self):
        self.left_enable.value(ENABLE_ACTIVE_VALUE)
        self.right_enable.value(ENABLE_ACTIVE_VALUE)

    def disable(self):
        self.left_enable.value(self.disable_value)
        self.right_enable.value(self.disable_value)

    def stop(self):
        self.left_step.duty_u16(0)
        self.right_step.duty_u16(0)
        self.disable()

    def speed_to_frequency(self, speed, trim_factor):
        speed = clamp(abs(speed), 0, 100)
        adjusted_speed = clamp(speed * trim_factor, 0, 100)
        if adjusted_speed <= 0:
            return 0
        return int(MIN_FREQ + (MAX_FREQ - MIN_FREQ) * (adjusted_speed / 100))

    def drive_signed(self, left_speed, right_speed):
        """Vorzeichen = Richtung. Negativ -> dieses Rad rueckwaerts."""
        # Richtung je Rad aus dem Vorzeichen bestimmen.
        left_forward = left_speed >= 0
        right_forward = right_speed >= 0
        left_dir = LEFT_FORWARD_DIR if left_forward else (1 - LEFT_FORWARD_DIR)
        right_dir = RIGHT_FORWARD_DIR if right_forward else (1 - RIGHT_FORWARD_DIR)

        left_freq = self.speed_to_frequency(left_speed, LEFT_TRIM_FACTOR)
        right_freq = self.speed_to_frequency(right_speed, RIGHT_TRIM_FACTOR)

        if left_freq <= 0 and right_freq <= 0:
            self.stop()
            return

        self.enable()
        self.left_dir.value(left_dir)
        self.right_dir.value(right_dir)
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
    return [read_line_sensor(ch) for ch in LINE_CHANNELS]


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
    return ticks_diff(ticks_us(), start) / 58.0


def obstacle_detected(distance_cm):
    return distance_cm is not None and distance_cm <= US_STOP_CM


def calculate_line_position(values):
    if all(v == LINE_DETECTED_VALUE for v in values):
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
    # +/- : verifiziert korrekte Regelrichtung fuer die aktuelle Verkabelung.
    left_speed = BASE_SPEED + correction
    right_speed = BASE_SPEED - correction

    # === SONDERFALL "nur linker Motor" ===
    # Grosse positive Korrektur -> rechtes Rad wuerde stehen, nur links faehrt.
    # Der linke Treiber schafft das Pivot alleine nicht -> stattdessen:
    #   linkes Rad STOP, rechtes Rad RUECKWAERTS (gleiche Drehrichtung).
    if right_speed <= 0:
        return 0.0, -float(RIGHT_BACK_SPEED)

    # Alle anderen Faelle unveraendert.
    left_speed = clamp(left_speed, MIN_SPEED, MAX_SPEED)
    right_speed = clamp(right_speed, MIN_SPEED, MAX_SPEED)
    return left_speed, right_speed


motors = DualStepperMotorPWM()
controller = PDController(KP, KD, MAX_CORRECTION, MAX_DERIVATIVE_PER_S)

last_control_ms = ticks_ms()
last_print_ms = ticks_ms()
last_us_ms = ticks_ms()
last_line_seen_ms = ticks_ms()
last_left_speed = BASE_SPEED
last_right_speed = BASE_SPEED
front_distance_cm = None

print("PD-Linienfolger MIT Gegenrotation (Kopie) - aktuelle Verkabelung")
print("Sonderfall: nur-links -> links STOP, rechts RUECKWAERTS")
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
            elif position == "street":
                controller.reset()
                correction = 0
                left_speed = 0
                right_speed = 0
                motors.stop()
            elif position is not None:
                last_line_seen_ms = now_ms
                correction = controller.calculate(position, 0, now_ms)
                left_speed, right_speed = speeds_from_correction(correction)
                last_left_speed = left_speed
                last_right_speed = right_speed
                motors.drive_signed(left_speed, right_speed)
            else:
                controller.reset()
                correction = 0
                if ticks_diff(now_ms, last_line_seen_ms) < LOST_LINE_STOP_MS:
                    left_speed = last_left_speed
                    right_speed = last_right_speed
                    motors.drive_signed(left_speed, right_speed)
                else:
                    left_speed = 0
                    right_speed = 0
                    motors.stop()

            if ticks_diff(now_ms, last_print_ms) >= PRINT_INTERVAL_MS:
                last_print_ms = now_ms
                lf = motors.speed_to_frequency(left_speed, LEFT_TRIM_FACTOR)
                rf = motors.speed_to_frequency(right_speed, RIGHT_TRIM_FACTOR)
                print(
                    "Sensoren:", line_values,
                    "Position:", position,
                    "Korrektur:", round(correction, 1),
                    "Speed L/R:", round(left_speed, 1), round(right_speed, 1),
                    "Frequenz L/R:", lf, rf,
                    "US vorne:", front_distance_cm,
                )

except KeyboardInterrupt:
    pass
finally:
    motors.stop()
    print("Linienfolger gestoppt")
