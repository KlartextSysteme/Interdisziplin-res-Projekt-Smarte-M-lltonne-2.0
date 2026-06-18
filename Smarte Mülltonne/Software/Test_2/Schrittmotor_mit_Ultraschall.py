from machine import Pin, PWM
from time import sleep, sleep_us, ticks_us, ticks_diff


class MultiplexerUltraschall:
    def __init__(self,s0_pin,s1_pin,s2_pin,s3_pin,trigger_pin,signal_pin,us_channels):

        self.s0 = Pin(s0_pin, Pin.OUT)
        self.s1 = Pin(s1_pin, Pin.OUT)
        self.s2 = Pin(s2_pin, Pin.OUT)
        self.s3 = Pin(s3_pin, Pin.OUT)

        self.trigger = Pin(trigger_pin, Pin.OUT)
        self.signal = Pin(signal_pin, Pin.IN)

        self.us_channels = us_channels

        self.trigger.value(0)

    def select_channel(self, channel):
        self.s0.value(channel & 1)
        self.s1.value((channel >> 1) & 1)
        self.s2.value((channel >> 2) & 1)
        self.s3.value((channel >> 3) & 1)
        sleep_us(1000)

    def measure_ultrasonic(self, channel):
        self.select_channel(channel)

        self.trigger.value(0)
        sleep_us(2)
        self.trigger.value(1)
        sleep_us(10)
        self.trigger.value(0)

        start_timeout = ticks_us()
        while self.signal.value() == 0:
            if ticks_diff(ticks_us(), start_timeout) > 30000:
                return None

        start = ticks_us()
        while self.signal.value() == 1:
            if ticks_diff(ticks_us(), start) > 30000:
                return None

        end = ticks_us()
        duration = ticks_diff(end, start)

        return duration / 58.0

    def nearest_distance(self):
        nearest = None
        nearest_channel = None

        for channel in self.us_channels:
            distance = self.measure_ultrasonic(channel)

            if distance is not None:
                if nearest is None or distance < nearest:
                    nearest = distance
                    nearest_channel = channel

            sleep_us(80000)

        return nearest, nearest_channel


class DualStepperPWM:
    def __init__(self,left_dir_pin,left_step_pin,left_enable_pin,right_dir_pin,right_step_pin,right_enable_pin,frequency=4500,enable_active_value=1):

        self.left_dir = Pin(left_dir_pin, Pin.OUT)
        self.right_dir = Pin(right_dir_pin, Pin.OUT)

        self.left_enable = Pin(left_enable_pin, Pin.OUT)
        self.right_enable = Pin(right_enable_pin, Pin.OUT)

        self.left_step = PWM(Pin(left_step_pin))
        self.right_step = PWM(Pin(right_step_pin))

        self.frequency = frequency

        self.enable_active_value = enable_active_value
        self.disable_value = 0 if enable_active_value == 1 else 1

        self.disable()

    def enable(self):
        self.left_enable.value(self.enable_active_value)
        self.right_enable.value(self.enable_active_value)

    def disable(self):
        self.left_enable.value(self.disable_value)
        self.right_enable.value(self.disable_value)

    def stop(self):
        self.left_step.duty_u16(0)
        self.right_step.duty_u16(0)
        self.disable()

    def start_moving(self, left_dir, right_dir, frequency=None):
        if frequency is None:
            frequency = self.frequency

        self.enable()

        self.left_dir.value(left_dir)
        self.right_dir.value(right_dir)

        sleep(0.02)

        self.left_step.freq(frequency)
        self.right_step.freq(frequency)

        self.left_step.duty_u16(32768)
        self.right_step.duty_u16(32768)

    def move_together(self, schritte, left_dir, right_dir, frequency=None):
        if frequency is None:
            frequency = self.frequency

        self.start_moving(left_dir, right_dir, frequency)

        dauer = schritte / frequency
        sleep(dauer)

        self.stop()

    def geradeaus_start(self):
        self.start_moving(1, 0, frequency=4000)

    def drehung_links(self, schritte):
        self.move_together(schritte, 0, 0, frequency=4000)
    def drehung_rechts(self, schritte):
        self.move_together(schritte, 1, 1, frequency=4000)


# ---------------- EINSTELLUNGEN ----------------

ABSTAND_STOP_CM = 30
SCHRITTE_LINKSDREHUNG_90_GRAD = 32080

US_CHANNELS = [5, 6, 7, 8]

MUX_S0_PIN = 2
MUX_S1_PIN = 3
MUX_S2_PIN = 4
MUX_S3_PIN = 5
US_TRIGGER_PIN = 6
MUX_SIGNAL_PIN = 28


# ---------------- OBJEKTE ----------------

motors = DualStepperPWM(left_dir_pin=10,left_step_pin=11,left_enable_pin=12,right_dir_pin=13,right_step_pin=8,right_enable_pin=9,frequency=4500,enable_active_value=1)

ultraschall_vorne = MultiplexerUltraschall(s0_pin=MUX_S0_PIN,s1_pin=MUX_S1_PIN,s2_pin=MUX_S2_PIN,s3_pin=MUX_S3_PIN,trigger_pin=US_TRIGGER_PIN,signal_pin=MUX_SIGNAL_PIN,us_channels=US_CHANNELS)


# ---------------- HAUPTPROGRAMM ----------------

print("Fahre geradeaus bis Hindernis erkannt wird")

motors.geradeaus_start()

while True:
    distance, channel = ultraschall_vorne.nearest_distance()

    if distance is None:
        print("Kein Ultraschall-Echo")
    else:
        print("Naechster Abstand:", round(distance, 1), "cm auf C" + str(channel))

        if distance <= ABSTAND_STOP_CM:
            print("Hindernis erkannt - stoppe")
            motors.stop()
            break

    sleep(0.05)

sleep(1)

print("Linksdrehung")
motors.drehung_links(SCHRITTE_LINKSDREHUNG_90_GRAD)
sleep(2)