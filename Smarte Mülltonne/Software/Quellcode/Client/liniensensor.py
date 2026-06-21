import time


class Liniensensor:
    """
    Klasse zur Verwaltung von 5 digitalen Liniensensoren am CD74HC4067.

    Die Klasse liest die Sensoren ueber eine Multiplexer-Instanz ein und
    berechnet daraus eine relative Linienposition.
    """

    def __init__(
        self,
        multiplexer,
        channels=(0, 1, 2, 3, 4),
        weights=(2, 1, 0, -1, -2),
        line_detected_value=1,
        target_position=0,
        min_read_interval_ms=8,
        samples_per_read=3,
        sample_delay_us=80,
    ):
        """
        Initialisiert das Liniensensor-Array.

        - multiplexer: Instanz der Klasse Multiplexer.
        - channels: Multiplexer-Kanaele der 5 Liniensensoren.
        - weights: Gewichtung für die Positionsberechnung.
        - line_detected_value: Sensorwert bei erkannter Linie.
        - target_position: Zielposition für den Regler, meistens 0.
        - min_read_interval_ms: Cache-Dauer zwischen zwei Hardware-Abfragen.
        - samples_per_read: Anzahl Messungen pro Kanal für Majority Vote.
        - sample_delay_us: Pause zwischen Samples.
        """
        if len(channels) != 5:
            raise ValueError("Liniensensor braucht genau 5 Kanäle")
        if len(weights) != 5:
            raise ValueError("Liniensensor braucht genau 5 Gewichte")

        self.mux = multiplexer
        self.channels = tuple(channels)
        self.weights = tuple(weights)
        self.line_detected_value = 1 if line_detected_value else 0
        self.target_position = target_position

        self._min_read_interval_ms = int(min_read_interval_ms)
        self._samples_per_read = int(samples_per_read)
        if self._samples_per_read < 1:
            self._samples_per_read = 1

        self._sample_delay_us = int(sample_delay_us)
        if self._sample_delay_us < 0:
            self._sample_delay_us = 0

        self._last_read_ms = 0
        self._cached_values = [0, 0, 0, 0, 0]
        self._cached_position = None
        self._cached_bits = 0
        self._cached_street_detected = False

    def _read_channel_majority(self, channel):
        """
        Liest einen Multiplexer-Kanal mehrfach und gibt den Mehrheitswert zurück.
        """
        ones = 0
        n = self._samples_per_read

        self.mux.select_channel(channel)

        if n == 1:
            return 1 if self.mux.value() else 0

        for _ in range(n):
            if self.mux.value():
                ones += 1
            if self._sample_delay_us:
                time.sleep_us(self._sample_delay_us)

        return 1 if ones > (n // 2) else 0

    def _values_to_bits(self, values):
        """
        Packt die 5 Sensorwerte in eine Bitmaske.
        Bit 4 entspricht values[0], Bit 0 entspricht values[4].
        """
        bits = 0
        for value in values:
            bits = (bits << 1) | (1 if value else 0)
        return bits

    def _read_hardware(self):
        values = []

        for channel in self.channels:
            values.append(self._read_channel_majority(channel))

        active_count = 0
        weighted_sum = 0

        for index, value in enumerate(values):
            if value == self.line_detected_value:
                active_count += 1
                weighted_sum += self.weights[index]

        self._cached_values = values
        self._cached_bits = self._values_to_bits(values)
        self._cached_street_detected = active_count == 5

        if active_count == 0:
            self._cached_position = None
        elif self._cached_street_detected:
            self._cached_position = "street"
        else:
            self._cached_position = weighted_sum / active_count

    def update(self, force=False):
        """
        Aktualisiert die Sensorwerte, falls der Cache abgelaufen ist.
        """
        now = time.ticks_ms()

        if (
            not force
            and time.ticks_diff(now, self._last_read_ms) < self._min_read_interval_ms
        ):
            return

        self._last_read_ms = now
        self._read_hardware()

    def read_values(self, force=False):
        """
        Gibt die 5 rohen Sensorwerte als Liste zurueck.
        """
        self.update(force)
        return list(self._cached_values)

    def get_position(self, force=False):
        """
        Gibt die Linienposition zurueck.

        Rueckgabe:
        - Zahl von ca. -2 bis +2: relative Linienposition.
        - None: keine Linie erkannt.
        - "street": alle 5 Sensoren erkennen Linie.
        """
        self.update(force)
        return self._cached_position

    def is_street_detected(self, force=False):
        """
        True, wenn alle 5 Sensoren gleichzeitig Linie erkennen.
        """
        self.update(force)
        return self._cached_street_detected

    def get_bits(self, force=False):
        """
        Gibt das rohe Bitmuster der letzten Messung zurueck.
        """
        self.update(force)
        return self._cached_bits
