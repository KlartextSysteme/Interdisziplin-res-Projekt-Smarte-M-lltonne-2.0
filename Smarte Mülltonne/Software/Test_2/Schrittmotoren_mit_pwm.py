from machine import Pin, PWM
from time import sleep


class DualStepperPWM:
    def __init__(self,
                 left_dir_pin,
                 left_step_pin,
                 left_enable_pin,
                 right_dir_pin,
                 right_step_pin,
                 right_enable_pin,
                 frequency=500,
                 enable_active_value=1):

        self.left_dir = Pin(left_dir_pin, Pin.OUT)
        self.right_dir = Pin(right_dir_pin, Pin.OUT)

        self.left_enable = Pin(left_enable_pin, Pin.OUT)
        self.right_enable = Pin(right_enable_pin, Pin.OUT)

        self.left_step = PWM(Pin(left_step_pin))
        self.right_step = PWM(Pin(right_step_pin))

        self.frequency = frequency

        self.enable_active_value = enable_active_value
        self.disable_value = 0 if enable_active_value == 1 else 1

        self.disable()

    def enable(self):
        self.left_enable.value(self.enable_active_value)
        self.right_enable.value(self.enable_active_value)

    def disable(self):
        self.left_enable.value(self.disable_value)
        self.right_enable.value(self.disable_value)

    def move_together(self, duration_s, left_dir, right_dir):

        self.enable()

        self.left_dir.value(left_dir)
        self.right_dir.value(right_dir)

        self.left_step.freq(self.frequency)
        self.right_step.freq(self.frequency)

        # PWM einschalten (50%)
        self.left_step.duty_u16(32768)
        self.right_step.duty_u16(32768)

        sleep(duration_s)

        # PWM ausschalten
        self.left_step.duty_u16(0)
        self.right_step.duty_u16(0)

        self.disable()

    def geradeaus_fahrt(self, dauer):
        self.move_together(dauer, 1, 1)

    def rueckwaerts_fahrt(self, dauer):
        self.move_together(dauer, 0, 0)

    def drehung_links(self, dauer):
        self.move_together(dauer, 0, 1)

    def drehung_rechts(self, dauer):
        self.move_together(dauer, 1, 0)


motors = DualStepperPWM(
    left_dir_pin=10,
    left_step_pin=11,
    left_enable_pin=12,
    right_dir_pin=13,
    right_step_pin=14,
    right_enable_pin=15,
    frequency=5000,
    enable_active_value=1
)

while True:
    print("Geradeaus")
    motors.geradeaus_fahrt(2)   # 2 Sekunden

    sleep(2)

    # print("Links drehen")
    # motors.drehung_links(1)     # 1 Sekunde

    # sleep(2)