from machine import Pin
from time import ticks_ms, ticks_diff

class Button:
    """
    Klasse zur Verwaltung eines physischen Tasters (Push Button).
    Unterstützt Entprellung (Debouncing) und unterscheidet zwischen
    kurzem ("SHORT") und langem ("LONG") Drücken.
    """
    def __init__(self, pin_number, debounce_ms=50):
        """
        Initialisiert den Taster.
        - pin_number: Die GPIO-Pin-Nummer, an der der Taster angeschlossen ist.
        - debounce_ms: Zeit in Millisekunden für die Entprellung.
        """
        # Konfiguriert den Pin als Eingang mit internem Pull-Up-Widerstand.
        # Active Low: Pin ist HIGH (1), wenn nicht gedrückt, und LOW (0), wenn gedrückt (gegen GND).
        self.pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
        self.debounce_ms = debounce_ms
        
        # Zeitstempel des letzten Loslassens (für Entprellung)
        self.last_release_time = 0
        
        # Zeitstempel, wann der Taster gedrückt wurde (für Dauer-Berechnung)
        self.press_start_time = None
        
        # Aktueller Status des Tasters (True = gedrückt)
        self.is_pressed = False

    def check_press_type(self):
        """
        Prüft den Taster-Status in jedem Zyklus (Poll), ohne das Programm zu blockieren.
        Diese Methode muss regelmäßig in der Hauptschleife aufgerufen werden.
        
        Rückgabe: 
        - "SHORT": Kurzer Druck erkannt (Losgelassen nach >50ms und <1000ms)
        - "LONG": Langer Druck erkannt (Losgelassen nach >1000ms)
        - None: Keine Aktion oder Taster wird noch gehalten
        """
        current_val = self.pin.value()
        current_time = ticks_ms()

        # Fall 1: Taster wird gerade gedrückt (Active Low -> Wert ist 0)
        if current_val == 0:
            # War vorher nicht gedrückt -> Neu drücken
            if not self.is_pressed:
                # Entprellung: Prüfen, ob seit dem letzten Loslassen genug Zeit vergangen ist
                if ticks_diff(current_time, self.last_release_time) > self.debounce_ms:
                    self.is_pressed = True
                    self.press_start_time = current_time # Startzeit merken
            # Wenn bereits gedrückt (is_pressed=True): Nichts tun, wir warten auf das Loslassen
        
        # Fall 2: Taster ist losgelassen (Wert ist 1 durch Pull-Up)
        else:
            # War vorher gedrückt -> Flanke erkannt (Low -> High)
            if self.is_pressed:
                self.is_pressed = False
                self.last_release_time = current_time # Zeitstempel für nächste Entprellung setzen
                
                # Sicherheitscheck: Sollte eigentlich gesetzt sein
                if self.press_start_time is None:
                    return None
                
                # Wie lange wurde gedrückt gehalten?
                duration = ticks_diff(current_time, self.press_start_time)
                self.press_start_time = None # Reset
                
                # Entscheidung anhand der Dauer
                if duration > 1000: # Länger als 1 Sekunde -> Lang
                    return "LONG"
                elif duration > 50: # Mindestens 50ms -> Kurz (Schutz gegen Prellen/Rauschen)
                    return "SHORT"
        
        # Kein Event erkannt
        return None
