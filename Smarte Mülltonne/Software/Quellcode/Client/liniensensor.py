from machine import Pin
import time


class Liniensensor:
    """
    Klasse zur Verwaltung von 5 digitalen Liniensensoren (z.B. KY-033 oder TCRT5000).
    Berechnet aus den Einzelwerten eine relative Position der Linie zur Fahrzeugmitte.
    
    Features:
    - Multi-Sampling (Mehrfachabtastung) zur Unterdrückung von Rauschen/Glitches.
    - Caching zur Entlastung des Prozessors bei zu häufigen Abfragen.
    - Gewichtete Positionsberechnung für weiche Regelung.
    """

    # Gewichtung der Sensoren für die Positionsberechnung.
    # Negativ = Links, Positiv = Rechts, 0 = Mitte.
    # Wertebereich ca. -100 bis +100.
    _W_LA = -100 # Links Außen
    _W_LM = -50  # Links Mitte
    _W_M  = 0    # Mitte
    _W_RM = 50   # Rechts Mitte
    _W_RA = 100  # Rechts Außen

    def __init__(
        self,
        pin_links_aussen,
        pin_links_mitte,
        pin_mitte,
        pin_rechts_mitte,
        pin_rechts_aussen,
        pull=None,
        min_read_interval_ms=8,
        samples_per_read=3,
        sample_delay_us=80
    ):
        """
        Initialisiert das Sensor-Array.
        - pin_...: GPIO-Nummern der 5 Sensoren.
        - pull: Interner Widerstand (None, Pin.PULL_UP, Pin.PULL_DOWN).
        - min_read_interval_ms: Mindestzeit zwischen zwei Hardware-Abfragen (Cache-Dauer).
        - samples_per_read: Anzahl der Messungen pro Sensor für Majority Vote (ungerade Zahl empfohlen).
        - ample_delay_us: Wartezeit zwischen den Samples in Mikrosekunden.
        """

        # Pins initialisieren (optional mit Pull-Up/Down)
        if pull is None:
            self.sensor_links_aussen = Pin(pin_links_aussen, Pin.IN)
            self.sensor_links_mitte = Pin(pin_links_mitte, Pin.IN)
            self.sensor_mitte = Pin(pin_mitte, Pin.IN)
            self.sensor_rechts_mitte = Pin(pin_rechts_mitte, Pin.IN)
            self.sensor_rechts_aussen = Pin(pin_rechts_aussen, Pin.IN)
        else:
            self.sensor_links_aussen = Pin(pin_links_aussen, Pin.IN, pull)
            self.sensor_links_mitte = Pin(pin_links_mitte, Pin.IN, pull)
            self.sensor_mitte = Pin(pin_mitte, Pin.IN, pull)
            self.sensor_rechts_mitte = Pin(pin_rechts_mitte, Pin.IN, pull)
            self.sensor_rechts_aussen = Pin(pin_rechts_aussen, Pin.IN, pull)

        # Gewichte speichern
        self.gewicht_links_aussen = self._W_LA
        self.gewicht_links_mitte = self._W_LM
        self.gewicht_mitte = self._W_M
        self.gewicht_rechts_mitte = self._W_RM
        self.gewicht_rechts_aussen = self._W_RA

        # Zielposition für den Regler (0 = Mitte)
        self.target_position = 0

        # Timing- und Caching-Variablen
        self._last_read_ms = 0
        self._cached_position = None # Letzte berechnete Position
        self._cached_bits = 0        # Letztes Bitmuster der Sensoren
        self._min_read_interval_ms = int(min_read_interval_ms)

        # Konfiguration für Multi-Sampling
        self._samples_per_read = int(samples_per_read)
        if self._samples_per_read < 1:
            self._samples_per_read = 1
        self._sample_delay_us = int(sample_delay_us)
        if self._sample_delay_us < 0:
            self._sample_delay_us = 0

    def _read_pin_majority(self, pin_obj):
        """
        Liest einen Pin mehrfach aus und bestimmt den Wert.
        Filtert kurze Störimpulse heraus.
        """
        ones = 0
        n = self._samples_per_read

        # Optimierung: Bei 1 Sample direkt lesen (schnell)
        if n == 1:
            return 1 if pin_obj.value() else 0

        # Mehrfach messen
        for _ in range(n):
            if pin_obj.value():
                ones += 1
            if self._sample_delay_us:
                time.sleep_us(self._sample_delay_us)

        # Mehrheit entscheidet: Wenn mehr als die Hälfte 1 sind, dann 1, sonst 0
        return 1 if ones > (n // 2) else 0

    def _read_sensors_bits(self):
        """
        Liest alle 5 Sensoren robust aus und packt die Ergebnisse in einen Integer (Bitmaske).
        Bit 4 (MSB) = Links Außen ... Bit 0 (LSB) = Rechts Außen.
        """
        la = self._read_pin_majority(self.sensor_links_aussen)
        lm = self._read_pin_majority(self.sensor_links_mitte)
        m = self._read_pin_majority(self.sensor_mitte)
        rm = self._read_pin_majority(self.sensor_rechts_mitte)
        ra = self._read_pin_majority(self.sensor_rechts_aussen)

        # Bits zusammenfügen: LA LM M RM RA
        bits = (la << 4) | (lm << 3) | (m << 2) | (rm << 1) | ra
        return bits

    def get_position(self):
        """
        Hauptfunktion: Bestimmt die aktuelle Linienposition.
        Rückgabe: 
        - Integer (ca. -100 bis +100): Position der Linie relativ zur Mitte.
          Negativ = Linie ist links, wir müssen nach links steuern.
          Positiv = Linie ist rechts.
        - None: Keine Linie erkannt (alle Sensoren zeigen Untergrund).
        """
        now = time.ticks_ms()

        # Cache nutzen, wenn die letzte Messung noch frisch genug ist
        if time.ticks_diff(now, self._last_read_ms) < self._min_read_interval_ms:
            return self._cached_position

        self._last_read_ms = now

        # Sensoren auslesen
        bits = self._read_sensors_bits()
        self._cached_bits = bits # Für Debugging oder Speziallogik speichern

        # Anzahl aktiver Sensoren zählen
        active = (
            ((bits >> 4) & 1) +
            ((bits >> 3) & 1) +
            ((bits >> 2) & 1) +
            ((bits >> 1) & 1) +
            (bits & 1)
        )

        # Keine Linie erkannt -> None zurückgeben
        if active == 0:
            self._cached_position = None
            return None

        # Werte extrahieren (0 oder 1)
        la = (bits >> 4) & 1
        lm = (bits >> 3) & 1
        m = (bits >> 2) & 1
        rm = (bits >> 1) & 1
        ra = bits & 1

        # Gewichtete Summe berechnen
        # (Gewicht * Aktivierung)
        # Hinweis: LM und RM haben hier evtl. noch zusätzliche Faktoren (1.5 / 1) für Feintuning
        weighted_sum = (
            la * self.gewicht_links_aussen +
            lm * (self.gewicht_links_mitte * 1.5) +
            m * self.gewicht_mitte +
            rm * (self.gewicht_rechts_mitte * 1) +
            ra * self.gewicht_rechts_aussen
        )

        # Durchschnitt bilden: Summe der Gewichte / Anzahl aktiver Sensoren
        pos = int(weighted_sum / active)
        
        self._cached_position = pos
        return pos
        
    def get_bits(self):
        """Gibt das rohe Bitmuster der letzten Messung zurück."""
        return self._cached_bits