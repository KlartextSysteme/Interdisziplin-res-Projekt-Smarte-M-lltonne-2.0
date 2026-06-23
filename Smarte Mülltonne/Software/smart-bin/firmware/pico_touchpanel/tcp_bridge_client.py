import errno
import socket
import time

import network

try:
    import uselect as select
except ImportError:
    import select


class TcpBridgeClient:
    WOULD_BLOCK = (
        getattr(errno, "EAGAIN", 11),
        getattr(errno, "EWOULDBLOCK", 11),
        11,
        35,
        10035,
    )

    def __init__(
        self,
        ssid,
        password,
        bridge_host,
        bridge_port,
        command_handler,
        status_provider=None,
        status_interval_ms=2000,
    ):
        self.ssid = ssid
        self.password = password
        self.bridge_host = bridge_host
        self.bridge_port = bridge_port
        self.command_handler = command_handler
        self.status_provider = status_provider
        self.status_interval_ms = status_interval_ms

        self.wlan = network.WLAN(network.STA_IF)
        self.sock = None
        self.rx = b""
        self.tx_queue = []
        self.tx_buf = b""
        self.tx_pos = 0

        self.last_wifi_try_ms = 0
        self.last_socket_try_ms = 0
        self.last_status_ms = 0
        self.connected = False

    def start(self):
        self.wlan.active(True)
        try:
            self.wlan.config(pm=0xA11140)
        except Exception:
            pass
        self._ensure_wifi()

    def tick(self):
        self._ensure_wifi()
        if not self.wlan.isconnected():
            return

        if self.sock is None:
            self._ensure_socket()
            return

        self._flush_tx()
        self._read_available()
        self._send_status_if_due()

    def send_line(self, line):
        if len(self.tx_queue) < 12:
            self.tx_queue.append(str(line))
        self._flush_tx()

    def close(self):
        self._close_socket()
        try:
            self.wlan.disconnect()
        except Exception:
            pass

    def _ensure_wifi(self):
        if self.wlan.isconnected():
            return

        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_wifi_try_ms) < 5000:
            return

        self.last_wifi_try_ms = now
        try:
            self.wlan.connect(self.ssid, self.password)
        except Exception as exc:
            print("WLAN connect failed:", exc)

    def _ensure_socket(self):
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_socket_try_ms) < 3000:
            return

        self.last_socket_try_ms = now
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(2)
            s.connect((self.bridge_host, self.bridge_port))
            s.setblocking(False)
        except Exception as exc:
            print("TCP bridge connect failed:", exc)
            try:
                s.close()
            except Exception:
                pass
            return

        self.sock = s
        self.connected = True
        self.rx = b""
        self.tx_buf = b""
        self.tx_pos = 0
        print("TCP bridge connected:", self.bridge_host, self.bridge_port)
        self.send_line("Pico ist bereit")

    def _close_socket(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None
        self.connected = False
        self.rx = b""
        self.tx_buf = b""
        self.tx_pos = 0

    def _read_available(self):
        while self.sock is not None:
            try:
                chunk = self.sock.recv(128)
            except OSError as exc:
                code = exc.args[0] if exc.args else None
                if code in self.WOULD_BLOCK:
                    return
                print("TCP recv failed:", exc)
                self._close_socket()
                return

            if not chunk:
                print("TCP bridge disconnected")
                self._close_socket()
                return

            self.rx += chunk
            if len(self.rx) > 512:
                self.rx = self.rx[-256:]

            while b"\n" in self.rx:
                line, self.rx = self.rx.split(b"\n", 1)
                try:
                    text = line.decode().strip()
                except Exception:
                    text = ""
                if text:
                    self.command_handler(text)

    def _flush_tx(self):
        if self.sock is None:
            return

        while True:
            if not self.tx_buf:
                if not self.tx_queue:
                    return
                self.tx_buf = (self.tx_queue.pop(0) + "\n").encode()
                self.tx_pos = 0

            try:
                sent = self.sock.send(self.tx_buf[self.tx_pos :])
            except OSError as exc:
                code = exc.args[0] if exc.args else None
                if code in self.WOULD_BLOCK:
                    return
                print("TCP send failed:", exc)
                self._close_socket()
                return

            if sent is None or sent == 0:
                return

            self.tx_pos += sent
            if self.tx_pos < len(self.tx_buf):
                return

            self.tx_buf = b""
            self.tx_pos = 0

    def _send_status_if_due(self):
        if self.status_provider is None:
            return

        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_status_ms) < self.status_interval_ms:
            return

        self.last_status_ms = now
        status = self.status_provider()
        if status:
            self.send_line("STATUS:" + str(status))
