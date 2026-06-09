import machine
import utime

s0 = machine.Pin(2, machine.Pin.OUT)
s1 = machine.Pin(3, machine.Pin.OUT)
s2 = machine.Pin(4, machine.Pin.OUT)
s3 = machine.Pin(5, machine.Pin.OUT)

# SIG/Z vom Multiplexer an GP28
mux_signal = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_DOWN)

# Bit-Zahl bilden
# &1    -> nur erstes Bit von rechts betrachten
# >>1   -> Binärzahl um 1 nach rechts verschieben
def select_channel(channel):
    s0.value(channel & 1)
    s1.value((channel >> 1) & 1)
    s2.value((channel >> 2) & 1)
    s3.value((channel >> 3) & 1)
    utime.sleep_ms(10)

# C1 auswaehlen
select_channel(1)

while True:
    wert = mux_signal.value()

    print("C1 Rohwert:", wert)

    if wert == 1:
        print("Linie erkannt")
    else:
        print("Hell / keine Linie")

    utime.sleep(0.3)