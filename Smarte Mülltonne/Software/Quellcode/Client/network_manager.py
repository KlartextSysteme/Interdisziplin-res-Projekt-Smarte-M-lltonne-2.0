import network
import socket
import time
import errno

try:
    import uselect as select
except ImportError:
    import select


class NetworkManager:
    """
    Verwaltet die Netzwerkverbindung (WLAN + TCP-Socket zum Server).
    Arbeitet vollständig non-blocking, damit der Roboter während des Verbindungsaufbaus
    weiterfahren kann. Implementiert State-Machines für WLAN und Server-Verbindung.
    """

    # --- Zustände für WLAN ---
    WIFI_IDLE = 0       # WLAN ist aus oder nicht verbunden
    WIFI_CONNECTING = 1 # Verbindungsaufbau läuft
    WIFI_CONNECTED = 2  # Verbunden mit Access Point

    # --- Zustände für Server-Verbindung ---
    SERVER_IDLE = 0       # Socket geschlossen
    SERVER_CONNECTING = 1 # TCP-Verbindungsaufbau (Handshake) läuft
    SERVER_CONNECTED = 2  # TCP-Verbindung steht

    # Timeouts und Retry-Intervalle
    WIFI_TIMEOUT_MS = 20_000   # Max Zeit für WLAN-Verbindungsversuch
    WIFI_RETRY_MS = 2_000      # Wartezeit vor nächstem WLAN-Versuch
    SERVER_TIMEOUT_MS = 8_000  # Max Zeit für TCP-Connect
    SERVER_RETRY_MS = 2_000    # Wartezeit vor nächstem Server-Versuch

    # Liste von Fehlercodes, die "Warte noch" bedeuten (kein echter Fehler)
    _WOULD_BLOCK = (getattr(errno, "EAGAIN", 11), getattr(errno, "EWOULDBLOCK", 11), 11, 35, 10035)

    def __init__(self, ssid, password, server_ip, server_port, global_controller):
        """
        Initialisiert den Netzwerk-Manager.
        - ssid: WLAN-Name
        - password: WLAN-Passwort
        - server_ip: IP-Adresse des Servers (Mac)
        - server_port: Port des Servers
        - global_controller: Referenz auf die Hauptsteuerung (für Status-Updates)
        """
        self.ssid = ssid
        self.password = password
        self.server_ip = server_ip
        self.server_port = server_port

        self.gc = global_controller
        self.wlan = network.WLAN(network.STA_IF) # Station Mode (Client)

        self.sock = None
        self._wifi_state = self.WIFI_IDLE
        self._server_state = self.SERVER_IDLE

        # Timer für Retries
        self._wifi_start_ms = 0
        self._wifi_next_retry_ms = 0

        self._server_start_ms = 0
        self._server_next_retry_ms = 0

        self._handshake_sent = False
        self.verbose = False # Debug-Ausgaben standardmäßig aus

        # Poller für non-blocking Connect-Prüfung
        try:
            self._poller = select.poll()
        except Exception:
            self._poller = None

        # Startzustand: Nicht verbunden
        self.gc.set_connection_state(self.gc.STATE_NOT_CONNECTED)

    def set_verbose(self, is_verbose):
        """Aktiviert/Deaktiviert ausführliche Logs."""
        self.verbose = bool(is_verbose)

    def start(self):
        """Startet den Verbindungsprozess (WLAN)."""
        self._ensure_wifi_connect_started()

    def run(self):
        """
        Hauptmethode: Muss zyklisch aufgerufen werden.
        Treibt die State-Machines für WLAN und Server voran.
        """
        self._tick_wifi()
        self._tick_server()

    def get_socket(self):
        """Gibt das aktive Socket zurück, wenn verbunden."""
        return self.sock if self._server_state == self.SERVER_CONNECTED else None

    def mark_server_disconnected(self):
        """
        Wird aufgerufen, wenn ein Fehler auf dem Socket erkannt wurde.
        Schließt das Socket und setzt den Zustand zurück, um Reconnect auszulösen.
        """
        self._close_sock()
        self._server_state = self.SERVER_IDLE
        self._handshake_sent = False
        self.gc.notify_connection_lost()

    def intentional_disconnect(self):
        """
        Trennung auf Wunsch (Hard-Offline-Mode).
        Unterschied zu mark_server_disconnected: Kein Fehler-Notify an den GC.
        """
        self._close_sock()
        self._server_state = self.SERVER_IDLE
        self._handshake_sent = False

        try:
            self.gc.set_connection_state(self.gc.STATE_NOT_CONNECTED)
        except Exception:
            pass

        # Nächsten Versuch verzögern
        now = time.ticks_ms()
        self._server_next_retry_ms = time.ticks_add(now, self.SERVER_RETRY_MS)

    def request_reconnect(self):
        """
        Erzwingt sofortigen Wiederverbindungsversuch (z.B. nach Ende des Hard-Offline-Mode).
        """
        now = time.ticks_ms()
        self._wifi_next_retry_ms = now
        self._server_next_retry_ms = now

        self._handshake_sent = False
        self._server_state = self.SERVER_IDLE

        # WLAN-Zustand prüfen und ggf. neu starten
        if not self.wlan.isconnected():
            self._wifi_state = self.WIFI_IDLE

        self._ensure_wifi_connect_started()


    # ----------------------------------------------------------------
    # WIFI LOGIK
    # ----------------------------------------------------------------

    def _ensure_wifi_connect_started(self):
        """Startet die WLAN-Verbindung, falls noch nicht geschehen."""
        now = time.ticks_ms()

        self.wlan.active(True)
        try:
            # Power-Management deaktivieren für bessere Latenz (optional, hex-Code)
            self.wlan.config(pm=0xa11140)
        except Exception:
            pass

        # Bereits verbunden?
        if self.wlan.isconnected():
            self._wifi_state = self.WIFI_CONNECTED
            return

        # Wartezeit abgelaufen?
        if time.ticks_diff(now, self._wifi_next_retry_ms) < 0:
            return

        # Verbindungsversuch starten
        try:
            self.wlan.connect(self.ssid, self.password)
        except Exception:
            pass

        self._wifi_state = self.WIFI_CONNECTING
        self._wifi_start_ms = now
        self.gc.set_connection_state(self.gc.STATE_CONNECTING)

    def _tick_wifi(self):
        """Prüft den WLAN-Status und behandelt Timeouts."""
        now = time.ticks_ms()

        if self._wifi_state == self.WIFI_IDLE:
            self._ensure_wifi_connect_started()
            return

        if self._wifi_state == self.WIFI_CONNECTING:
            if self.wlan.isconnected():
                # Erfolgreich verbunden
                self._wifi_state = self.WIFI_CONNECTED
                # Status auf NOT_CONNECTED setzen, da TCP noch fehlt (aber WLAN da ist)
                self.gc.set_connection_state(self.gc.STATE_NOT_CONNECTED)
                return

            # Timeout prüfen
            if time.ticks_diff(now, self._wifi_start_ms) > self.WIFI_TIMEOUT_MS:
                try:
                    self.wlan.disconnect() # Reset
                except Exception:
                    pass
                self._wifi_state = self.WIFI_IDLE
                self._wifi_next_retry_ms = time.ticks_add(now, self.WIFI_RETRY_MS)
                self.gc.set_connection_state(self.gc.STATE_NOT_CONNECTED)
            return

    # ----------------------------------------------------------------
    # SERVER (TCP) LOGIK
    # ----------------------------------------------------------------

    def _start_server_connect(self):
        """Startet den TCP-Connect zum Server (non-blocking)."""
        now = time.ticks_ms()

        # Voraussetzung: WLAN muss da sein
        if not self.wlan.isconnected():
            self._wifi_state = self.WIFI_IDLE
            self._server_state = self.SERVER_IDLE
            self.gc.set_connection_state(self.gc.STATE_CONNECTING)
            return

        # Retry-Timer prüfen
        if time.ticks_diff(now, self._server_next_retry_ms) < 0:
            return

        self._close_sock()
        self._handshake_sent = False

        # Neues Socket erstellen
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(False) # Wichtig: Non-blocking Mode

        try:
            s.connect((self.server_ip, self.server_port))
        except OSError as e:
            code = e.args[0] if e.args else None
            # EINPROGRESS (115) bedeutet: Verbindungsaufbau läuft im Hintergrund -> OK
            if code in (errno.EINPROGRESS, errno.EALREADY, 115, 114, 36):
                pass
            else:
                # Echter Fehler -> Abbruch
                try:
                    s.close()
                except Exception:
                    pass
                self._server_state = self.SERVER_IDLE
                self._server_next_retry_ms = time.ticks_add(now, self.SERVER_RETRY_MS)
                self.gc.set_connection_state(self.gc.STATE_NOT_CONNECTED)
                return

        self.sock = s
        self._server_state = self.SERVER_CONNECTING
        self._server_start_ms = now
        self.gc.set_connection_state(self.gc.STATE_CONNECTING)

        # Socket im Poller registrieren, um auf "Writable" (Connect fertig) zu warten
        if self._poller is not None:
            try:
                self._poller.register(self.sock, select.POLLOUT | select.POLLERR | select.POLLHUP)
            except Exception:
                pass

    def _connect_finished_ok(self):
        """
        Prüft, ob der asynchrone Connect erfolgreich war.
        Rückgabe:
        - True: Verbunden
        - False: Fehler
        - None: Noch beschäftigt (weiter warten)
        """
        if not self.sock:
            return False

        # Methode 1: SO_ERROR Socket-Option (Standard)
        try:
            SO_ERROR = getattr(socket, "SO_ERROR", 4)
            err = self.sock.getsockopt(socket.SOL_SOCKET, SO_ERROR)
            return True if err == 0 else False
        except Exception:
            pass

        # Methode 2: Leeres Paket senden (Fallback)
        try:
            self.sock.send(b"")
            return True
        except OSError as e:
            code = e.args[0] if e.args else None

            # Diese Codes bedeuten "noch nicht fertig" -> None
            if code in self._WOULD_BLOCK or code in (errno.EINPROGRESS, errno.EALREADY, 115, 114, 36):
                return None

            # EISCONN (106) bedeutet "schon verbunden" -> True
            if code in (getattr(errno, "EISCONN", 106), 106):
                return True

            return False # Echter Fehler


    def _tick_server(self):
        """Treibt die Server-Verbindungs-State-Machine voran."""
        now = time.ticks_ms()

        # Wenn WLAN weg ist -> alles resetten
        if self._wifi_state != self.WIFI_CONNECTED:
            self._close_sock()
            self._server_state = self.SERVER_IDLE
            return

        # IDLE -> Versuch starten
        if self._server_state == self.SERVER_IDLE:
            self._start_server_connect()
            return

        # CONNECTING -> Warten auf Fertigstellung oder Timeout
        if self._server_state == self.SERVER_CONNECTING:
            if not self.sock:
                self._server_state = self.SERVER_IDLE
                return

            # Timeout prüfen
            if time.ticks_diff(now, self._server_start_ms) > self.SERVER_TIMEOUT_MS:
                self._close_sock()
                self._server_state = self.SERVER_IDLE
                self._server_next_retry_ms = time.ticks_add(now, self.SERVER_RETRY_MS)
                self.gc.set_connection_state(self.gc.STATE_CONNECTING)
                return

            # Prüfen ob Socket bereit ist (poll)
            ready = False
            if self._poller is not None:
                try:
                    events = self._poller.poll(0) # 0 = non-blocking
                    for _, ev in events:
                        if ev & (select.POLLERR | select.POLLHUP | select.POLLOUT):
                            ready = True
                except Exception:
                    ready = False
            else:
                # Fallback ohne Poller
                try:
                    _, w, x = select.select([], [self.sock], [self.sock], 0)
                    if self.sock in w or self.sock in x:
                        ready = True
                except Exception:
                    ready = False

            if not ready:
                return # Noch warten

            # Ergebnis prüfen
            result = self._connect_finished_ok()

            if result is None:
                return # Weiter warten

            if result is True:
                # Erfolg!
                self._server_state = self.SERVER_CONNECTED
                self.gc.set_connection_state(self.gc.STATE_CONNECTED)

                # Poller bereinigen
                if self._poller is not None:
                    try:
                        self._poller.unregister(self.sock)
                    except Exception:
                        pass
                return

            # Fehler -> Reset
            self._close_sock()
            self._server_state = self.SERVER_IDLE
            self._server_next_retry_ms = time.ticks_add(now, self.SERVER_RETRY_MS)
            self.gc.set_connection_state(self.gc.STATE_NOT_CONNECTED)
            return

        # CONNECTED -> Initialen Handshake senden
        if self._server_state == self.SERVER_CONNECTED:
            if self.sock and not self._handshake_sent:
                try:
                    self.sock.send(b"Pico ist bereit\n")
                    self._handshake_sent = True
                except OSError as e:
                    code = e.args[0] if e.args else None
                    if code in self._WOULD_BLOCK:
                        return # Später versuchen
                    self.mark_server_disconnected()

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _close_sock(self):
        """Schließt das Socket sicher und deregistriert es vom Poller."""
        if self._poller is not None and self.sock is not None:
            try:
                self._poller.unregister(self.sock)
            except Exception:
                pass

        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass

        self.sock = None
