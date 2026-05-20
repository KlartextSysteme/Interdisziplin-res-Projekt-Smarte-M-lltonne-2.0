"""TCP bridge for the legacy Pico firmware.

The old Pico robot already has a robust non-blocking TCP client and a local
state machine. This bridge preserves that firmware contract and translates it
to the FastAPI command queue used by the fleet dashboard.

Run:
    python bridge/tcp_bridge.py --bin-id 1 --backend http://localhost:8000

Pico side:
    SERVER_IP   = <laptop-ip>
    SERVER_PORT = 50002
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import signal
from dataclasses import dataclass, field
from typing import Any

import httpx


LOGGER = logging.getLogger("smart_bin.tcp_bridge")

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 50002
DEFAULT_BACKEND = "http://localhost:8000"
DEFAULT_POLL_INTERVAL_S = 1.0

BACKEND_TO_PICO_COMMAND = {
    "goto_street": "CMD_GOTO_STREET",
    "go_to_street": "CMD_GOTO_STREET",
    "start": "CMD_GOTO_STREET",
    "return_home": "CMD_RETURN_HOME",
    "go_home": "CMD_RETURN_HOME",
    "stop": "CMD_STOP",
    "pause": "CMD_STOP",
    "lock": "CMD_STOP",
}

@dataclass
class BridgeState:
    bin_id: int
    last_pico_state: str | None = None
    connected: bool = False
    inflight_by_pico_cmd: dict[str, int] = field(default_factory=dict)
    sent_command_ids: set[int] = field(default_factory=set)


class PicoBridge:
    def __init__(self, *, backend_url: str, bin_id: int, poll_interval_s: float):
        self.backend_url = backend_url.rstrip("/")
        self.state = BridgeState(bin_id=bin_id)
        self.poll_interval_s = poll_interval_s
        self.client = httpx.AsyncClient(timeout=5.0)

    async def close(self) -> None:
        await self.client.aclose()

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername")
        LOGGER.info("Pico connected from %s", peer)
        self.state.connected = True
        self.state.inflight_by_pico_cmd.clear()
        self.state.sent_command_ids.clear()

        poll_task = asyncio.create_task(self._poll_commands(writer))
        try:
            while not reader.at_eof():
                raw = await reader.readline()
                if not raw:
                    break
                line = raw.decode(errors="ignore").strip()
                if line:
                    await self._handle_pico_line(line, writer)
        finally:
            poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await poll_task
            self.state.connected = False
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            LOGGER.info("Pico disconnected from %s", peer)

    async def _poll_commands(self, writer: asyncio.StreamWriter) -> None:
        while True:
            try:
                command = await self._get_pending_command()
                if command:
                    await self._send_backend_command_to_pico(command, writer)
            except Exception:
                LOGGER.exception("command polling failed")
            await asyncio.sleep(self.poll_interval_s)

    async def _get_pending_command(self) -> dict[str, Any] | None:
        resp = await self.client.get(
            f"{self.backend_url}/bins/{self.state.bin_id}/pending-command",
        )
        resp.raise_for_status()
        if not resp.content or resp.text == "null":
            return None
        return resp.json()

    async def _send_backend_command_to_pico(
        self,
        command: dict[str, Any],
        writer: asyncio.StreamWriter,
    ) -> None:
        command_id = int(command["id"])
        if command_id in self.state.sent_command_ids:
            return

        action = str(command.get("action", "")).lower()
        pico_cmd = BACKEND_TO_PICO_COMMAND.get(action)

        if pico_cmd is None:
            LOGGER.warning("unsupported command %s, acking as failed", action)
            await self._ack_backend(command_id, success=False, error=f"unsupported action: {action}")
            self.state.sent_command_ids.add(command_id)
            return

        self.state.inflight_by_pico_cmd[pico_cmd] = command_id
        self.state.sent_command_ids.add(command_id)
        LOGGER.info("backend command #%s %s -> pico %s", command_id, action, pico_cmd)
        writer.write((pico_cmd + "\n").encode())
        await writer.drain()

    async def _handle_pico_line(self, line: str, writer: asyncio.StreamWriter) -> None:
        LOGGER.info("pico: %s", line)

        if line == "Pico ist bereit":
            await self._post_telemetry("STANDBY")
            return

        if line.startswith("STATUS:"):
            state = line.split(":", 1)[1].strip()
            self.state.last_pico_state = state
            await self._post_telemetry(state)
            return

        if line.startswith("ARRIVED:"):
            place = line.split(":", 1)[1].strip()
            state = "WAIT_AT_STREET" if place == "STREET" else "STANDBY"
            self.state.last_pico_state = state
            await self._post_telemetry(state, target_destination=place)
            return

        if line.startswith("ACK "):
            pico_cmd = line.split(" ", 1)[1].strip()
            command_id = self.state.inflight_by_pico_cmd.pop(pico_cmd, None)

            if command_id is not None:
                await self._ack_backend(command_id, success=True, pico_state=self.state.last_pico_state)
                LOGGER.info("acked backend command #%s for %s", command_id, pico_cmd)
            else:
                LOGGER.warning("pico ack without known backend command: %s", pico_cmd)

            writer.write((f"ACK_RECEIVED {pico_cmd}\n").encode())
            await writer.drain()
            return

        LOGGER.debug("ignored pico line: %s", line)

    async def _post_telemetry(
        self,
        pico_state: str,
        *,
        target_destination: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {"pico_state": pico_state}
        if target_destination:
            payload["target_destination"] = target_destination

        resp = await self.client.post(
            f"{self.backend_url}/bins/{self.state.bin_id}/telemetry",
            json=payload,
        )
        resp.raise_for_status()

    async def _ack_backend(
        self,
        command_id: int,
        *,
        success: bool,
        error: str | None = None,
        pico_state: str | None = None,
    ) -> None:
        payload = {
            "command_id": command_id,
            "success": success,
            "error": error,
            "pico_state": pico_state,
        }
        resp = await self.client.post(
            f"{self.backend_url}/bins/{self.state.bin_id}/ack",
            json=payload,
        )
        resp.raise_for_status()


async def run_server(args: argparse.Namespace) -> None:
    bridge = PicoBridge(
        backend_url=args.backend,
        bin_id=args.bin_id,
        poll_interval_s=args.poll_interval,
    )

    server = await asyncio.start_server(bridge.handle_client, args.host, args.port)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    LOGGER.info("TCP bridge listening on %s; backend=%s bin_id=%s", addrs, args.backend, args.bin_id)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    try:
        async with server:
            await stop_event.wait()
    finally:
        server.close()
        await server.wait_closed()
        await bridge.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bridge legacy Pico TCP protocol to FastAPI.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--bin-id", type=int, default=1)
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL_S)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(message)s",
    )
    try:
        asyncio.run(run_server(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
