from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.bin import Bin
from models.event import SecurityEvent
from routers.commands import enqueue

router = APIRouter()


class TamperEvent(BaseModel):
    bin_id: int
    event_type: str   # tamper | theft_attempt | unauthorized_open
    timestamp: datetime | None = None


@router.get("/events")
def get_open_events(db: Session = Depends(get_db)):
    return db.query(SecurityEvent).filter(SecurityEvent.resolved == False).all()


@router.post("/events")
def create_event(payload: TamperEvent, db: Session = Depends(get_db)):
    event = SecurityEvent(
        bin_id=payload.bin_id,
        event_type=payload.event_type,
        timestamp=payload.timestamp or datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    # TODO: push alert via WebSocket connection manager
    return event


@router.post("/{bin_id}/lock")
def lock_bin(bin_id: int, x_admin_token: str = Header(default=""), db: Session = Depends(get_db)):
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bin not found")
    b.locked = True
    b.status = "locked"
    db.commit()
    cmd = enqueue(db, bin_id, "lock")
    return {"bin_id": bin_id, "locked": True, "command_id": cmd.id}


@router.post("/{bin_id}/unlock")
def unlock_bin(bin_id: int, x_admin_token: str = Header(default=""), db: Session = Depends(get_db)):
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bin not found")
    b.locked = False
    b.status = "idle"
    db.commit()
    cmd = enqueue(db, bin_id, "unlock")
    return {"bin_id": bin_id, "locked": False, "command_id": cmd.id}


@router.post("/{bin_id}/resolve")
def resolve_events(bin_id: int, db: Session = Depends(get_db)):
    db.query(SecurityEvent).filter(
        SecurityEvent.bin_id == bin_id, SecurityEvent.resolved == False
    ).update({"resolved": True})
    db.commit()
    return {"bin_id": bin_id, "resolved": True}


@router.post("/events/{event_id}/resolve")
def resolve_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.resolved = True
    db.commit()
    return {"event_id": event_id, "resolved": True}
