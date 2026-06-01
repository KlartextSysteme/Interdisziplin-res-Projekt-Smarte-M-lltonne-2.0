from machine import Pin, PWM
import time
import math

# ===================================================================
# LED-BASISKLASSE (PWM für Dimm-Effekte)
# ===================================================================

class LED:
    """
    Abstrahiert eine RGB-LED. Nutzt PWM, um Helligkeit und Farbmischung zu ermöglichen.
    """
    def __init__(self, pin_rot, pin_gruen, pin_blau):
        """
        Initialisiert die drei Farbkanäle als PWM-Ausgänge.
        - pin_rot: GPIO-Pin für Rot
        - pin_gruen: GPIO-Pin für Grün
        - pin_blau: GPIO-Pin für Blau
        """
        # Initialisierung als PWM für Helligkeitssteuerung
        self.pwm_rot = PWM(Pin(pin_rot))
        self.pwm_gruen = PWM(Pin(pin_gruen))
        self.pwm_blau = PWM(Pin(pin_blau))
        
        # Frequenz auf 1000 Hz setzen (flimmerfrei für das menschliche Auge)
        for pwm in [self.pwm_rot, self.pwm_gruen, self.pwm_blau]:
            pwm.freq(1000)
            pwm.duty_u16(0) # Startwert: Aus
            
        self.ist_an = False

    def set_farbe(self, r, g, b):
        """
        Setzt die Farbe mittels RGB Werten (0-65535).
        - r: Rot-Anteil (0-65535)
        - g: Grün-Anteil (0-65535)
        - b: Blau-Anteil (0-65535)
        """
        self.pwm_rot.duty_u16(int(r))
        self.pwm_gruen.duty_u16(int(g))
        self.pwm_blau.duty_u16(int(b))

    def rot(self):
        """Schaltet die LED auf konstant Rot."""
        self.set_farbe(65535, 0, 0)
        self.ist_an = True

    def gruen(self):
        """Schaltet die LED auf konstant Grün."""
        self.set_farbe(0, 65535, 0)
        self.ist_an = True

    def blau(self):
        """Schaltet die LED auf konstant Blau."""
        self.set_farbe(0, 0, 65535)
        self.ist_an = True

    def gelb(self):
        """Schaltet die LED auf Gelb (Mischung aus Rot und Grün)."""
        self.set_farbe(65535, 65535, 0)
        self.ist_an = True

    def lila(self):
        """Schaltet die LED auf Lila (Mischung aus Rot und Blau)."""
        self.set_farbe(30000, 0, 30000)
        self.ist_an = True

    def aus(self):
        """Schaltet die LED komplett aus."""
        self.set_farbe(0, 0, 0)
        self.ist_an = False

    def status(self):
        """Gibt zurück, ob die LED (logisch) an ist."""
        return self.ist_an

# ===================================================================
# PICO-STATE-MACHINE (Zustands-LED)
# ===================================================================

class LEDStateMachine:
    """
    Steuert die Haupt-Status-LED des Roboters basierend auf seinem aktuellen Zustand.
    Implementiert Effekte wie Pulsieren oder Blitzen, ohne den Hauptprozessor zu blockieren.
    """
    def __init__(self, led):
        self.led = led
        self.pico_state = "STANDBY"
        self._start_time = time.ticks_ms() # Zeitstempel für Animationsberechnungen

        # Pending-Overlay: Überlagert den normalen Status (z.B. blinken beim Warten auf Start)
        self._pending_active = False
        self._pending_is_full = False

    def set_pico_state(self, state):
        """Aktualisiert den Zustand und setzt Animationen zurück."""
        if state != self.pico_state:
            self.pico_state = state
            self._start_time = time.ticks_ms() # Reset für sauberen Start neuer Effekte

    def _pulsieren(self, r_max, g_max, b_max, dauer_ms=1500):
        """
        Erzeugt einen weichen "Atem"-Effekt (Sinus-Kurve).
        - r_max, g_max, b_max: Maximale Helligkeit der Farbe.
        - dauer_ms: Dauer eines kompletten Zyklus.
        """
        now = time.ticks_ms()
        # Sinus-Welle von 0.0 bis 1.0 berechnen
        # (ticks_ms läuft kontinuierlich, daher ergibt das eine flüssige Animation)
        faktor = (math.sin((now / dauer_ms) * 2 * math.pi) + 1) / 2
        self.led.set_farbe(r_max * faktor, g_max * faktor, b_max * faktor)

    def _doppelblitz(self, r, g, b):
        """
        Erzeugt ein Doppelblitz-Muster (z.B. für Warnungen).
        Muster: Blitz - Pause - Blitz - Lange Pause.
        """
        zyklus_dauer = 1400 # Gesamtdauer eines Musters in ms
        t = time.ticks_diff(time.ticks_ms(), self._start_time) % zyklus_dauer
        
        # Zeitgesteuerte Ablaufsteuerung
        if 0 <= t < 100:           # 1. Blitz an
            self.led.set_farbe(r, g, b)
        elif 100 <= t < 200:       # Aus
            self.led.aus()
        elif 200 <= t < 300:       # 2. Blitz an
            self.led.set_farbe(r, g, b)
        elif 300 <= t < 400:       # Aus
            self.led.aus()
        else:                      # Lange Pause
            self.led.aus()

    def set_pending_feedback(self, active, is_full=False):
        """Aktiviert/Deaktiviert das Pending-Overlay (Warten auf Bestätigung)."""
        if (active != self._pending_active) or (is_full != self._pending_is_full):
            self._pending_active = active
            self._pending_is_full = is_full
            self._start_time = time.ticks_ms()  # Animation neu starten

    def _blink(self, r, g, b, interval_ms=250):
        """Einfaches Blinken (An/Aus)."""
        t = time.ticks_diff(time.ticks_ms(), self._start_time)
        phase = (t // interval_ms) % 2
        if phase == 0:
            self.led.set_farbe(r, g, b)
        else:
            self.led.aus()

    def run(self):
        """
        Hauptmethode: Muss zyklisch aufgerufen werden.
        Wählt basierend auf dem aktuellen Zustand den passenden Lichteffekt.
        """
        # Overlay hat Priorität (z.B. Feedback beim Tastendruck)
        if self._pending_active:
            if self._pending_is_full:
                # Voll -> gelb blinken
                self._blink(65535, 65535, 0, interval_ms=250)
            else:
                # Leer -> grün blinken
                self._blink(0, 65535, 0, interval_ms=250)
            return
        
        s = self.pico_state

        # --- MAPPING DER ZUSTÄNDE AUF LICHTEFFEKTE ---
        
        if s == "STANDBY": 
            # Bereit / Zuhause -> Grünes Dauerlicht
            self.led.gruen()
            
        elif s == "FULL":
            # Voll -> Gelbes Dauerlicht
            self.led.gelb()
            
        elif s == "LINE_FOLLOWING" or s == "LINE_LOST":
            # Fährt -> Blau pulsieren ("Arbeitet")
            self._pulsieren(0, 0, 65535) 
            
        elif s == "USER_PAUSED":
            # Pausiert -> Blaues Dauerlicht
            self.led.blau()
            
        elif s == "WAIT_AT_STREET":
            # Wartet auf Entleerung -> Gelb pulsieren
            self._pulsieren(65535, 65535, 0)

        elif s == "EMPTIED":
            # Entleert -> Grün pulsieren
            self._pulsieren(0, 65535, 0)
            
        elif s == "OBSTACLE":
            # Hindernis -> Orange Doppelblitz (Warnung)
            # Orange ca.: Rot voll + Grün 1/3
            self._doppelblitz(65535, 21845, 0)
            
        elif s == "ARRIVED":
            # Ankunft/Drehen -> Blau pulsieren
            self._pulsieren(0, 0, 65535) 

        elif s in ("MANUAL_GOTO_STREET_REQUEST", "MANUAL_RETURN_HOME_REQUEST"):
            # Übergangszustand -> Gelb pulsieren
            self._pulsieren(65535, 65535, 0)

        else:
            pass


# ===================================================================
# SERVER-CONNECTION-STATE-MACHINE
# ===================================================================
# Konstanten für den Verbindungsstatus
STATE_CONNECTED = "CONNECTED"
STATE_NOT_CONNECTED = "NOT_CONNECTED"
STATE_CONNECTING = "CONNECTING"
STATE_OFFLINE = "OFFLINE"

class ConnectionLEDStateMachine:
    """
    Steuert die zweite RGB-LED, die den Netzwerkstatus anzeigt.
    """

    _INTERVAL_CONNECTING_MS = 150 # Schnelles Blinken beim Verbinden
    _INTERVAL_NOT_CONNECTED_MS = 700  # Langsames Blinken wenn Verbindung weg

    def __init__(self, led):
        self.led = led
        self.state = STATE_NOT_CONNECTED
        self._last_toggle_ms = time.ticks_ms()
        self._phase_on = False
        self._on_enter_state()

    def set_connection_state(self, state):
        """Aktualisiert den Verbindungsstatus."""
        if state == self.state:
            return
        self.state = state
        self._last_toggle_ms = time.ticks_ms()
        self._phase_on = False
        self._on_enter_state()

    def _on_enter_state(self):
        """Initiale LED-Aktion beim Zustandswechsel."""
        if self.state == STATE_CONNECTED:
            self.led.gruen()
        elif self.state == STATE_CONNECTING:
            self.led.aus() # Startet Blinken
        elif self.state == STATE_NOT_CONNECTED:
            self.led.aus() # Startet Blinken
        elif self.state == STATE_OFFLINE:
            self.led.lila() # Offline-Modus -> Lila Dauerlicht
        else:
            self.led.aus()

    def _blink(self, interval_ms, on_fn):
        """Generisches Blinken."""
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_toggle_ms) < interval_ms:
            return
        self._last_toggle_ms = now
        self._phase_on = not self._phase_on
        if self._phase_on:
            on_fn() # Einschalt-Funktion (z.B. self.led.blau)
        else:
            self.led.aus()

    def _run_connecting(self):
        self._blink(self._INTERVAL_CONNECTING_MS, self.led.blau)

    def _run_not_connected(self):
        self._blink(self._INTERVAL_NOT_CONNECTED_MS, self.led.blau)

    def _run_connected(self):
        self.led.gruen()

    def run(self):
        """Hauptmethode für den Verbindungsstatus."""
        if self.state == STATE_CONNECTING:
            self._run_connecting()
            return

        if self.state == STATE_NOT_CONNECTED:
            self._run_not_connected()
            return

        if self.state == STATE_CONNECTED:
            self._run_connected()
            return

        if self.state == STATE_OFFLINE:
            self.led.lila()
            return

        self.led.aus()
