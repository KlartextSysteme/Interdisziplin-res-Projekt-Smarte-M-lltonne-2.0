"""
Simulates fill-level drift for all bins in the DB.

Each bin slowly fills up (0–2 %/tick, 10s default). The tick rate + fill
increment scale with the global /sim/speed multiplier so demos can speed up.

Run: python mock_bins.py
"""
import asyncio
import random
import httpx

BASE_URL = "http://localhost:8000"
TICK_S = 10.0                   # base interval between fill updates
FILL_PER_TICK = (0.0, 2.0)      # uniform increment per tick at 1×
MIN_TICK_S = 0.5                # floor for tick interval at high speedups
INCREMENT_SPEED_CAP = 5.0       # increment scales sublinearly so the truck can keep up


async def get_sim_state(client: httpx.AsyncClient) -> tuple[float, bool]:
    """Returns (speed, paused). Defaults to (1.0, False) on error."""
    try:
        r = await client.get(f"{BASE_URL}/sim/speed", timeout=2.0)
        data = r.json()
        return float(data.get("speed", 1.0)), bool(data.get("paused", False))
    except Exception:
        return 1.0, False


async def fetch_bins(client: httpx.AsyncClient) -> list[dict]:
    try:
        r = await client.get(f"{BASE_URL}/bins", timeout=5.0)
        return r.json()
    except Exception as e:
        print(f"[mock_bins] fetch error: {e}")
        return []


async def simulate():
    async with httpx.AsyncClient(timeout=5.0) as client:
        # In-memory tracker so we can accumulate fractional fill-drift
        local_fill: dict[int, float] = {}

        while True:
            speed, paused = await get_sim_state(client)
            if paused:
                # Pausiert — keine Füllstand-Drift, nur kurz pollen
                await asyncio.sleep(0.5)
                continue
            bins = await fetch_bins(client)
            if not bins:
                await asyncio.sleep(2)
                continue

            for b in bins:
                bid = b["id"]
                # Resync to DB when truck just emptied (drop detected)
                if bid not in local_fill or b["fill_level"] < local_fill[bid] - 5:
                    local_fill[bid] = float(b["fill_level"])

                # Increment scaled by speed but capped — sonst füllen sich Tonnen
                # schneller, als der Truck sie leeren kann.
                increment = random.uniform(*FILL_PER_TICK) * min(speed, INCREMENT_SPEED_CAP)
                local_fill[bid] = min(100.0, local_fill[bid] + increment)

                try:
                    await client.post(
                        f"{BASE_URL}/bins/{bid}/update",
                        json={"fill_level": int(local_fill[bid])},
                    )
                except Exception as e:
                    print(f"[mock_bins] bin {bid} error: {e}")

            # Sleep interval shrinks with speed, clamped to MIN_TICK_S
            await asyncio.sleep(max(MIN_TICK_S, TICK_S / speed))


if __name__ == "__main__":
    asyncio.run(simulate())
