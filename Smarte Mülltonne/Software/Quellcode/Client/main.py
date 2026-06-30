from time import sleep_ms

from buzzer import Buzzer
from global_controller_test import GlobalController
from liniensensor import Liniensensor
from multiplexer import Multiplexer
from PDcontroller import PDController
from steppermotor import DualStepperMotorPWM
from touchpanel import Touchpanel
from ultraschallsensor import FuellstandSensor, HindernisSensoren

#from tcp_bridge_client import TcpBridgeClient


# Pins laut aktuellem Pico-Pinout
MUX_S0_PIN = 2
MUX_S1_PIN = 3
MUX_S2_PIN = 4
MUX_S3_PIN = 5
MUX_SIGNAL_PIN = 28

US_TRIGGER_PIN = 6
US_FRONT_CHANNEL = 5
US_LEFT_CHANNEL = 7
US_RIGHT_CHANNEL = 6

# Testweise nutzt der Füllstand aktuell den vorderen US-Sensor.
# Werte nach dem Test am realen Aufbau kalibrieren.
FUELLSTAND_LEER_CM = 40
FUELLSTAND_VOLL_CM = 5

BUZZER_PIN = 0

LEFT_DIR_PIN = 10
LEFT_STEP_PIN = 11
LEFT_ENABLE_PIN = 12

RIGHT_DIR_PIN = 13
RIGHT_STEP_PIN = 8
RIGHT_ENABLE_PIN = 9

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
        side_clear_cm=200,
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
        base_speed=45,
        min_speed=0,
        max_speed=95,
    )

    # network_client = TcpBridgeClient(
    #     ssid="DEIN_WLAN_NAME",
    #     password="DEIN_WLAN_PASSWORT",
    #     bridge_host="IP_DES_LAPTOPS",
    #     bridge_port=50002,
    #     command_handler=controller.handle_network_command,
    #     status_provider=controller.get_network_status,
    # )
    
    #network_client.start()

    touchpanel = Touchpanel(action_handler=controller.handle_touch_action)
    touchpanel.init()
    controller.touchpanel = touchpanel

    return controller#, network_client



#controller, network_client = create_controller()
controller = create_controller()

print("Main gestartet")
print("Touchpanel: ABHOLUNG -> goto_street, HEIM -> goto_home")
print("Zum Stoppen: Strg+C / Reset")

try:
    while True:
        controller.run()
        #network_client.tick()
        sleep_ms(20)
except KeyboardInterrupt:
    controller.stop()
    print("Main gestoppt")
