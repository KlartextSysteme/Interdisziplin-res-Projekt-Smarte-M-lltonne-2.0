from machine import Pin, PWM
from time import sleep_ms


class DualStepperMotorPWM:
    """
    Treiberklasse für zwei Schrittmotoren mit STEP/DIR/ENABLE-Treibern.

    Die STEP-Signale werden per PWM erzeugt. Dadurch wird die
    Geschwindigkeit über die STEP-Frequenz geregelt.
    """

    def __init__(
        self,
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
        left_forward_dir=1,
        right_forward_dir=0,
        enable_active_value=1,
        name="DUAL_STEPPER",
        debug=False,
    ):
        self.left_dir = Pin(left_dir_pin, Pin.OUT)
        self.right_dir = Pin(right_dir_pin, Pin.OUT)

        self.left_step = PWM(Pin(left_step_pin))
        self.right_step = PWM(Pin(right_step_pin))

        self.left_enable = Pin(left_enable_pin, Pin.OUT)
        self.right_enable = Pin(right_enable_pin, Pin.OUT)

        self.min_freq = int(min_freq)
        self.max_freq = int(max_freq)
        self.left_trim_factor = left_trim_factor
        self.right_trim_factor = right_trim_factor

        self.left_forward_dir = 1 if left_forward_dir else 0
        self.right_forward_dir = 1 if right_forward_dir else 0

        self.enable_active_value = 1 if enable_active_value else 0
        self.disable_value = 0 if self.enable_active_value == 1 else 1

        self.name = name
        self.debug = debug

        self.current_mode = "stop"
        self.last_left_speed = 0
        self.last_right_speed = 0
        self.last_left_freq = 0
        self.last_right_freq = 0

        self.stop()

    def _clamp(self, value, low, high):
        if value < low:
            return low
        if value > high:
            return high
        return value

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
        self.last_left_speed = 0
        self.last_right_speed = 0
        self.last_left_freq = 0
        self.last_right_freq = 0

        if self.debug:
            print(self.name, "STOP")

    def speed_to_frequency(self, speed, trim_factor=1.0):
        """
        Rechnet eine Geschwindigkeit von 0-100 Prozent in STEP-Frequenz um.
        """
        speed = self._clamp(speed, 0, 100)
        adjusted_speed = self._clamp(speed * trim_factor, 0, 100)

        if adjusted_speed <= 0:
            return 0

        return int(
            self.min_freq
            + (self.max_freq - self.min_freq) * (adjusted_speed / 100)
        )

    def _apply_pwm(self, left_speed, right_speed, left_dir, right_dir, mode):
        left_speed = self._clamp(left_speed, 0, 100)
        right_speed = self._clamp(right_speed, 0, 100)

        if left_speed <= 0 and right_speed <= 0:
            self.stop()
            return

        left_freq = self.speed_to_frequency(left_speed, self.left_trim_factor)
        right_freq = self.speed_to_frequency(right_speed, self.right_trim_factor)

        self.enable()
        self.left_dir.value(left_dir)
        self.right_dir.value(right_dir)

        sleep_ms(2)

        if left_freq > 0:
            self.left_step.freq(left_freq)
            self.left_step.duty_u16(32768)
        else:
            self.left_step.duty_u16(0)

        if right_freq > 0:
            self.right_step.freq(right_freq)
            self.right_step.duty_u16(32768)
        else:
            self.right_step.duty_u16(0)

        self.current_mode = mode
        self.last_left_speed = left_speed
        self.last_right_speed = right_speed
        self.last_left_freq = left_freq
        self.last_right_freq = right_freq

        if self.debug:
            print(
                self.name,
                mode,
                "L",
                round(left_speed, 1),
                left_freq,
                "R",
                round(right_speed, 1),
                right_freq,
            )

    def drive_forward_differential(self, left_speed, right_speed):
        """
        Fährt vorwärts mit getrennten Geschwindigkeiten.
        Wird für die PD-Linienfolge verwendet.
        """
        self._apply_pwm(
            left_speed,
            right_speed,
            self.left_forward_dir,
            self.right_forward_dir,
            "forward_differential",
        )

    def forward(self, speed):
        self.drive_forward_differential(speed, speed)

    def backward(self, speed):
        self._apply_pwm(
            speed,
            speed,
            1 - self.left_forward_dir,
            1 - self.right_forward_dir,
            "backward",
        )

    def turn_left(self, speed):
        self._apply_pwm(
            speed,
            speed,
            1 - self.left_forward_dir,
            self.right_forward_dir,
            "turn_left",
        )

    def turn_right(self, speed):
        self._apply_pwm(
            speed,
            speed,
            self.left_forward_dir,
            1 - self.right_forward_dir,
            "turn_right",
        )

    def get_last_frequencies(self):
        return self.last_left_freq, self.last_right_freq

    def get_last_speeds(self):
        return self.last_left_speed, self.last_right_speed