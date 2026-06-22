import time
from machine import Pin


class UltraschallsensorMUX:
    """
    Treiber für einen Ultraschallsensor am Multiplexer.

    Der Trigger-Pin kann gemeinsam mit anderen Ultraschallsensoren genutzt
    werden. Das Echo-Signal wird ueber den CD74HC4067 Multiplexer gelesen.
    """

    def __init__(
        self,
        multiplexer,
        trigger_pin,
        echo_channel,
        interval_ms=120,
        timeout_us=30000,
        name="US_MUX",
        debug=False,
    ):
        self.mux = multiplexer
        self.trigger = Pin(trigger_pin, Pin.OUT)
        self.echo_channel = echo_channel
        self.interval_ms = int(interval_ms)
        self.timeout_us = int(timeout_us)
        self.name = name
        self.debug = debug

        self.trigger.value(0)

        self.distance_cm = None
        self._last_measure_ms = 0

    def measure_cm(self):
        """
        Führt eine einzelne blockierende Messung aus.

        Rückgabe:
        - Distanz in cm
        - None bei Timeout / keinem Echo
        """
        self.mux.select_channel(self.echo_channel)

        self.trigger.value(0)
        time.sleep_us(2)
        self.trigger.value(1)
        time.sleep_us(10)
        self.trigger.value(0)

        start_timeout = time.ticks_us()
        while self.mux.value() == 0:
            if time.ticks_diff(time.ticks_us(), start_timeout) > self.timeout_us:
                self.distance_cm = None
                return None

        start = time.ticks_us()
        while self.mux.value() == 1:
            if time.ticks_diff(time.ticks_us(), start) > self.timeout_us:
                self.distance_cm = None
                return None

        end = time.ticks_us()
        duration = time.ticks_diff(end, start)
        self.distance_cm = duration / 58.0

        if self.debug:
            print(self.name, round(self.distance_cm, 1), "cm")

        return self.distance_cm

    def run(self, force=False):
        """
        Aktualisiert die Distanz in einem festen Messintervall.
        """
        now = time.ticks_ms()

        if (
            not force
            and time.ticks_diff(now, self._last_measure_ms) < self.interval_ms
        ):
            return self.distance_cm

        self._last_measure_ms = now
        return self.measure_cm()

    def read_distance_cm(self):
        """
        Gibt den zuletzt gemessenen Abstand zurück.
        """
        return self.distance_cm

    def is_below(self, limit_cm):
        """
        True, wenn ein gültiger Abstand kleiner/gleich limit_cm ist.
        """
        return self.distance_cm is not None and self.distance_cm <= limit_cm

    def is_clear(self, clear_cm):
        """
        True, wenn kein Echo kam oder der Abstand größer als clear_cm ist.
        """
        return self.distance_cm is None or self.distance_cm > clear_cm


class HindernisSensoren:
    """
    Bündelt die drei Hindernis-Ultraschallsensoren vorne, links und rechts.

    Normalerweise wird nur vorne zyklisch gemessen. Links und rechts können
    gezielt für die Hindernisumfahrung abgefragt werden.
    """

    def __init__(
        self,
        multiplexer,
        trigger_pin=6,
        front_channel=5,
        left_channel=6,
        right_channel=7,
        stop_cm=20,
        side_clear_cm=35,
        interval_ms=120,
        timeout_us=30000,
        debug=False,
    ):
        self.stop_cm = stop_cm
        self.side_clear_cm = side_clear_cm

        self.front = UltraschallsensorMUX(
            multiplexer,
            trigger_pin,
            front_channel,
            interval_ms=interval_ms,
            timeout_us=timeout_us,
            name="US vorne",
            debug=debug,
        )
        self.left = UltraschallsensorMUX(
            multiplexer,
            trigger_pin,
            left_channel,
            interval_ms=interval_ms,
            timeout_us=timeout_us,
            name="US links",
            debug=debug,
        )
        self.right = UltraschallsensorMUX(
            multiplexer,
            trigger_pin,
            right_channel,
            interval_ms=interval_ms,
            timeout_us=timeout_us,
            name="US rechts",
            debug=debug,
        )

    def run_front(self, force=False):
        return self.front.run(force)

    def front_obstacle_detected(self):
        return self.front.is_below(self.stop_cm)

    def measure_left(self):
        return self.left.measure_cm()

    def measure_right(self):
        return self.right.measure_cm()

    def left_is_clear(self):
        return self.left.is_clear(self.side_clear_cm)

    def right_is_clear(self):
        return self.right.is_clear(self.side_clear_cm)

    def choose_avoidance_side(self):
        """
        Misst links und rechts und gibt die bevorzugte Umfahrungsseite zurück.

        Rückgabe:
        - "right"
        - "left"
        - None, wenn beide Seiten blockiert wirken
        """
        left_distance = self.measure_left()
        time.sleep_ms(60)
        right_distance = self.measure_right()

        left_clear = self.left_is_clear()
        right_clear = self.right_is_clear()

        if right_clear and left_clear:
            if right_distance is None:
                return "right"
            if left_distance is None:
                return "left"
            if right_distance >= left_distance:
                return "right"
            return "left"

        if right_clear:
            return "right"
        if left_clear:
            return "left"

        return None


class FuellstandSensor:
    """
    Logik-Klasse fuer die Füllstandsmessung der Mülltonne.

    Nutzt einen Ultraschallsensor und berechnet daraus:
    - deckel_offen
    - fuellstand_prozent
    """

    def __init__(
        self,
        ultrasonic,
        leer_abstand_cm,
        voll_abstand_cm=5.0,
        deckel_offen_margin_cm=5.0,
        no_echo_for_deckel_offen=3,
    ):
        self.us = ultrasonic
        self.leer_abstand_cm = float(leer_abstand_cm)
        self.voll_abstand_cm = float(voll_abstand_cm)
        self.deckel_offen_margin_cm = float(deckel_offen_margin_cm)

        self.deckel_offen = False
        self.fuellstand_prozent = None
        self.last_distance_cm = None

        self._no_echo_count = 0
        self.no_echo_for_deckel_offen = int(no_echo_for_deckel_offen)

    def run(self, force=False):
        """
        Aktualisiert Abstand, Deckelstatus und Füllstand.
        """
        distance = self.us.run(force)
        self.update_from_distance(distance)

    def update_from_distance(self, distance):
        """
        Interpretiert eine Distanzmessung für den Füllstand.
        """
        if distance is None:
            self._no_echo_count += 1
            if self._no_echo_count >= self.no_echo_for_deckel_offen:
                self.deckel_offen = True
                self.fuellstand_prozent = None
            return

        self.last_distance_cm = distance

        if distance > (self.leer_abstand_cm + self.deckel_offen_margin_cm):
            self.deckel_offen = True
            self.fuellstand_prozent = None
            self._no_echo_count = self.no_echo_for_deckel_offen
            return

        self._no_echo_count = 0
        self.deckel_offen = False

        if distance <= self.voll_abstand_cm:
            self.fuellstand_prozent = 100
            return

        span = max(0.001, self.leer_abstand_cm - self.voll_abstand_cm)
        ratio = (self.leer_abstand_cm - distance) / span
        ratio = max(0.0, min(1.0, ratio))
        self.fuellstand_prozent = int(round(ratio * 100))

    def get_fuellstand_prozent(self):
        return self.fuellstand_prozent

    def is_deckel_offen(self):
        return self.deckel_offen
