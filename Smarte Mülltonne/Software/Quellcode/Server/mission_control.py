import time

# Protokoll-Konstanten (Identisch zu denen im Pico)
CMD_GOTO_STREET = "CMD_GOTO_STREET"
CMD_RETURN_HOME = "CMD_RETURN_HOME"

STATUS_MONITORING = "MONITORING"
STATUS_PLANING = "PLANING"
STATUS_MISSION_MONITORING = "MISSION_MONITORING"
STATUS_WAITING_FOR_EMPTYING = "WAITING_FOR_EMPTYING"
STATUS_WAITING_FOR_ACK = "STATUS_WAITING_FOR_ACK"

PICO_MANUAL_GOTO_STREET_REQUEST = "MANUAL_GOTO_STREET_REQUEST"
PICO_MANUAL_RETURN_HOME_REQUEST = "MANUAL_RETURN_HOME_REQUEST"

PICO_STATUS_USER_PAUSED = "USER_PAUSED"
PICO_STATUS_OBSTACLE = "OBSTACLE"
PICO_STATUS_ARRIVED = "ARRIVED"
PICO_STATUS_STANDBY = "STANDBY"
PICO_STATUS_WAIT_AT_STREET = "WAIT_AT_STREET"


ACK_RECEIVED_PREFIX = "ACK_RECEIVED"


class MissionControl:
    """
    Demo-freundliche Missionslogik mit Reconnect-Optimierung.
    Verwaltet den Zustand der Mülltonne (Server-seitig) und reagiert auf Events vom Pico.
    - Reconnect: Zeigt den letzten bekannten Pico-Status (z.B. USER_PAUSED, OBSTACLE, ARRIVED).
    - Merkt letzten Ankunftsort durch ARRIVED: HOME / ARRIVED: STREET.
    """

    def __init__(self, logger=None):
        # Default-Logger gibt einfach auf der Konsole aus, falls keiner übergeben wird
        self._logger = logger or (lambda tag, msg: print(f"[{tag}] {msg}"))

        # Merker für Reconnect/Context
        self._pico_ready = False
        self._last_seen_pico_state = None          # Speichert den letzten gemeldeten Status (z.B. "USER_PAUSED")
        self._last_arrived_place = None            # Speichert den letzten Ort: "HOME" | "STREET" | None

        self._reset_runtime()

    def _log(self, tag, msg):
        """Wrapper für die Logging-Funktion mit Fehlerbehandlung."""
        try:
            self._logger(tag, msg)
        except Exception:
            print(f"[{tag}] {msg}")

    def _section(self, title: str):
        """Erstellt eine visuelle Trennung im Log."""
        self._log("SECTION", title)

    def _reset_runtime(self):
        """Setzt alle Laufzeit-Variablen auf ihren Initialzustand zurück."""
        self.state = STATUS_MONITORING
        self.last_pico_status_msg = None

        self._planning_start_time = None   # Zeitstempel für den Start der Planung (10s Timer)
        self._pending_cmd = None           # Nächster Befehl, der gesendet werden soll
        self._waiting_for_ack_cmd = None   # Befehl, auf dessen Bestätigung gewartet wird
        self._empty_received_time = None   # Zeitstempel, wann "Leer" gemeldet wurde
        self._ack_wait_start_time = None   # Zeitstempel für den Start des ACK-Timeouts

        self._known_pico_ip = None
        self._known_pico_port = None

    def on_socket_connected(self, client_addr):
        """Wird aufgerufen, wenn eine TCP-Verbindung hergestellt wird (noch vor Handshake)."""
        ip, port = client_addr[0], client_addr[1]
        self._known_pico_ip, self._known_pico_port = ip, port
        self._section(f"Neue Verbindung ({ip})")
        self._log("NETZ", "Warte auf Handshake...")


    def on_client_connected(self, client_addr):
        """
        Wird aufgerufen, wenn der Pico "Pico ist bereit" (Handshake) sendet.
        Entscheidet, ob es ein neuer Start oder ein Reconnect ist.
        """
        # Reconnect erkennen: War der Pico schon mal da?
        is_reconnect = bool(getattr(self, "_pico_ready", False))
        self._pico_ready = True

        # State NICHT blind resetten bei Reconnect, sondern anhand des letzten bekannten Status entscheiden
        if is_reconnect:
            print(f"[LOGIC] Pico ist bereit (Reconnect): {client_addr}")

            # Aktuellen Status beim Reconnect anzeigen (USER_PAUSED, OBSTACLE, ARRIVED, ...)
            if self._last_seen_pico_state:
                print(f"[LOGIC] Aktueller Pico-Status (Reconnect): {self._last_seen_pico_state}")

            # Kontext korrekt wiederherstellen:
            
            # Fall 1: Pico war zuletzt zuhause -> Monitoring fortsetzen
            if self._last_arrived_place == "HOME" or self._last_seen_pico_state == PICO_STATUS_STANDBY:
                self.state = STATUS_MONITORING
                print("[LOGIC] Reconnect-Kontext: Pico ist zuhause. Überwachung läuft weiter.")
                return

            # Fall 2: Pico war zuletzt an der Straße -> Warten auf Leerung
            if self._last_arrived_place == "STREET" or self._last_seen_pico_state == PICO_STATUS_WAIT_AT_STREET:
                self.state = STATUS_WAITING_FOR_EMPTYING
                print("[LOGIC] Reconnect-Kontext: Pico ist an der Straße. Bitte Mülltonne entleeren.")
                return

            # Fall 3: ARRIVED ist mehrdeutig -> NICHT automatisch Zustand ändern
            if self._last_seen_pico_state == PICO_STATUS_ARRIVED:
                print("[LOGIC] Reconnect-Kontext: 'ARRIVED' ist mehrdeutig. Warte auf ARRIVED: HOME/STREET oder STANDBY/WAIT_AT_STREET.")
                return

            # Fall 4: Pausiert / Hindernis -> Status beibehalten
            if self._last_seen_pico_state == PICO_STATUS_USER_PAUSED:
                print("[LOGIC] Reconnect-Kontext: Pico ist pausiert.")
                return

            if self._last_seen_pico_state == PICO_STATUS_OBSTACLE:
                print("[LOGIC] Reconnect-Kontext: Hindernis erkannt.")
                return

            return

        # Normalfall (kein Reconnect): Initialisierung
        self.state = STATUS_MONITORING
        self.last_pico_status_msg = None
        self._planning_start_time = None
        self._pending_cmd = None
        self._waiting_for_ack_cmd = None
        self._empty_received_time = None
        self.last_pico_status_msg = None
        self._ack_wait_start_time = None

        print(f"[LOGIC] Client verbunden: {client_addr} -> State: {self.state}")


    def pop_pending_command(self):
        """
        Holt den nächsten zu sendenden Befehl aus der Warteschlange.
        Wird vom Server-Thread (mac_server.py) regelmäßig abgefragt.
        """
        cmd = self._pending_cmd
        self._pending_cmd = None
        return cmd

    def notify_cmd_sent(self, cmd):
        """
        Callback: Wird aufgerufen, nachdem ein Befehl erfolgreich über das Netzwerk gesendet wurde.
        Startet die Timer für das Warten auf Bestätigung (ACK).
        """
        if self.state == STATUS_PLANING and cmd == CMD_GOTO_STREET:
            # Timer sauber beenden (Planung ist abgeschlossen)
            self._planning_start_time = None

            # Zustand wechseln: Warten auf ACK
            self.state = STATUS_WAITING_FOR_ACK
            self._waiting_for_ack_cmd = CMD_GOTO_STREET
            self._ack_wait_start_time = time.time()

            self._section("Mission startet")
            self._log("MISSION", "Befehl gesendet: Fahrt zur Straße.")
            self._log("NETZ", "Warte auf Bestätigung (ACK).")
            return

        if self.state == STATUS_WAITING_FOR_EMPTYING and cmd == CMD_RETURN_HOME:
            # Timer sauber beenden (Rückfahrt-Planung ist abgeschlossen)
            self._empty_received_time = None

            # Zustand wechseln: Warten auf ACK
            self.state = STATUS_WAITING_FOR_ACK
            self._waiting_for_ack_cmd = CMD_RETURN_HOME
            self._ack_wait_start_time = time.time()

            self._section("Rückfahrt startet")
            self._log("MISSION", "Befehl gesendet: Rückfahrt nach Hause.")
            self._log("NETZ", "Warte auf Bestätigung (ACK).")
            return


    def process_incoming_msg(self, msg, client_addr):
        """
        Hauptlogik: Verarbeitet eingehende Nachrichten vom Pico.
        Entscheidet über Zustandsübergänge und Log-Ausgaben.
        """
        # Status-Nachrichten entprellen (nicht dauernd das gleiche loggen)
        should_print = True
        if msg.startswith("STATUS:"):
            if msg == self.last_pico_status_msg:
                should_print = False
            else:
                self.last_pico_status_msg = msg
                should_print = True

        # Handshake: "Pico ist bereit"
        if msg == "Pico ist bereit":
            self.on_client_connected(client_addr)
            return None

        # ARRIVED-Ort merken (für korrekte Reconnect-Wiederherstellung)
        if msg == "ARRIVED: HOME":
            self._last_arrived_place = "HOME"
        elif msg == "ARRIVED: STREET":
            self._last_arrived_place = "STREET"

        # Demo-Ausgabe (Formatierung für den Benutzer)
        if should_print:
            if msg.startswith("STATUS:"):
                pico_state_info = msg.split(":", 1)[1].strip()
                self._last_seen_pico_state = pico_state_info  # Merken für Reconnect
                self._log("PICO", f"Status: {self._human_pico_status(pico_state_info)}")

            elif msg.startswith("ACK "):
                ack_cmd = msg.split(" ", 1)[1].strip()
                self._log("PICO", f"Bestätigung: {self._human_cmd(ack_cmd)}")

            elif msg.startswith("ARRIVED:"):
                self._log("PICO", msg.replace(":", " -", 1))

            else:
                self._log("PICO", f"Nachricht: {msg}")

        # --- Heartbeat-Auswertung ---
        if msg.startswith("STATUS:"):
            pico_state_info = msg.split(":", 1)[1].strip()

            # Self-healing / Kontextabgleich (z.B. STANDBY/WAIT_AT_STREET/LINE_FOLLOWING)
            self._sync_state_with_pico(pico_state_info)

            # Trigger: Füllstand voll oder manueller Start -> Einsatzplanung (10s) starten
            if pico_state_info in ("FULL", PICO_MANUAL_GOTO_STREET_REQUEST):

                # Wenn wir gerade senden/warten oder schon unterwegs sind: ignorieren (keine Doppel-Mission)
                if self.state in (STATUS_WAITING_FOR_ACK, STATUS_MISSION_MONITORING):
                    return None

                # Wenn wir noch nicht PLANING sind, Timer starten
                if self.state != STATUS_PLANING:
                    self.state = STATUS_PLANING
                    self._planning_start_time = time.time()

                    reason = "Füllstand ist voll" if pico_state_info == "FULL" else "Manueller Start angefordert"
                    self._section("Einsatzplanung")
                    self._log("MISSION", f"{reason}. Abfahrt in 10 Sekunden...")


            # Trigger: Leerung oder manueller Rückruf -> Rückfahrt-Planung (10s) starten
            if self.state == STATUS_WAITING_FOR_EMPTYING and pico_state_info in ("EMPTIED", PICO_MANUAL_RETURN_HOME_REQUEST):
                if self._empty_received_time is None:
                    self._empty_received_time = time.time()
                    reason = "Entleerung erkannt" if pico_state_info == "EMPTIED" else "Manueller Rückfahrt-Start angefordert"
                    self._section("Rückfahrt wird vorbereitet")
                    self._log("MISSION", f"{reason}. Rückfahrt in 10 Sekunden...")

            return None

        # ACK Handling (Bestätigung vom Pico)
        if self.state == STATUS_WAITING_FOR_ACK and msg.startswith("ACK "):
            ack_cmd = msg.split(" ", 1)[1].strip()

            if self._waiting_for_ack_cmd and self._waiting_for_ack_cmd == ack_cmd:
                self.state = STATUS_MISSION_MONITORING
                self._waiting_for_ack_cmd = None
                self._log("NETZ", "ACK passend. Pico führt den Befehl aus.")
                # Bestätigt dem Pico, dass das ACK angekommen ist (Handshake-Abschluss)
                return f"{ACK_RECEIVED_PREFIX} {ack_cmd}"

            self._log("WARN", "ACK kam unerwartet. Wird trotzdem bestätigt.")
            return f"{ACK_RECEIVED_PREFIX} {ack_cmd}"

        # ACK auch außerhalb des erwarteten Zustands bestätigen (Robustheit)
        if msg.startswith("ACK "):
            ack_cmd = msg.split(" ", 1)[1].strip()
            return f"{ACK_RECEIVED_PREFIX} {ack_cmd}"

        # ARRIVED-Events (mit korrektem Kontext)
        if msg == "ARRIVED: STREET":
            self.state = STATUS_WAITING_FOR_EMPTYING
            self._section("Ankunft: Straße")
            self._log("MISSION", "Bitte Mülltonne entleeren.")
            return None

        if msg == "ARRIVED: HOME":
            self.state = STATUS_MONITORING
            self._section("Mission abgeschlossen")
            self._log("MISSION", "Tonne ist zuhause. Überwachung läuft weiter.")
            return None

        return None

    def _sync_state_with_pico(self, pico_state):
        """
        Self-Healing / Statusabgleich.
        Korrigiert den Server-Status, falls dieser vom Pico-Status abweicht (z.B. nach Neustart).
        """

        # Wenn eindeutig zuhause (STANDBY)
        if pico_state == "STANDBY":
            if self.state != STATUS_MONITORING:
                self._log("SYSTEM", "Statusabgleich: Pico ist zuhause. Überwachung aktiv.")
            self.state = STATUS_MONITORING
            self._last_arrived_place = "HOME"
            return

        # Wenn eindeutig an der Straße (WAIT_AT_STREET)
        if pico_state == "WAIT_AT_STREET":
            if self.state != STATUS_WAITING_FOR_EMPTYING:
                self._log("SYSTEM", "Statusabgleich: Pico ist an der Straße. Warte auf Entleerung.")
            self.state = STATUS_WAITING_FOR_EMPTYING
            self._last_arrived_place = "STREET"
            return

        # Wenn unterwegs (LINE_FOLLOWING)
        if self.state == STATUS_MONITORING and pico_state == "LINE_FOLLOWING":
            self._log("SYSTEM", "Statusabgleich: Pico ist bereits unterwegs.")
            self.state = STATUS_MISSION_MONITORING
            return

        # Implizites ACK: Wenn Pico schon fährt, obwohl wir auf ACK warten
        if self.state == STATUS_WAITING_FOR_ACK and self._waiting_for_ack_cmd in (CMD_GOTO_STREET, CMD_RETURN_HOME):
            if pico_state == "LINE_FOLLOWING":
                self._log("SYSTEM", "Implizites ACK: Pico ist losgefahren ('Unterwegs').")
                self.state = STATUS_MISSION_MONITORING
                self._waiting_for_ack_cmd = None
                return

        # Wenn Pico "EMPTIED" meldet -> Bereite Rückfahrt vor
        if self.state == STATUS_MONITORING and pico_state == "EMPTIED":
            self._log("SYSTEM", "Statusabgleich: Pico meldet 'Entleert'. Rückfahrt wird vorbereitet.")
            self.state = STATUS_WAITING_FOR_EMPTYING
            if self._empty_received_time is None:
                self._empty_received_time = time.time()
            return

        # Andere Stati (USER_PAUSED, OBSTACLE) ändern den Hauptzustand nicht zwingend
        if pico_state in ("USER_PAUSED", "OBSTACLE", "ARRIVED"):
            return


    def check_timeouts(self):
        """
        Prüft zeitabhängige Bedingungen (Timer für Abfahrt, Timeouts für ACKs).
        Wird regelmäßig vom Server-Loop aufgerufen.
        """
        now = time.time()

        # PLANING: Nach 10s Wartezeit -> Befehl "Fahrt zur Straße" vorbereiten
        if self.state == STATUS_PLANING and self._planning_start_time is not None:
            if (now - self._planning_start_time) >= 10:
                if self._pending_cmd is None:
                    self._pending_cmd = CMD_GOTO_STREET
                    self._log("MISSION", "Startsignal: Abfahrt zur Straße wird jetzt gesendet...")

        # WAITING_FOR_EMPTYING: Nach 10s Wartezeit -> Befehl "Rückfahrt" vorbereiten
        if self.state == STATUS_WAITING_FOR_EMPTYING and self._empty_received_time is not None:
            if (now - self._empty_received_time) >= 10:
                if self._pending_cmd is None:
                    self._pending_cmd = CMD_RETURN_HOME
                    self._log("MISSION", "Startsignal: Rückfahrt nach Hause wird jetzt gesendet...")

        # WAITING_FOR_ACK: Nach 5s ohne Bestätigung -> Befehl erneut senden (Retry)
        if self.state == STATUS_WAITING_FOR_ACK and self._ack_wait_start_time is not None:
            if (now - self._ack_wait_start_time) > 5.0:
                self._log("WARN", f"Keine Bestätigung nach 5s. Sende erneut: {self._human_cmd(self._waiting_for_ack_cmd)}")
                self._pending_cmd = self._waiting_for_ack_cmd
                self._ack_wait_start_time = now # Timer zurücksetzen


    def _human_cmd(self, cmd):
        """Übersetzt interne Befehle in lesbare Strings für das Log."""
        return {
            CMD_GOTO_STREET: "Fahrt zur Straße",
            CMD_RETURN_HOME: "Rückfahrt nach Hause",
        }.get(cmd, cmd)

    def _human_pico_status(self, pico_state):
        """Übersetzt Pico-Statuscodes in lesbare Strings für das Log."""
        return {
            "STANDBY": "Bereit / Zuhause",
            "USER_PAUSED": "Pausiert",
            "OBSTACLE": "Hindernis",
            "LINE_FOLLOWING": "Unterwegs",
            "WAIT_AT_STREET": "Wartet an der Straße",
            "ARRIVED": "Angekommen",
            "FULL": "Voll",
            "EMPTIED": "Entleert",
            "LINE_LOST": "Linie verloren",
            "ERROR": "Fehler",
            PICO_MANUAL_GOTO_STREET_REQUEST: "Manueller Start (zur Straße)",
            PICO_MANUAL_RETURN_HOME_REQUEST: "Manueller Start (nach Hause)",
        }.get(pico_state, pico_state)
