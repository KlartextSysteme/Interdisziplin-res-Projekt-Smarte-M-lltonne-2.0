from machine import Pin, time_pulse_us
from time import sleep_us, sleep

# GPIO-Pins anpassen
TRIG_PIN = 28
ECHO_PIN = 27

trigger = Pin(TRIG_PIN, Pin.OUT)
echo = Pin(ECHO_PIN, Pin.IN)

def entfernung_messen():
    trigger.off()
    sleep_us(2)

    trigger.on()
    sleep_us(10)
    trigger.off()

    dauer = time_pulse_us(echo, 1, 30000)  # Timeout: 30 ms

    if dauer < 0:
        return None

    # Schallgeschwindigkeit: ca. 343 m/s
    # Entfernung in cm = Zeit / 58
    entfernung_cm = dauer / 58

    return entfernung_cm

print("Starte HC-SR04 Ultraschall-Test...")

while True:
    distanz = entfernung_messen()

    if distanz is None:
        print("Keine Messung möglich")
    else:
        print("Entfernung:", round(distanz, 1), "cm")

    sleep(0.5)