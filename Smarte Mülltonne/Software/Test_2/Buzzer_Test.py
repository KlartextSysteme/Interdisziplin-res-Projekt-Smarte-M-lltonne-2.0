# from machine import Pin
# from time import sleep

# # GPIO-Pin des Buzzers anpassen
# buzzer = Pin(28, Pin.OUT)

# # Buzzer einschalten
# while True:
#     buzzer.on()
#     print("Buzzer EIN")
#     sleep(2)

#     # Buzzer ausschalten
#     buzzer.off()
#     print("Buzzer AUS")
#     sleep(2000)

import machine
import utime

# Initialisierung des Buzzer-Pins (GP15)
buzzer = machine.Pin(28, machine.Pin.OUT)

while True:
    # Schleife, um den Buzzer viermal piepen zu lassen
    for i in range(4):
        buzzer.value(1)  # Buzzer einschalten
        utime.sleep(0.3)  # 0,3 Sekunden warten
        buzzer.value(0)  # Buzzer ausschalten
        utime.sleep(0.3)  # 0,3 Sekunden warten
    utime.sleep(1)  # Längere Pause vor dem nächsten Zyklus