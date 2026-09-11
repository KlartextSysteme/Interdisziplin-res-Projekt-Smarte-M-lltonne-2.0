import machine
import utime

s0 = machine.Pin(2, machine.Pin.OUT)
s1 = machine.Pin(3, machine.Pin.OUT)
s2 = machine.Pin(4, machine.Pin.OUT)
s3 = machine.Pin(5, machine.Pin.OUT)

mux_signal = machine.Pin(15, machine.Pin.IN)

def select_channel(channel):
    s0.value(channel & 1)
    s1.value((channel >> 1) & 1)
    s2.value((channel >> 2) & 1)
    s3.value((channel >> 3) & 1)
    utime.sleep_ms(5)

def read_line_sensor(channel):
    select_channel(channel)
    return mux_signal.value()

while True:
    werte = []

    for channel in range(5):
        wert = read_line_sensor(channel)
        werte.append(wert)

    print("C0-C4:", werte)

    for i, wert in enumerate(werte):
        if wert == 1:
            print("Sensor", i, ": Linie erkannt")
        else:
            print("Sensor", i, ": Hell / keine Linie")

    print("-----")
    utime.sleep(0.3)