from machine import Pin
from time import sleep_us, sleep_ms


class DualStepper:
    def __init__(self,
                 left_dir_pin,
                 left_step_pin,
                 left_enable_pin,
                 right_dir_pin,
                 right_step_pin,
                 right_enable_pin,
                 enable_active_value=1,
                 pulse_width_us=10):

        self.left_dir = Pin(left_dir_pin, Pin.OUT)
        self.left_step = Pin(left_step_pin, Pin.OUT)
        self.left_enable = Pin(left_enable_pin, Pin.OUT)

        self.right_dir = Pin(right_dir_pin, Pin.OUT)
        self.right_step = Pin(right_step_pin, Pin.OUT)
        self.right_enable = Pin(right_enable_pin, Pin.OUT)

        self.enable_active_value = enable_active_value
        self.disable_value = 0 if enable_active_value == 1 else 1

        self.pulse_width_us = pulse_width_us

        self.left_step.value(0)
        self.right_step.value(0)

        self.disable()

    def enable(self):
        self.left_enable.value(self.enable_active_value)
        self.right_enable.value(self.enable_active_value)
        sleep_ms(10)

    def disable(self):
        self.left_step.value(0)
        self.right_step.value(0)
        self.left_enable.value(self.disable_value)
        self.right_enable.value(self.disable_value)

    def step_both(self, delay_us):
        self.left_step.value(1)
        self.right_step.value(1)

        sleep_us(self.pulse_width_us)

        self.left_step.value(0)
        self.right_step.value(0)

        sleep_us(delay_us)

    def move_both(self,
                  steps,
                  left_direction,
                  right_direction,
                  start_delay_us=8000,
                  run_delay_us=3000,
                  ramp_steps=200,
                  disable_after=True):

        self.enable()

        self.left_dir.value(left_direction)
        self.right_dir.value(right_direction)

        sleep_ms(5)

        print("Move both:", steps, "steps")
        print("Left dir:", left_direction, "Right dir:", right_direction)

        for i in range(steps):
            delay_us = run_delay_us

            # Beschleunigungsrampe am Anfang
            if i < ramp_steps:
                delay_us = start_delay_us - int((start_delay_us - run_delay_us) * i / ramp_steps)

            # Bremsrampe am Ende
            elif i > steps - ramp_steps:
                remaining = steps - i
                delay_us = start_delay_us - int((start_delay_us - run_delay_us) * remaining / ramp_steps)

            self.step_both(delay_us)

        if disable_after:
            self.disable()

    def geradeaus(self, steps):
        self.move_both(steps, 1, 1)

    def rueckwaerts(self, steps):
        self.move_both(steps, 0, 0)

    def drehung_links(self, steps):
        self.move_both(steps, 0, 1)

    def drehung_rechts(self, steps):
        self.move_both(steps, 1, 0)


# ---------------- TEST ----------------

motors = DualStepper(
    left_dir_pin=10,
    left_step_pin=11,
    left_enable_pin=12,

    right_dir_pin=13,
    right_step_pin=14,
    right_enable_pin=15,

    # Bei eurem Aufbau scheint 1 = aktiv zu sein
    enable_active_value=1
)


while True:
    print("Beide Motoren vorwärts")
    motors.geradeaus(1000)

    sleep_ms(1500)

    print("Beide Motoren rückwärts")
    motors.rueckwaerts(1000)

    sleep_ms(1500)