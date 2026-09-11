from machine import Pin, time_pulse_us
from time import sleep_us, sleep

# ohne pwm und Liniensensor und Multiplexer muss bearbeitet werden
# =====================================
# Ultraschallsensor HC-SR04
# =====================================

class Ultraschall:
    def __init__(self, trig_pin, echo_pin):
        self.trig = Pin(trig_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)

        self.trig.value(0)
        sleep_us(2)

    def distance_cm(self):

        self.trig.value(0)
        sleep_us(2)

        self.trig.value(1)
        sleep_us(10)
        self.trig.value(0)

        try:
            dauer = time_pulse_us(self.echo, 1, 30000)

            if dauer < 0:
                return 999

            return dauer / 58.0

        except:
            return 999


# =====================================
# Slide Switch muss mit LinienSensor ersetzt
# =====================================

switch = Pin(6, Pin.IN, Pin.PULL_UP)

# =====================================
# Dual Stepper A4988
# =====================================

class DualStepper:

    def __init__(
        self,
        left_dir_pin,
        left_step_pin,
        left_enable_pin,
        right_dir_pin,
        right_step_pin,
        right_enable_pin,
        delay_us=500
    ):

        self.left_dir = Pin(left_dir_pin, Pin.OUT)
        self.left_step = Pin(left_step_pin, Pin.OUT)
        self.left_enable = Pin(left_enable_pin, Pin.OUT)

        self.right_dir = Pin(right_dir_pin, Pin.OUT)
        self.right_step = Pin(right_step_pin, Pin.OUT)
        self.right_enable = Pin(right_enable_pin, Pin.OUT)

        self.delay_us = delay_us

        # A4988 aktivieren
        self.left_enable.value(0)
        self.right_enable.value(0)

    def move_together(self, schritte, left_dir, right_dir):

        self.left_dir.value(left_dir)
        self.right_dir.value(right_dir)

        for _ in range(schritte):

            self.left_step.value(1)
            self.right_step.value(1)

            sleep_us(self.delay_us)

            self.left_step.value(0)
            self.right_step.value(0)

            sleep_us(self.delay_us)

    def geradeaus_fahrt(self, schritte):
        self.move_together(schritte, 1, 1)

    def rueckwaerts_fahrt(self, schritte):
        self.move_together(schritte, 0, 0)

    def drehung_links(self, schritte):
        self.move_together(schritte, 0, 1)

    def drehung_rechts(self, schritte):
        self.move_together(schritte, 1, 0)


# Motoren


motors = DualStepper(
    left_dir_pin=10,
    left_step_pin=11,
    left_enable_pin=12,

    right_dir_pin=13,
    right_step_pin=14,
    right_enable_pin=15,

    delay_us=50000
)


# Ultraschallsensoren
# US1 Mitte: Trig=0 Echo=1
# US2 Rechts: Trig=2 Echo=3
# US3 Links: Trig=4 Echo=5


us_mitte = Ultraschall(0, 1)
us_rechts = Ultraschall(2, 3)
us_links = Ultraschall(4, 5)


# Hauptprogramm


MIN_ABSTAND = 30  # cm


#while True:

links = us_links.distance_cm()
mitte = us_mitte.distance_cm()
rechts = us_rechts.distance_cm()

print("--------------------------------")
print("Links :", round(links, 1), "cm")
print("Mitte :", round(mitte, 1), "cm")
print("Rechts:", round(rechts, 1), "cm")


motors.geradeaus_fahrt(300)

    # Hindernis direkt vor dem Roboter
if mitte < MIN_ABSTAND:
    print("Hindernis vorne!")

    motors.drehung_rechts(50)

    sleep(0.2)
        

    motors.geradeaus_fahrt(100)

    links = us_links.distance_cm()
    mitte = us_mitte.distance_cm()
    rechts = us_rechts.distance_cm()

    if links > MIN_ABSTAND:

        print("links drehen")

        motors.drehung_links(50)

        motors.geradeaus_fahrt(100)

        links = us_links.distance_cm()
        mitte = us_mitte.distance_cm()
        rechts = us_rechts.distance_cm()
        
        if links > MIN_ABSTAND:

            print("links drehen")

            motors.drehung_links(50)

            motors.geradeaus_fahrt(100)

            if switch.value() == 1 :

                print("rechts drehen")

                motors.drehung_rechts(50)
                sleep(0.2)

    elif rechts > MIN_ABSTAND:

        print("links drehen")

        motors.drehung_rechts(50)

        motors.geradeaus_fahrt(100)
        
        links = us_links.distance_cm()
        mitte = us_mitte.distance_cm()
        rechts = us_rechts.distance_cm()

        if rechts > MIN_ABSTAND:

            print("links drehen")

            motors.drehung_rechts(50)

            motors.geradeaus_fahrt(100)

            if switch.value() == 1 :

                motors.drehung_links(50)
                sleep(0.2)        
