import time
import gc
from time import sleep


class GlobalController:
    """
    Zentrale State Machine des Picos.
    Koordiniert Sensoren, Motoren, Netzwerk und Logik.
    """

    # --- Pico-Zustände (Interne Logik) ---
    STATE_STANDBY = "STANDBY"
    STATE_LINE_FOLLOWING = "LINE_FOLLOWING"
    STATE_OBSTACLE = "OBSTACLE"
    STATE_USER_PAUSED = "USER_PAUSED"
    STATE_LINE_LOST = "LINE_LOST"
    STATE_ARRIVED = "ARRIVED"            # Kurzzeitiger Zustand beim Erreichen eines Ziels (Drehung)
    STATE_WAIT_AT_STREET = "WAIT_AT_STREET"
    # Zustände für manuelle Anforderungen per Button
    STATE_MANUAL_GOTO_STREET_REQUEST = "MANUAL_GOTO_STREET_REQUEST"
    STATE_MANUAL_RETURN_HOME_REQUEST = "MANUAL_RETURN_HOME_REQUEST"


    # --- Zustände für die Füllstände (Reporting) ---
    STATE_FULL = "FULL"
    STATE_EMPTIED = "EMPTIED"

    # --- Verbindungs-Zustände (für Server-LED Anzeige) ---
    STATE_CONNECTED = "CONNECTED"
    STATE_NOT_CONNECTED = "NOT_CONNECTED"
    STATE_CONNECTING = "CONNECTING"
    STATE_OFFLINE = "OFFLINE" # Bewusster Offline-Modus

    # --- Protokoll-Befehle (vom Server empfangen) ---
    CMD_GOTO_STREET = "CMD_GOTO_STREET"
    CMD_RETURN_HOME = "CMD_RETURN_HOME"
    CMD_STOP = "CMD_STOP"

    def __init__(
        self,
        pico_led=None,
        pico_led_sm=None,
        connection_led_sm=None,
        sensor_array=None,
        pd_controller=None,
        motor_A=None,
        motor_B=None,
        base_speed=60,
        btn_red=None,
        btn_green=None,
        network_manager=None,
        obstacle_sensor=None,
        buzzer=None,
        pivot_use_line_counter=True,
        pivot_center_count_target=3
        ):
        """
        Initialisiert den GlobalController mit allen Hardware-Komponenten.
        """

        # Hardware-Referenzen speichern
        self.sensor_array = sensor_array
        self.pd_controller = pd_controller
        self.motor_A = motor_A
        self.motor_B = motor_B
        self.base_speed = base_speed
        self.buzzer = buzzer

        # Default-Trim-Faktoren sichern (aus main.py übergeben),
        # damit follow_line() den korrekten Wert wiederherstellen kann.
        self._default_trim_A = motor_A.trim_factor if motor_A else 1.0
        self._default_trim_B = motor_B.trim_factor if motor_B else 1.0

        # Buttons
        self.btn_red = btn_red
        self.btn_green = btn_green

        # Hinderniserkennung
        self.obstacle_sensor = obstacle_sensor
        self.previous_state_before_obstacle = None # Um nach Hindernis in alten Zustand zurückzukehren
        self.obstacle_clear_counter = 0
        self.OBSTACLE_CLEAR_NEEDED = 30 # Anzahl Samples ohne Hindernis, bis weitergefahren wird

        # Füllstandssensorik
        self.fuellstand_sensor = None
        self.fuellstand_prozent = None
        self.deckel_offen = False

        # FULL-Reporting (Entprellung für "Voll"-Meldung)
        self._full_reported = False     # Wurde "Voll" schon an Server gemeldet?
        self._full_candidate = False    # Ist aktuell ein "Voll"-Signal erkannt (Debounce start)?
        self._full_first_ms = 0
        self.FULL_THRESHOLD = 95        # Ab 95% gilt als voll
        self.FULL_RESET_THRESHOLD = 90  # Hysterese: Erst unter 90% gilt wieder als nicht voll
        self.FULL_CONFIRM_MS = 5000     # Muss 5s lang voll sein

        # EMPTY-Reporting (Entprellung für "Leer"-Meldung)
        self._empty_reported = False
        self._empty_candidate = False
        self._empty_first_ms = 0
        self.EMPTY_THRESHOLD = 20       # Unter 20% gilt als leer
        self.EMPTY_RESET_THRESHOLD = 30
        self.EMPTY_CONFIRM_MS = 5000

        # Debug-Ausgabe-Entprellung (verhindert Log-Spam während Debounce-Phase)
        self._debounce_print_interval_ms = 1000
        self._full_debug_last_ms = 0
        self._empty_debug_last_ms = 0


        # Netzwerk-Management
        self.network_manager = network_manager
        self._pending_server_msgs = []  # Warteschlange für ausgehende Nachrichten
        self.MAX_PENDING_SERVER_MSGS = 10

        # TX-State (für robustes Senden bei instabiler Verbindung)
        self._tx_in_progress_msg = None # Aktuell sendende Nachricht
        self._tx_in_progress_buf = b""
        self._tx_in_progress_pos = 0

        # Offline-Handling & Hard-Offline
        # Hard-Offlinemode: WLAN wird für die Fahrt komplett deaktiviert
        self.hard_offline_active = False

        # Pre-Drive Logic: Ablaufsteuerung vor dem Start (ACK senden -> Trennen -> Fahren)
        self._hard_offline_requested = False
        self._hard_offline_ack_required = None
        self._pending_drive_state = None

        self._hard_offline_close_due_ms = 0
        self._hard_offline_request_start_ms = 0

        # Timing für Pre-Drive
        self._HARDOFFLINE_ACK_TIMEOUT_MS = 5000 # Max Zeit warten auf ACK-Sendung
        self._HARDOFFLINE_CLOSE_GRACE_MS = 150  # Zeit zum Schließen des Sockets

        # Server-Handshake (ACK_RECEIVED ...)
        self._ack_received_expected = None
        self._ack_received_ok = False

        # Allgemeiner Verbindungsstatus
        self.offline_mode = False
        self.connection_timeout_ms = 30_000 # 30s ohne Kontakt -> Offline-Modus
        self.last_connection_check_ms = 0

        # Heartbeat (Lebenszeichen an Server)
        self.last_heartbeat_ms = 0
        self.HEARTBEAT_INTERVAL_MS = 2000 # Alle 2s Status senden

        # State Machine Init
        self.state = self.STATE_STANDBY
        self.connection_state = self.STATE_NOT_CONNECTED
        self.target_destination = None # "HOME" oder "STREET"

        # Arrived-Logik (Drehung am Ziel)
        self.arrived_phase = 0
        self.arrived_timer = 0

        # Pivot-Filter (Drehung am Ziel verbessern)
        self.PIVOT_USE_LINE_COUNTER = bool(pivot_use_line_counter)
        self.PIVOT_CENTER_COUNT_TARGET = int(pivot_center_count_target)
        self._pivot_center_count = 0
        self._pivot_centered_last = False

        # Line Lost Logic (Verhalten bei Linienverlust)
        self.LINE_LOST_TIMEOUT_MS = 10_000 # 10s suchen, dann aufgeben
        self._line_lost_start_ms = 0

        # Toleranz für kurze Lücken in der Linie
        self._no_line_count = 0
        self.NO_LINE_NEEDED = 12          # Benötigte Samples ohne Linie für "Lost"
        self.NO_LINE_TIMEOUT_MS = 800     # Zeitfenster für Lückenüberbrückung
        self._no_line_first_ms = 0        
        self._last_position = 0           # Letzte bekannte Position speichern

        # Drive-Start-Seek: Suchverhalten beim Losfahren
        self.DRIVE_START_SEEK_MS = 300  # Kurz blind geradeaus fahren, um Linie zu finden
        self._drive_start_seek_active = False
        self._drive_start_seek_start_ms = 0


        # LEDs & Feedback
        self.pico_led = pico_led
        self.pico_led_sm = pico_led_sm
        self.connection_led_sm = connection_led_sm

        # Pending-LED (Feedback bevor losgefahren wird)
        self._pending_led_active = False
        self._pending_led_is_full = False

        # Debug-Optionen
        self.DEBUG_LINE_FOLLOW = False
        self.DEBUG_LINE_INTERVAL_MS = 200
        self._debug_line_last_ms = 0


        # Initiale Status-Updates an LEDs senden
        self._apply_pico_state()
        self._apply_connection_state()


    # =========================================================================
    # NETZWERK
    # =========================================================================

    def set_network_manager(self, network_manager):
        """Setzt die Referenz auf den NetworkManager."""
        self.network_manager = network_manager

    def is_network_allowed(self):
        """
        Prüft, ob Netzwerkaktivität erlaubt ist.
        Gibt False zurück, wenn der 'Hard-Offline'-Modus (Fahrt) aktiv ist.
        """
        return not self.hard_offline_active

    def _cancel_pending_drive_start(self):
        """Bricht einen geplanten Startvorgang ab (Reset aller Flags)."""
        self._hard_offline_requested = False
        self._hard_offline_ack_required = None
        self._pending_drive_state = None
        self._hard_offline_close_due_ms = 0
        self._hard_offline_request_start_ms = 0
        self._ack_received_expected = None
        self._ack_received_ok = False

    def _arm_hard_offline_after_ack(self, ack_msg, drive_state):
        """
        Startet die Sequenz für den 'Hard-Offline'-Start:
        1. Sende ACK -> 2. Warte auf Bestätigung -> 3. Trenne WLAN -> 4. Fahre los
        """
        self._hard_offline_requested = True
        self._hard_offline_ack_required = ack_msg # Nachricht, die erst raus muss (z.B. "ACK CMD_GOTO_STREET")
        self._pending_drive_state = drive_state   # Zustand, in den danach gewechselt wird (z.B. LINE_FOLLOWING)

        self._hard_offline_close_due_ms = 0
        self._hard_offline_request_start_ms = time.ticks_ms()

        # Erwarte optional ein "ACK_RECEIVED" vom Server zurück
        cmd_part = None
        try:
            cmd_part = ack_msg.split(" ", 1)[1].strip()
        except Exception:
            cmd_part = None

        if cmd_part:
            self._ack_received_expected = "ACK_RECEIVED " + cmd_part
        else:
            self._ack_received_expected = None

        self._ack_received_ok = False

    def _enter_hard_offline_now(self):
        """
        Aktiviert den Hard-Offline-Modus sofort:
        Trennt die Verbindung proaktiv, um Lags während der Fahrt zu verhindern.
        """
        if self.hard_offline_active:
            return

        self.hard_offline_active = True
        self.offline_mode = True # Logischer Offline-Status für LED/Logic
        self._apply_connection_state()

        if self.network_manager:
            try:
                self.network_manager.intentional_disconnect() # Physisches Trennen
            except Exception:
                pass

    def _exit_hard_offline_now(self):
        """
        Beendet den Hard-Offline-Modus (z.B. bei Ankunft):
        Erlaubt und fordert Wiederverbindung an.
        """
        if not self.hard_offline_active and not self._hard_offline_requested:
            return

        self.hard_offline_active = False
        self._cancel_pending_drive_start()

        self.offline_mode = False
        self._apply_connection_state()

        if self.network_manager:
            try:
                self.network_manager.request_reconnect() # Wiederverbinden
            except Exception:
                pass

    def _tick_pre_drive(self):
        """
        Schrittweise Verarbeitung des Startvorgangs (Pre-Drive).
        Sorgt dafür, dass das ACK sicher gesendet wird, bevor getrennt wird.
        """
        now = time.ticks_ms()

        # 1. Versuche, die anstehende Nachricht (ACK) zu senden
        sent_msg = self._try_send_pending_message(return_sent_msg=True)

        # 2. Wenn ACK gesendet wurde, prüfe ob wir auf Server-Antwort warten
        if sent_msg and (sent_msg == self._hard_offline_ack_required):
            # Falls keine Antwort erwartet wird -> Timer für Socket-Close starten
            if not self._ack_received_expected:
                self._hard_offline_close_due_ms = time.ticks_add(now, self._HARDOFFLINE_CLOSE_GRACE_MS)

        # Wenn erwartete Antwort (ACK_RECEIVED) da ist -> Timer für Socket-Close starten
        if self._ack_received_expected and self._ack_received_ok:
            if self._hard_offline_close_due_ms == 0:
                self._hard_offline_close_due_ms = time.ticks_add(now, self._HARDOFFLINE_CLOSE_GRACE_MS)

        # 3. Fallback: Timeout (Start erzwingen, wenn Server nicht antwortet)
        if (self._hard_offline_request_start_ms != 0 and
                time.ticks_diff(now, self._hard_offline_request_start_ms) > self._HARDOFFLINE_ACK_TIMEOUT_MS):
            self._hard_offline_close_due_ms = now

        # 4. Wenn Zeit abgelaufen -> Trennen und Losfahren
        if self._hard_offline_close_due_ms != 0 and time.ticks_diff(now, self._hard_offline_close_due_ms) >= 0:
            drive_state = self._pending_drive_state

            self._enter_hard_offline_now() # Trennen
            self._cancel_pending_drive_start() # Reset

            if drive_state:
                self.set_pico_state(drive_state) # Fahren


    def handle_network_command(self, cmd):
        """
        Verarbeitet eingehende Befehle vom Server.
        """
        cmd = cmd.strip()

        # Server-Bestätigung (Handshake)
        if cmd.startswith("ACK_RECEIVED "):
            if self._hard_offline_requested and self._ack_received_expected and (cmd == self._ack_received_expected):
                self._ack_received_ok = True
            return

        # Befehls-Mapping
        if cmd == "GO_TO_STREET": cmd = self.CMD_GOTO_STREET
        elif cmd == "RETURN_HOME": cmd = self.CMD_RETURN_HOME
        elif cmd == "STOP": cmd = self.CMD_STOP

        # Befehl: Zur Straße
        if cmd == self.CMD_GOTO_STREET:
            # Nur ausführen, wenn wir stehen
            if self.state in (self.STATE_STANDBY, self.STATE_FULL, self.STATE_MANUAL_GOTO_STREET_REQUEST):
                self._queue_server_message("ACK CMD_GOTO_STREET")
                self.target_destination = "STREET"
                # Startsequenz einleiten
                self._arm_hard_offline_after_ack("ACK CMD_GOTO_STREET", self.STATE_LINE_FOLLOWING)
            return

        # Befehl: Nach Hause
        if cmd == self.CMD_RETURN_HOME:
            if self.state in (self.STATE_WAIT_AT_STREET, self.STATE_EMPTIED, self.STATE_MANUAL_RETURN_HOME_REQUEST):
                self._queue_server_message("ACK CMD_RETURN_HOME")
                self.target_destination = "HOME"
                # Startsequenz einleiten
                self._arm_hard_offline_after_ack("ACK CMD_RETURN_HOME", self.STATE_LINE_FOLLOWING)
            return

        # Befehl: Stopp (Not-Aus / Pause)
        if cmd == self.CMD_STOP:
            self._cancel_pending_drive_start() # Start abbrechen falls geplant
            self._stop_motors()
            self.set_pico_state(self.STATE_USER_PAUSED)
            return

        return

    def _queue_server_message(self, msg):
        """Fügt Nachricht in Sendepuffer ein."""
        if len(self._pending_server_msgs) >= self.MAX_PENDING_SERVER_MSGS:
            return False
        self._pending_server_msgs.append(msg)
        return True

    def _try_send_pending_message(self, return_sent_msg=False):
        """
        Versucht Nachrichten zu senden.
        Unterstützt 'Partial Sends' (wenn Puffer voll) und Wiederholung bei Fehlern.
        """
        if not self._pending_server_msgs or not self.network_manager:
            return None

        sock = self.network_manager.get_socket()
        if not sock:
            return None

        # Nachricht vorbereiten (falls nicht schon im Gange)
        if self._tx_in_progress_msg is None:
            self._tx_in_progress_msg = self._pending_server_msgs[0]
            self._tx_in_progress_buf = (self._tx_in_progress_msg + "\n").encode()
            self._tx_in_progress_pos = 0

        try:
            # Sende verbleibenden Teil
            remaining = self._tx_in_progress_buf[self._tx_in_progress_pos :]
            if not remaining:
                # Bereits fertig (Sicherheitscheck)
                sent_msg = self._tx_in_progress_msg
                if self._pending_server_msgs and self._pending_server_msgs[0] == sent_msg:
                    self._pending_server_msgs.pop(0) # Aus Queue entfernen
                self._tx_in_progress_msg = None
                self._tx_in_progress_buf = b""
                self._tx_in_progress_pos = 0
                return sent_msg if return_sent_msg else None

            n = sock.send(remaining)

            if n is None or n == 0:
                return None

            self._tx_in_progress_pos += n

            # Noch nicht alles gesendet?
            if self._tx_in_progress_pos < len(self._tx_in_progress_buf):
                return None

            # Erfolg: Nachricht entfernen und Reset
            sent_msg = self._tx_in_progress_msg
            if self._pending_server_msgs and self._pending_server_msgs[0] == sent_msg:
                self._pending_server_msgs.pop(0)

            self._tx_in_progress_msg = None
            self._tx_in_progress_buf = b""
            self._tx_in_progress_pos = 0

            return sent_msg if return_sent_msg else None

        except OSError as e:
            # Fehlerbehandlung: Would-Block ignorieren, bei echtem Fehler Disconnect melden
            err = e.args[0] if e.args else None
            if err in (11, 35, 10035): # EAGAIN / EWOULDBLOCK
                return None

            # Bei Fehler: Reset, aber Nachricht NICHT löschen (Retry beim nächsten Mal)
            self._tx_in_progress_msg = None
            self._tx_in_progress_buf = b""
            self._tx_in_progress_pos = 0

            try:
                self.network_manager.mark_server_disconnected()
            except Exception:
                pass

            return None


    def _send_heartbeat(self):
        """Sendet regelmäßig Status-Updates (Heartbeat)."""
        if self.offline_mode:
            return

        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_heartbeat_ms) <= self.HEARTBEAT_INTERVAL_MS:
            return

        if self.network_manager:
            sock = self.network_manager.get_socket()
            if sock:
                try:
                    sock.send(("STATUS:%s\n" % self.state).encode())
                except OSError:
                    self.network_manager.mark_server_disconnected()

        self.last_heartbeat_ms = now

    def _manage_connection_mode(self):
        """
        Verwaltet den Verbindungsstatus basierend auf Timeouts.
        Schaltet in den 'Offline-Modus', wenn der Server zu lange nicht erreichbar ist,
        um unnötige Verbindungsversuche zu vermeiden.
        """
        now = time.ticks_ms()

        # Wenn wir verbunden sind, aktualisieren wir den Zeitstempel "letzte Prüfung"
        if self.connection_state == self.STATE_CONNECTED:
            self.last_connection_check_ms = now
            # Falls wir vorher im Offline-Modus waren, jetzt deaktivieren
            if self.offline_mode:
                self.offline_mode = False
                if self.network_manager:
                    self.network_manager.set_verbose(False) # Weniger Logs im stabilen Betrieb
                self._apply_connection_state()
            return

        # Initialisierung des Timers beim ersten Aufruf
        if self.last_connection_check_ms == 0:
            self.last_connection_check_ms = now

        # Wenn wir NICHT verbunden sind und NICHT offline: Prüfen auf Timeout
        if not self.offline_mode:
            # Wenn Timeout abgelaufen ist -> Offline-Modus aktivieren
            if time.ticks_diff(now, self.last_connection_check_ms) > self.connection_timeout_ms:
                self.offline_mode = True
                if self.network_manager:
                    self.network_manager.set_verbose(False)
                self._apply_connection_state()

    def set_connection_state(self, new_state):
        """Setzt den internen Verbindungsstatus und aktualisiert die Status-LED."""
        if new_state == self.connection_state:
            return
        self.connection_state = new_state
        self._apply_connection_state()

    def notify_connection_lost(self):
        """
        Wird vom NetworkManager aufgerufen, wenn der Socket bricht (z.B. WLAN weg).
        Strategie: Nicht sofort aufgeben (OFFLINE), sondern Status 'NOT_CONNECTED' setzen
        und Timer starten. Erst nach Ablauf des Timeouts (in _manage_connection_mode) wird 'OFFLINE' gesetzt.
        """
        now = time.ticks_ms()

        # Startpunkt für den Timeout auf "jetzt" setzen (Countdown beginnt ab Disconnect)
        self.last_connection_check_ms = now

        # NICHT: self.offline_mode = True  (das würde den Timeout aushebeln)

        # LED/State: solange versuchen wir zu reconnecten (NOT_CONNECTED/CONNECTING),
        # OFFLINE erst, wenn _manage_connection_mode() nach connection_timeout_ms auslöst.
        self.set_connection_state(self.STATE_NOT_CONNECTED)

        if self.network_manager:
            try:
                self.network_manager.set_verbose(False)
            except Exception:
                pass

        self._apply_connection_state()


    def _apply_connection_state(self):
        """Überträgt den logischen Verbindungsstatus auf die physische LED (z.B. Blaues Blinken)."""
        if self.connection_led_sm is None:
            return
        if self.offline_mode:
            self.connection_led_sm.set_connection_state(self.STATE_OFFLINE)
        else:
            self.connection_led_sm.set_connection_state(self.connection_state)

    # Wird in main.py im Netzwerk-Takt aufgerufen
    def network_tick(self):
        """
        Zentrale Methode für Netzwerk-Aufgaben.
        Wird periodisch vom Main-Loop aufgerufen (z.B. alle 50ms).
        """
        # Während Hard-Offlinemode (Fahren) keinerlei Netzwerk-Logik ausführen
        # Dies spart Rechenzeit für die Motorsteuerung.
        if self.hard_offline_active:
            return

        # Timeouts prüfen
        self._manage_connection_mode()

        # Pre-Drive Phase: nur ACK-Handling, kein Heartbeat
        # Wenn wir gerade dabei sind, loszufahren (ACK senden -> Disconnect),führen wir nur diese spezielle Logik aus.
        if self._hard_offline_requested:
            self._tick_pre_drive()
            return

        # Normalbetrieb: Warteschlange abarbeiten und Heartbeat senden
        self._try_send_pending_message()
        self._send_heartbeat()


    # Backwards compatibility (falls irgendwo noch networktick() verwendet wird)
    def networktick(self):
        return self.network_tick()

    # =========================================================================
    # STATE / LED
    # =========================================================================

    def set_pico_state(self, new_state):
        """
        Zentrale Methode zum Wechseln des Roboter-Zustands.
        Hier werden Hardware-Aktionen (Motoren stopp, LED, Buzzer) ausgelöst,
        die mit dem Zustandswechsel verbunden sind.
        """
        if new_state == self.state:
            return

        old_state = self.state

        # Drive-Start-Seek standardmäßig zurücksetzen (damit kein Zustand "hängen bleibt")
        self._drive_start_seek_active = False
        self._drive_start_seek_start_ms = 0

        # Nur beim Start in den Fahrmodus: Prüfen, ob wir überhaupt eine Linie haben.
        # Wenn nicht -> Suchmodus aktivieren.
        if new_state == self.STATE_LINE_FOLLOWING and old_state in (
            self.STATE_STANDBY, self.STATE_FULL, self.STATE_EMPTIED, self.STATE_WAIT_AT_STREET, 
            self.STATE_MANUAL_GOTO_STREET_REQUEST, self.STATE_MANUAL_RETURN_HOME_REQUEST, self.STATE_OBSTACLE, self.STATE_USER_PAUSED):

            pos = self.sensor_array.get_position() if self.sensor_array else None
            if pos is None:
                self._drive_start_seek_active = True
                self._drive_start_seek_start_ms = time.ticks_ms()

        # State wirklich erst jetzt umstellen
        self.state = new_state

        # Debounce sauber neu starten, wenn wir in die Mess-Zustände wechseln
        # (Verhindert, dass alte Messwerte sofort wieder triggern)
        if new_state == self.STATE_STANDBY:
            self._full_candidate = False
            self._full_first_ms = 0
            self._full_debug_last_ms = 0
            # Werte zurücksetzen, damit STANDBY->FULL wieder möglich ist
            self._full_reported = False

        if new_state == self.STATE_WAIT_AT_STREET:
            self._empty_candidate = False
            self._empty_first_ms = 0
            self._empty_debug_last_ms = 0
            # Werte zurücksetzen, damit WAIT->EMPTIED wieder möglich ist
            self._empty_reported = False

        # Buzzer-Feedback abspielen (z.B. Piepen bei Start)
        self._handle_buzzer_state_change(old_state, new_state)

        # Motoren stoppen, wenn pausiert wird
        if new_state == self.STATE_USER_PAUSED:
            self._stop_motors()

        # PID-Regler zurücksetzen, wenn die Linie verloren oder neu gefunden wurde
        if new_state == self.STATE_LINE_LOST:
            self._line_lost_start_ms = time.ticks_ms()
            if self.pd_controller:
                self.pd_controller.reset()
        elif new_state == self.STATE_LINE_FOLLOWING:
            if self.pd_controller:
                self.pd_controller.reset()
        else:
            if new_state in (self.STATE_STANDBY, self.STATE_WAIT_AT_STREET, self.STATE_ERROR, self.STATE_USER_PAUSED):
                self._line_lost_start_ms = 0

        # Sobald der Pico wirklich losfährt -> Pending-Overlay (Blinken) aus
        if new_state in (self.STATE_LINE_FOLLOWING, self.STATE_LINE_LOST):
            self._stop_pending_led_feedback()


        if new_state == self.STATE_ARRIVED:
            self.arrived_phase = 0
            self.arrived_timer = 0
            self._pivot_center_count = 0
            self._pivot_centered_last = False
            # Nachricht an Server senden: "ARRIVED: HOME" oder "ARRIVED: STREET"
            dest = self.target_destination if self.target_destination is not None else "UNKNOWN"
            self._queue_server_message("ARRIVED: %s" % dest)

        # Hard-Offlinemode-Policy:
        # Wenn wir in einen ruhenden Zustand wechseln, schalten wir das Netzwerk wieder ein (Exit Hard-Offline).
        if new_state in (
            self.STATE_ARRIVED,
            self.STATE_OBSTACLE,
            self.STATE_USER_PAUSED,
            self.STATE_STANDBY,
            self.STATE_WAIT_AT_STREET,
            self.STATE_FULL,
            self.STATE_EMPTIED,
        ):
            # Sobald nicht mehr gefahren wird: wieder online gehen (reconnect erlauben)
            if self.hard_offline_active or self._hard_offline_requested:
                self._exit_hard_offline_now()


        elif new_state in (self.STATE_LINE_FOLLOWING, self.STATE_LINE_LOST):
            # Wenn wir lokal starten (Button) und kein Server-Befehl vorlag (kein _hard_offline_requested),
            # schalten wir hier sofort hart offline, um CPU für Motoren freizugeben.
            if (not self.hard_offline_active) and (not self._hard_offline_requested):
                self._enter_hard_offline_now()

        # Status auf die LEDs übertragen
        self._apply_pico_state()


    def _apply_pico_state(self):
        """Aktualisiert die Zustandsmaschine der Pico-Status-LED (z.B. Grün, Gelb blinkend)."""
        if self.pico_led_sm is not None:
            self.pico_led_sm.set_pico_state(self.state)

    def set_fuellstand_sensor(self, fuellstand_sensor):
        self.fuellstand_sensor = fuellstand_sensor

    def _compute_pending_is_full(self):
        """
        Entscheidet, ob die LED "Voll" (Rot blinkend) oder "Leer" (Grün blinkend) anzeigen soll,
        während auf einen Startbefehl gewartet wird.
        Priorität: 1. Deckel offen -> Leer, 2. Messwert, 3. Letzter Zustand.
        """
        # Voll/Leer-Entscheidung für das Blink-Feedback
        # Priorität: Messwert -> sonst latched state/report
        if self.deckel_offen or (self.fuellstand_prozent is None):
            if self.state == self.STATE_FULL or self._full_reported:
                return True
            if self.state == self.STATE_EMPTIED or self._empty_reported:
                return False
            return False  # Default: "leer"

        if self.fuellstand_prozent >= self.FULL_THRESHOLD:
            return True
        if self.fuellstand_prozent <= self.EMPTY_THRESHOLD:
            return False

        # Zwischenbereich: nimm latched state/report, sonst Default "leer"
        if self.state == self.STATE_FULL or self._full_reported:
            return True
        if self.state == self.STATE_EMPTIED or self._empty_reported:
            return False
        return False

    def _start_pending_led_feedback(self):
        """Aktiviert das visuelle Feedback (Blinken), während auf Bestätigung/Start gewartet wird."""
        self._pending_led_active = True
        self._pending_led_is_full = self._compute_pending_is_full()
        if self.pico_led_sm:
            self.pico_led_sm.set_pending_feedback(True, self._pending_led_is_full)

    def _stop_pending_led_feedback(self):
        """Deaktiviert das Pending-Blinken."""
        self._pending_led_active = False
        if self.pico_led_sm:
            self.pico_led_sm.set_pending_feedback(False, False)

    def _refresh_pending_led_feedback(self):
        """Aktualisiert den Status des Blinkens (z.B. wenn sich der Füllstand ändert, während man wartet)."""
        if not self._pending_led_active:
            return
        new_is_full = self._compute_pending_is_full()
        if new_is_full != self._pending_led_is_full:
            self._pending_led_is_full = new_is_full
            if self.pico_led_sm:
                self.pico_led_sm.set_pending_feedback(True, self._pending_led_is_full)

    # =========================================================================
    # HARDWARE / INPUT
    # =========================================================================

    def _stop_motors(self):
        """Stoppt beide Motoren sofort."""
        if self.motor_A:
            self.motor_A.stop()
        if self.motor_B:
            self.motor_B.stop()

    def _pivot_right_non_blocking(self):
        """
        Lässt den Roboter auf der Stelle nach rechts drehen (Pivot).
        Wird für Suchmanöver verwendet.
        """
        if self.motor_A and self.motor_B:
            self.motor_A.forward(50)  # Links vorwärts
            self.motor_B.backward(50) # Rechts rückwärts


    def _handle_buzzer_state_change(self, old_state, new_state):
        """
        Spielt akustische Signale ab, abhängig vom Zustandswechsel.
        """
        if not self.buzzer:
            return

        # Definition der Beep-Muster: [(TonAn, DauerMs), (TonAus, DauerMs), ...]
        BEEP_SHORT = [(True, 100), (False, 1)]
        BEEP_MED = [(True, 200), (False, 1)]
        BEEP_LONG = [(True, 400), (False, 1)]
        DOUBLE = [(True, 100), (False, 100), (True, 100), (False, 1)]

        # Wenn Hindernis beseitigt wurde -> Alarm stoppen
        if old_state == self.STATE_OBSTACLE and new_state != self.STATE_OBSTACLE:
            self.buzzer.stop()

        # Neuer Zustand -> Passendes Signal abspielen
        if new_state == self.STATE_OBSTACLE:
            # Bei Hindernis: Doppel-Beep wiederholen
            self.buzzer.play(DOUBLE, repeat=True, repeat_min_ms=2000, repeat_max_ms=3000)
            return
        if new_state == self.STATE_ARRIVED:
            self.buzzer.play(BEEP_MED)
            return
        if new_state == self.STATE_USER_PAUSED:
            self.buzzer.play(BEEP_SHORT)
            return
        if new_state == self.STATE_LINE_FOLLOWING and old_state != self.STATE_LINE_LOST:
            # Langer Beep beim Losfahren (aber nicht beim Wiederfinden der Linie)
            self.buzzer.play(BEEP_LONG)
            return
        if new_state in (self.STATE_MANUAL_GOTO_STREET_REQUEST, self.STATE_MANUAL_RETURN_HOME_REQUEST):
            self.buzzer.play(BEEP_SHORT)
            return


    def _handle_button_logic(self):
        """
        Verarbeitet Eingaben der physischen Buttons (Grün/Rot).
        Steuert Start, Stopp, Reset und Offline-Modus.
        """
        # GRÜN (Start / Bestätigen)
        if self.btn_green:
            press = self.btn_green.check_press_type()
            if press in ("SHORT", "LONG"):
                # In Ruhe-Zuständen: Aktion auslösen
                if self.state in (self.STATE_STANDBY, self.STATE_WAIT_AT_STREET, self.STATE_FULL, self.STATE_EMPTIED):
                    
                    # Long Press: Offline-Modus erzwingen, falls keine Verbindung besteht
                    if press == "LONG" and self.connection_state != self.STATE_CONNECTED:
                        self.offline_mode = True
                        self.set_connection_state(self.STATE_OFFLINE)
                        if self.network_manager:
                            self.network_manager.set_verbose(False)
                        return

                    # Short Press (Connected): Manuellen Start anfordern (via Server)
                    if press == "SHORT" and self.connection_state == self.STATE_CONNECTED:
                        self._start_pending_led_feedback() # Visuelles Feedback (Blinken)

                        if self.state == self.STATE_STANDBY:
                            self.target_destination = "STREET"
                            self.set_pico_state(self.STATE_MANUAL_GOTO_STREET_REQUEST)
                        elif self.state == self.STATE_WAIT_AT_STREET:
                            self.target_destination = "HOME"
                            self.set_pico_state(self.STATE_MANUAL_RETURN_HOME_REQUEST)

                        return
                    
                    # Short Press (Offline): Lokal starten (ohne Server)
                    if press == "SHORT" and self.offline_mode:
                        if self.state in (self.STATE_STANDBY, self.STATE_FULL):
                            self.target_destination = "STREET"
                            self.set_pico_state(self.STATE_LINE_FOLLOWING)
                        elif self.state in (self.STATE_WAIT_AT_STREET, self.STATE_EMPTIED):
                            self.target_destination = "HOME"
                            self.set_pico_state(self.STATE_LINE_FOLLOWING)
                        return

                # Wenn pausiert: Fortsetzen
                if self.state == self.STATE_USER_PAUSED:
                    self.set_pico_state(self.STATE_LINE_FOLLOWING)
                    return

        # ROT (Stop / Reset)
        if self.btn_red:
            press = self.btn_red.check_press_type()
            if press == "LONG":
                # Alles abbrechen und zurücksetzen
                self._stop_motors()
                self.set_pico_state(self.STATE_STANDBY)
                return
            if press == "SHORT":
                # Pause / Stop
                if self.state in (self.STATE_LINE_FOLLOWING, self.STATE_LINE_LOST, self.STATE_OBSTACLE):
                    self.set_pico_state(self.STATE_USER_PAUSED)

    # =========================================================================
    # SENSOREN / LOGIK
    # =========================================================================

    def _check_obstacle(self):
        """
        Prüft den Ultraschallsensor auf Hindernisse in Fahrtrichtung.
        Löst bei < 30cm den OBSTACLE-Zustand aus.
        """
        if not self.obstacle_sensor:
            return False

        self.obstacle_sensor.run() # Trigger Messung
        dist = self.obstacle_sensor.read_distance_cm()
        if dist is not None and dist < 30.0:
            self.previous_state_before_obstacle = self.state
            self.obstacle_clear_counter = 0
            self.set_pico_state(self.STATE_OBSTACLE)
            return True
        return False

    def _check_all_sensors_active(self):
        """
        Prüft, ob alle Liniensensoren gleichzeitig aktiv sind.
        Dies deutet oft auf eine Querlinie (Zielmarkierung) oder Anheben hin.
        """
        if not self.sensor_array:
            return False
        s1 = self.sensor_array.sensor_links_aussen.value()
        s2 = self.sensor_array.sensor_links_mitte.value()
        s3 = self.sensor_array.sensor_mitte.value()
        s4 = self.sensor_array.sensor_rechts_mitte.value()
        s5 = self.sensor_array.sensor_rechts_aussen.value()
        return (s1 + s2 + s3 + s4 + s5) == 5

    def _handle_full_reporting(self):
        """
        Überwacht den Füllstand und löst bei "Voll" den Zustandswechsel aus.
        Beinhaltet Entprellung (Debounce), um Fehlalarme durch wackelnden Müll zu verhindern.
        """
        # Nur prüfen, wenn wir zuhause stehen
        if self.state not in (self.STATE_STANDBY, self.STATE_MANUAL_GOTO_STREET_REQUEST):
            return

        # Keine Messung oder Deckel offen -> Abbruch
        if self.fuellstand_prozent is None or self.deckel_offen:
            self._full_candidate = False
            return

        # Reset Latch, wenn Müll wieder leer wird (Hysterese)
        if self._full_reported and (self.fuellstand_prozent <= self.FULL_RESET_THRESHOLD):
            self._full_reported = False

        if self._full_reported:
            return

        now = time.ticks_ms()
        is_full = self.fuellstand_prozent >= self.FULL_THRESHOLD

        # Candidate starten (erstes Mal erkannt)
        if not self._full_candidate:
            if is_full:
                self._full_candidate = True
                self._full_first_ms = now
                self._full_debug_last_ms = 0
                print(f"[DEBOUNCE][FULL] Start: {self.fuellstand_prozent}% (>= {self.FULL_THRESHOLD}%). Warte {self.FULL_CONFIRM_MS}ms...")
            return

        # Candidate läuft: wenn Bedingung zwischendurch nicht mehr stimmt -> abbrechen
        if not is_full:
            print(f"[DEBOUNCE][FULL] Abbruch: {self.fuellstand_prozent}% (< {self.FULL_THRESHOLD}%).")
            self._full_candidate = False
            return

        # Candidate läuft: während Entprellzeit regelmäßig Debug ausgeben
        elapsed = time.ticks_diff(now, self._full_first_ms)
        if self._full_debug_last_ms == 0 or time.ticks_diff(now, self._full_debug_last_ms) >= self._debounce_print_interval_ms:
            remaining = self.FULL_CONFIRM_MS - elapsed
            if remaining < 0:
                remaining = 0
            print(f"[DEBOUNCE][FULL] {self.fuellstand_prozent}% (>= {self.FULL_THRESHOLD}%) noch {remaining}ms")
            self._full_debug_last_ms = now

        # Bestätigung nach Ablauf der Entprellzeit -> Zustandswechsel
        if elapsed >= self.FULL_CONFIRM_MS:
            self._full_reported = True
            self._full_candidate = False
            print(f"[DEBOUNCE][FULL] Bestätigt: {self.fuellstand_prozent}% -> STATE_FULL")
            self.set_pico_state(self.STATE_FULL)


    def _handle_empty_reporting(self):
        """
        Überwacht, ob die Mülltonne entleert wurde.
        Ähnlich wie _handle_full_reporting, nur umgekehrte Logik.
        """
        # Nur prüfen, wenn wir an der Straße warten
        if self.state not in (self.STATE_WAIT_AT_STREET, self.STATE_MANUAL_RETURN_HOME_REQUEST):
            self._empty_candidate = False
            return

        # Deckel offen oder keine Daten -> ignorieren
        if self.deckel_offen or self.fuellstand_prozent is None:
            self._empty_candidate = False
            return

        now = time.ticks_ms()
        is_empty = self.fuellstand_prozent <= self.EMPTY_THRESHOLD
        not_empty_again = self.fuellstand_prozent >= self.EMPTY_RESET_THRESHOLD # Hysterese

        if self._empty_reported and not_empty_again:
            self._empty_reported = False

        if self._empty_reported:
            return

        # Candidate starten
        if not self._empty_candidate:
            if is_empty:
                self._empty_candidate = True
                self._empty_first_ms = now
                self._empty_debug_last_ms = 0
                print(f"[DEBOUNCE][EMPTY] Start: {self.fuellstand_prozent}% (<= {self.EMPTY_THRESHOLD}%). Warte {self.EMPTY_CONFIRM_MS}ms...")
            return

        # Candidate läuft: Abbruch wenn Bedingung verletzt
        if not is_empty:
            print(f"[DEBOUNCE][EMPTY] Abbruch: {self.fuellstand_prozent}% (> {self.EMPTY_THRESHOLD}%).")
            self._empty_candidate = False
            return

        # Debug-Ausgabe
        elapsed = time.ticks_diff(now, self._empty_first_ms)
        if self._empty_debug_last_ms == 0 or time.ticks_diff(now, self._empty_debug_last_ms) >= self._debounce_print_interval_ms:
            remaining = self.EMPTY_CONFIRM_MS - elapsed
            if remaining < 0:
                remaining = 0
            print(f"[DEBOUNCE][EMPTY] {self.fuellstand_prozent}% (<= {self.EMPTY_THRESHOLD}%) noch {remaining}ms")
            self._empty_debug_last_ms = now

        # Bestätigung -> State EMPTIED
        if elapsed >= self.EMPTY_CONFIRM_MS:
            self._empty_reported = True
            self._empty_candidate = False
            print(f"[DEBOUNCE][EMPTY] Bestätigt: {self.fuellstand_prozent}% -> STATE_EMPTIED")
            self.set_pico_state(self.STATE_EMPTIED)


    def apply_speeds(self, left, right):
        """
        Steuert die Motoren direkt an.
        Konvertiert vorzeichenbehaftete Geschwindigkeiten in Forward/Backward-Befehle.
        - left: Geschwindigkeit links (-100 bis 100)
        - right: Geschwindigkeit rechts (-100 bis 100)
        """
        # links (Motor A)
        if left == 0:
            self.motor_A.stop()
        elif left > 0:
            self.motor_A.forward(left)
        else:
            self.motor_A.backward(-left)

        # rechts (Motor B)
        if right == 0:
            self.motor_B.stop()
        elif right > 0:
            self.motor_B.forward(right)
        else:
            self.motor_B.backward(-right)

    def follow_line(self):
        """
        Kernfunktion der Linienverfolgung.
        Liest Sensoren, berechnet PID-Korrektur und steuert Motoren.
        Rückgabe: True wenn Linie gefunden/verfolgt, False wenn Linie verloren.
        """
        if not self.sensor_array or not self.pd_controller:
            return False

        now = time.ticks_ms()
        fallback_used = False

        # 1) Position holen
        # Liefert Wert zwischen -100 (ganz links) und +100 (ganz rechts), 0 ist mittig.
        position = self.sensor_array.get_position()

        # 2) Line-lost / Fallback sauber behandeln
        # Wenn keine Linie gesehen wird (position is None), versuchen wir kurzzeitig die letzte bekannte Position zu nutzen.
        if position is None:
            if self._no_line_first_ms == 0:
                self._no_line_first_ms = now
            self._no_line_count += 1

            # Innerhalb des Toleranzfensters (NO_LINE_TIMEOUT_MS): noch NICHT regeln -> line_found=False
            if not (self._no_line_count >= self.NO_LINE_NEEDED and
                    time.ticks_diff(now, self._no_line_first_ms) >= self.NO_LINE_TIMEOUT_MS):
                return False

            # Nach Ablauf der Toleranz: Fallback nutzen -> Wir tun so, als wären wir an der letzten Position
            position = self._last_position
            fallback_used = True

        else:
            # Linie da: Timer zurücksetzen + aktuelle Position merken
            self._no_line_count = 0
            self._no_line_first_ms = 0
            self._last_position = position

        # 3) PD-Regler berechnen
        # Berechnet die Korrektur basierend auf der Abweichung vom Sollwert (0)
        target = self.sensor_array.target_position
        correction = self.pd_controller.calculate(position, target, now_ms=now)

        # Motorgeschwindigkeiten berechnen (Differential Drive)
        left  = self.base_speed - correction
        right = self.base_speed + correction

        # Sharp right turn assist (Spezialfall):
        # Wenn das kurveninnere Rad (rechts) fast stehen bleibt, drehen wir es rückwärts (Pivot),
        # um engere Kurven zu ermöglichen.
        if right <= 5:          # Schwelle ab wann Pivot greift
            left = 100          # Außenrad volle Kraft
            right = -20         # Innenrad rückwärts drehen

        # Begrenzung auf zulässigen Bereich (-100 bis +100)
        if left < -100: left = -100
        if left >  100: left =  100
        if right < -100: right = -100
        if right >  100: right =  100

        left = int(left)
        right = int(right)

        # Workaround für spezifische Sensor-Bits (optionales Feintuning)
        bits = getattr(self.sensor_array, "_cached_bits", None)

        # Default-Trim wiederherstellen
        self.motor_A.trim_factor = self._default_trim_A  # Standard-Trim

        # Vorheriger, falscher Wert
        # self.motor_A.trim_factor = 0.8 # Standard-Trim

        # Spezialfall: Nur äußerster rechter Sensor aktiv -> Enge Rechtskurve nötig
        if bits == 0b00001:
            self.motor_A.trim_factor = 1.2 # Linken Motor boosten
            left = 100

        # 4) Motoren ansteuern
        self.apply_speeds(left, right)

        # Debug-Ausgabe (nur wenn aktiviert und Intervall erreicht)
        if self.DEBUG_LINE_FOLLOW and time.ticks_diff(now, self._debug_line_last_ms) >= self.DEBUG_LINE_INTERVAL_MS:
            flag = "*" if fallback_used else ""
            print("[LINE]", "pos=", position, flag, "target=", target, "corr=%.2f" % float(correction),
                "base=", int(self.base_speed), "L=", left, "R=", right)
            self._debug_line_last_ms = now

        return True

    # =========================================================================
    # RUN (Fahr-Tick) – ohne Netzwerk
    # =========================================================================

    def run(self):
        """
        Hauptzyklus der Roboter-Steuerung.
        Wird von main.py periodisch aufgerufen (z.B. alle 20ms).
        Führt Sensoren, Hardware, Input und Logik nacheinander aus.
        """
        self._step_sensors()
        self._step_hardware()
        self._step_input()
        self._step_logic()

    def _step_sensors(self):
        """Liest Füllstandssensor aus (nur im Stand, um Messfehler durch Vibration zu vermeiden)."""
        if self.fuellstand_sensor and self.state in (self.STATE_STANDBY, self.STATE_WAIT_AT_STREET, self.STATE_FULL,
                                                     self.STATE_EMPTIED, self.STATE_MANUAL_GOTO_STREET_REQUEST, 
                                                     self.STATE_MANUAL_RETURN_HOME_REQUEST):
            self.fuellstand_sensor.run()
            self.fuellstand_prozent = self.fuellstand_sensor.fuellstand_prozent
            self.deckel_offen = self.fuellstand_sensor.deckel_offen
            
            # Aktualisiert Logik basierend auf neuen Messwerten
            self._refresh_pending_led_feedback()
            self._handle_full_reporting()
            self._handle_empty_reporting()


    def _step_hardware(self):
        """Aktualisiert nicht-blockierende Hardware (LEDs blinken lassen, Buzzer)."""
        if self.pico_led_sm:
            self.pico_led_sm.run()
        if self.connection_led_sm:
            self.connection_led_sm.run()
        if self.buzzer:
            self.buzzer.run()

    def _step_input(self):
        """Prüft Button-Eingaben."""
        self._handle_button_logic()

    def _step_logic(self):
        """
        Verzweigt in die spezifische Logik des aktuellen Zustands.
        State-Machine Pattern.
        """
        if self.state == self.STATE_ERROR:
            self._logic_error()
        elif self.state == self.STATE_USER_PAUSED:
            self._logic_user_paused()
        elif self.state == self.STATE_LINE_FOLLOWING:
            self._logic_line_following()
        elif self.state == self.STATE_LINE_LOST:
            self._logic_line_lost()
        elif self.state == self.STATE_OBSTACLE:
            self._logic_obstacle()
        elif self.state == self.STATE_ARRIVED:
            self._logic_arrived()
        elif self.state == self.STATE_STANDBY:
            self._logic_standby()
        elif self.state == self.STATE_WAIT_AT_STREET:
            self._logic_wait_at_street()

    # -----------------------------------------------------------------
    # Zustandshandler
    # -----------------------------------------------------------------

    def _logic_error(self):
        self._stop_motors()

    def _logic_user_paused(self):
        self._stop_motors()

    def _logic_line_following(self):
        """Logik während der Fahrt auf der Linie."""
        
        # 1. Priorität: Hindernisse?
        if self._check_obstacle():
            return

        # 2. Priorität: Ziel erreicht? (Alle Sensoren aktiv -> Querlinie)
        if self._check_all_sensors_active():
            self._stop_motors()
            self.set_pico_state(self.STATE_ARRIVED)
            return
        
        # 3. Anfahrhilfe:
        # Wenn beim Losfahren keine Linie da ist, fahren wir kurz blind geradeaus,
        # in der Hoffnung, die Linie zu finden.
        if self._drive_start_seek_active:
            now = time.ticks_ms()

            # Safety: Motoren müssen existieren
            if not (self.motor_A and self.motor_B):
                self._drive_start_seek_active = False
                self._stop_motors()
                return

            pos = self.sensor_array.get_position() if self.sensor_array else None

            # Sobald Linie gefunden: Anfahren beenden und normal regeln
            if pos is not None:
                self._drive_start_seek_active = False
            else:
                # Noch keine Linie: für kurze Zeit geradeaus fahren
                if time.ticks_diff(now, self._drive_start_seek_start_ms) < self.DRIVE_START_SEEK_MS:
                    self.motor_A.forward(self.base_speed)
                    self.motor_B.forward(self.base_speed)
                    return

                # Timeout: Anfahren beenden, ab hier normale LINE_FOLLOWING-Logik greifen lassen
                self._drive_start_seek_active = False

        # 4. Normale Linienverfolgung
        line_found = self.follow_line()
        if not line_found:
            # Wenn Follow-Line fehlschlägt (Timeout), wechseln wir den Zustand
            self.set_pico_state(self.STATE_LINE_LOST)


    def _logic_line_lost(self):
        """Logik wenn die Linie verloren wurde (Suchmodus)."""
        if self._check_obstacle():
            return

        # Linie wieder da -> zurück in Regelbetrieb
        if self.sensor_array and (self.sensor_array.get_position() is not None):
            self.set_pico_state(self.STATE_LINE_FOLLOWING)
            return

        # Versuche weiter zu regeln (mit Fallback-Werten)
        line_found_or_fallback = self.follow_line()
        
        # Wenn auch Fallback nicht mehr greift (oder wir bewusst "blind" fahren wollen):
        if not line_found_or_fallback:
            # Gap-Überbrückung: wir fahren einfach geradeaus weiter, vielleicht kommt die Linie wieder
            if self.motor_A and self.motor_B:
                self.motor_A.forward(self.base_speed)
                self.motor_B.forward(self.base_speed)

        # Timeout: Wenn Linie zu lange weg ist -> Not-Aus (Standby)
        if self._line_lost_start_ms != 0:
            now = time.ticks_ms()
            if time.ticks_diff(now, self._line_lost_start_ms) > self.LINE_LOST_TIMEOUT_MS:
                self._stop_motors()
                self.set_pico_state(self.STATE_STANDBY)


    def _logic_obstacle(self):
        """Logik wenn ein Hindernis erkannt wurde."""
        self._stop_motors() # Erstmal stehen bleiben

        if not self.obstacle_sensor:
            self.set_pico_state(self.STATE_LINE_FOLLOWING)
            return

        self.obstacle_sensor.run()

        # Prüfen, ob Weg wieder frei ist
        if self.obstacle_sensor.has_new_sample():
            dist = self.obstacle_sensor.read_distance_cm()
            if dist is None or dist > 35.0:
                self.obstacle_clear_counter += 1 # Zähler hochzählen (Entprellung)
            else:
                self.obstacle_clear_counter = 0 # Reset wenn Hindernis noch da

            # Wenn lange genug frei -> Weiterfahren
            if self.obstacle_clear_counter >= self.OBSTACLE_CLEAR_NEEDED:
                self.obstacle_clear_counter = 0
                if self.previous_state_before_obstacle:
                    self.set_pico_state(self.previous_state_before_obstacle)
                else:
                    self.set_pico_state(self.STATE_LINE_FOLLOWING)
                self.previous_state_before_obstacle = None

    def _logic_arrived(self):
        """
        Logik für das Ankunftsmanöver (Drehen um 180 Grad / Pivot).
        Ablauf: Stop -> Warten -> Drehen -> Zentrieren auf Linie.
        """
        current_time = time.ticks_ms()

        # Phase 0: Initiale Pause
        if self.arrived_phase == 0:
            self._stop_motors()
            self.arrived_timer = current_time
            self._pivot_right_non_blocking() # Drehung schonmal anstoßen
            self.arrived_phase = 1
            return

        # Phase 1: Warten (Drehung läuft eventuell schon an)
        if self.arrived_phase == 1:
            if time.ticks_diff(current_time, self.arrived_timer) > 500: # 500ms warten
                self.arrived_phase = 2
            else:
                self._pivot_right_non_blocking()
            return

        # Phase 2: Aktives Drehen bis Linie gefunden (Zentrieren)
        if self.arrived_phase == 2:
            self._pivot_right_non_blocking()

            # Prüfen ob wir mittig auf einer Linie sind
            pos = self.sensor_array.get_position() if self.sensor_array else None
            centered_now = (pos is not None and abs(pos) < 25) # Toleranz +/- 25

            if self.PIVOT_USE_LINE_COUNTER:
                # Experimentell: Zähle Linien-Flanken (wenn Drehung über mehrere Linien erfolgt bis zur echten Fahrlinie)
                if centered_now and (not self._pivot_centered_last):
                    self._pivot_center_count += 1
                self._pivot_centered_last = centered_now

                accept_center = centered_now and (self._pivot_center_count >= self.PIVOT_CENTER_COUNT_TARGET)
            else:
                # Standard: Sobald wir die Linie mittig sehen, stoppen wir.
                accept_center = centered_now

            if accept_center:
                self._stop_motors()

                # Zielzustand setzen (je nach Fahrtrichtung)
                if self.target_destination == "STREET":
                    self.set_pico_state(self.STATE_WAIT_AT_STREET)
                else:
                    self.set_pico_state(self.STATE_STANDBY)


    def _logic_standby(self):
        """Ruhezustand Zuhause."""
        self._stop_motors()

    def _logic_wait_at_street(self):
        """Ruhezustand an der Straße."""
        self._stop_motors()
