from machine import Pin
from time import sleep

# KY-021 Magnet-Schalter an GP1
# Bei internem Pull-up gilt normalerweise:
# 1 = kein Magnet erkannt, 0 = Magnet erkannt
magnet_schalter = Pin(1, Pin.IN, Pin.PULL_UP)

print("Starte KY-021 Magnet-Schalter-Test auf GP2...")

while True:
    wert = magnet_schalter.value()

    print("Sensorwert:", wert)

    if wert == 0:
        print("Magnet erkannt")
    else:
        print("kein Magnet erkannt")

    print("-------------------")
    sleep(0.2)