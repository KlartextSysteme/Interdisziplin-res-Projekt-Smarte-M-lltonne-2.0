from machine import Pin
import time


class Multiplexer16:
    """
    Treiber für einen 16-Kanal-Multiplexer (CD74HC4067)
    S0-S3 waehlen den aktiven Kanal C0-C15.
    """

    def __init__(self, s0_pin, s1_pin, s2_pin, s3_pin, signal_pin, settle_ms=2):
        # S0-S3 steuern den ausgewaehlten Kanal C0-C15.
        self.s0 = Pin(s0_pin, Pin.OUT)
        self.s1 = Pin(s1_pin, Pin.OUT)
        self.s2 = Pin(s2_pin, Pin.OUT)
        self.s3 = Pin(s3_pin, Pin.OUT)

        self.signal = Pin(signal_pin, Pin.IN)
        self.settle_ms = settle_ms
        self.current_channel = None

    def select_channel(self, channel):
        if channel < 0 or channel > 15:
            raise ValueError("Multiplexer-Kanal muss zwischen 0 und 15 liegen")

        # Auswahl des Multiplexer-Kanals; Bit-Zahl bilden; &1-> nur erstes Bit von rechts betrachten; >>1-> Binärzahl um 1 nach rechts verschieben
        self.s0.value(channel & 1)
        self.s1.value((channel >> 1) & 1)
        self.s2.value((channel >> 2) & 1)
        self.s3.value((channel >> 3) & 1)

        self.current_channel = channel
        time.sleep_ms(self.settle_ms)

    def read_digital(self, channel):
        self.select_channel(channel)
        return self.signal.value()