try:
    import uselect as select
except ImportError:
    import select

# Importiert errno für standardisierte Fehlercodes (wichtig für plattformübergreifende Kompatibilität)
import errno


class NetworkController:
    """
    Verarbeitet eingehende Daten vom Server-Socket.
    Nutzt non-blocking I/O und Polling, um den Hauptprozess nicht zu blockieren.
    Puffert eingehende Bytes und extrahiert vollständige Befehlszeilen.
    """
    
    # Definition von Fehlercodes für "Würde blockieren"
    # Dies ist kein echter Fehler, sondern bedeutet nur "gerade keine Daten da".
    _EAGAIN = getattr(errno, "EAGAIN", 11)
    _EWOULDBLOCK = getattr(errno, "EWOULDBLOCK", _EAGAIN)
    _WOULD_BLOCK = (_EAGAIN, _EWOULDBLOCK, 11, 35, 10035) # Liste aller bekannten Codes

    # Konstanten für select.poll() Ereignisse
    _POLLIN = getattr(select, "POLLIN", 1)   # Daten zum Lesen verfügbar
    _POLLERR = getattr(select, "POLLERR", 8) # Fehlerbedingung
    _POLLHUP = getattr(select, "POLLHUP", 16) # Verbindung aufgelegt (Hang Up)

    def __init__(self, sock, global_controller, network_manager=None):
        """
        Initialisiert den Controller.
        - sock: Das aktive Socket-Objekt (kann initial None sein).
        - global_controller: Referenz auf die Hauptsteuerung zur Befehlsausführung.
        - network_manager: Referenz auf den NetworkManager, um neue Sockets zu holen.
        """
        self.sock = sock
        self.global_controller = global_controller
        self.network_manager = network_manager

        # Puffer für eingehende Rohdaten (Bytes)
        self._rx_buffer = bytearray()
        
        # Polling-Objekt erstellen
        self._poller = select.poll()

        # Falls ein Socket übergeben wurde, direkt registrieren
        if self.sock:
            try:
                self._poller.register(self.sock, self._POLLIN | self._POLLERR | self._POLLHUP)
            except Exception:
                pass

    def _set_socket(self, new_sock):
        """
        Ersetzt das aktuelle Socket durch ein neues (z.B. nach Reconnect).
        Meldet das alte ab und registriert das neue im Poller.
        """
        if self.sock:
            try:
                self._poller.unregister(self.sock)
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass

        self.sock = new_sock
        self._rx_buffer = bytearray() # Puffer leeren bei neuer Verbindung

        if self.sock:
            try:
                self._poller.register(self.sock, self._POLLIN | self._POLLERR | self._POLLHUP)
            except Exception:
                pass

    def _handle_disconnect(self):
        """
        Behandelt einen Verbindungsabbruch: Socket schließen, aufräumen
        und GlobalController/NetworkManager benachrichtigen.
        """
        try:
            if self.sock:
                try:
                    self._poller.unregister(self.sock)
                except Exception:
                    pass
                try:
                    self.sock.close()
                except Exception:
                    pass
        finally:
            self.sock = None
            self._rx_buffer = bytearray()

        # GlobalController informieren (LED Status ändern)
        try:
            self.global_controller.set_connection_state(self.global_controller.STATE_NOT_CONNECTED)
        except Exception:
            pass

        # NetworkManager informieren (für Auto-Reconnect Logik)
        if self.network_manager is not None:
            try:
                self.network_manager.mark_server_disconnected()
            except Exception:
                pass

    def _process_rx_buffer(self):
        """
        Verarbeitet den Empfangspuffer:
        - Sucht nach Zeilenumbrüchen (\n) als Befehlstrenner.
        - Extrahiert vollständige Befehle.
        - Übergibt Befehle an den GlobalController.
        """
        # Schutz: Buffer begrenzen, falls Server Müll sendet (Memory Leak Schutz)
        if len(self._rx_buffer) > 2048:
            self._rx_buffer = self._rx_buffer[-1024:] # Nur die letzten 1024 Bytes behalten

        while True:
            # Suche nach dem nächsten Zeilenumbruch
            idx = self._rx_buffer.find(b"\n")
            if idx < 0:
                break # Kein vollständiger Befehl mehr im Puffer

            # Zeile extrahieren (bis zum \n)
            line = bytes(self._rx_buffer[:idx])
            
            # Puffer bereinigen (Bytes nach dem \n behalten)
            self._rx_buffer = self._rx_buffer[idx + 1 :]

            if not line:
                continue # Leere Zeile ignorieren

            try:
                # Bytes zu String dekodieren
                cmd = line.decode().strip()
            except UnicodeError:
                continue # Dekodierfehler ignorieren

            if cmd:
                try:
                    # Befehl ausführen
                    self.global_controller.handle_network_command(cmd)
                except Exception:
                    pass

    def _recv_once_and_process(self):
        """
        Versucht, Daten vom Socket zu lesen (non-blocking).
        Fügt Daten dem Puffer hinzu und startet die Verarbeitung.
        Rückgabe: True wenn erfolgreich gelesen, False bei Fehler/Disconnect/WouldBlock.
        """
        if not self.sock:
            return False

        try:
            # Versuche bis zu 256 Bytes zu lesen
            data = self.sock.recv(256)
        except OSError as e:
            code = e.args[0] if e.args else None
            # Prüfen ob es nur "keine Daten" (Would Block) ist
            if code in self._WOULD_BLOCK:
                return False
            # Echter Fehler -> Disconnect
            self._handle_disconnect()
            return False

        # Leeres Datenpaket bedeutet bei TCP: Gegenstelle hat Verbindung geschlossen
        if not data:
            self._handle_disconnect()
            return False

        # Daten empfangen -> an Puffer anhängen
        self._rx_buffer.extend(data)
        self._process_rx_buffer()
        return True

    def run(self):
        """
        Hauptmethode: Muss zyklisch aufgerufen werden.
        Prüft auf neue Sockets, pollt auf Ereignisse und liest Daten.
        """
        # Socket ggf. vom NetworkManager übernehmen, falls wir noch keins haben
        if (self.sock is None) and (self.network_manager is not None):
            new_sock = self.network_manager.get_socket()
            if new_sock:
                self._set_socket(new_sock)

        if not self.sock:
            return # Nichts zu tun

        # Polling auf Ereignisse (Timeout 0 = non-blocking)
        try:
            events = self._poller.poll(0)
        except Exception:
            self._handle_disconnect()
            return

        # Fallback: Wenn poll keine Events liefert, trotzdem einmal recv versuchen (non-blocking).
        # Manche MicroPython-Ports/Sockets melden POLLIN nicht immer zuverlässig.
        if not events:
            self._recv_once_and_process()
            return

        did_pollin = False

        for _, event in events:
            # Prüfen auf echte Fehlerbits
            if event & (self._POLLERR | self._POLLHUP):
                self._handle_disconnect()
                return

            # Prüfen auf lesbare Daten
            if event & self._POLLIN:
                did_pollin = True
                # Daten lesen und verarbeiten
                self._recv_once_and_process()

        # Falls poll Events liefert, aber kein POLLIN gesetzt ist (Port-Besonderheit),
        # probiere sicherheitshalber trotzdem einmal recv().
        if not did_pollin:
            self._recv_once_and_process()
