from machine import Pin
from time import sleep, sleep_us


class DualStepperDelay:
    def __init__(self,
                 left_dir_pin,
                 left_step_pin,
                 left_enable_pin,
                 right_dir_pin,
                 right_step_pin,
                 right_enable_pin,
                 enable_active_value=1):

        self.left_dir = Pin(left_dir_pin, Pin.OUT)
        self.right_dir = Pin(right_dir_pin, Pin.OUT)

        self.left_step = Pin(left_step_pin, Pin.OUT)
        self.right_step = Pin(right_step_pin, Pin.OUT)

        self.left_enable = Pin(left_enable_pin, Pin.OUT)
        self.right_enable = Pin(right_enable_pin, Pin.OUT)

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

    def freq_to_delay_us(self, freq):
        return max(1, int(1000000 / (2 * freq)))

    def step_both_once(self, delay_us):
        self.left_step.value(1)
        self.right_step.value(1)
        sleep_us(delay_us)

        self.left_step.value(0)
        self.right_step.value(0)
        sleep_us(delay_us)

    def move_together_delay(self, schritte, left_dir, right_dir,
                            start_freq=2000,
                            max_freq=4500,
                            ramp_steps=100):

        self.enable()

        self.left_dir.value(left_dir)
        self.right_dir.value(right_dir)

        sleep(0.02)

        steps_per_part = schritte // (ramp_steps * 2 + 1)

        # Beschleunigen
        for i in range(ramp_steps):
            freq = start_freq + (max_freq - start_freq) * i // ramp_steps
            delay_us = self.freq_to_delay_us(freq)

            for _ in range(steps_per_part):
                self.step_both_once(delay_us)

        # Konstant fahren
        rest_steps = schritte - steps_per_part * ramp_steps * 2
        delay_us = self.freq_to_delay_us(max_freq)

        for _ in range(rest_steps):
            self.step_both_once(delay_us)

        # Abbremsen
        for i in range(ramp_steps, 0, -1):
            freq = start_freq + (max_freq - start_freq) * i // ramp_steps
            delay_us = self.freq_to_delay_us(freq)

            for _ in range(steps_per_part):
                self.step_both_once(delay_us)

        self.left_step.value(0)
        self.right_step.value(0)

        self.disable()

    def geradeaus_fahrt(self, schritte):
        self.move_together_delay(schritte, 1, 0,
                                 start_freq=2000,
                                 max_freq=4500,
                                 ramp_steps=100)

    def rueckwaerts_fahrt(self, schritte):
        self.move_together_delay(schritte, 0, 1,
                                 start_freq=2000,
                                 max_freq=4500,
                                 ramp_steps=100)

    def drehung_links(self, schritte):
        self.move_together_delay(schritte, 0, 0,
                                 start_freq=2000,
                                 max_freq=4500,
                                 ramp_steps=100)

    def drehung_rechts(self, schritte):
        self.move_together_delay(schritte, 1, 1,
                                 start_freq=2000,
                                 max_freq=4500,
                                 ramp_steps=100)


motors = DualStepperDelay(
    left_dir_pin=10,
    left_step_pin=11,
    left_enable_pin=12,
    right_dir_pin=13,
    right_step_pin=8,
    right_enable_pin=9,
    enable_active_value=1
)


while True:
    print("Geradeaus")
    motors.geradeaus_fahrt(20000)
    sleep(1)

    print("Rueckwaerts")
    motors.rueckwaerts_fahrt(20000)
    sleep(1)

    print("Links drehen 90 Grad")
    motors.drehung_links(29980)
    sleep(1)

    print("Rechts drehen 90 Grad")
    motors.drehung_rechts(29980)
    sleep(1)