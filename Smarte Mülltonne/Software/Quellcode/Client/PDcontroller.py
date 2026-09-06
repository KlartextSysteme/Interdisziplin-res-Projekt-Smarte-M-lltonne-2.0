import time


class PDController:
    """
    PD-Regler für die Linienverfolgung.

    Der Liniensensor liefert aktuell eine Position von ca. -2 bis +2.
    Der Regler berechnet daraus eine Korrektur, die auf die linke und
    rechte Motorgeschwindigkeit verteilt wird.
    """

    def __init__(
        self,
        kp=32,
        kd=2,
        target_position=0,
        max_correction=60,
        max_derivative_per_s=45,
        default_dt_s=0.025,
    ):
        self.kp = kp
        self.kd = kd
        self.target_position = target_position
        self.max_correction = max_correction
        self.max_derivative_per_s = max_derivative_per_s
        self.default_dt_s = default_dt_s

        self.last_error = 0
        self.last_ms = None
        self.last_correction = 0

    def _clamp(self, value, low, high):
        if value < low:
            return low
        if value > high:
            return high
        return value

    def calculate(self, current_position, target_position=None, now_ms=None):
        """
        Berechnet die PD-Korrektur.

        Rückgabe:
        - correction > 0: linker Motor wird langsamer, rechter schneller.
        - correction < 0: linker Motor wird schneller, rechter langsamer.
        - 0 bei None oder Sonderwerten wie "end_marker".
        """
        if target_position is None:
            target_position = self.target_position

        if current_position is None or current_position == "end_marker":
            self.reset()
            return 0

        if now_ms is None:
            now_ms = time.ticks_ms()

        # Dieses Vorzeichen entspricht den Tests des aktuellen Fahrzeugs.
        error = current_position - target_position

        if self.last_ms is None:
            dt_s = self.default_dt_s
        else:
            dt_ms = time.ticks_diff(now_ms, self.last_ms)
            dt_s = max(0.001, dt_ms / 1000.0)

        derivative_per_s = (error - self.last_error) / dt_s
        derivative_per_s = self._clamp(
            derivative_per_s,
            -self.max_derivative_per_s,
            self.max_derivative_per_s,
        )

        correction = error * self.kp + derivative_per_s * self.kd
        correction = self._clamp(
            correction,
            -self.max_correction,
            self.max_correction,
        )

        self.last_error = error
        self.last_ms = now_ms
        self.last_correction = correction

        return correction

    def get_motor_speeds(
        self,
        current_position,
        base_speed=45,
        min_speed=0,
        max_speed=95,
        target_position=None,
        now_ms=None,
    ):
        """
        Berechnet direkt linke und rechte Motorgeschwindigkeit.

        Rückgabe:
        (left_speed, right_speed, correction)
        """
        correction = self.calculate(current_position, target_position, now_ms)

        left_speed = base_speed + correction
        right_speed = base_speed - correction

        left_speed = self._clamp(left_speed, min_speed, max_speed)
        right_speed = self._clamp(right_speed, min_speed, max_speed)

        return left_speed, right_speed, correction

    def reset(self):
        """
        Setzt den internen Speicher des Reglers zurück.
        """
        self.last_error = 0
        self.last_ms = None
        self.last_correction = 0
