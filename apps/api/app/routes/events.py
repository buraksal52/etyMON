from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE,
    SESSION_MAX_AGE_SECONDS,
    create_session_token,
    get_current_participant,
    normalize_email,
)
from app.db.models import (
    AssignmentStatus,
    Event,
    EventParticipant,
    EventState,
    Participant,
    TaskAssignment,
)
from app.db.session import get_db
from app.settings import settings
from app.rate_limit import join_rate_limiter

router = APIRouter(prefix="/events", tags=["events"])


class JoinRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


@router.get("/{slug}")
def get_event(slug: str, db: Session = Depends(get_db)) -> dict[str, object]:
    event = db.query(Event).filter_by(slug=slug).one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return {
        "id": event.id,
        "name": event.name,
        "slug": event.slug,
        "description": event.description,
        "state": event.state,
        "timezone": event.timezone,
        "taskDeadlineAt": event.task_deadline_at,
    }


@router.post("/{slug}/join")
def join_event(
    slug: str,
    payload: JoinRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    client_host = request.client.host if request.client else "unknown"
    if not join_rate_limiter.allow(f"{client_host}:{normalize_email(payload.email)}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many join attempts",
            headers={"Retry-After": "60"},
        )
    event = db.query(Event).filter_by(slug=slug).one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.state != EventState.WAITING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Event is not accepting entries"
        )

    participant = (
        db.query(Participant).filter_by(email=normalize_email(payload.email)).one_or_none()
    )
    event_participant = None
    if participant is not None:
        event_participant = (
            db.query(EventParticipant)
            .filter_by(event_id=event.id, participant_id=participant.id, eligible=True)
            .one_or_none()
        )
    if participant is None or event_participant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Participant is not eligible"
        )

    event_participant.checked_in_at = event_participant.checked_in_at or datetime.utcnow()
    db.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(event.id, participant.id),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="none" if settings.app_env == "production" else "lax",
    )
    return {
        "eventId": event.id,
        "participant": {"displayName": participant.display_name},
        "state": event.state,
    }


@router.get("/{event_id}/status")
def get_event_status(
    event_id: str,
    current: tuple = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    session, _, _ = current
    if session.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event session mismatch")
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return {"eventId": event.id, "state": event.state, "taskDeadlineAt": event.task_deadline_at}


@router.get("/{event_id}/me")
def get_me(
    event_id: str,
    current: tuple = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    session, participant, event_participant = current
    if session.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event session mismatch")
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return {
        "eventId": event.id,
        "participant": {"displayName": participant.display_name},
        "score": event_participant.score,
        "state": event.state,
    }


@router.get("/{event_id}/progress")
def get_progress(
    event_id: str,
    current: tuple = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    session, participant, event_participant = current
    if session.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event session mismatch")
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    assignments = (
        db.query(TaskAssignment).filter_by(event_id=event_id, participant_id=participant.id).all()
    )
    return {
        "eventId": event.id,
        "participant": {"displayName": participant.display_name},
        "score": event_participant.score,
        "state": event.state,
        "counts": {
            "assigned": sum(a.status == AssignmentStatus.ASSIGNED.value for a in assignments),
            "submitted": sum(a.status == AssignmentStatus.SUBMITTED.value for a in assignments),
            "approved": sum(a.status == AssignmentStatus.APPROVED.value for a in assignments),
            "rejected": sum(a.status == AssignmentStatus.REJECTED.value for a in assignments),
            "total": len(assignments),
        },
    }
