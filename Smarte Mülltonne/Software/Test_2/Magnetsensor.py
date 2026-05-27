from machine import Pin
from time import sleep_ms

# =========================
# MAGNETSCHALTER
# =========================

# GPIO anpassen
MAGNET_PIN = 28

magnet = Pin(MAGNET_PIN, Pin.IN, Pin.PULL_UP)

print("Starte Magnetschalter-Test")


# =========================
# HAUPTSCHLEIFE
# =========================

last_state = None

while True:

    # LOW = geschlossen
    # HIGH = offen
    state = magnet.value()

    if state != last_state:

        if state == 0:
            print("Deckel GESCHLOSSEN")

        else:
            print("Deckel GEOEFFNET")

        last_state = state

    sleep_ms(100)