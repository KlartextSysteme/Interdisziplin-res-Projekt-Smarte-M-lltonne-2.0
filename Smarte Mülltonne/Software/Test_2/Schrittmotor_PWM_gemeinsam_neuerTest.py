from machine import Pin, PWM
from time import sleep, sleep_us


class StepperPWM:
    def __init__(self, dir_left_pin, step_left_pin, enable_left_pin, dir_right_pin, step_right_pin, enable_right_pin, step_freq=1000, name="STEPPER_dual", debug=True):
        self.dir_left = Pin(dir_left_pin, Pin.OUT)
        self.step_left_pin = Pin(step_left_pin, Pin.OUT)
        self.enable_left = Pin(enable_left_pin, Pin.OUT)

        self.dir_right = Pin(dir_right_pin, Pin.OUT)
        self.step_right_pin = Pin(step_right_pin, Pin.OUT)
        self.enable_right = Pin(enable_right_pin, Pin.OUT)

        self.pwm_left = PWM(self.step_left_pin)
        self.pwm_right = PWM(self.step_right_pin)
        self.pwm_left.duty_u16(0)
        self.pwm_right.duty_u16(0)

        self.step_freq = step_freq
        self.name = name
        self.debug = debug

        self.disable()

    def enable_motor(self):
        self.enable_left.value(1) 
        self.enable_right.value(1)

    def disable(self):
        self.pwm_left.duty_u16(0)
        self.pwm_right.duty_u16(0)
        self.enable_left.value(0)
        self.enable_right.value(0)

    def move(self, steps, direction_left, direction_right):
        self.enable_motor()
        self.dir_left.value(direction_left)
        self.dir_right.value(direction_right)

        sleep_us(20)  # kurze Zeit, damit DIR stabil ist

        if self.debug:
            print(self.name, "dir:", direction_left, "dir", direction_right, "steps:", steps, "freq:", self.step_freq)

        self.pwm_left.freq(self.step_freq)
        self.pwm_right.freq(self.step_freq)
        self.pwm_left.duty_u16(32768)
        self.pwm_right.duty_u16(32768)

        move_time = steps / self.step_freq
        sleep(move_time)

        self.disable()


# ---------------- TEST ----------------

motors = StepperPWM(
    dir_left_pin=10,
    step_left_pin=11,
    enable_left_pin=12,
    step_freq=2000,
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