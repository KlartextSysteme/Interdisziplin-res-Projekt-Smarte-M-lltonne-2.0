"""Tiny Pico TCP simulator for demo rehearsals.

Run after the backend and tcp_bridge are up:
    python bridge/pico_tcp_simulator.py --host 127.0.0.1 --port 50002

It accepts the same line protocol as the Pico firmware and reports ACK/status
frames back to the bridge. This is only a fallback/testing helper; the real
Pico should still connect to tcp_bridge.py for the hardware demo.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging


LOGGER = logging.getLogger("smart_bin.pico_tcp_simulator")


class PicoTcpSimulator:
    def __init__(self, *, host: str, port: int, arrival_delay_s: float) -> None:
        self.host = host
        self.port = port
        self.arrival_delay_s = arrival_delay_s
        self.state = "STANDBY"

    async def run(self) -> None:
        while True:
            try:
                await self._run_once()
            except (ConnectionError, OSError, asyncio.IncompleteReadError) as exc:
                LOGGER.warning("connection lost: %s", exc)
            await asyncio.sleep(1.0)

    async def _run_once(self) -> None:
        LOGGER.info("connecting to bridge at %s:%s", self.host, self.port)
        reader, writer = await asyncio.open_connection(self.host, self.port)
        LOGGER.info("connected")

        heartbeat = asyncio.create_task(self._heartbeat(writer))
        try:
            await self._send(writer, "Pico ist bereit")
            while True:
                raw = await reader.readline()
                if not raw:
                    raise ConnectionError("bridge closed socket")
                cmd = raw.decode(errors="ignore").strip()
                if cmd:
                    await self._handle_command(cmd, writer)
        finally:
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    async def _heartbeat(self, writer: asyncio.StreamWriter) -> None:
        while True:
            await asyncio.sleep(2.0)
            await self._send(writer, f"STATUS:{self.state}")

    async def _handle_command(self, cmd: str, writer: asyncio.StreamWriter) -> None:
        LOGGER.info("bridge: %s", cmd)

        if cmd == "CMD_GOTO_STREET":
            await self._send(writer, "ACK CMD_GOTO_STREET")
            self.state = "LINE_FOLLOWING"
            await self._send(writer, "STATUS:LINE_FOLLOWING")
            await asyncio.sleep(self.arrival_delay_s)
            self.state = "WAIT_AT_STREET"
            await self._send(writer, "ARRIVED: STREET")
            return

        if cmd == "CMD_RETURN_HOME":
            await self._send(writer, "ACK CMD_RETURN_HOME")
            self.state = "LINE_FOLLOWING"
            await self._send(writer, "STATUS:LINE_FOLLOWING")
            await asyncio.sleep(self.arrival_delay_s)
            self.state = "STANDBY"
            await self._send(writer, "ARRIVED: HOME")
            return

        if cmd == "CMD_STOP":
            await self._send(writer, "ACK CMD_STOP")
            self.state = "USER_PAUSED"
            await self._send(writer, "STATUS:USER_PAUSED")
            return

        if cmd.startswith("ACK_RECEIVED"):
            LOGGER.info("bridge confirmed pico ack: %s", cmd)
            return

        LOGGER.warning("unknown command: %s", cmd)

    async def _send(self, writer: asyncio.StreamWriter, line: str) -> None:
        LOGGER.info("pico: %s", line)
        writer.write((line + "\n").encode())
        await writer.drain()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate Pico TCP protocol.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50002)
    parser.add_argument("--arrival-delay", type=float, default=3.0)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(message)s",
    )
    asyncio.run(
        PicoTcpSimulator(
            host=args.host,
            port=args.port,
            arrival_delay_s=args.arrival_delay,
        ).run()
    )


if __name__ == "__main__":
    main()
