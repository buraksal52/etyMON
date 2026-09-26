from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import (
    ADMIN_SESSION_COOKIE,
    SESSION_MAX_AGE_SECONDS,
    create_admin_session_token,
    get_current_organizer,
    normalize_email,
    verify_password,
)
from app.db.models import (
    Event,
    EventParticipant,
    EventState,
    Organizer,
    Submission,
    Task,
    TaskAssignment,
)
from app.db.session import get_db
from app.settings import settings

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
def admin_login(
    payload: AdminLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    organizer = db.query(Organizer).filter_by(email=normalize_email(payload.email)).one_or_none()
    if organizer is None or not verify_password(
        payload.password, organizer.password_hash_or_auth_provider_id
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid organizer credentials"
        )
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=create_admin_session_token(organizer.id),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="none" if settings.app_env == "production" else "lax",
    )
    return {"status": "authenticated"}


@router.get("/events/{event_id}")
def get_dashboard(
    event_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return {
        "event": {"id": event.id, "name": event.name, "state": event.state},
        "metrics": {
            "registeredParticipants": db.query(EventParticipant)
            .filter_by(event_id=event.id)
            .count(),
            "activeParticipants": db.query(EventParticipant)
            .filter(
                EventParticipant.event_id == event.id, EventParticipant.checked_in_at.is_not(None)
            )
            .count(),
            "totalAssignments": db.query(TaskAssignment).filter_by(event_id=event.id).count(),
            "totalSubmissions": db.query(Submission)
            .join(TaskAssignment)
            .filter(TaskAssignment.event_id == event.id)
            .count(),
            "activeTasks": db.query(Task)
            .filter(Task.event_id == event.id, Task.active.is_(True))
            .count(),
        },
    }


@router.post("/events/{event_id}/start")
def start_event(
    event_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.state != EventState.WAITING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event cannot be started from its current state",
        )
    if db.query(Task).filter(Task.event_id == event.id, Task.active.is_(True)).count() == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Event has no active tasks"
        )
    event.state = EventState.ACTIVE.value
    event.starts_at = datetime.now(timezone.utc)
    db.commit()
    return {"eventId": event.id, "state": event.state, "startsAt": event.starts_at}


@router.post("/events/{event_id}/end")
def end_event(
    event_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.state != EventState.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event cannot be ended from its current state",
        )
    event.state = EventState.ENDED.value
    event.ended_at = datetime.now(timezone.utc)
    db.commit()
    return {"eventId": event.id, "state": event.state, "endedAt": event.ended_at}
