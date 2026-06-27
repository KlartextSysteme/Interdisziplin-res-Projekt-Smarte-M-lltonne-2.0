from machine import Pin, PWM
from time import sleep


class DualStepperMotorPWM:
    """
    Treiberklasse für zwei Schrittmotoren mit STEP/DIR/ENABLE-Treibern.

    Geschwindigkeit wird über die STEP-Frequenz gesteuert.
    Beide Motoren werden zeitgleich per PWM angesteuert.
    """

    def __init__(self,
                 left_dir_pin,
                 left_step_pin,
                 left_enable_pin,
                 right_dir_pin,
                 right_step_pin,
                 right_enable_pin,
                 min_freq=2000,
                 max_freq=4500,
                 left_trim_factor=1.0,
                 right_trim_factor=1.0,
                 enable_active_value=1,
                 name="DUAL_STEPPER",
                 debug=True):

        self.left_dir = Pin(left_dir_pin, Pin.OUT)
        self.right_dir = Pin(right_dir_pin, Pin.OUT)

        self.left_step = PWM(Pin(left_step_pin))
        self.right_step = PWM(Pin(right_step_pin))

        self.left_enable = Pin(left_enable_pin, Pin.OUT)
        self.right_enable = Pin(right_enable_pin, Pin.OUT)

        self.min_freq = min_freq
        self.max_freq = max_freq

        self.left_trim_factor = left_trim_factor
        self.right_trim_factor = right_trim_factor

        self.enable_active_value = enable_active_value
        self.disable_value = 0 if enable_active_value == 1 else 1

        self.name = name
        self.debug = debug

        self.current_mode = "stop"
        self.current_speed = 0

        self.stop()

    def enable(self):
        self.left_enable.value(self.enable_active_value)
        self.right_enable.value(self.enable_active_value)

    def disable(self):
        self.left_enable.value(self.disable_value)
        self.right_enable.value(self.disable_value)

    def stop(self):
        self.left_step.duty_u16(0)
        self.right_step.duty_u16(0)
        self.disable()

        self.current_mode = "stop"
        self.current_speed = 0

        if self.debug:
            print(self.name, "STOP")

    def _speed_to_frequency(self, speed, trim_factor):
        speed = max(0, min(100, int(speed)))
        adjusted_speed = int(speed * trim_factor)
        adjusted_speed = max(0, min(100, adjusted_speed))

        if adjusted_speed == 0:
            return 0

        return int(
            self.min_freq +
            (self.max_freq - self.min_freq) * (adjusted_speed / 100)
        )

    def _drive(self, mode, speed, left_dir, right_dir):
        speed = max(0, min(100, int(speed)))

        left_trim = self.left_trim_factor
        right_trim = self.right_trim_factor

        left_freq = self._speed_to_frequency(speed, left_trim)
        right_freq = self._speed_to_frequency(speed, right_trim)

        if left_freq <= 0 or right_freq <= 0:
            self.stop()
            return

        self.enable()

        self.left_dir.value(left_dir)
        self.right_dir.value(right_dir)

        sleep(0.02)

        self.left_step.freq(4500)
        self.right_step.freq(4500)

        self.left_step.duty_u16(32768)
        self.right_step.duty_u16(32768)

        self.current_mode = mode
        self.current_speed = speed

        if self.debug:
            print(self.name,
                mode,
                "speed", speed,
                "left_freq", left_freq,
                "right_freq", right_freq)

    def forward(self, speed):
        self._drive("forward", speed, 1, 0)

    def backward(self, speed):
        self._drive("backward", speed, 0, 1)

    def turn_left(self, speed):
        self._drive("turn_left", speed, 0, 0)

    def turn_right(self, speed):
        self._drive("turn_right", speed, 1, 1)

    def move_steps(self, steps, mode, speed):
        if mode == "forward":
            self.forward(speed)
        elif mode == "backward":
            self.backward(speed)
        elif mode == "turn_left":
            self.turn_left(speed)
        elif mode == "turn_right":
            self.turn_right(speed)
        else:
            self.stop()
            return

        left_freq = self._speed_to_frequency(speed, self.left_trim_factor)
        right_freq = self._speed_to_frequency(speed, self.right_trim_factor)

        duration = steps / min(left_freq, right_freq)

        sleep(duration)
        self.stop()

motors = DualStepperMotorPWM(
    left_dir_pin=10,
    left_step_pin=11,
    left_enable_pin=12,
    right_dir_pin=13,
    right_step_pin=8,
    right_enable_pin=9,
    min_freq=2000,
    max_freq=4500,
    left_trim_factor=1.0,
    right_trim_factor=1.0,
    enable_active_value=1,
    name="Muelltonne"
)
try: 
    while True:
        motors.move_steps(20000, "forward", 80)
        sleep(1)

        motors.move_steps(20000, "backward", 80)
        sleep(1)

        motors.move_steps(20000, "turn_left", 80)
        sleep(1)

        motors.move_steps(20000, "turn_right", 80)
        sleep(1)

except KeyboardInterrupt:
    pass
finally:
    motors.stop()
    print("Linienfolger gestoppt")