from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_organizer, get_current_participant
from app.db.models import (
    Event,
    EventParticipant,
    AuditLog,
    Participant,
    ReimbursementStatus,
    TravelReimbursement,
)
from app.db.session import get_db
from app.file_validation import ALLOWED_UPLOAD_TYPES, validate_file_signature
from app.storage import StorageProvider, get_storage_provider

router = APIRouter(tags=["reimbursements"])


class ReimbursementReviewRequest(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    note: str = Field(default="", max_length=2000)


def parse_amount(value: str | None) -> Decimal | None:
    if not value or not value.strip():
        return None
    try:
        amount = Decimal(value.strip())
    except InvalidOperation as exc:
        raise HTTPException(status_code=422, detail="Amount must be a valid number") from exc
    if not amount.is_finite() or amount < 0:
        raise HTTPException(status_code=422, detail="Amount must be zero or greater")
    return amount.quantize(Decimal("0.01"))


def serialize_reimbursement(
    reimbursement: TravelReimbursement,
    storage: StorageProvider,
    participant: dict[str, object] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "id": reimbursement.id,
        "eventId": reimbursement.event_id,
        "participantId": reimbursement.participant_id,
        "amount": str(reimbursement.amount) if reimbursement.amount is not None else None,
        "currency": reimbursement.currency,
        "transportType": reimbursement.transport_type,
        "description": reimbursement.description,
        "status": reimbursement.status,
        "reviewNote": reimbursement.review_note,
        "submittedAt": reimbursement.submitted_at,
        "reviewedAt": reimbursement.reviewed_at,
        "paidAt": reimbursement.paid_at,
        "receiptUrl": storage.get_download_url(reimbursement.storage_key),
    }
    if participant is not None:
        result["participant"] = participant
    return result


def get_event_participant(
    event_id: str, current: tuple, db: Session
) -> tuple[Event, EventParticipant]:
    session, _, event_participant = current
    if session.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event session mismatch")
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event, event_participant


@router.post("/events/{event_id}/reimbursements")
async def submit_reimbursement(
    event_id: str,
    file: UploadFile = File(...),
    amount: str | None = Form(default=None),
    currency: str | None = Form(default=None),
    transport_type: str | None = Form(default=None, alias="transportType"),
    description: str | None = Form(default=None),
    current=Depends(get_current_participant),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> dict[str, object]:
    event, event_participant = get_event_participant(event_id, current, db)
    if not event_participant.eligible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Participant is not eligible"
        )
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported receipt file type")
    content_type = file.content_type
    extension, max_size = ALLOWED_UPLOAD_TYPES[content_type]
    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="Receipt file is too large")
    validate_file_signature(content, content_type)
    parsed_amount = parse_amount(amount)
    normalized_currency = currency.strip().upper() if currency and currency.strip() else None
    if normalized_currency is not None and len(normalized_currency) != 3:
        raise HTTPException(status_code=422, detail="Currency must be a 3-letter code")
    now = datetime.now(timezone.utc)
    storage_key = f"events/{event.id}/participants/{event_participant.participant_id}/reimbursements/{uuid4()}.{extension}"
    storage.put_bytes(storage_key, content, content_type)
    reimbursement = TravelReimbursement(
        event_id=event.id,
        participant_id=event_participant.participant_id,
        amount=parsed_amount,
        currency=normalized_currency,
        transport_type=transport_type.strip() if transport_type else None,
        description=description.strip() if description else None,
        storage_key=storage_key,
        status=ReimbursementStatus.SUBMITTED.value,
        submitted_at=now,
    )
    db.add(reimbursement)
    db.commit()
    db.refresh(reimbursement)
    return {"reimbursement": serialize_reimbursement(reimbursement, storage)}


@router.get("/events/{event_id}/reimbursements/me")
def list_my_reimbursements(
    event_id: str,
    current=Depends(get_current_participant),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> dict[str, object]:
    _, event_participant = get_event_participant(event_id, current, db)
    rows = (
        db.query(TravelReimbursement)
        .filter_by(event_id=event_id, participant_id=event_participant.participant_id)
        .order_by(TravelReimbursement.submitted_at.desc())
        .all()
    )
    return {"reimbursements": [serialize_reimbursement(row, storage) for row in rows]}


@router.get("/admin/events/{event_id}/reimbursements")
def list_reimbursements(
    event_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> dict[str, object]:
    if db.get(Event, event_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    rows = (
        db.query(TravelReimbursement, Participant)
        .join(Participant, TravelReimbursement.participant_id == Participant.id)
        .filter(TravelReimbursement.event_id == event_id)
        .order_by(TravelReimbursement.submitted_at.asc())
        .all()
    )
    return {
        "reimbursements": [
            serialize_reimbursement(
                reimbursement,
                storage,
                {
                    "id": participant.id,
                    "displayName": participant.display_name,
                    "email": participant.email,
                },
            )
            for reimbursement, participant in rows
        ]
    }


@router.post("/admin/reimbursements/{reimbursement_id}/review")
def review_reimbursement(
    reimbursement_id: str,
    payload: ReimbursementReviewRequest,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _, organizer = current
    reimbursement = db.get(TravelReimbursement, reimbursement_id)
    if reimbursement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reimbursement not found")
    if reimbursement.status != ReimbursementStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Reimbursement is not awaiting review"
        )
    reimbursement.status = payload.decision
    reimbursement.review_note = payload.note or None
    reimbursement.reviewed_at = datetime.now(timezone.utc)
    reimbursement.reviewed_by = organizer.id
    db.add(
        AuditLog(
            event_id=reimbursement.event_id,
            actor_type="ORGANIZER",
            actor_id=organizer.id,
            action=f"REIMBURSEMENT_{payload.decision}",
            entity_type="TRAVEL_REIMBURSEMENT",
            entity_id=reimbursement.id,
            metadata_json={"decision": payload.decision, "note": payload.note},
        )
    )
    db.commit()
    return {"reimbursementId": reimbursement.id, "status": reimbursement.status}


@router.post("/admin/reimbursements/{reimbursement_id}/paid")
def mark_reimbursement_paid(
    reimbursement_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _, organizer = current
    reimbursement = db.get(TravelReimbursement, reimbursement_id)
    if reimbursement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reimbursement not found")
    if reimbursement.status != ReimbursementStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only approved reimbursements can be marked paid",
        )
    reimbursement.status = ReimbursementStatus.PAID.value
    reimbursement.paid_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            event_id=reimbursement.event_id,
            actor_type="ORGANIZER",
            actor_id=organizer.id,
            action="REIMBURSEMENT_PAID",
            entity_type="TRAVEL_REIMBURSEMENT",
            entity_id=reimbursement.id,
            metadata_json=None,
        )
    )
    db.commit()
    return {"reimbursementId": reimbursement.id, "status": reimbursement.status}
