from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.bin import Bin

router = APIRouter()


@router.get("")
def get_energy(db: Session = Depends(get_db)):
    bins = db.query(Bin).all()
    return [
        {
            "bin_id": b.id,
            "name": b.name,
            "battery": b.battery,
        }
        for b in bins
    ]


@router.get("/{bin_id}/history")
def get_energy_history(bin_id: int, db: Session = Depends(get_db)):
    # TODO: store time-series readings in separate table for 24h chart
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bin not found")
    return {"bin_id": bin_id, "history": [], "message": "Time-series not yet implemented"}


@router.post("/{bin_id}/dock")
def dock_bin(bin_id: int, db: Session = Depends(get_db)):
    # TODO: called by RPi when bin reaches charging station
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bin not found")
    b.is_charging = True
    db.commit()
    return {"bin_id": bin_id, "is_charging": True}
