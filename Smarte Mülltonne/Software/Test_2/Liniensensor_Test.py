from machine import Pin
from time import sleep

# GPIO-Pin des Liniensensors anpassen
sensor = Pin(28, Pin.IN)

print("Starte Liniensensor-Test...")

while True:
    wert = sensor.value()

    print("Sensorwert:", wert)

    if wert == 1:
        print("Linie erkannt")
    else:
        print("keine Linie erkannt")

    print("-------------------")

    sleep(0.2)