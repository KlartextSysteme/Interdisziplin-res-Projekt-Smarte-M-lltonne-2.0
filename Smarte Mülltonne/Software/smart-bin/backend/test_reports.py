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


def test_resolve_single_event_leaves_others():
    a = client.post("/security/events", json={"bin_id": 22, "event_type": "hygiene_report"}).json()
    b = client.post("/security/events", json={"bin_id": 22, "event_type": "damage_report"}).json()

    r = client.post(f"/security/events/{a['id']}/resolve")
    assert r.status_code == 200
    assert r.json() == {"event_id": a["id"], "resolved": True}

    open_ids = [e["id"] for e in client.get("/security/events").json()]
    assert a["id"] not in open_ids          # quittiertes Event weg
    assert b["id"] in open_ids              # anderes Event derselben Tonne bleibt

    client.post(f"/security/events/{b['id']}/resolve")  # cleanup


def test_resolve_unknown_event_returns_404():
    r = client.post("/security/events/99999999/resolve")
    assert r.status_code == 404


def test_alert_timestamp_is_utc_z():
    created = client.post("/security/events", json={"bin_id": 22, "event_type": "hygiene_report"}).json()
    payload = _build_live_payload()
    alert = next(a for a in payload["alerts"] if a["id"] == created["id"])
    assert alert["timestamp"].endswith("Z")
    assert "T" in alert["timestamp"]          # ISO-8601, kein Space-Separator
    client.post(f"/security/events/{created['id']}/resolve")  # cleanup
