"""Pico W network + bridge LED test for the SmartBinDemo WLAN.

Run on a MicroPython Pico W with:
    python -m mpremote connect auto run network_led_test.py

Visual states:
- slow blink: trying to join Wi-Fi
- 10 fast flashes: Wi-Fi connected
- very fast flicker: TCP bridge connected successfully
- three short flashes + pause: bridge connection failed, retrying
"""

import socket
import time

import network
from machine import Pin


WLAN_SSID = "SmartBinDemo"
WLAN_PASSWORD = "SmartBin2026!"
BRIDGE_HOST = "192.168.50.10"
BRIDGE_PORT = 50002


def make_led():
    try:
        return Pin("LED", Pin.OUT)
    except Exception:
        return Pin(25, Pin.OUT)


led = make_led()


def led_on():
    led.value(1)


def led_off():
    led.value(0)


def blink(times, on_ms=80, off_ms=80):
    for _ in range(times):
        led_on()
        time.sleep_ms(on_ms)
        led_off()
        time.sleep_ms(off_ms)


def bridge_error_pattern():
    blink(3, 90, 90)
    time.sleep_ms(700)


def fast_flicker(duration_ms=5000):
    end = time.ticks_add(time.ticks_ms(), duration_ms)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        led_on()
        time.sleep_ms(25)
        led_off()
        time.sleep_ms(25)


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        wlan.config(pm=0xA11140)
    except Exception:
        pass

    if not wlan.isconnected():
        print("Connecting Wi-Fi:", WLAN_SSID)
        wlan.connect(WLAN_SSID, WLAN_PASSWORD)

    start = time.ticks_ms()
    while not wlan.isconnected():
        led_on()
        time.sleep_ms(120)
        led_off()
        time.sleep_ms(880)
        if time.ticks_diff(time.ticks_ms(), start) > 20000:
            print("Wi-Fi timeout, retrying")
            try:
                wlan.disconnect()
            except Exception:
                pass
            time.sleep_ms(500)
            wlan.connect(WLAN_SSID, WLAN_PASSWORD)
            start = time.ticks_ms()

    print("Wi-Fi connected:", wlan.ifconfig())
    blink(10, 45, 45)
    return wlan


def connect_bridge_once():
    print("Connecting bridge:", BRIDGE_HOST, BRIDGE_PORT)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(5)
        sock.connect((BRIDGE_HOST, BRIDGE_PORT))
        sock.send(b"Pico ist bereit\n")
        sock.send(b"STATUS:STANDBY\n")
        print("Bridge connected. LED party.")
        fast_flicker(8000)

        while True:
            sock.send(b"STATUS:STANDBY\n")
            fast_flicker(1000)
            time.sleep_ms(1000)
    finally:
        try:
            sock.close()
        except Exception:
            pass


def main():
    blink(2, 180, 180)
    connect_wifi()
    while True:
        try:
            connect_bridge_once()
        except Exception as exc:
            print("Bridge failed:", exc)
            bridge_error_pattern()


main()
