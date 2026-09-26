from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE,
    SESSION_MAX_AGE_SECONDS,
    create_session_token,
    get_current_participant,
    normalize_email,
)
from app.blockchain.processing import (
    ProviderFactory,
    SessionFactory,
    get_reward_provider_factory,
    get_settlement_session_factory,
    normalize_wallet_address,
    process_settlements,
    serialize_settlement,
)
from app.db.models import (
    AssignmentStatus,
    AuditLog,
    Event,
    EventParticipant,
    EventState,
    Participant,
    RewardSettlement,
    SettlementStatus,
    Task,
    TaskAssignment,
)
from app.db.session import get_db
from app.settings import settings
from app.rate_limit import join_rate_limiter

router = APIRouter(prefix="/events", tags=["events"])


class JoinRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str | None = Field(default=None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def accept_camel_case_name(cls, values: object) -> object:
        if isinstance(values, dict) and "display_name" not in values and "displayName" in values:
            values = dict(values)
            values["display_name"] = values.pop("displayName")
        return values


class WalletRequest(BaseModel):
    wallet_address: str = Field(min_length=42, max_length=42)

    @model_validator(mode="before")
    @classmethod
    def accept_camel_case_wallet(cls, values: object) -> object:
        if (
            isinstance(values, dict)
            and "wallet_address" not in values
            and "walletAddress" in values
        ):
            values = dict(values)
            values["wallet_address"] = values.pop("walletAddress")
        return values


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


@router.get("/code/{code}")
def get_event_by_code(code: str, db: Session = Depends(get_db)) -> dict[str, object]:
    """Resolve the participant-facing event code (the event slug)."""
    return get_event(code.strip().lower(), db)


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

    normalized_email = normalize_email(payload.email)
    participant = db.query(Participant).filter_by(email=normalized_email).one_or_none()
    if participant is None:
        participant = Participant(
            email=normalized_email,
            display_name=payload.display_name.strip() if payload.display_name else None,
        )
        db.add(participant)
        db.flush()
    elif payload.display_name and not participant.display_name:
        participant.display_name = payload.display_name.strip()

    event_participant = (
        db.query(EventParticipant)
        .filter_by(event_id=event.id, participant_id=participant.id)
        .one_or_none()
    )
    if event_participant is None:
        event_participant = EventParticipant(
            event_id=event.id,
            participant_id=participant.id,
            eligible=True,
        )
        db.add(event_participant)
    elif not event_participant.eligible:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Participant is blocked")

    event_participant.checked_in_at = event_participant.checked_in_at or datetime.now(timezone.utc)
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


@router.post("/code/{code}/join")
def join_event_by_code(
    code: str,
    payload: JoinRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Join through a typed event code without exposing authentication data."""
    return join_event(code.strip().lower(), payload, request, response, db)


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
        "participant": {
            "displayName": participant.display_name,
            "walletAddress": participant.wallet_address,
        },
        "score": event_participant.score,
        "state": event.state,
    }


@router.put("/{event_id}/wallet")
def set_wallet(
    event_id: str,
    payload: WalletRequest,
    background_tasks: BackgroundTasks,
    current: tuple = Depends(get_current_participant),
    db: Session = Depends(get_db),
    session_factory: SessionFactory = Depends(get_settlement_session_factory),
    provider_factory: ProviderFactory = Depends(get_reward_provider_factory),
) -> dict[str, object]:
    session, participant, _ = current
    if session.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event session mismatch")
    try:
        wallet_address = normalize_wallet_address(payload.wallet_address)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    participant.wallet_address = wallet_address
    db.add(
        AuditLog(
            event_id=event_id,
            actor_type="PARTICIPANT",
            actor_id=participant.id,
            action="PARTICIPANT_WALLET_UPDATED",
            entity_type="PARTICIPANT",
            entity_id=participant.id,
            metadata_json={"walletAddress": wallet_address},
        )
    )
    db.commit()
    # Rewards approved before the wallet existed can now be paid.
    waiting_ids = [
        settlement_id
        for (settlement_id,) in db.query(RewardSettlement.id)
        .filter_by(participant_id=participant.id, status=SettlementStatus.PENDING.value)
        .all()
    ]
    if waiting_ids:
        background_tasks.add_task(
            process_settlements, waiting_ids, session_factory, provider_factory
        )
    return {"walletAddress": wallet_address}


@router.get("/{event_id}/rewards")
def list_my_rewards(
    event_id: str,
    current: tuple = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    session, participant, _ = current
    if session.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event session mismatch")
    rows = (
        db.query(RewardSettlement, Task)
        .outerjoin(TaskAssignment, RewardSettlement.assignment_id == TaskAssignment.id)
        .outerjoin(Task, TaskAssignment.task_id == Task.id)
        .filter(
            RewardSettlement.event_id == event_id,
            RewardSettlement.participant_id == participant.id,
        )
        .order_by(RewardSettlement.created_at.desc())
        .all()
    )
    return {
        "rewards": [
            serialize_settlement(settlement, participant, task) for settlement, task in rows
        ]
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
