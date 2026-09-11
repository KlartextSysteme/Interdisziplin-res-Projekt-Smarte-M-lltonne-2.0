from machine import Pin
from time import sleep, sleep_ms, sleep_us, ticks_diff, ticks_us


# Diese Datei heisst main.py, damit sie auf dem Pico beim Einschalten
# automatisch gestartet wird.


# ---------------- EINSTELLUNGEN ----------------
DEBUG = False
STARTUP_DELAY_S = 2

FORWARD = 1
BACKWARD = 0
LINE_DETECTED = 1
US_LIMIT_CM = 30

MOTOR1_STEPS = 40000
MOTOR2_STEPS = 40000
STEP_DELAY_US = 2


# ---------------- MULTIPLEXER CD74HC4067 ----------------
# S0-S3 steuern den ausgewaehlten Kanal C0-C15.
s0 = Pin(2, Pin.OUT)
s1 = Pin(3, Pin.OUT)
s2 = Pin(4, Pin.OUT)
s3 = Pin(5, Pin.OUT)

# Gemeinsamer Trigger fuer alle Ultraschallsensoren
trigger = Pin(6, Pin.OUT)

# SIG/Z/COM vom Multiplexer am Pico
mux_signal = Pin(28, Pin.IN)

# C0-C4: Liniensensoren 1-5
# C5-C8: Ultraschallsensoren 1-4
LINE_CHANNELS = [0, 1, 2, 3, 4]
US_CHANNELS = [5, 6, 7, 8]


# ---------------- MOTOREN ----------------
MOTOR1_DIR_PIN = 10
MOTOR1_STEP_PIN = 11
MOTOR1_ENABLE_PIN = 12

MOTOR2_DIR_PIN = 13
MOTOR2_STEP_PIN = 14
MOTOR2_ENABLE_PIN = 15


def log(*values):
    if DEBUG:
        print(*values)


def create_status_led():
    try:
        return Pin("LED", Pin.OUT)
    except Exception:
        return Pin(25, Pin.OUT)


status_led = create_status_led()


class Stepper:
    def __init__(self, dir_pin, step_pin, enable_pin, delay_us=2000, name="STEPPER"):
        self.dir = Pin(dir_pin, Pin.OUT)
        self.step = Pin(step_pin, Pin.OUT)
        self.enable = Pin(enable_pin, Pin.OUT)
        self.delay_us = delay_us
        self.name = name

        self.step.value(0)
        self.stop()

    def enable_motor(self):
        self.enable.value(1)

    def stop(self):
        self.step.value(0)
        self.enable.value(0)

    def set_direction(self, direction):
        self.dir.value(direction)

    def step_once(self):
        self.step.value(1)
        sleep_us(self.delay_us)
        self.step.value(0)
        sleep_us(self.delay_us)

    def move(self, steps, direction):
        self.enable_motor()
        self.set_direction(direction)

        log(self.name, "dir:", direction, "steps:", steps)

        for _ in range(steps):
            self.step_once()

        self.stop()


class Robot:
    def __init__(self, motor1, motor2):
        self.m1 = motor1
        self.m2 = motor2

    def stop(self):
        self.m1.stop()
        self.m2.stop()

    def motor1_forward(self):
        log("Motor 1 vorwaerts, Motor 2 stop")
        self.m2.stop()
        self.m1.move(MOTOR1_STEPS, FORWARD)

    def motor2_forward(self):
        log("Motor 2 vorwaerts, Motor 1 stop")
        self.m1.stop()
        self.m2.move(MOTOR2_STEPS, FORWARD)

    def both_forward(self):
        log("Motor 1 + Motor 2 vorwaerts")
        self.move_both(MOTOR1_STEPS, MOTOR2_STEPS, FORWARD, FORWARD)

    def both_backward(self):
        log("Motor 1 + Motor 2 rueckwaerts")
        self.move_both(MOTOR1_STEPS, MOTOR2_STEPS, BACKWARD, BACKWARD)

    def motor1_backward(self):
        log("Motor 1 rueckwaerts, Motor 2 stop")
        self.m2.stop()
        self.m1.move(MOTOR1_STEPS, BACKWARD)

    def motor2_backward(self):
        log("Motor 2 rueckwaerts, Motor 1 stop")
        self.m1.stop()
        self.m2.move(MOTOR2_STEPS, BACKWARD)

    def move_both(self, steps1, steps2, direction1, direction2):
        self.m1.enable_motor()
        self.m2.enable_motor()
        self.m1.set_direction(direction1)
        self.m2.set_direction(direction2)

        max_steps = max(steps1, steps2)
        accumulator1 = 0
        accumulator2 = 0

        for _ in range(max_steps):
            accumulator1 += steps1
            accumulator2 += steps2

            do_step1 = accumulator1 >= max_steps
            do_step2 = accumulator2 >= max_steps

            if do_step1:
                self.m1.step.value(1)
                accumulator1 -= max_steps
            if do_step2:
                self.m2.step.value(1)
                accumulator2 -= max_steps

            sleep_us(STEP_DELAY_US)

            if do_step1:
                self.m1.step.value(0)
            if do_step2:
                self.m2.step.value(0)

            sleep_us(STEP_DELAY_US)

        self.stop()


def select_channel(channel):
    s0.value(channel & 1)
    s1.value((channel >> 1) & 1)
    s2.value((channel >> 2) & 1)
    s3.value((channel >> 3) & 1)
    sleep_ms(10)


def read_line_sensor(channel):
    select_channel(channel)
    sleep_ms(2)
    return mux_signal.value()


def measure_ultrasonic(channel):
    select_channel(channel)

    trigger.value(0)
    sleep_us(2)
    trigger.value(1)
    sleep_us(10)
    trigger.value(0)

    start_timeout = ticks_us()
    while mux_signal.value() == 0:
        if ticks_diff(ticks_us(), start_timeout) > 30000:
            return None

    start = ticks_us()
    while mux_signal.value() == 1:
        if ticks_diff(ticks_us(), start) > 30000:
            return None

    end = ticks_us()
    duration = ticks_diff(end, start)
    return duration / 58.0


def read_line_sensors():
    values = []

    for channel in LINE_CHANNELS:
        values.append(read_line_sensor(channel))

    return values


def read_ultrasonic_sensors():
    distances = []

    for channel in US_CHANNELS:
        distances.append(measure_ultrasonic(channel))
        sleep_ms(80)

    return distances


def is_too_close(distance):
    return distance is not None and distance < US_LIMIT_CM


def startup_signal():
    for _ in range(3):
        status_led.value(1)
        sleep_ms(150)
        status_led.value(0)
        sleep_ms(150)


def heartbeat():
    status_led.value(1)
    sleep_ms(20)
    status_led.value(0)


def run_robot(robot):
    while True:
        heartbeat()

        line_values = read_line_sensors()
        us_values = read_ultrasonic_sensors()

        log("Linien C0-C4:", line_values)
        log("Ultraschall 1-4:", us_values)

        # Ultraschall hat Vorrang vor den Liniensensoren.
        if is_too_close(us_values[0]):
            log("Ultraschall 1 < 30 cm -> Motoren stoppen")
            robot.stop()

        elif is_too_close(us_values[1]):
            log("Ultraschall 2 < 30 cm -> beide Motoren rueckwaerts")
            robot.both_backward()

        elif is_too_close(us_values[2]):
            log("Ultraschall 3 < 30 cm -> Motor 1 rueckwaerts")
            robot.motor1_backward()

        elif is_too_close(us_values[3]):
            log("Ultraschall 4 < 30 cm -> Motor 2 rueckwaerts")
            robot.motor2_backward()

        elif line_values[0] == LINE_DETECTED:
            log("Liniensensor 1 erkannt -> Motor 1 vorwaerts")
            robot.motor1_forward()

        elif line_values[1] == LINE_DETECTED:
            log("Liniensensor 2 erkannt -> Motor 2 vorwaerts")
            robot.motor2_forward()

        elif line_values[2] == LINE_DETECTED:
            log("Liniensensor 3 erkannt -> beide Motoren vorwaerts")
            robot.both_forward()

        elif line_values[3] == LINE_DETECTED:
            log("Liniensensor 4 erkannt -> Motor 1 vorwaerts")
            robot.motor1_forward()

        elif line_values[4] == LINE_DETECTED:
            log("Liniensensor 5 erkannt -> Motor 2 vorwaerts")
            robot.motor2_forward()

        else:
            log("Keine Ausloesung -> Motoren stoppen")
            robot.stop()

        sleep(0.3)


def main():
    sleep(STARTUP_DELAY_S)
    startup_signal()

    motor1 = Stepper(
        dir_pin=MOTOR1_DIR_PIN,
        step_pin=MOTOR1_STEP_PIN,
        enable_pin=MOTOR1_ENABLE_PIN,
        delay_us=STEP_DELAY_US,
        name="Motor 1",
    )
    motor2 = Stepper(
        dir_pin=MOTOR2_DIR_PIN,
        step_pin=MOTOR2_STEP_PIN,
        enable_pin=MOTOR2_ENABLE_PIN,
        delay_us=STEP_DELAY_US,
        name="Motor 2",
    )
    robot = Robot(motor1, motor2)

    trigger.value(0)
    robot.stop()

    log("Autostart: Liniensensoren + Ultraschall + Motoren")
    run_robot(robot)


main()
