"""Pico W command/ACK LED test for the TCP bridge demo.

This is for a spare test Pico. It simulates the smart bin protocol:
- connects to SmartBinDemo
- connects to the laptop TCP bridge
- sends handshake/status
- receives CMD_* lines
- sends ACK lines back
- blinks the onboard LED with different patterns
"""

import socket
import time

import network
from machine import Pin


WLAN_SSID = "SmartBinDemo"
WLAN_PASSWORD = "SmartBin2026!"
BRIDGE_HOST = "192.168.50.10"
BRIDGE_PORT = 50002

CMD_GOTO_STREET = "CMD_GOTO_STREET"
CMD_RETURN_HOME = "CMD_RETURN_HOME"
CMD_STOP = "CMD_STOP"


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


def flicker(duration_ms, on_ms=25, off_ms=25):
    end = time.ticks_add(time.ticks_ms(), duration_ms)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        led_on()
        time.sleep_ms(on_ms)
        led_off()
        time.sleep_ms(off_ms)


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
        blink(1, 120, 880)
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


def send_line(sock, line):
    print("pico ->", line)
    sock.send((line + "\n").encode())


def handle_command(sock, cmd):
    print("bridge ->", cmd)

    if cmd == CMD_GOTO_STREET:
        send_line(sock, "ACK " + CMD_GOTO_STREET)
        send_line(sock, "STATUS:LINE_FOLLOWING")
        flicker(2500, 18, 18)
        send_line(sock, "ARRIVED: STREET")
        send_line(sock, "STATUS:WAIT_AT_STREET")
        blink(6, 180, 120)
        return

    if cmd == CMD_RETURN_HOME:
        send_line(sock, "ACK " + CMD_RETURN_HOME)
        send_line(sock, "STATUS:LINE_FOLLOWING")
        flicker(1800, 70, 35)
        send_line(sock, "ARRIVED: HOME")
        send_line(sock, "STATUS:STANDBY")
        blink(4, 250, 160)
        return

    if cmd == CMD_STOP:
        send_line(sock, "ACK " + CMD_STOP)
        send_line(sock, "STATUS:USER_PAUSED")
        blink(12, 35, 180)
        return

    if cmd.startswith("ACK_RECEIVED"):
        blink(2, 45, 45)
        return

    print("Ignored:", cmd)


def run_bridge_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    print("Connecting bridge:", BRIDGE_HOST, BRIDGE_PORT)
    sock.connect((BRIDGE_HOST, BRIDGE_PORT))
    sock.settimeout(0.25)

    send_line(sock, "Pico ist bereit")
    send_line(sock, "STATUS:STANDBY")
    print("Bridge connected. Waiting for CMD_*.")
    flicker(1200, 25, 25)

    rx = b""
    last_status_ms = time.ticks_ms()

    try:
        while True:
            try:
                data = sock.recv(128)
                if not data:
                    raise OSError("bridge closed")
                rx += data
            except OSError:
                data = None

            while b"\n" in rx:
                raw, rx = rx.split(b"\n", 1)
                try:
                    line = raw.decode().strip()
                except Exception:
                    line = ""
                if line:
                    handle_command(sock, line)

            now = time.ticks_ms()
            if time.ticks_diff(now, last_status_ms) > 3000:
                send_line(sock, "STATUS:STANDBY")
                last_status_ms = now
                blink(1, 25, 25)

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
            run_bridge_loop()
        except Exception as exc:
            print("Bridge loop failed:", exc)
            blink(3, 90, 180)
            time.sleep_ms(800)


main()
