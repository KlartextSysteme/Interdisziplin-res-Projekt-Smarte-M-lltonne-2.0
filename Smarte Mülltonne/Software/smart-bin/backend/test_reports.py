from fastapi.testclient import TestClient

from main import app
from routers.ws import _build_live_payload

client = TestClient(app)


def test_report_event_flows_into_events_and_ws():
    r = client.post("/security/events", json={"bin_id": 22, "event_type": "hygiene_report"})
    assert r.status_code == 200
    created = r.json()
    assert created["event_type"] == "hygiene_report"
    event_id = created["id"]

    open_events = client.get("/security/events").json()
    assert any(e["id"] == event_id for e in open_events)

    payload = _build_live_payload()
    assert any(a["id"] == event_id and a["event_type"] == "hygiene_report" for a in payload["alerts"])

    # Cleanup: unser Test-Event wieder aufloesen (id-basiert, robust gegen Altdaten)
    client.post("/security/22/resolve")
    assert all(e["id"] != event_id for e in client.get("/security/events").json())
