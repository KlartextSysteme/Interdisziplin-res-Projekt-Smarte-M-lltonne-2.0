from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.bin import Bin
from models.command import Command

router = APIRouter()


class CommandIn(BaseModel):
    action: str                  # lock | unlock | empty | custom
    params: dict | None = None


class AckIn(BaseModel):
    command_id: int
    success: bool = True
    error: str | None = None
    pico_state: str | None = None


def enqueue(db: Session, bin_id: int, action: str, params: dict | None = None) -> Command:
    """Utility for other routers to queue a command."""
    cmd = Command(bin_id=bin_id, action=action, params=params)
    db.add(cmd)
    db.commit()
    db.refresh(cmd)
    return cmd


@router.post("/{bin_id}/command")
def create_command(bin_id: int, payload: CommandIn, db: Session = Depends(get_db)):
    if not db.query(Bin).filter(Bin.id == bin_id).first():
        raise HTTPException(status_code=404, detail="Bin not found")
    return enqueue(db, bin_id, payload.action, payload.params)


@router.get("/{bin_id}/pending-command")
def get_pending(bin_id: int, db: Session = Depends(get_db)):
    """Called by the bin's RPi every ~2s. Returns oldest unacked command or null."""
    cmd = (
        db.query(Command)
        .filter(Command.bin_id == bin_id, Command.ack_at.is_(None))
        .order_by(Command.created_at.asc())
        .first()
    )
    if not cmd:
        return None
    return {
        "id": cmd.id,
        "bin_id": cmd.bin_id,
        "action": cmd.action,
        "params": cmd.params,
        "created_at": cmd.created_at.isoformat(),
    }


@router.post("/{bin_id}/ack")
def ack_command(bin_id: int, payload: AckIn, db: Session = Depends(get_db)):
    cmd = db.query(Command).filter(Command.id == payload.command_id, Command.bin_id == bin_id).first()
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    cmd.ack_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "command_id": cmd.id}


@router.get("/{bin_id}/command-history")
def command_history(bin_id: int, limit: int = 20, db: Session = Depends(get_db)):
    return (
        db.query(Command)
        .filter(Command.bin_id == bin_id)
        .order_by(Command.created_at.desc())
        .limit(limit)
        .all()
    )
