from machine import Pin
from time import sleep

# GPIO-Pin des Liniensensors anpassen
sensor_1 = Pin(15, Pin.IN)
sensor_2 = Pin(27, Pin.IN)

print("Starte Liniensensor-Test...")

while True:
    wert_1 = sensor_1.value()
    wert_2 = sensor_2.value()

    print("Sensorwert 1:", wert_1)
    print("Sensorwert 2:", wert_2)

    if wert_1 == 1 and wert_2 == 1:
        print("Linie 1+2 erkannt")
    elif wert_1 == 1:
        print("Linie 1 erkannt")
    elif wert_2 == 1:
        print("Linie 2 erkannt")
    else:
        print("keine Linie erkannt")

    print("-------------------")

    sleep(0.2)