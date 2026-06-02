from machine import Pin
from time import sleep, sleep_us


class Stepper:
    def __init__(self, dir_pin, step_pin, enable_pin, delay_us=2000, name="STEPPER", debug=True):
        self.dir = Pin(dir_pin, Pin.OUT)
        self.step = Pin(step_pin, Pin.OUT)
        self.enable = Pin(enable_pin, Pin.OUT)

        self.delay = delay_us
        self.name = name
        self.debug = debug

        self.step.value(0)
        self.disable()  # Start: Motor aus

    # -------- ENABLE / DISABLE --------
    def enable_motor(self):
        self.enable.value(1)   # A4988: LOW = ON

    def disable(self):
        self.enable.value(0)   # A4988: HIGH = OFF

    # -------- STEP --------
    def step_once(self):
        self.step.value(1)
        sleep_us(self.delay)
        self.step.value(0)
        sleep_us(self.delay)

    def move(self, steps, direction):
        self.enable_motor()     # Motor einschalten

        self.dir.value(direction)

        if self.debug:
            print(self.name, "dir:", direction, "steps:", steps)

        # while True:
        #     self.step(200)
        #     sleep(1)
        for _ in range(steps):
            self.step_once()

        self.disable()          # Motor wieder ausschalten


# ---------------- TEST ----------------

motor1 = Stepper(dir_pin=10, step_pin=11, enable_pin=12, delay_us=2, name="Motor 1")
motor2 = Stepper(dir_pin=13, step_pin=14, enable_pin=15, delay_us=2000, name="Motor 2")

while True:
    print("Motor 1 forward")
    motor1.move(2000, 0)
    sleep(1)

    print("Motor 1 backward")
    motor1.move(2000, 0)
    sleep(1)

    print("Motor 2 forward")
    motor2.move(200, 1)
    sleep(1)

    print("Motor 2 backward")
    motor2.move(200, 0)
    sleep(1)

    #PWM Objekt hinzufügen für delay, um genauer arbeiten zu können