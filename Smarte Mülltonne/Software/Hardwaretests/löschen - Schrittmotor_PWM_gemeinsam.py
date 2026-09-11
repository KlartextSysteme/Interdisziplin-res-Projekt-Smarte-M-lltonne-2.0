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
        # Bei eurem Aufbau scheint 1 = aktiv zu sein
        self.enable.value(1)

    def disable(self):
        self.pwm.duty_u16(0)
        self.enable.value(0)

    def start(self, direction):
        self.enable_motor()
        self.dir.value(direction)

        sleep_us(20)

        if self.debug:
            print(self.name, "start dir:", direction, "freq:", self.step_freq)

        self.pwm.freq(self.step_freq)
        self.pwm.duty_u16(32768)

    def stop(self):
        if self.debug:
            print(self.name, "stop")

        self.pwm.duty_u16(0)
        self.disable()

    def time_for_steps(self, steps):
        return steps / self.step_freq


def move_two_motors(motor_a, steps_a, direction_a, motor_b, steps_b, direction_b):
    time_a = motor_a.time_for_steps(steps_a)
    time_b = motor_b.time_for_steps(steps_b)

    motor_a.start(direction_a)
    motor_b.start(direction_b)

    # Wenn beide gleich lange laufen sollen
    if time_a == time_b:
        sleep(time_a)
        motor_a.stop()
        motor_b.stop()

    # Wenn Motor A früher fertig ist
    elif time_a < time_b:
        sleep(time_a)
        motor_a.stop()

        sleep(time_b - time_a)
        motor_b.stop()

    # Wenn Motor B früher fertig ist
    else:
        sleep(time_b)
        motor_b.stop()

        sleep(time_a - time_b)
        motor_a.stop()


# ---------------- TEST ----------------

motor1 = StepperPWM(
    dir_pin=10,
    step_pin=11,
    enable_pin=12,
    step_freq=200,
    name="Motor 1"
)

motor2 = StepperPWM(
    dir_pin=13,
    step_pin=8,
    enable_pin=9,
    step_freq=200,
    name="Motor 2"
)


while True:
    print("Beide Motoren vorwärts")
    move_two_motors(
        motor1, 5200, 1,
        motor2, 5200, 1
    )

    sleep(1)

    print("Beide Motoren rückwärts")
    move_two_motors(
        motor1, 5200, 0,
        motor2, 5200, 0
    )

    sleep(1)