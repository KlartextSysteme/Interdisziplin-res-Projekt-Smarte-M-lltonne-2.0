from time import sleep_ms

from buzzer import Buzzer
from global_controller_test import GlobalController
from liniensensor import Liniensensor
from multiplexer import Multiplexer
from network_controller import NetworkController
from network_manager import NetworkManager
from PDcontroller import PDController
from steppermotor import DualStepperMotorPWM
from touchpanel import Touchpanel
from ultraschallsensor import FuellstandSensor, HindernisSensoren


# Pins laut aktuellem Pico-Pinout
MUX_S0_PIN = 2
MUX_S1_PIN = 3
MUX_S2_PIN = 4
MUX_S3_PIN = 5
MUX_SIGNAL_PIN = 28

US_TRIGGER_PIN = 6
US_FRONT_CHANNEL = 5
US_LEFT_CHANNEL = 6
US_RIGHT_CHANNEL = 7
US_STOP_CM = 15
US_INTERVAL_MS = 120

# Testweise nutzt der Füllstand aktuell den vorderen US-Sensor.
# Werte nach dem Test am realen Aufbau kalibrieren.
FUELLSTAND_LEER_CM = 40
FUELLSTAND_VOLL_CM = 5

ENABLE_NETWORK = True
WIFI_SSID = "SmartBinDemo"
WIFI_PASSWORD = "SmartBin2026!"
BRIDGE_HOST = "192.168.50.10"
BRIDGE_PORT = 50002

BUZZER_PIN = 0

LEFT_DIR_PIN = 10
LEFT_STEP_PIN = 11
LEFT_ENABLE_PIN = 12

RIGHT_DIR_PIN = 13
RIGHT_STEP_PIN = 8
RIGHT_ENABLE_PIN = 9

LEFT_FORWARD_DIR = 1
RIGHT_FORWARD_DIR = 0


def create_runtime():
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
        samples_per_read=1,
        sample_delay_us=0,
        read_delay_us=300,
    )

    obstacle_sensors = HindernisSensoren(
        multiplexer=mux,
        trigger_pin=US_TRIGGER_PIN,
        front_channel=US_FRONT_CHANNEL,
        left_channel=US_LEFT_CHANNEL,
        right_channel=US_RIGHT_CHANNEL,
        stop_cm=US_STOP_CM,
        side_clear_cm=200,
        interval_ms=US_INTERVAL_MS,
    )

    fuellstand_sensor = FuellstandSensor(
        ultrasonic=obstacle_sensors.front,
        leer_abstand_cm=FUELLSTAND_LEER_CM,
        voll_abstand_cm=FUELLSTAND_VOLL_CM,
    )

    pd_controller = PDController(
        kp=32,
        kd=2,
        target_position=0,
        max_correction=80,
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
        base_speed=45,
        min_speed=0,
        max_speed=95,
    )

    touchpanel = Touchpanel(action_handler=controller.handle_touch_action)
    touchpanel.init()
    controller.touchpanel = touchpanel

    network_manager = None
    network_controller = None
    if ENABLE_NETWORK:
        network_manager = NetworkManager(
            WIFI_SSID,
            WIFI_PASSWORD,
            BRIDGE_HOST,
            BRIDGE_PORT,
            controller,
        )
        controller.set_network_manager(network_manager)
        network_controller = NetworkController(
            None,
            controller,
            network_manager,
        )
        network_manager.start()

    return controller, network_manager, network_controller


controller, network_manager, network_controller = create_runtime()

print("Main gestartet")
print("Touchpanel: ABHOLUNG -> goto_street, HEIM -> goto_home")
if ENABLE_NETWORK:
    print("Netzwerk: " + WIFI_SSID + " -> " + BRIDGE_HOST + ":" + str(BRIDGE_PORT))
print("Zum Stoppen: Strg+C / Reset")

try:
    while True:
        if network_manager is not None:
            network_manager.run()
        if network_controller is not None:
            network_controller.run()
        controller.run()
        sleep_ms(20)
except KeyboardInterrupt:
    controller.stop()
    print("Main gestoppt")
