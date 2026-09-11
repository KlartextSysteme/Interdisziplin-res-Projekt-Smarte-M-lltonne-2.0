from machine import Pin
from time import sleep, sleep_us


class Stepper:
    def __init__(self, dir_pin, step_pin, delay_us=2000, name="STEPPER", debug=True):
        self.dir = Pin(dir_pin, Pin.OUT)
        self.step = Pin(step_pin, Pin.OUT)

        self.delay = delay_us
        self.name = name
        self.debug = debug

        self.step.value(0)

    def step_once(self):
        self.step.value(1)
        sleep_us(self.delay)
        self.step.value(0)
        sleep_us(self.delay)

    def move(self, steps, direction):
        self.dir.value(direction)

        if self.debug:
            print(self.name, "direction:", direction, "steps:", steps)

        for _ in range(steps):
            self.step_once()


# ---------------- TEST ----------------
motor = Stepper(dir_pin=2, step_pin=3, delay_us=2000)

while True:
    print("forwardd")
    motor.move(200, 1)
    sleep(1)

    print("backward")
    motor.move(200, 0)
    sleep(1)