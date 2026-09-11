import machine
import utime

# Multiplexer-Steuerleitungen
s0 = machine.Pin(2, machine.Pin.OUT)
s1 = machine.Pin(3, machine.Pin.OUT)
s2 = machine.Pin(4, machine.Pin.OUT)
s3 = machine.Pin(5, machine.Pin.OUT)

# Gemeinsamer Trigger fuer alle Ultraschallsensoren
trigger = machine.Pin(6, machine.Pin.OUT)

# Gemeinsamer Echo-Eingang ueber MUX SIG/Z
echo = machine.Pin(15, machine.Pin.IN)

trigger.value(0)

def select_channel(channel):
    s0.value(channel & 1)
    s1.value((channel >> 1) & 1)
    s2.value((channel >> 2) & 1)
    s3.value((channel >> 3) & 1)
    utime.sleep_ms(5)

def measure_distance(channel):
    select_channel(channel)

    # kurzen Trigger-Impuls senden
    trigger.value(0)
    utime.sleep_us(2)
    trigger.value(1)
    utime.sleep_us(10)
    trigger.value(0)

    # warten bis Echo HIGH wird, mit Timeout
    timeout_start = utime.ticks_us()
    while echo.value() == 0:
        if utime.ticks_diff(utime.ticks_us(), timeout_start) > 30000:
            return None

    start = utime.ticks_us()

    # warten bis Echo wieder LOW wird, mit Timeout
    while echo.value() == 1:
        if utime.ticks_diff(utime.ticks_us(), start) > 30000:
            return None

    end = utime.ticks_us()

    duration = utime.ticks_diff(end, start)

    # Schallgeschwindigkeit: ca. 343 m/s
    # Entfernung in cm = Zeit_us / 58
    distance_cm = duration / 58.0

    return distance_cm

while True:
    for channel in range(5, 9):
        distance = measure_distance(channel)

        if distance is None:
            print("C{}: kein Echo / Timeout".format(channel))
        else:
            print("C{}: {:.1f} cm".format(channel, distance))

        utime.sleep_ms(80)

    print("-----")
    utime.sleep(0.5)