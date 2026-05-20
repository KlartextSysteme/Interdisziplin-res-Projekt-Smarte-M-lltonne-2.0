from machine import Pin, PWM

class DCMotor:
    """
    Treiberklasse für einen DC-Motor, der über eine H-Brücke (z.B. L298N) angesteuert wird.
    Steuert Richtung (über 2 Pins) und Geschwindigkeit (über PWM am Enable-Pin).
    """
    def __init__(self, pin1, pin2, enable_pin,
                 min_duty=15000, max_duty=65535,
                 trim_factor=1.0, name="MOTOR", debug=True):
        """
        Initialisiert den Motor.
        - pin1: Erster Richtungspin (GPIO).
        - pin2: Zweiter Richtungspin (GPIO).
        - enable_pin: PWM-Objekt für die Geschwindigkeitssteuerung.
        - min_duty: Minimaler PWM-Wert, bei dem der Motor gerade so anläuft (Totzone).
        - max_duty: Maximaler PWM-Wert (typisch 65535 bei MicroPython).
        - trim_factor: Faktor zur Anpassung der Geschwindigkeit (z.B. um ungleiche Motoren auszugleichen).
        - name: Name des Motors für Debug-Ausgaben.
        - debug: Wenn True, werden Steuerbefehle auf der Konsole ausgegeben.
        """
        self.pin1 = pin1
        self.pin2 = pin2
        self.enable_pin = enable_pin
        self.min_duty = min_duty
        self.max_duty = max_duty
        self.trim_factor = trim_factor

        self.name = name
        self.debug = debug

        # Speichert den aktuellen Zustand, um unnötige Hardware-Schreibzugriffe zu vermeiden
        self.current_speed = 0
        self.current_direction = None

    def forward(self, speed):
        """Fährt vorwärts mit angegebener Geschwindigkeit (0-100%)."""
        self._drive("forward", speed)

    def backward(self, speed):
        """Fährt rückwärts mit angegebener Geschwindigkeit (0-100%)."""
        self._drive("backward", speed)

    def stop(self):
        """Stoppt den Motor sofort."""
        self._drive("stop", 0)

    def _drive(self, direction, speed):
        """
        Interne Methode zur Hardware-Ansteuerung.
        - direction: "forward", "backward" oder "stop"
        - speed: Geschwindigkeit in Prozent (0-100)
        """
        # Geschwindigkeit begrenzen auf 0-100
        speed = max(0, min(100, int(speed)))

        # Redundanz-Check: Wenn sich nichts ändert, nichts tun (spart CPU und I/O)
        if direction == self.current_direction and speed == self.current_speed:
            return

        self.current_direction = direction
        self.current_speed = speed

        # Fall: STOP
        if direction == "stop":
            self.enable_pin.duty_u16(0) # PWM aus
            self.pin1.value(0)          # Alle Phasen auf Low -> Motor aus
            self.pin2.value(0)
            if self.debug:
                print(self.name, "STOP", "duty", 0)
            return

        # Richtungspins setzen
        if direction == "forward":
            self.pin1.value(1)
            self.pin2.value(0)
        elif direction == "backward":
            self.pin1.value(0)
            self.pin2.value(1)

        # Trim-Faktor anwenden (z.B. 0.9 für 90% Leistung)
        adjusted_speed = int(speed * self.trim_factor)
        adjusted_speed = max(0, min(100, adjusted_speed))

        # Duty Cycle berechnen: Skaliert 0-100% auf den Bereich [min_duty, max_duty]
        # Dies kompensiert die mechanische Reibung (Motor dreht erst ab min_duty).
        duty = 0
        if adjusted_speed > 0:
            duty = int(self.min_duty + (self.max_duty - self.min_duty) * (adjusted_speed / 100))

        if self.debug:
            print(self.name, direction,
                  "speed", speed,
                  "trim", self.trim_factor,
                  "adj", adjusted_speed,
                  "min", self.min_duty,
                  "max", self.max_duty,
                  "duty", duty)

        # PWM-Wert auf den Pin schreiben
        self.enable_pin.duty_u16(duty)
