from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_touchpanel_dispatch_updates_location_state():
    """Eine (auch am Touchpanel ausgeloeste) Fahrt muss location_state sofort
    ueberschreiben, ohne dass die Bridge location_state/target mitschickt."""
    # Losfahren zur Abholpos
    r = client.post("/bins/22/telemetry", json={"pico_state": "MANUAL_GOTO_STREET_REQUEST"})
    assert r.status_code == 200
    assert client.get("/bins/22").json()["location_state"] == "moving_to_pickup"

    # An der Abholpos
    client.post("/bins/22/telemetry", json={"pico_state": "WAIT_AT_STREET"})
    assert client.get("/bins/22").json()["location_state"] == "truck"

    # Rueckfahrt
    client.post("/bins/22/telemetry", json={"pico_state": "MANUAL_RETURN_HOME_REQUEST"})
    assert client.get("/bins/22").json()["location_state"] == "moving_home"

    # Zuhause / Leerlauf
    client.post("/bins/22/telemetry", json={"pico_state": "STANDBY"})
    assert client.get("/bins/22").json()["location_state"] == "home"


def test_explicit_location_state_wins_over_pico_state_fallback():
    """Explizites location_state/target hat weiter Vorrang vor dem Fallback."""
    client.post(
        "/bins/22/telemetry",
        json={"pico_state": "MANUAL_GOTO_STREET_REQUEST", "location_state": "home"},
    )
    assert client.get("/bins/22").json()["location_state"] == "home"
