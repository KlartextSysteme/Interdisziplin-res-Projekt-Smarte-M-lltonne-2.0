import time
from machine import Pin


class HCSR04P:
    """
    Treiber für den HC-SR04(P) Ultraschallsensor.
    Besonderheit: Die Messung erfolgt nicht-blockierend über Interrupts (IRQ).
    
    Ablauf:
    1. Trigger wird kurz (10µs) gesetzt.
    2. Ein Interrupt lauscht auf die steigende Flanke des Echo-Pins (Startzeit).
    3. Ein Interrupt lauscht auf die fallende Flanke des Echo-Pins (Endzeit).
    4. Aus der Differenz wird die Distanz berechnet.
    """

    def __init__(self, trigger_pin: int, echo_pin: int, interval_ms: int = 250, timeout_us: int = 30_000):
        """
        Initialisiert den Sensor.
        - trigger_pin: GPIO für Trigger (Ausgang)
        - echo_pin: GPIO für Echo (Eingang)
        - interval_ms: Wie oft soll gemessen werden? (z.B. alle 250ms)
        - timeout_us: Wann gilt eine Messung als fehlgeschlagen? (30ms ~ 5m Reichweite)
        """
        self.trig = Pin(trigger_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)

        self.trig.value(0)

        self.interval_ms = interval_ms
        self.timeout_us = timeout_us

        self._next_measure_ms = time.ticks_ms()

        # Zustands-Flags für die Interrupt-Steuerung
        self._measuring = False      # Läuft gerade eine Messung?
        self._waiting_rise = False   # Warten wir auf den Start des Echos?
        self._waiting_fall = False   # Warten wir auf das Ende des Echos?
        
        # Zeitstempel für die Berechnung
        self._trigger_us = 0
        self._rise_us = 0

        # Ergebnis-Speicher
        self.distance_cm = None
        self._new_sample = False

        # Interrupt für beide Flanken (Rising & Falling) aktivieren
        self.echo.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._echo_irq)

    def _echo_irq(self, pin):
        """
        Interrupt Service Routine (ISR). Wird bei Pegeländerung am Echo-Pin aufgerufen.
        Muss extrem schnell sein (keine Prints, keine komplexen Rechnungen!).
        """
        # Wenn wir gar nicht messen wollten (Störimpuls?), ignorieren
        if not self._measuring:
            return

        now = time.ticks_us()
        level = pin.value()

        # Steigende Flanke (Rising Edge): Das Echo beginnt -> Zeit merken
        if self._waiting_rise and level == 1:
            self._rise_us = now
            self._waiting_rise = False
            self._waiting_fall = True
            return

        # Fallende Flanke (Falling Edge): Das Echo ist zu Ende -> Dauer berechnen
        if self._waiting_fall and level == 0:
            pulse_us = time.ticks_diff(now, self._rise_us)

            # Umrechnung: Schallgeschwindigkeit ~343m/s -> 1cm braucht ca. 29µs
            # Da der Schall hin und zurück muss: 29 * 2 = 58µs pro cm.
            self.distance_cm = pulse_us / 58.0
            self._new_sample = True

            # Messung erfolgreich beenden
            self._measuring = False
            self._waiting_rise = False
            self._waiting_fall = False

    def has_new_sample(self) -> bool:
        """Prüft, ob ein neuer Messwert vorliegt."""
        return self._new_sample

    def read_distance_cm(self):
        """
        Gibt den letzten gemessenen Abstand zurück.
        Löscht das 'New Sample'-Flag, damit man jeden Wert nur einmal verarbeitet.
        """
        if not self._new_sample:
            return None
        self._new_sample = False
        return self.distance_cm

    def _start_measurement(self):
        """Sendet den Trigger-Impuls, um eine Messung zu starten."""
        # 10µs High-Puls auf Trigger
        self.trig.value(0)
        time.sleep_us(2)
        self.trig.value(1)
        time.sleep_us(10)
        self.trig.value(0)

        # Zustandsvariablen setzen
        self._trigger_us = time.ticks_us()
        self._measuring = True
        self._waiting_rise = True
        self._waiting_fall = False

    def run(self):
        """
        Hauptmethode: Muss zyklisch aufgerufen werden.
        Startet neue Messungen und überwacht Timeouts.
        """
        now_ms = time.ticks_ms()

        # Wenn keine Messung läuft: Prüfen, ob Zeit für die nächste ist
        if not self._measuring:
            if time.ticks_diff(now_ms, self._next_measure_ms) >= 0:
                self._start_measurement()
                self._next_measure_ms = time.ticks_add(now_ms, self.interval_ms)
            return

        # Wenn Messung läuft: Prüfen auf Timeout (Echo kam nie an)
        # Passiert oft bei offener Umgebung oder zu großen Entfernungen
        now_us = time.ticks_us()
        if time.ticks_diff(now_us, self._trigger_us) > self.timeout_us:
            self.distance_cm = None  # Kein gültiger Wert
            self._new_sample = True  # Signalisiert "Messung fertig (aber leer)"

            # Reset
            self._measuring = False
            self._waiting_rise = False
            self._waiting_fall = False


class FuellstandSensor:
    """
    Logik-Klasse für die Mülltonnen-Füllstandsmessung.
    Nutzt den HCSR04P Treiber.
    
    Berechnet Füllstand in % basierend auf kalibrierten Abständen:
    - Leer: Großer Abstand (Deckel bis Boden)
    - Voll: Kleiner Abstand (Deckel bis Müll)
    """

    def __init__(
        self,
        ultrasonic: HCSR04P,
        leer_abstand_cm: float,
        voll_abstand_cm: float = 5.0,
        deckel_offen_margin_cm: float = 5.0
    ):
        """
        - ultrasonic: Instanz des HCSR04P Treibers.
        - leer_abstand_cm: Abstand Sensor -> Boden (Tonne leer).
        - voll_abstand_cm: Abstand Sensor -> Müll (Tonne voll).
        - deckel_offen_margin_cm: Toleranz. Wenn gemessener Abstand > leer + margin -> Deckel offen.
        """
        self.us = ultrasonic

        self.leer_abstand_cm = float(leer_abstand_cm)
        self.voll_abstand_cm = float(voll_abstand_cm)
        self.deckel_offen_margin_cm = float(deckel_offen_margin_cm)

        self.deckel_offen = False
        self.fuellstand_prozent = None
        self._last_valid_distance = None

        # Entprellung für "Deckel offen" / "Kein Echo"
        self._no_echo_count = 0               
        self.NO_ECHO_FOR_DECKEL_OFFEN = 3 # Erst nach 3 Fehlversuchen als "Offen" werten

    def run(self):
        """
        Zyklische Logik. Ruft den Treiber auf und interpretiert die Ergebnisse.
        """
        self.us.run()

        # Nur weiterarbeiten, wenn der Treiber eine neue Messung fertig hat
        if not self.us.has_new_sample():
            return

        d = self.us.read_distance_cm()  # Distanz in cm oder None (Timeout)

        # Fall 1: Sensor liefert Timeout (kein Echo)
        # Deutet oft darauf hin, dass der Schall ins Leere geht -> Deckel offen
        if d is None:
            self._no_echo_count += 1
            if self._no_echo_count >= self.NO_ECHO_FOR_DECKEL_OFFEN:
                self.deckel_offen = True
                self.fuellstand_prozent = None
            return

        # Fall 2: Gemessener Abstand ist größer als die Tonnenhöhe
        # -> Sensor schaut in den Raum -> Deckel offen
        if d > (self.leer_abstand_cm + self.deckel_offen_margin_cm):
            self.deckel_offen = True
            self.fuellstand_prozent = None
            self._no_echo_count = self.NO_ECHO_FOR_DECKEL_OFFEN # Zähler hochsetzen (für Stabilität)
            return

        # Fall 3: Gültige Messung im erwarteten Bereich
        self._no_echo_count = 0
        self.deckel_offen = False
        self._last_valid_distance = d

        # Füllstand berechnen
        # Wenn Müll sehr nah am Deckel (<= voll_abstand) -> 100%
        if d <= self.voll_abstand_cm:
            self.fuellstand_prozent = 100
            return

        # Lineare Interpolation zwischen Leer und Voll
        # span = Nutzbarer Messbereich (z.B. 80cm - 5cm = 75cm)
        span = max(1e-6, (self.leer_abstand_cm - self.voll_abstand_cm))
        
        # ratio: Wie viel Müll ist drin? (1.0 = Voll, 0.0 = Leer)
        ratio = (self.leer_abstand_cm - d) / span
        
        # Begrenzen auf 0..1
        ratio = max(0.0, min(1.0, ratio))
        
        # Prozentwert speichern
        self.fuellstand_prozent = int(round(ratio * 100))
