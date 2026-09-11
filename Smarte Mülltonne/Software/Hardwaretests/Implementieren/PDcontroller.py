import time

class PDController:
    """
    Ein PD-Regler (Proportional-Derivative Controller) für die Linienverfolgung.
    
    Funktionsweise:
    - P-Anteil (Proportional): Je weiter der Roboter von der Linie weg ist, desto stärker lenkt er gegen.
    - D-Anteil (Derivative): Berücksichtigt die Änderungsgeschwindigkeit des Fehlers. 
      Dies dämpft das Überschwingen ("Wackeln") ab, indem es gegenlenkt, wenn sich der Fehler zu schnell ändert.
    """

    def __init__(self, kp, kd, max_correction=30, max_derivative_per_s=2000):
        """
        Initialisiert den Regler mit Parametern.
        - kp: Proportional-Verstärkung. Bestimmt die Reaktionsstärke auf Abweichungen.
        - kd: Differential-Verstärkung. Bestimmt die Dämpfung.
        - max_correction: Maximal zulässige Korrekturgröße (Clipping), um Motoren nicht zu übersteuern.
        - max_derivative_per_s: Begrenzung der Änderungsrate, um extreme Spitzen (z.B. durch Messfehler) zu filtern.
        """
        self.kp = kp
        self.kd = kd
        
        # Sicherheitslimits
        self.max_correction = max_correction
        self.max_derivative_per_s = max_derivative_per_s
        
        # Zustandsspeicher für den nächsten Durchlauf
        self.last_error = 0
        self.last_ms = None # Zeitstempel der letzten Berechnung

    def calculate(self, current_position, target_position, now_ms=None):
        """
        Berechnet den Korrekturwert für die Motoren.
        
        - current_position: Aktuelle Ist-Position (vom Sensor, z.B. -100 bis +100).
        - target_position: Soll-Position (meist 0 für Mitte).
        - now_ms: Optionaler Zeitstempel (für präzises Timing, falls extern gemessen).
        - return: Korrekturwert (float), der auf die Motorgeschwindigkeiten addiert/subtrahiert wird.
        """
        
        # Fail-Safe: Wenn Sensor keine gültigen Daten liefert (z.B. Linie verloren -> None)
        if current_position is None or target_position is None:
            self.reset() # Regler zurücksetzen, damit beim Wiederfinden der Linie kein alter "Sprung" passiert
            return 0     # Keine Lenkbewegung

        # Zeitstempel holen
        if now_ms is None:
            now_ms = time.ticks_ms()

        # 1. Fehler berechnen (Abweichung vom Soll)
        error = target_position - current_position

        # 2. Zeitdifferenz (dt) seit letzter Berechnung bestimmen
        if self.last_ms is None:
            dt_s = 0.02 # Annahme für ersten Durchlauf: 20ms (vermeidet Division durch Null)
        else:
            dt_ms = time.ticks_diff(now_ms, self.last_ms)
            # Schutz gegen Null-Division und extrem kleine Werte (Min 1ms)
            dt_s = max(0.001, dt_ms / 1000.0) 

        # 3. D-Anteil (Änderungsgeschwindigkeit) berechnen
        # (Fehler_neu - Fehler_alt) / Zeitdauer
        derivative_per_s = (error - self.last_error) / dt_s

        # D-Anteil begrenzen (Filtern von Rauschspitzen)
        if derivative_per_s > self.max_derivative_per_s:
            derivative_per_s = self.max_derivative_per_s
        if derivative_per_s < -self.max_derivative_per_s:
            derivative_per_s = -self.max_derivative_per_s

        # Zustände für nächsten Durchlauf speichern
        self.last_error = error
        self.last_ms = now_ms

        # 4. Gesamtkorrektur berechnen: P * kp + D * kd
        correction = error * self.kp + derivative_per_s * self.kd

        # 5. Ausgang begrenzen (Clipping)
        if correction > self.max_correction:
            correction = self.max_correction
        if correction < -self.max_correction:
            correction = -self.max_correction

        return correction

    def reset(self):
        """
        Setzt den internen Zustand des Reglers zurück.
        Sollte aufgerufen werden, wenn die Linie verloren wurde oder der Roboter gestoppt hat,
        um beim Neustart kein "Gedächtnis" an alte Fehler zu haben.
        """
        self.last_error = 0
        self.last_ms = None
