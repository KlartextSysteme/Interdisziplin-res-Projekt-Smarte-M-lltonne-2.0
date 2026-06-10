from machine import Pin, time_pulse_us
from time import sleep, sleep_us


class Stepper:
    def __init__(self, dir_pin, step_pin, delay_us=2000,
                 steps_per_rev=200, name="STEPPER", debug=True):

        self.dir = Pin(dir_pin, Pin.OUT)
        self.step = Pin(step_pin, Pin.OUT)

        self.delay = delay_us
        self.steps_per_rev = steps_per_rev
        self.name = name
        self.debug = debug

        self.step.value(0)

    def step_once(self):
        self.step.value(1)
        sleep_us(self.delay)
        self.step.value(0)
        sleep_us(self.delay)

    def move(self, steps, direction):
        self.dir.value(direction)

        for _ in range(steps):
            self.step_once()

    def dreh_rechts(self):
        schritte_90 = self.steps_per_rev // 4
        self.move(schritte_90, 1)

    def dreh_links(self):
        schritte_90 = self.steps_per_rev // 4
        self.move(schritte_90, 0)


# ---------------- ULTRASCHALL ----------------
# Sensor 1
TRIG1 = Pin(4, Pin.OUT)
ECHO1 = Pin(5, Pin.IN)

# Sensor 2
TRIG2 = Pin(6, Pin.OUT)
ECHO2 = Pin(7, Pin.IN)

# Sensor 3
TRIG3 = Pin(8, Pin.OUT)
ECHO3 = Pin(9, Pin.IN)


def entfernung_cm(trig, echo):
    trig.value(0)
    sleep_us(2)

    trig.value(1)
    sleep_us(10)
    trig.value(0)

    dauer = time_pulse_us(echo, 1, 30000)

    if dauer < 0:
        return None

    return dauer / 58.0

#------------------------------Test----------------------------#

#motor1 = Stepper(dir_pin=0, step_pin=1)
#motor2 = Stepper(dir_pin=2, step_pin=3)

#while True:
#    motor1.dreh_rechts()
#    sleep(1)

#    motor1.dreh_links()
#    sleep(1)

#    motor2.dreh_rechts()
#    sleep(1)

#    motor2.dreh_links()
#    sleep(1)

# ---------------- TEST ----------------
#while True:

 #   motor1 = Stepper(dir_pin=0, step_pin=1)
  #  abstand = entfernung_cm()

   # if abstand is not None:
   #     print("Abstand:", round(abstand, 1), "cm")
#
 #       if abstand <= 50:
  #          print("Objekt erkannt -> Motor rechts")
   #         motor1.dreh_rechts()
#
 #   sleep(0.5)


class Robot:
    def __init__(self, motor1, motor2):
        self.m1 = motor1
        self.m2 = motor2

    def forward(self):
        self.m1.dreh_rechts()   # oder move(...) falls du vorwärts definiert hast
        self.m2.dreh_rechts()

    def back(self):
        self.m1.dreh_links()
        self.m2.dreh_links()

    def right(self):
        self.m1.dreh_rechts()
        self.m2.dreh_links()

    def left(self):
        self.m1.dreh_links()
        self.m2.dreh_rechts()

 # ---------------- TEST Ultraschall und Motor combination----------------
#while True:

 #   motor1 = Stepper(dir_pin=0, step_pin=1)
 #   motor2 = Stepper(dir_pin=2, step_pin=3)

 #   abstand1 = entfernung_cm(TRIG1, ECHO1)
 #   abstand2 = entfernung_cm(TRIG2, ECHO2)
 #   abstand3 = entfernung_cm(TRIG3, ECHO3)

 #   if abstand1 is not None and abstand1 <= 50:
 #       print("Sensor 1 erkannt")
 #       motor1.dreh_rechts()

  #  if abstand2 is not None and abstand2 <= 50:
 #       print("Sensor 2 erkannt")
  #      motor2.dreh_rechts()

 #   if abstand3 is not None and abstand3 <= 50:
 #       print("Sensor 3 erkannt")
  #      motor1.dreh_rechts()

  #  sleep(0.5)

 # ---------------- TEST Ultraschall und Motor combination----------------

motor1 = Stepper(dir_pin=0, step_pin=1)
motor2 = Stepper(dir_pin=2, step_pin=3)

robot = Robot(motor1, motor2)

while True:

    abstand1 = entfernung_cm(TRIG1, ECHO1)
    abstand2 = entfernung_cm(TRIG2, ECHO2)
    abstand3 = entfernung_cm(TRIG3, ECHO3)

    # Default: vorwärts fahren
    move_done = False

    # Sensor 1 → Hindernis links
    if abstand1 is not None and abstand1 <= 50:
        print("Sensor 1 -> links ausweichen")
        robot.left()
        move_done = True

    # Sensor 2 → vorne
    elif abstand2 is not None and abstand2 <= 50:
        print("Sensor 2 -> zurück")
        robot.back()
        move_done = True

    # Sensor 3 → rechts
    elif abstand3 is not None and abstand3 <= 50:
        print("Sensor 3 -> rechts ausweichen")
        robot.right()
        move_done = True

    # Wenn nichts erkannt → vorwärts
    if not move_done:
       robot.forward()

    sleep(0.3)