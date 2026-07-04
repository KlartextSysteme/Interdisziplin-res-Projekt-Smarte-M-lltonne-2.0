from time import sleep_ms, ticks_ms, ticks_diff

from buzzer import Buzzer
from global_controller_test import GlobalController
from liniensensor import Liniensensor
from multiplexer import Multiplexer
from PDcontroller import PDController
from steppermotor import DualStepperMotorPWM
from touchpanel import Touchpanel
from ultraschallsensor import FuellstandSensor, HindernisSensoren, UltraschallsensorMUX

from tcp_bridge_client import TcpBridgeClient
from config import (
    ENABLE_TCP_BRIDGE,
    WLAN_SSID,
    WLAN_PASSWORD,
    BRIDGE_HOST,
    BRIDGE_PORT,
)


# Pins laut aktuellem Pico-Pinout (MUX-Steuerung: GP1-GP4 = S0-S3, GP5 = SIG)
MUX_S0_PIN = 1
MUX_S1_PIN = 2
MUX_S2_PIN = 3
MUX_S3_PIN = 4
MUX_SIGNAL_PIN = 5

US_TRIGGER_PIN = 6
US_FRONT_CHANNEL = 5
US_LEFT_CHANNEL = 7
US_RIGHT_CHANNEL = 6

# Füllstand hat einen eigenen MUX-Kanal (C8), gemeinsamer Trigger mit den US-Sensoren.
# Werte nach dem Test am realen Aufbau kalibrieren.
FUELLSTAND_CHANNEL = 8
FUELLSTAND_LEER_CM = 40
FUELLSTAND_VOLL_CM = 5

BUZZER_PIN = 0

# Motor-Pinsaetze L<->R getauscht: am realen Aufbau (2026-07-04, T1) fuhr die
# alte Zuordnung 10/11/12=links, 13/8/9=rechts rueckwaerts + spiegelverkehrt.
# Verifiziert per Referenz-Linienlauf (Position pendelt sauber um 0).
LEFT_DIR_PIN = 13
LEFT_STEP_PIN = 8
LEFT_ENABLE_PIN = 9

RIGHT_DIR_PIN = 10
RIGHT_STEP_PIN = 11
RIGHT_ENABLE_PIN = 12

LEFT_FORWARD_DIR = 1
RIGHT_FORWARD_DIR = 0


def create_controller():
    mux = Multiplexer(
        s0_pin=MUX_S0_PIN,
        s1_pin=MUX_S1_PIN,
        s2_pin=MUX_S2_PIN,
        s3_pin=MUX_S3_PIN,
        signal_pin=MUX_SIGNAL_PIN,
    )

    line_sensor = Liniensensor(
        multiplexer=mux,
        channels=(0, 1, 2, 3, 4),
        weights=(2, 1, 0, -1, -2),
        line_detected_value=1,
    )

    obstacle_sensors = HindernisSensoren(
        multiplexer=mux,
        trigger_pin=US_TRIGGER_PIN,
        front_channel=US_FRONT_CHANNEL,
        left_channel=US_LEFT_CHANNEL,
        right_channel=US_RIGHT_CHANNEL,
        stop_cm=30,
        side_clear_cm=40,
        # Ohne Echo (freie Fahrt) sonst 30ms Block pro Messung -> Regel-Jitter.
        # 8000us decken ~138cm ab, mehr wird fuers Hindernis nicht gebraucht.
        timeout_us=8000,
    )

    fuellstand_us = UltraschallsensorMUX(
        multiplexer=mux,
        trigger_pin=US_TRIGGER_PIN,
        echo_channel=FUELLSTAND_CHANNEL,
        timeout_us=8000,
        name="US Fuellstand",
    )

    fuellstand_sensor = FuellstandSensor(
        ultrasonic=fuellstand_us,
        leer_abstand_cm=FUELLSTAND_LEER_CM,
        voll_abstand_cm=FUELLSTAND_VOLL_CM,
    )

    pd_controller = PDController(
        kp=32,
        kd=2,
        target_position=0,
        max_correction=60,
    )

    motors = DualStepperMotorPWM(
        left_dir_pin=LEFT_DIR_PIN,
        left_step_pin=LEFT_STEP_PIN,
        left_enable_pin=LEFT_ENABLE_PIN,
        right_dir_pin=RIGHT_DIR_PIN,
        right_step_pin=RIGHT_STEP_PIN,
        right_enable_pin=RIGHT_ENABLE_PIN,
        min_freq=2000,
        max_freq=4500,
        left_forward_dir=LEFT_FORWARD_DIR,
        right_forward_dir=RIGHT_FORWARD_DIR,
        enable_active_value=1,
        debug=False,
    )

    buzzer = Buzzer(BUZZER_PIN, active_high=True)

    controller = GlobalController(
        line_sensor=line_sensor,
        obstacle_sensors=obstacle_sensors,
        pd_controller=pd_controller,
        motors=motors,
        buzzer=buzzer,
        fuellstand_sensor=fuellstand_sensor,
        touchpanel=None,
        base_speed=60,
        min_speed=0,
        max_speed=95,
    )

    touchpanel = Touchpanel(action_handler=controller.handle_touch_action)
    touchpanel.init()
    controller.touchpanel = touchpanel

    network_client = None
    if ENABLE_TCP_BRIDGE:
        network_client = TcpBridgeClient(
            ssid=WLAN_SSID,
            password=WLAN_PASSWORD,
            bridge_host=BRIDGE_HOST,
            bridge_port=BRIDGE_PORT,
            command_handler=controller.handle_network_command,
            status_provider=controller.get_network_status,
        )
        controller.set_network_client(network_client)
        network_client.start()

    return controller, network_client



controller, network_client = create_controller()

print("Main gestartet")
print("Touchpanel: ABHOLUNG -> goto_street, HEIM -> goto_home")
print("Zum Stoppen: Strg+C / Reset")

last_net_ms = ticks_ms()

try:
    while True:
        controller.run()

        # Netzwerk gedrosselt bedienen (nicht-blockierend): Befehle empfangen +
        # STATUS senden. So bleibt der enge Regeltakt der Fahrt ungestoert und
        # ein CMD_STOP aus der Web-App greift trotzdem mitten in der Fahrt.
        if network_client is not None:
            now = ticks_ms()
            if ticks_diff(now, last_net_ms) >= 40:
                last_net_ms = now
                try:
                    network_client.tick()
                except Exception as exc:
                    print("network tick failed:", exc)

        sleep_ms(5)
except KeyboardInterrupt:
    controller.stop()
    print("Main gestoppt")
