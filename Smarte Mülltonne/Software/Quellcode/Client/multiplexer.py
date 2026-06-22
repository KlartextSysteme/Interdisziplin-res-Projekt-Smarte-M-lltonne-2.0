from machine import Pin
from time import sleep_us

class Multiplexer:
    """
    Treiberklasse für den CD74HC4067 Multiplexer.

    Der Multiplexer wählt einen von 16 Kanaelen C0-C15 aus.
    Das gemeinsame Signal liegt am SIG/Z/COM-Pin.
    """

    def __init__(
        self,
        s0_pin,
        s1_pin,
        s2_pin,
        s3_pin,
        signal_pin,
        settle_us=500,
        signal_mode=Pin.IN,
        signal_pull=None,
        debug=False,
    ):
        self.s0 = Pin(s0_pin, Pin.OUT)
        self.s1 = Pin(s1_pin, Pin.OUT)
        self.s2 = Pin(s2_pin, Pin.OUT)
        self.s3 = Pin(s3_pin, Pin.OUT)

        if signal_pull is None:
            self.signal = Pin(signal_pin, signal_mode)
        else:
            self.signal = Pin(signal_pin, signal_mode, signal_pull)

        self.settle_us = settle_us
        self.debug = debug
        self.current_channel = None

    def select_channel(self, channel):
        """
        Wählt einen Multiplexer-Kanal von 0 bis 15 aus.
        """
        if channel < 0 or channel > 15:
            raise ValueError("Multiplexer-Kanal muss zwischen 0 und 15 liegen")

        self.s0.value(channel & 1)
        self.s1.value((channel >> 1) & 1)
        self.s2.value((channel >> 2) & 1)
        self.s3.value((channel >> 3) & 1)

        self.current_channel = channel

        if self.settle_us > 0:
            sleep_us(self.settle_us)

        if self.debug:
            print("MUX Kanal:", channel)

    def read(self, channel):
        """
        W#hlt einen Kanal aus und liest danach den SIG-Pin digital ein.
        """
        self.select_channel(channel)
        return self.signal.value()

    def value(self):
        """
        Liest den SIG-Pin des aktuell ausgewählten Kanals.
        """
        return self.signal.value()
