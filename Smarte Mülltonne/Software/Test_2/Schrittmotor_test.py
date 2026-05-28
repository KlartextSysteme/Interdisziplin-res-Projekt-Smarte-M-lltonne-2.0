from machine import Pin
from time import sleep, sleep_us


class Stepper:
    def __init__(
        self,
        dir_pin,
        step_pin,
        enable_pin,
        mode0_pin=None,
        mode1_pin=None,
        mode2_pin=None,
        delay_us=2000,
        name="STEPPER",
        debug=True
    ):

        # ---------------- CONTROL ----------------
        self.dir = Pin(dir_pin, Pin.OUT)
        self.step = Pin(step_pin, Pin.OUT)
        self.enable = Pin(enable_pin, Pin.OUT)

        # ---------------- MICROSTEP MODE ----------------
        self.mode0 = Pin(mode0_pin, Pin.OUT) if mode0_pin is not None else None
        self.mode1 = Pin(mode1_pin, Pin.OUT) if mode1_pin is not None else None
        self.mode2 = Pin(mode2_pin, Pin.OUT) if mode2_pin is not None else None

        self.delay = delay_us
        self.name = name
        self.debug = debug

        self.step.value(0)

        # Motor deaktiviert starten
        self.disable()

    # ---------------------------------------------------
    # ENABLE / DISABLE
    # ---------------------------------------------------

    def enable_motor(self):
        self.enable.value(0)   # LOW = aktiv

    def disable(self):
        self.enable.value(1)   # HIGH = deaktiviert

    # ---------------------------------------------------
    # MICROSTEPPING
    # ---------------------------------------------------

    def set_mode(self, mode):

        # Full Step
        if mode == "FULL":
            m0, m1, m2 = 0, 0, 0

        # Half Step
        elif mode == "HALF":
            m0, m1, m2 = 1, 0, 0

        # 1/4 Step
        elif mode == "QUARTER":
            m0, m1, m2 = 0, 1, 0

        # 1/8 Step
        elif mode == "EIGHTH":
            m0, m1, m2 = 1, 1, 0

        # 1/16 Step
        elif mode == "SIXTEENTH":
            m0, m1, m2 = 0, 0, 1

        # 1/32 Step
        elif mode == "THIRTYSECOND":
            m0, m1, m2 = 1, 0, 1

        else:
            raise ValueError("Unknown mode")

        if self.mode0:
            self.mode0.value(m0)

        if self.mode1:
            self.mode1.value(m1)

        if self.mode2:
            self.mode2.value(m2)

        if self.debug:
            print(self.name, "Mode:", mode)

    # ---------------------------------------------------
    # STEP
    # ---------------------------------------------------

    def step_once(self):
        self.step.value(1)
        sleep_us(self.delay)

        self.step.value(0)
        sleep_us(self.delay)

    # ---------------------------------------------------
    # MOVE
    # ---------------------------------------------------

    def move(self, steps, direction):

        self.enable_motor()

        self.dir.value(direction)

        if self.debug:
            print(self.name, "dir:", direction, "steps:", steps)

        for _ in range(steps):
            self.step_once()

        self.disable()


# =======================================================
# MOTOR SETUP
# =======================================================

motor1 = Stepper(
    dir_pin=10,
    step_pin=11,
    enable_pin=12,

    # MODE PINS
    mode0_pin=2,
    mode1_pin=3,
    mode2_pin=4,

    delay_us=2000,
    name="Motor 1"
)

motor2 = Stepper(
    dir_pin=13,
    step_pin=14,
    enable_pin=15,

    mode0_pin=5,
    mode1_pin=6,
    mode2_pin=7,

    delay_us=2000,
    name="Motor 2"
)

# =======================================================
# MICROSTEP MODE SETZEN
# =======================================================

motor1.set_mode("FULL")
motor2.set_mode("FULL")

# Andere Modi:
# "HALF"
# "QUARTER"
# "EIGHTH"
# "SIXTEENTH"
# "THIRTYSECOND"

# =======================================================
# TEST
# =======================================================

while True:

    print("Motor 1 forward")
    motor1.move(200, 1)
    sleep(1)

    print("Motor 1 backward")
    motor1.move(200, 0)
    sleep(1)

    print("Motor 2 forward")
    motor2.move(200, 1)
    sleep(1)

    print("Motor 2 backward")
    motor2.move(200, 0)
    sleep(1)