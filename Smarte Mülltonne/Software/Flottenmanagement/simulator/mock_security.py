"""
Randomly fires tamper events to test the security pipeline.
Run: python mock_security.py
"""
import asyncio
import random
import httpx

BASE_URL = "http://localhost:8000"
EVENT_TYPES = ["tamper", "theft_attempt", "unauthorized_open"]
# Average one event every ~5 minutes (300 s / 10 s ticks = 30 ticks per event)
EVENT_PROBABILITY = 1 / 30


async def simulate():
    async with httpx.AsyncClient() as client:
        while True:
            if random.random() < EVENT_PROBABILITY:
                bin_id = random.randint(1, 6)
                event_type = random.choice(EVENT_TYPES)
                try:
                    resp = await client.post(
                        f"{BASE_URL}/security/events",
                        json={"bin_id": bin_id, "event_type": event_type},
                    )
                    print(f"[mock_security] {event_type} on bin {bin_id} → {resp.status_code}")
                except Exception as e:
                    print(f"[mock_security] Error: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(simulate())
