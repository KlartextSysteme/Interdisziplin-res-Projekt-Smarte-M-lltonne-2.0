from machine import Pin, time_pulse_us
from time import sleep_us, sleep

# =========================
# GPIO
# =========================

TRIG_PIN = 16

ECHO_PINS = {
    "1": 28,
    "2": 27,
    "3": 26,
    "4": 22
}

# =========================
# SETUP
# =========================

trigger = Pin(TRIG_PIN, Pin.OUT)

echo_sensoren = {}

for name, pin in ECHO_PINS.items():
    echo_sensoren[name] = Pin(pin, Pin.IN)

trigger.off()

# =========================
# MESSUNG
# =========================

def entfernung_messen(echo_pin):

    # Triggerpuls
    trigger.off()
    sleep_us(2)

    trigger.on()
    sleep_us(10)
    trigger.off()

    # Echo messen
    dauer = time_pulse_us(echo_pin, 1, 30000)

    if dauer < 0:
        return None

    entfernung_cm = dauer / 58

    return entfernung_cm


# =========================
# TEST
# =========================

print("Starte Ultraschall-Test")

while True:

    for name, echo_pin in echo_sensoren.items():

        distanz = entfernung_messen(echo_pin)

        if distanz is None:
            print(name, ": Keine Messung")

        else:
            print(name, ":", round(distanz, 1), "cm")

        # kurze Pause zwischen Sensoren
        sleep_us(5000)

    print("----------------------")

    sleep(0.5)