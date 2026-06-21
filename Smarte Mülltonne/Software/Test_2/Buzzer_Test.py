import machine
import utime

# Initialisierung des Buzzer-Pins (GP0)
buzzer = machine.Pin(0, machine.Pin.OUT)

while True:
    # Schleife, um den Buzzer viermal piepen zu lassen
    for i in range(4):
        buzzer.value(1)  # Buzzer einschalten
        utime.sleep(0.3)  # 0,3 Sekunden warten
        buzzer.value(0)  # Buzzer ausschalten
        utime.sleep(0.3)  # 0,3 Sekunden warten
    utime.sleep(1)  # Längere Pause vor dem nächsten Zyklus