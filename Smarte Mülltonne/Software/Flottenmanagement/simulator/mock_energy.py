"""
Simulates solar output (sine curve) and battery drain/charge for bins 1–6.
Run: python mock_energy.py
"""
import asyncio
import math
import random
import time
import httpx

BASE_URL = "http://localhost:8000"
PEAK_SOLAR_W = 15.0    # max watt output at noon
CHARGE_RATE = 0.5      # battery % gained per tick while charging
DRAIN_RATE = 0.1       # battery % lost per tick while idle


async def simulate():
    async with httpx.AsyncClient() as client:
        battery = {i: 60 + random.randint(0, 35) for i in range(1, 7)}

        while True:
            # Use real wall-clock hour so charts match actual time
            hour = (time.localtime().tm_hour + time.localtime().tm_min / 60)
            # sin curve: 0 W before 6h, peak at 12h, 0 W after 18h
            solar_raw = math.sin((hour - 6) * math.pi / 12) * PEAK_SOLAR_W
            solar = max(0.0, solar_raw + random.uniform(-1, 1))
            is_charging = solar > 2.0

            for bin_id in range(1, 7):
                if is_charging:
                    battery[bin_id] = min(100, battery[bin_id] + CHARGE_RATE)
                else:
                    battery[bin_id] = max(0, battery[bin_id] - DRAIN_RATE)

                try:
                    await client.post(
                        f"{BASE_URL}/bins/{bin_id}/update",
                        json={
                            "solar_output_w": round(solar + random.uniform(-0.5, 0.5), 2),
                            "is_charging": is_charging,
                            "battery": int(battery[bin_id]),
                        },
                    )
                except Exception as e:
                    print(f"[mock_energy] Bin {bin_id} error: {e}")

            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(simulate())
