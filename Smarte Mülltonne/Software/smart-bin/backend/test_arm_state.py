from fastapi.testclient import TestClient

import truck_state
from main import app

client = TestClient(app)


def test_arm_state_geofence():
    b = client.get("/bins/22").json()
    blat = b.get("current_lat") or b["lat"]
    blng = b.get("current_lng") or b["lng"]

    # Truck weit weg -> nicht entschaerft (scharf, wenn ausser Haus)
    truck_state.update(lat=blat + 0.01, lng=blng + 0.01)
    r = client.get("/bins/22/arm-state").json()
    assert r["disarmed"] is False
    assert r["distance_m"] > 10

    # Truck direkt an der Tonne -> entschaerft (Leerung)
    truck_state.update(lat=blat, lng=blng)
    r = client.get("/bins/22/arm-state").json()
    assert r["disarmed"] is True
    assert r["distance_m"] <= 10


def test_arm_state_unknown_truck_position_is_armed():
    truck_state.update(lat=None, lng=None)
    assert client.get("/bins/22/arm-state").json()["disarmed"] is False
