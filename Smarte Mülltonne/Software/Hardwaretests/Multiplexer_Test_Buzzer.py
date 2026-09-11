import machine
import utime

# CD74HC4067 Steuerleitungen
s0 = machine.Pin(2, machine.Pin.OUT)
s1 = machine.Pin(3, machine.Pin.OUT)
s2 = machine.Pin(4, machine.Pin.OUT)
s3 = machine.Pin(5, machine.Pin.OUT)

# Gemeinsamer Signalpin SIG/Z des Multiplexers
mux_signal = machine.Pin(28, machine.Pin.OUT)

# C0 auswaehlen: S0-S3 alle LOW
s0.value(0)
s1.value(0)
s2.value(1)
s3.value(1)

while True:
    mux_signal.value(1)
    utime.sleep(0.3)

    mux_signal.value(0)
    utime.sleep(0.3)