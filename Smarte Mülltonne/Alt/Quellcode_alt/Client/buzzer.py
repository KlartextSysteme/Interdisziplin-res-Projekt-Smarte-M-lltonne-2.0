from machine import Pin
import time

# Versuche, das Zufallsmodul für MicroPython zu laden, sonst Standard-Python (für Tests)
try:
    import urandom as random
except ImportError:
    import random


class Buzzer:
    """
    Klasse zur Steuerung eines Buzzersignals (digital an/aus) im Hintergrund.
    Erlaubt das Abspielen von Mustern (Patterns) und optionalen Wiederholungen,
    ohne die Hauptschleife mit sleep() zu blockieren.
    """

    def __init__(self, pin_number: int, active_high: bool = True):
        """
        Initialisiert den Buzzer an einem GPIO-Pin.
        - pin_number: Die GPIO-Pin-Nummer.
        - active_high: True, wenn High-Pegel den Buzzer aktiviert. False für Active Low.
        """
        self.pin = Pin(pin_number, Pin.OUT)
        self.active_high = active_high

        # Interne Zustandsvariablen für das aktuelle Muster
        self._pattern = []       # Liste von Tupeln (on: bool, duration_ms: int)
        self._i = 0              # Index des aktuellen Schritts im Pattern
        self._phase_end_ms = 0   # Zeitstempel, wann der aktuelle Schritt endet
        self._running = False    # Gibt an, ob gerade ein Pattern abgespielt wird

        # Variablen für Wiederholungen
        self._repeat = False
        self._repeat_min_ms = 0
        self._repeat_max_ms = 0
        self._next_repeat_ms = 0 # Zeitstempel für den nächsten Start

        self.off() # Sicherstellen, dass der Buzzer zu Beginn aus ist

    def on(self):
        """Schaltet den Buzzer ein (berücksichtigt Active High/Low)."""
        self.pin.value(1 if self.active_high else 0)

    def off(self):
        """Schaltet den Buzzer aus."""
        self.pin.value(0 if self.active_high else 1)

    def stop(self):
        """Stoppt sofort jede Wiedergabe und schaltet den Buzzer aus."""
        self._running = False
        self._repeat = False
        self._next_repeat_ms = 0
        self.off()

    def play(self, pattern, repeat=False, repeat_min_ms=0, repeat_max_ms=0):
        """
        Startet das Abspielen eines Musters.
        - pattern: Liste von Tupeln [(True, 100), (False, 50), ...] -> (An/Aus, Dauer in ms)
        - repeat: Soll das Muster wiederholt werden?
        - repeat_min_ms: Minimale Pause vor der Wiederholung.
        - repeat_max_ms: Maximale Pause vor der Wiederholung (für zufällige Variation).
        """
        if not pattern:
            self.stop()
            return

        self._pattern = pattern
        self._i = 0
        self._running = True

        self._repeat = bool(repeat)
        self._repeat_min_ms = int(repeat_min_ms)
        self._repeat_max_ms = int(max(repeat_min_ms, repeat_max_ms))
        self._next_repeat_ms = 0

        self._apply_phase() # Ersten Schritt sofort ausführen

    def _rand_between(self, a, b):
        """Hilfsfunktion für Zufallszahlen zwischen a und b (inklusive)."""
        if b <= a:
            return a
        try:
            # MicroPython Implementierung
            return a + (random.getrandbits(16) % (b - a + 1))
        except AttributeError:
            # Standard Python Fallback
            return a + random.randint(0, b - a)

    def _apply_phase(self):
        """Wendet den aktuellen Schritt des Patterns auf die Hardware an."""
        on, dur = self._pattern[self._i]
        if on:
            self.on()
        else:
            self.off()
        # Berechnet, wann dieser Schritt vorbei ist
        self._phase_end_ms = time.ticks_add(time.ticks_ms(), int(dur))

    def run(self):
        """
        Hauptmethode, die zyklisch (in der Main-Loop) aufgerufen werden muss.
        Prüft Zeitstempel und schaltet den Buzzer entsprechend weiter.
        """
        now = time.ticks_ms()

        # Fall 1: Ein Pattern wird gerade abgespielt
        if self._running:
            # Wenn die Zeit für den aktuellen Schritt noch nicht abgelaufen ist -> warten
            if time.ticks_diff(now, self._phase_end_ms) < 0:
                return

            # Zeit abgelaufen -> nächster Schritt
            self._i += 1

            # Prüfen, ob das Pattern zu Ende ist
            if self._i >= len(self._pattern):
                self.off()
                self._running = False # Pattern beendet

                # Wenn Wiederholung aktiviert ist -> Zeit für nächsten Start berechnen
                if self._repeat:
                    delay = self._rand_between(self._repeat_min_ms, self._repeat_max_ms)
                    self._next_repeat_ms = time.ticks_add(now, delay)
                return

            # Nächsten Schritt im Pattern anwenden
            self._apply_phase()
            return

        # Fall 2: Warten auf Wiederholung
        if self._repeat and self._next_repeat_ms and time.ticks_diff(now, self._next_repeat_ms) >= 0:
            # Wartezeit vorbei -> Pattern von vorne starten
            self._i = 0
            self._running = True
            self._apply_phase()
