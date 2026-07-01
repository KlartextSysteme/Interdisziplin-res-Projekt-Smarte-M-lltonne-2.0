import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from database import SessionLocal
from models.bin import Bin
from models.event import SecurityEvent
import truck_state

router = APIRouter()
LIVE_UPDATE_INTERVAL_S = 0.35

# Simple in-memory connection manager
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        msg = json.dumps(data, default=str)
        for ws in list(self.active):
            try:
                await ws.send_text(msg)
            except Exception:
                self.active.remove(ws)


manager = ConnectionManager()


def _build_live_payload() -> dict:
    db: Session = SessionLocal()
    try:
        bins = db.query(Bin).all()
        alerts = db.query(SecurityEvent).filter(SecurityEvent.resolved == False).all()
        truck = truck_state.get()
        return {
            "bins": [
                {
                    "id": b.id, "name": b.name, "address": b.address,
                    "lat": b.lat, "lng": b.lng,
                    "home_lat": b.home_lat, "home_lng": b.home_lng,
                    "pickup_lat": b.pickup_lat, "pickup_lng": b.pickup_lng,
                    "current_lat": b.current_lat, "current_lng": b.current_lng,
                    "fill_level": b.fill_level, "battery": b.battery,
                    "status": b.status, "location_state": b.location_state,
                    "movement_state": b.movement_state,
                    "locked": b.locked, "last_seen": str(b.last_seen),
                }
                for b in bins
            ],
            "alerts": [
                {"id": e.id, "bin_id": e.bin_id, "event_type": e.event_type, "timestamp": str(e.timestamp)}
                for e in alerts
            ],
            "truck": truck if truck["lat"] is not None else None,
        }
    finally:
        db.close()


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            payload = _build_live_payload()
            await websocket.send_text(json.dumps(payload, default=str))
            await asyncio.sleep(LIVE_UPDATE_INTERVAL_S)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
