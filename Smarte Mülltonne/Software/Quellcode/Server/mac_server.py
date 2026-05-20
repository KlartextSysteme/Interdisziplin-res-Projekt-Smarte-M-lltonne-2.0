import socket
import threading
import select
import time

# Importiert die Logik-Klasse für die Missionssteuerung
from mission_control import MissionControl

# Konfiguration des Servers
HOST = "0.0.0.0"       # Lauscht auf allen verfügbaren Netzwerk-Interfaces
PORT = 50002           # Port für die Kommunikation (muss mit Pico übereinstimmen)
INACTIVITY_TIMEOUT = 300 # Zeit in Sekunden, nach der eine inaktive Verbindung getrennt wird

# Liste der aktiven Client-Verbindungen und Lock für Thread-Sicherheit
clients = []
clients_lock = threading.Lock()


def _ts():
    """Erstellt einen Zeitstempel für Log-Ausgaben im Format HH:MM:SS."""
    return time.strftime("%H:%M:%S")


def log(tag, msg):
    """
    Zentrale Logging-Funktion für formatierte Ausgaben.
    - tag: Kategorie der Nachricht (z.B. 'NETZ', 'FEHLER')
    - msg: Die eigentliche Nachricht
    """
    if tag == "SECTION":
        # Erstellt eine Trennlinie für bessere Lesbarkeit bei neuen Abschnitten
        line = "=" * 64
        print("\n" + line)
        print(msg)
        print(line)
        return
    # Gibt die Nachricht mit Zeitstempel und Tag formatiert aus
    print(f"{_ts()} | {tag:<7} {msg}")


# Initialisiert die Missionssteuerung (Logik-Einheit)
controller = MissionControl(logger=log)


def handle_client(conn, addr):
    """
    Behandelt eine einzelne Client-Verbindung in einem separaten Thread.
    - conn: Das Socket-Objekt der Verbindung
    - addr: Die Adresse des Clients (IP, Port)
    """
    ip = addr[0]
    conn.settimeout(None) # Setzt den Socket auf blockierend (wird aber durch select gesteuert)

    # Meldet der Steuerung, dass ein neuer Socket verbunden ist
    controller.on_socket_connected(addr)

    last_activity = time.time()
    buffer = ""

    try:
        while True:
            # Prüft auf Inaktivität (Timeout)
            if time.time() - last_activity > INACTIVITY_TIMEOUT:
                log("WARN", f"Verbindung zu {ip} getrennt (keine Daten > {INACTIVITY_TIMEOUT}s).")
                break

            # select prüft, ob Daten zum Lesen bereitstehen (Timeout 1.0s), ohne zu blockieren
            readable, _, _ = select.select([conn], [], [], 1.0)
            if readable:
                try:
                    data = conn.recv(1024) # Empfängt bis zu 1024 Bytes
                    if not data:
                        log("NETZ", f"Pico {ip} hat die Verbindung geschlossen.")
                        break

                    # Fügt empfangene Daten dem Puffer hinzu (ignoriert Decodierfehler)
                    buffer += data.decode(errors="ignore")

                    # Verarbeitet vollständige Nachrichten (getrennt durch Zeilenumbruch)
                    while "\n" in buffer:
                        message, buffer = buffer.split("\n", 1)
                        message = message.strip()
                        if not message:
                            continue

                        last_activity = time.time() # Aktualisiert Aktivitätszeit

                        # Übergibt die Nachricht an die Missionssteuerung und erhält ggf. eine Antwort
                        response_cmd = controller.process_incoming_msg(message, addr)
                        if response_cmd:
                            log("NETZ", f"Sende Antwort: {response_cmd}")
                            conn.send((response_cmd + "\n").encode())
                            last_activity = time.time()

                except Exception as e:
                    log("FEHLER", f"Fehler beim Empfangen von {ip}: {e}")
                    break

            # Prüft regelmäßig auf Timeouts in der Logik (z.B. fehlende Bestätigungen)
            controller.check_timeouts()

            # Prüft, ob die Steuerung einen Befehl senden möchte (proaktiv)
            pending = controller.pop_pending_command()
            if pending:
                try:
                    # Formatiert den Befehl für die Log-Ausgabe (falls vorhanden)
                    human = getattr(controller, "_human_cmd", lambda x: x)(pending)
                    log("MISSION", f"Sende Missionsbefehl: {human}")
                    conn.send((pending + "\n").encode())
                    last_activity = time.time()
                    # Bestätigt der Steuerung, dass der Befehl gesendet wurde
                    controller.notify_cmd_sent(pending)
                except Exception as e:
                    log("FEHLER", f"Geplantes Senden fehlgeschlagen: {e}")

            # Beendet den Thread, wenn der Haupt-Thread (Server) beendet wurde
            if not threading.main_thread().is_alive():
                break

    except Exception as e:
        log("FEHLER", f"Verbindung {ip} abgestürzt: {e}")

    finally:
        # Aufräumen beim Beenden der Verbindung
        with clients_lock:
            if conn in clients:
                clients.remove(conn)
        try:
            conn.close()
        except Exception:
            pass

        log("SECTION", f"Pico getrennt ({ip})")
        log("NETZ", "Verbindung bereinigt.")


def accept_connections(server_socket):
    """
    Hauptschleife zum Akzeptieren neuer Verbindungen.
    Läuft in einem eigenen Thread.
    """
    log("SECTION", "Autonome Mülltonne – Demo-Server")
    log("SYSTEM", f"Warte auf Pico-Verbindungen (Port {PORT}).")
    log("SYSTEM", "Beenden: Ctrl+C")

    while True:
        try:
            # Wartet auf eine eingehende Verbindung
            conn, addr = server_socket.accept()
            with clients_lock:
                clients.append(conn)
            # Startet einen neuen Thread für den verbundenen Client
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
        except Exception:
            break


# Erstellt den TCP-Socket (IPv4, Stream/TCP)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Erlaubt das sofortige Wiederverwenden der Adresse nach Beenden (verhindert "Address already in use")
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    # Bindet den Socket an Host und Port und beginnt zu lauschen
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    # Startet den Thread zum Akzeptieren von Verbindungen
    accept_thread = threading.Thread(target=accept_connections, args=(server_socket,), daemon=True)
    accept_thread.start()

    # Hauptschleife hält das Programm am Laufen
    while True:
        time.sleep(1.0)

except KeyboardInterrupt:
    # Behandelt Strg+C zum sauberen Beenden
    log("SECTION", "Server wird beendet")
    log("SYSTEM", "Stoppe Server...")

finally:
    # Schließt alle Sockets beim Beenden
    try:
        server_socket.close()
    except Exception:
        pass

    with clients_lock:
        for c in clients:
            try:
                c.close()
            except Exception:
                pass
