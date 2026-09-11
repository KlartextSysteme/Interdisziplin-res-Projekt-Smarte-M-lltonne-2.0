#https://github.com/gsampallo/micropython_examples/blob/master/74HC4067/multiplexor.py

from machine import Pin, ADC
import time

# -----------------------------
# Pinbelegung Raspberry Pi Pico
# -----------------------------

S0_PIN = 14
S1_PIN = 15
S2_PIN = 22
S3_PIN = 28
SIG_PIN = 26   # ADC0


# -----------------------------
# Kanäle am Multiplexer
# -----------------------------

LINE_LEFT = 0
LINE_MID_LEFT = 1
LINE_MID = 2
LINE_MID_RIGHT = 3
LINE_RIGHT = 4

US_FRONT_ECHO = 5
US_LEFT_ECHO = 6
US_RIGHT_ECHO = 7
US_FILL_ECHO = 8

MAGNET_SWITCH = 9
BATTERY = 10


# -----------------------------
# Multiplexer-Klasse
# -----------------------------

class Multiplexer4067:
    def __init__(self, s0, s1, s2, s3, sig_pin):
        self.s0 = Pin(s0, Pin.OUT)
        self.s1 = Pin(s1, Pin.OUT)
        self.s2 = Pin(s2, Pin.OUT)
        self.s3 = Pin(s3, Pin.OUT)

        self.adc = ADC(sig_pin)

        self.channels = [
            [0, 0, 0, 0],  # C0
            [1, 0, 0, 0],  # C1
            [0, 1, 0, 0],  # C2
            [1, 1, 0, 0],  # C3
            [0, 0, 1, 0],  # C4
            [1, 0, 1, 0],  # C5
            [0, 1, 1, 0],  # C6
            [1, 1, 1, 0],  # C7
            [0, 0, 0, 1],  # C8
            [1, 0, 0, 1],  # C9
            [0, 1, 0, 1],  # C10
            [1, 1, 0, 1],  # C11
            [0, 0, 1, 1],  # C12
            [1, 0, 1, 1],  # C13
            [0, 1, 1, 1],  # C14
            [1, 1, 1, 1],  # C15
        ]

    def select_channel(self, channel):
        if channel < 0 or channel > 15:
            raise ValueError("Kanal muss zwischen 0 und 15 liegen")

        self.s0.value(self.channels[channel][0])
        self.s1.value(self.channels[channel][1])
        self.s2.value(self.channels[channel][2])
        self.s3.value(self.channels[channel][3])

        time.sleep_us(20)

    def read_analog(self, channel):
        self.select_channel(channel)
        return self.adc.read_u16()

    def read_digital(self, channel, threshold=30000):
        value = self.read_analog(channel)
        return value > threshold


# -----------------------------
# Objekt erstellen
# -----------------------------

mux = Multiplexer4067(
    s0=S0_PIN,
    s1=S1_PIN,
    s2=S2_PIN,
    s3=S3_PIN,
    sig_pin=SIG_PIN
)


# -----------------------------
# Hauptprogramm zum Testen
# -----------------------------

while True:
    line_values = [
        mux.read_analog(LINE_LEFT),
        mux.read_analog(LINE_MID_LEFT),
        mux.read_analog(LINE_MID),
        mux.read_analog(LINE_MID_RIGHT),
        mux.read_analog(LINE_RIGHT)
    ]

    us_values = [
        mux.read_analog(US_FRONT_ECHO),
        mux.read_analog(US_LEFT_ECHO),
        mux.read_analog(US_RIGHT_ECHO),
        mux.read_analog(US_FILL_ECHO)
    ]

    deckel_offen = mux.read_digital(MAGNET_SWITCH)
    battery_value = mux.read_analog(BATTERY)

    print("-------------------------")
    print("Liniensensoren:", line_values)
    print("Ultraschall Echo:", us_values)
    print("Deckel offen:", deckel_offen)
    print("Akkuwert:", battery_value)

    time.sleep_ms(500)