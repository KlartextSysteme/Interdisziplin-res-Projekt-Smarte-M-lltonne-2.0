from machine import Pin, PWM
from time import sleep


class DualStepperPWM:
    def __init__(self,left_dir_pin,left_step_pin,left_enable_pin,right_dir_pin,right_step_pin,right_enable_pin,frequency=4500,enable_active_value=1):

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

    def move_together(self, schritte, left_dir, right_dir):

        self.enable()

        self.left_dir.value(left_dir)
        self.right_dir.value(right_dir)

        self.left_step.freq(self.frequency)
        self.right_step.freq(self.frequency)

        # PWM starten (50 % Tastgrad)
        self.left_step.duty_u16(32768)
        self.right_step.duty_u16(32768)

        # Zeit aus Schrittzahl berechnen
        dauer = schritte / self.frequency
        sleep(dauer)

        # PWM stoppen
        self.left_step.duty_u16(0)
        self.right_step.duty_u16(0)

        self.disable()

    def move_together_ramp(self, schritte, left_dir, right_dir,start_freq=800,max_freq=5500,ramp_steps=30):

        self.enable()

        self.left_dir.value(left_dir)
        self.right_dir.value(right_dir)

        sleep(0.05)

        steps_per_part = schritte // (ramp_steps * 2 + 1)

        # Beschleunigen
        for i in range(ramp_steps):
            freq = start_freq + (max_freq - start_freq) * i // ramp_steps
            self.left_step.freq(freq)
            self.right_step.freq(freq)

            self.left_step.duty_u16(32768)
            self.right_step.duty_u16(32768)

            sleep(steps_per_part / freq)

        # Konstant fahren
        rest_steps = schritte - steps_per_part * ramp_steps * 2

        self.left_step.freq(max_freq)
        self.right_step.freq(max_freq)
        sleep(rest_steps / max_freq)

        # Abbremsen
        for i in range(ramp_steps, 0, -1):
            freq = start_freq + (max_freq - start_freq) * i // ramp_steps
            self.left_step.freq(freq)
            self.right_step.freq(freq)

            sleep(steps_per_part / freq)

        self.left_step.duty_u16(0)
        self.right_step.duty_u16(0)

        self.disable()

    def geradeaus_fahrt(self, schritte):
        self.move_together_ramp(schritte, 1, 0, start_freq=4500, max_freq=10000, ramp_steps=300)

    def rueckwaerts_fahrt(self, schritte):
        self.move_together_ramp(schritte, 0, 1, start_freq=4500, max_freq=10000, ramp_steps=300)

    def drehung_links(self, schritte):
        self.move_together_ramp(schritte, 1, 1, start_freq=4500, max_freq=10000, ramp_steps=300)

    def drehung_rechts(self, schritte):
        self.move_together_ramp(schritte, 0, 0, start_freq=4500, max_freq=10000, ramp_steps=300)


# ---------------- EINSTELLUNGEN ----------------

SCHRITTE_LINKSDREHUNG_90_GRAD = 32080
SCHRITTE_LINKSDREHUNG_180_GRAD = 2*SCHRITTE_LINKSDREHUNG_90_GRAD
SCHRITTE_RECHTSDREHUNG_90_GRAD = 32080
SCHRITTE_RECHTSDREHUNG_180_GRAD = 2*SCHRITTE_RECHTSDREHUNG_90_GRAD