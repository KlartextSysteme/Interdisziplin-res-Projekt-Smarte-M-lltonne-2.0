import machine
import utime


# Multiplexer CD74HC4067
# S0-S3 steuern den ausgewaehlten Kanal C0-C15.
s0 = machine.Pin(2, machine.Pin.OUT)
s1 = machine.Pin(3, machine.Pin.OUT)
s2 = machine.Pin(4, machine.Pin.OUT)
s3 = machine.Pin(5, machine.Pin.OUT)

# Gemeinsamer Trigger fuer alle Ultraschallsensoren
trigger = machine.Pin(6, machine.Pin.OUT)

# SIG/Z/COM vom Multiplexer am Pico
mux_signal = machine.Pin(15, machine.Pin.IN)


LINE_CHANNELS = [0, 1, 2, 3, 4]
US_CHANNELS = [5, 6, 7, 8]


def select_channel(channel):
    s0.value(channel & 1)
    s1.value((channel >> 1) & 1)
    s2.value((channel >> 2) & 1)
    s3.value((channel >> 3) & 1)
    utime.sleep_ms(10)


def read_line_sensor(channel):
    select_channel(channel)
    utime.sleep_ms(2)
    return mux_signal.value()


def measure_ultrasonic(channel):
    select_channel(channel)

    trigger.value(0)
    utime.sleep_us(2)
    trigger.value(1)
    utime.sleep_us(10)
    trigger.value(0)

    start_timeout = utime.ticks_us()
    while mux_signal.value() == 0:
        if utime.ticks_diff(utime.ticks_us(), start_timeout) > 30000:
            return None

    start = utime.ticks_us()
    while mux_signal.value() == 1:
        if utime.ticks_diff(utime.ticks_us(), start) > 30000:
            return None

    end = utime.ticks_us()
    duration = utime.ticks_diff(end, start)
    return duration / 58.0


print("Starte Multiplexer-Test")
print("Liniensensoren: C0-C4")
print("Ultraschall-Echos: C5-C8")
print("Ultraschall-Trigger gemeinsam: GP6")
print("MUX SIG/Z: GP28")
print("-------------------")

trigger.value(0)

while True:
    line_values = []

    for channel in LINE_CHANNELS:
        value = read_line_sensor(channel)
        line_values.append(value)

    print("Linie C0-C4:", line_values)

    for index, value in enumerate(line_values):
        if value == 1:
            print("Linie Sensor", index, "(C" + str(index) + "): Linie erkannt")
        else:
            print("Linie Sensor", index, "(C" + str(index) + "): Hell")

    for channel in US_CHANNELS:
        distance = measure_ultrasonic(channel)

        if distance is None:
            print("Ultraschall C" + str(channel) + ": kein Echo / Timeout")
        else:
            print("Ultraschall C" + str(channel) + ":", round(distance, 1), "cm")

        utime.sleep_ms(80)

    print("-------------------")
    utime.sleep(0.5)