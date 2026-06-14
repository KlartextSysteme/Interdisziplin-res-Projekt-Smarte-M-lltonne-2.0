from machine import Pin, PWM
from time import sleep, sleep_us


class StepperPWM:
    def __init__(self, dir_pin, step_pin, enable_pin, step_freq=1000, name="STEPPER", debug=True):
        self.dir = Pin(dir_pin, Pin.OUT)
        self.step_pin = Pin(step_pin, Pin.OUT)
        self.enable = Pin(enable_pin, Pin.OUT)

        self.pwm = PWM(self.step_pin)
        self.pwm.duty_u16(0)

        self.step_freq = step_freq
        self.name = name
        self.debug = debug

        self.disable()

    def enable_motor(self):
        self.enable.value(1)   # A4988: LOW = ON

    def disable(self):
        self.pwm.duty_u16(0)
        self.enable.value(0)   # A4988: HIGH = OFF

    def move(self, steps, direction):
        self.enable_motor()
        self.dir.value(direction)

        sleep_us(20)  # kurze Zeit, damit DIR stabil ist

        if self.debug:
            print(self.name, "dir:", direction, "steps:", steps, "freq:", self.step_freq)

        self.pwm.freq(self.step_freq)
        self.pwm.duty_u16(32768)  # 50 Prozent Duty Cycle

        move_time = steps / self.step_freq
        sleep(move_time)

        self.disable()


# ---------------- TEST ----------------

motor1 = StepperPWM(
    dir_pin=10,
    step_pin=11,
    enable_pin=12,
    step_freq=10000,
    name="Motor 1"
)

motor2 = StepperPWM(
    dir_pin=13,
    step_pin=8,
    enable_pin=9,
    step_freq=2000,
    name="Motor 2"
)

while True:
    print("Motor 1 forward")
    motor1.move(5200, 1)
    sleep(1)

    print("Motor 1 backward")
    motor1.move(5200, 0)
    sleep(1)

    print("Motor 2 forward")
    motor2.move(5200, 1)
    sleep(1)

    print("Motor 2 backward")
    motor2.move(5200, 0)
    sleep(1)