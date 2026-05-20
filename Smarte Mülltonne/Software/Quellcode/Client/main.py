from dcmotor import DCMotor
from button import Button
from liniensensor import Liniensensor
from PDcontroller import PDController
from network_manager import NetworkManager
from network_controller import NetworkController
from led import LED, LEDStateMachine, ConnectionLEDStateMachine
from ultraschallsensor import HCSR04P, FuellstandSensor
from global_controller import GlobalController
from machine import Pin, PWM
from buzzer import Buzzer

from time import sleep
import time
import gc

# ===================================================================
# KONFIGURATION
# ===================================================================

FREQUENCY = 1000       # PWM-Frequenz für die Motoren

BASE_SPEED = 40        # Grundgeschwindigkeit der Motoren (0-100)
KP_WERT = 0.6          # Proportional-Anteil für den PD-Regler (Lenkempfindlichkeit)
KD_WERT = 0.02         # Differential-Anteil für den PD-Regler (Dämpfung gegen Schwingen)


TRIM_MOTOR_A = 1.1     # Korrekturfaktor für linken Motor (A), falls er schwächer ist
TRIM_MOTOR_B = 1       # Korrekturfaktor für rechten Motor (B)

SERVER_IP = "192.168.67.100"  # IP-Adresse des Mac-Servers
SERVER_PORT = 50002           # Port (muss mit Server übereinstimmen)

WLAN_SSID = "iot-netz"        # WLAN-Name
WLAN_PASS = "13248918"        # WLAN-Passwort

# Feste Taktraten (Fahren priorisiert, Netzwerk gedrosselt)
DRIVE_INTERVAL_MS = 20       # Alle 20ms (50 Hz) wird die Fahr-Logik aufgerufen (Echtzeit)
NETWORK_INTERVAL_MS = 50     # Alle 50ms (20 Hz) wird das Netzwerk geprüft (weniger Last)

# Test-Flag: Netzwerk komplett deaktivieren (keine Verbindungsversuche)
ENABLE_NETWORK = True

# Linienzähler bei der Pivot-Drehung (experimentell)
PIVOT_LINE_COUNTER_ENABLED = False
PIVOT_TARGET_CENTER_COUNT = 3



# ===================================================================
# HARDWARE SETUP
# ===================================================================

MINDUTY_A = 29500    # Minimaler Duty-Cycle, damit Motor A sich dreht (Totzone)
MINDUTY_B = 27500    # Minimaler Duty-Cycle für Motor B

# Motor A (Links) - Pins definieren und PWM initialisieren
pin1_A = Pin(3, Pin.OUT)
pin2_A = Pin(4, Pin.OUT)
enable_A = PWM(Pin(2))
enable_A.freq(FREQUENCY)

# Motor B (Rechts)
pin1_B = Pin(5, Pin.OUT)
pin2_B = Pin(6, Pin.OUT)
enable_B = PWM(Pin(7))
enable_B.freq(FREQUENCY)

# Motoren-Objekte erstellen (mit MinDuty-Kalibrierung und Trim)
motor_A = DCMotor(pin1_A, pin2_A, enable_A, MINDUTY_A, 65535, TRIM_MOTOR_A, name="MOTOR_A", debug=False)
motor_B = DCMotor(pin1_B, pin2_B, enable_B, MINDUTY_B, 65535, TRIM_MOTOR_B, name="MOTOR_B", debug=False)


# Buttons
btn_red = Button(0)     # Roter Button (GPIO 0) für Pause/Reset
btn_green = Button(1)   # Grüner Button (GPIO 1) für Start/Resume

# Linien-Sensoren (Array mit 5 Sensoren)
sensor_array = Liniensensor(8, 9, 10, 11, 12, pull=Pin.PULL_UP)
# PD-Regler für die Linienverfolgung initialisieren
pd_controller = PDController(KP_WERT, KD_WERT, max_correction=55)

# LEDs
server_led = LED(16, 17, 18)   # RGB-LED für Server-Status
pico_led = LED(19, 20, 21)     # RGB-LED für Pico-Status
pico_led_sm = LEDStateMachine(pico_led)              # Zustandsmaschine für Pico-LED (blinken etc.)
connection_led_sm = ConnectionLEDStateMachine(server_led) # Zustandsmaschine für Netzwerk-LED

# Ultraschall-Sensoren
# HCSR04P ist eine angepasste Klasse für den Sensor
ultra = HCSR04P(trigger_pin=22, echo_pin=26, interval_ms=250, timeout_us=30_000) # Füllstand
obstacle_sensor = HCSR04P(trigger_pin=27, echo_pin=28, interval_ms=100, timeout_us=30_000) # Hindernis

# Wrapper für den Füllstandssensor (berechnet Prozentwerte)
fuell = FuellstandSensor(
    ultrasonic=ultra,
    leer_abstand_cm=27.85,
    voll_abstand_cm=10.0,
    deckel_offen_margin_cm=5.0)

# Buzzer für akustische Signale
buzzer = Buzzer(13, active_high=False)

# ===================================================================
# CONTROLLER SETUP
# ===================================================================

# Der GlobalController verbindet alle Hardware-Komponenten und steuert die Hauptlogik
global_controller = GlobalController(
    pico_led=pico_led,
    pico_led_sm=pico_led_sm,
    connection_led_sm=connection_led_sm,
    sensor_array=sensor_array,
    pd_controller=pd_controller,
    motor_A=motor_A,
    motor_B=motor_B,
    base_speed=BASE_SPEED,
    btn_red=btn_red,
    btn_green=btn_green,
    obstacle_sensor=obstacle_sensor,
    buzzer=buzzer,
    pivot_use_line_counter=PIVOT_LINE_COUNTER_ENABLED,
    pivot_center_count_target=PIVOT_TARGET_CENTER_COUNT
)
global_controller.set_fuellstand_sensor(fuell)

# Netzwerk-Manager initialisieren (verwaltet WLAN & Socket)
netman = NetworkManager(WLAN_SSID, WLAN_PASS, SERVER_IP, SERVER_PORT, global_controller)
global_controller.set_network_manager(netman)

if ENABLE_NETWORK:
    netman.start() # Startet den Verbindungsaufbau (non-blocking wenn möglich)

# NetworkController verarbeitet eingehende Befehle
networkcontroller = NetworkController(None, global_controller, network_manager=netman)


# ===================================================================
# GC-SETUP (stabilere Echtzeit)
# ===================================================================
gc.collect() # Speicherbereinigung vor dem Start
try:
    # Setzt den Schwellenwert für automatische GC höher, um Ruckler zu vermeiden
    # Nicht auf jedem Port verfügbar -> safe
    gc.threshold(50_000)
except AttributeError:
    pass

# ===================================================================
# HAUPTPROGRAMM
# ===================================================================
import dcmotor

# Zeitstempel für die nächsten Ausführungen initialisieren
next_drive_tick = time.ticks_ms()
next_network_tick = time.ticks_ms()

try:
    while True:
        now = time.ticks_ms()

        # --- TASK 1: FAHREN (Priorität) ---
        # Wird alle DRIVE_INTERVAL_MS (20ms) ausgeführt
        if time.ticks_diff(now, next_drive_tick) >= 0:
            global_controller.run() # Hauptlogik (Sensoren lesen, Motoren steuern)
            next_drive_tick = time.ticks_add(next_drive_tick, DRIVE_INTERVAL_MS)

            # Anti-Lag-Schutz: wenn wir zu weit hinterher sind, überspringen wir Ticks (Resync)
            if time.ticks_diff(time.ticks_ms(), next_drive_tick) > 0:
                next_drive_tick = time.ticks_add(time.ticks_ms(), DRIVE_INTERVAL_MS)

        # --- TASK 2: NETZWERK (gedrosselt) ---
        # Wird alle NETWORK_INTERVAL_MS (50ms) ausgeführt
        now = time.ticks_ms()

        if time.ticks_diff(now, next_network_tick) >= 0:
            # Netzwerk nur bearbeiten, wenn erlaubt (nicht im Hard-Offline-Mode beim Fahren)
            if ENABLE_NETWORK and global_controller.is_network_allowed():
                netman.run()             # Verbindung prüfen / wiederherstellen
                networkcontroller.run()  # Nachrichten empfangen
                global_controller.network_tick() # Nachrichten senden (Queue abarbeiten)

            next_network_tick = time.ticks_add(now, NETWORK_INTERVAL_MS)

        # Kurzer Sleep um CPU nicht unnötig zu belasten (optional, da Scheduler eh wartet)
        sleep(0.001)

except KeyboardInterrupt:
    pass # Erlaubt sauberes Beenden mit Strg+C

finally:
    # Cleanup: Alles sicher abschalten beim Beenden
    try:
        motor_A.stop()
    except Exception:
        pass
    try:
        motor_B.stop()
    except Exception:
        pass
    try:
        buzzer.stop()
    except Exception:
        pass
    try:
        # Pin 13 auf HIGH setzen (falls Active Low), um Buzzer stummzuschalten
        Pin(13, Pin.OUT).value(1)
    except Exception:
        pass
    try:
        enable_A.deinit()
    except Exception:
        pass
    try:
        enable_B.deinit()
    except Exception:
        pass

    try:
        s = netman.get_socket()
        if s:
            s.close()
    except Exception:
        pass

    try:
        pico_led.aus()
    except Exception:
        pass
    try:
        server_led.aus()
    except Exception:
        pass


# # # ----------------------------------------------------------------------------------------------------------------

# # # Einfaches Programm, das den Wert der Liniensensoren ausgibt

# # # print("=== Liniensensor Test ===")
# # # print("Format: [LA, LM, M, RM, RA] -> Position")

# # # while True:
# # #     # 1. Berechnete Position holen (None = keine Linie)
# # #     position = sensor_array.get_position()
    
# # #     # 2. Rohwerte der einzelnen Pins lesen (für die Anzeige)
# # #     raw = [
# # #         sensor_array.sensor_links_aussen.value(),
# # #         sensor_array.sensor_links_mitte.value(),
# # #         sensor_array.sensor_mitte.value(),
# # #         sensor_array.sensor_rechts_mitte.value(),
# # #         sensor_array.sensor_rechts_aussen.value()
# # #     ]
    
# # #     # 3. Ausgabe formatieren
# # #     # Position 0 ist mittig, negative Werte links, positive rechts
# # #     print(f"Sensoren: {raw} | Position: {position}")
    
# # #     sleep(0.2)

# # # ----------------------------------------------------------------------------------------------------------------

# # # # # # Programm für einfaches Geradeaus fahren:
# from machine import Pin, PWM
# from time import sleep

# from dcmotor import DCMotor
# from button import Button

# FREQUENCY = 1000

# # Zeiten
# STRAIGHT_S = 3.0
# TURN_S = 3.0

# # Geschwindigkeiten (0..100)
# STRAIGHT_SPEED = 40
# OUTER_TURN_SPEED = 40   # äußerer Motor in der Kurve
# INNER_TURN_SPEED = 10    # innerer Motor in der Kurve (sehr langsam)

# # Trim (wirkt automatisch auf alle forward()-Befehle)
# TRIM_MOTOR_A = 1.00
# TRIM_MOTOR_B = 0.85

# MINDUTY_A = 29500
# MINDUTY_B = 27500  # Beispielwert -> durch Test ersetzen

# # Motor A (Links)
# pin1_A = Pin(3, Pin.OUT)
# pin2_A = Pin(4, Pin.OUT)
# enable_A = PWM(Pin(2))
# enable_A.freq(FREQUENCY)


# # Motor B (Rechts)
# pin1_B = Pin(5, Pin.OUT)
# pin2_B = Pin(6, Pin.OUT)
# enable_B = PWM(Pin(7))
# enable_B.freq(FREQUENCY)

# motor_A = DCMotor(pin1_A, pin2_A, enable_A, MINDUTY_A, 65535, TRIM_MOTOR_A, name="MOTOR_A")
# motor_B = DCMotor(pin1_B, pin2_B, enable_B, MINDUTY_B, 65535, TRIM_MOTOR_B, name="MOTOR_B")

# # Grüner Button (GPIO 1)
# btn_green = Button(1)

# def stop_all():
#     motor_A.stop()
#     motor_B.stop()

# def drive_straight(seconds):
#     motor_A.forward(STRAIGHT_SPEED)
#     motor_B.forward(STRAIGHT_SPEED)
#     sleep(seconds)
#     stop_all()

# def curve_left(seconds):
#     # Links-Kurve: linker Motor = innerer (langsam), rechter Motor = äußerer (schnell)
#     motor_A.forward(INNER_TURN_SPEED)
#     motor_B.forward(OUTER_TURN_SPEED)
#     sleep(seconds)
#     stop_all()

# def curve_right(seconds):
#     # Rechts-Kurve: rechter Motor = innerer (langsam), linker Motor = äußerer (schnell)
#     motor_A.forward(OUTER_TURN_SPEED)
#     motor_B.forward(INNER_TURN_SPEED)
#     sleep(seconds)
#     stop_all()

# try:
#     while True:
#         press = btn_green.check_press_type()
#         if press == "SHORT":
#             drive_straight(STRAIGHT_S)
#             sleep(5)

#             motor_A.stop()
#             motor_B.stop()
#         sleep(0.01)

# except KeyboardInterrupt:
#     pass
# finally:
#     stop_all()
#     try:
#         enable_A.deinit()
#         enable_B.deinit()
#     except Exception:
#         pass

# # # --------------------------------------------------------

# # # Einfaches Programm zum Auslesen der Ultraschallwerte: (Maße der echten Distanzen werden oben beim Initialisieren definiert)

# # # Wie oft soll in der Konsole ausgegeben werden?
# # # PRINT_INTERVAL_MS = 1000

# # # print("Starte Füllstandsmessung (Ultraschall)...")
# # # print("Ausgabe: Distanz in cm und Füllstand in %")

# # # last_print_ms = time.ticks_ms()

# # # try:
# # #     while True:
# # #         # Sensor läuft non-blocking: einfach oft aufrufen
# # #         fuell.run()

# # #         # Nur alle PRINT_INTERVAL_MS eine Zeile ausgeben (sonst spamt es)
# # #         if time.ticks_diff(time.ticks_ms(), last_print_ms) >= PRINT_INTERVAL_MS:
# # #             last_print_ms = time.ticks_ms()

# # #             dist_cm = ultra.distance_cm  # letzter Messwert (kann auch None sein)
# # #             fuell_prozent = fuell.fuellstand_prozent

# # #             if fuell.deckel_offen:
# # #                 print("Deckel offen / kein Echo -> Distanz:", dist_cm, "cm")
# # #             else:
# # #                 if dist_cm is None or fuell_prozent is None:
# # #                     print("Keine gültige Messung -> Distanz:", dist_cm, "cm")
# # #                 else:
# # #                     print("Distanz: {:.1f} cm | Füllstand: {} %".format(dist_cm, fuell_prozent))

# # #         sleep(0.05)

# # # except KeyboardInterrupt:
# # #     print("Programm beendet.")

