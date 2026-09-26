from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_participant
from app.db.models import Event
from app.db.session import get_db
from app.leaderboard import calculate_leaderboard, serialize_leaderboard

router = APIRouter(tags=["leaderboard"])


@router.get("/events/{event_id}/leaderboard")
def participant_leaderboard(
    event_id: str,
    current=Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    session, _, _ = current
    if session.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event session mismatch")
    if db.get(Event, event_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return {"leaderboard": serialize_leaderboard(calculate_leaderboard(db, event_id))}
