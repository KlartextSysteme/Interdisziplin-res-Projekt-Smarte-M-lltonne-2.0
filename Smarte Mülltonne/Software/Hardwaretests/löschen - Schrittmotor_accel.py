from machine import Pin, Timer
import time


# ---------------------------
# Motor-Klasse
# ---------------------------

class Stepper:
    def __init__(self, step_pin, dir_pin, enable_pin,
                 accel=800, enable_active_value=1):
        self.step = Pin(step_pin, Pin.OUT)
        self.dir = Pin(dir_pin, Pin.OUT)
        self.enable = Pin(enable_pin, Pin.OUT)

        self.enable_active_value = enable_active_value
        self.disable_value = 0 if enable_active_value == 1 else 1

        self.freq = 0.0
        self.target = 0.0
        self.accel = accel  # Hz/s

        self.state = 0
        self.period = 0  # us

        self.timer = Timer(-1)

        self.step.value(0)
        self.disable_motor()

    def enable_motor(self):
        self.enable.value(self.enable_active_value)

    def disable_motor(self):
        self.enable.value(self.disable_value)

    def set_direction(self, direction):
        self.dir.value(1 if direction > 0 else 0)

    def move_to_freq(self, target_freq):
        self.enable_motor()
        self.target = target_freq

    def stop(self):
        self.target = 0

    def update(self, dt):
        # Ramp up/down
        if self.freq < self.target:
            self.freq += self.accel * dt
            if self.freq > self.target:
                self.freq = self.target

        elif self.freq > self.target:
            self.freq -= self.accel * dt
            if self.freq < self.target:
                self.freq = self.target

        # Timer period update
        if self.freq > 0:
            self.period = int(1_000_000 / self.freq / 2)  # half cycle in us
        else:
            self.period = 0
            self.step.value(0)
            self.state = 0
            self.disable_motor()

    def step_tick(self, timer):
        if self.period == 0:
            self.step.value(0)
            self.state = 0
            self.timer.init(period=1000, mode=Timer.ONE_SHOT, callback=self.step_tick)
            return

        self.state ^= 1
        self.step.value(self.state)

        self.timer.init(period=self.period, mode=Timer.ONE_SHOT, callback=self.step_tick)

    def start(self):
        self.timer.init(period=1, mode=Timer.ONE_SHOT, callback=self.step_tick)


# ---------------------------
# Motoren erstellen
# ---------------------------

m1 = Stepper(
    step_pin=11,
    dir_pin=10,
    enable_pin=12,
    accel=1200,
    enable_active_value=1
)

m2 = Stepper(
    step_pin=8,
    dir_pin=13,
    enable_pin=9,
    accel=600,
    enable_active_value=1
)

m1.set_direction(1)
m2.set_direction(1)

m1.start()
m2.start()


# ---------------------------
# Bewegung setzen
# ---------------------------

m1.move_to_freq(2000)
m2.move_to_freq(1000)


# ---------------------------
# Main loop: Ramp Update
# ---------------------------

last = time.ticks_ms()

while True:
    now = time.ticks_ms()
    dt = time.ticks_diff(now, last) / 1000
    last = now

    m1.update(dt)
    m2.update(dt)

    time.sleep_ms(10)