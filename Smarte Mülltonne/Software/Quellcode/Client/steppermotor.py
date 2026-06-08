from machine import Pin
from time import sleep_us


class DualStepper:
    def __init__(
        self,
        left_dir_pin,
        left_step_pin,
        left_enable_pin,
        right_dir_pin,
        right_step_pin,
        right_enable_pin,
        delay_us=2,
        enable_active_value=1
    ):
        self.left_dir = Pin(left_dir_pin, Pin.OUT)
        self.left_step = Pin(left_step_pin, Pin.OUT)
        self.left_enable = Pin(left_enable_pin, Pin.OUT)

        self.right_dir = Pin(right_dir_pin, Pin.OUT)
        self.right_step = Pin(right_step_pin, Pin.OUT)
        self.right_enable = Pin(right_enable_pin, Pin.OUT)

        self.delay_us = delay_us
        self.enable_active_value = enable_active_value
        self.disable_value = 0 if enable_active_value == 1 else 1

        self.left_step.value(0)
        self.right_step.value(0)
        self.disable()

    def enable(self):
        self.left_enable.value(self.enable_active_value)
        self.right_enable.value(self.enable_active_value)

    def disable(self):
        self.left_enable.value(self.disable_value)
        self.right_enable.value(self.disable_value)

    def stop(self):
        self.disable()

    def move_together(self, steps, left_dir, right_dir):
        self.enable()

        self.left_dir.value(left_dir)
        self.right_dir.value(right_dir)

        for _ in range(steps):
            self.left_step.value(1)
            self.right_step.value(1)
            sleep_us(self.delay_us)

            self.left_step.value(0)
            self.right_step.value(0)
            sleep_us(self.delay_us)

        self.disable()

    def geradeaus_fahrt(self, steps):
        self.move_together(steps, left_dir=1, right_dir=1)

    def rueckwaerts_fahrt(self, steps):
        self.move_together(steps, left_dir=0, right_dir=0)

    def drehung_90_links(self, steps_90):
        self.move_together(steps_90, left_dir=0, right_dir=1)

    def drehung_90_rechts(self, steps_90):
        self.move_together(steps_90, left_dir=1, right_dir=0)

    def drehung_180_links(self, steps_180):
        self.move_together(steps_180, left_dir=0, right_dir=1)

    def drehung_180_rechts(self, steps_180):
        self.move_together(steps_180, left_dir=1, right_dir=0)