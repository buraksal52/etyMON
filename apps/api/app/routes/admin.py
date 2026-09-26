from datetime import datetime, timezone

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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
    AssignmentStatus,
    AuditLog,
    Event,
    EventParticipant,
    EventState,
    Organizer,
    Participant,
    ScoreEntry,
    Submission,
    SubmissionStatus,
    Task,
    TaskAssignment,
    TravelReimbursement,
)
from app.db.session import get_db
from app.settings import settings
from app.rate_limit import login_rate_limiter
from app.storage import StorageProvider, get_storage_provider
from app.leaderboard import calculate_leaderboard, serialize_leaderboard

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class SubmissionReviewRequest(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    note: str = Field(default="", max_length=2000)


class EventCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = None
    timezone: str = Field(min_length=1, max_length=64)
    registration_opens_at: datetime | None = None
    starts_at: datetime | None = None
    task_deadline_at: datetime


class EventUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    registration_opens_at: datetime | None = None
    starts_at: datetime | None = None
    task_deadline_at: datetime | None = None
    state: str | None = Field(default=None, pattern="^(DRAFT|WAITING)$")


class TaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str
    instructions: str
    points: int = Field(gt=0)
    proof_type: str = Field(min_length=1, max_length=32)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    assignment_weight: int = Field(default=1, ge=1)
    max_assignments: int | None = Field(default=None, ge=1)
    active: bool = True
    metadata: dict[str, object] | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    instructions: str | None = None
    points: int | None = Field(default=None, gt=0)
    proof_type: str | None = Field(default=None, min_length=1, max_length=32)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    assignment_weight: int | None = Field(default=None, ge=1)
    max_assignments: int | None = Field(default=None, ge=1)
    active: bool | None = None
    metadata: dict[str, object] | None = None


def event_qr_svg(url: str) -> str:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    size = len(matrix)
    modules = "".join(
        f'<rect x="{column}" y="{row}" width="1" height="1"/>'
        for row, values in enumerate(matrix)
        for column, enabled in enumerate(values)
        if enabled
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'role="img" aria-label="Event QR code"><rect width="100%" height="100%" fill="white"/>'
        f'<g fill="black" shape-rendering="crispEdges">{modules}</g></svg>'
    )


@router.post("/login")
def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    client_host = request.client.host if request.client else "unknown"
    if not login_rate_limiter.allow(f"{client_host}:{normalize_email(payload.email)}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            headers={"Retry-After": "60"},
        )
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


@router.get("/events/{event_id}/qr")
def get_event_qr(
    event_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    event_url = f"{settings.app_url.rstrip('/')}/e/{event.slug}"
    return {"url": event_url, "svg": event_qr_svg(event_url)}


def serialize_task(task: Task) -> dict[str, object]:
    return {
        "id": task.id,
        "eventId": task.event_id,
        "title": task.title,
        "description": task.description,
        "instructions": task.instructions,
        "points": task.points,
        "proofType": task.proof_type,
        "startsAt": task.starts_at,
        "expiresAt": task.expires_at,
        "assignmentWeight": task.assignment_weight,
        "maxAssignments": task.max_assignments,
        "active": task.active,
        "metadata": task.metadata_json,
    }


@router.post("/events")
def create_event(
    payload: EventCreateRequest,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if db.query(Event).filter_by(slug=payload.slug).one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Event slug already exists")
    event = Event(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        timezone=payload.timezone,
        state=EventState.DRAFT.value,
        registration_opens_at=payload.registration_opens_at,
        starts_at=payload.starts_at,
        task_deadline_at=payload.task_deadline_at,
    )
    db.add(event)
    db.flush()
    organizer = current[1]
    db.add(
        AuditLog(
            event_id=event.id,
            actor_type="ORGANIZER",
            actor_id=organizer.id,
            action="EVENT_CREATED",
            entity_type="EVENT",
            entity_id=event.id,
            metadata_json=None,
        )
    )
    db.commit()
    db.refresh(event)
    return {"event": serialize_event(event)}


def serialize_event(event: Event) -> dict[str, object]:
    return {
        "id": event.id,
        "name": event.name,
        "slug": event.slug,
        "description": event.description,
        "timezone": event.timezone,
        "state": event.state,
        "registrationOpensAt": event.registration_opens_at,
        "startsAt": event.starts_at,
        "taskDeadlineAt": event.task_deadline_at,
        "endedAt": event.ended_at,
    }


@router.get("/events")
def list_events(
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    events = db.query(Event).order_by(Event.created_at.desc()).all()
    return {"events": [serialize_event(event) for event in events]}


@router.patch("/events/{event_id}")
def update_event(
    event_id: str,
    payload: EventUpdateRequest,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.state not in {EventState.DRAFT.value, EventState.WAITING.value}:
        raise HTTPException(status_code=409, detail="Event cannot be edited after start")
    updates = payload.model_dump(exclude_unset=True)
    requested_state = updates.get("state")
    if requested_state is not None and requested_state != event.state:
        if event.state != EventState.DRAFT.value or requested_state != EventState.WAITING.value:
            raise HTTPException(status_code=409, detail="Invalid event state transition")
    for field, value in updates.items():
        setattr(event, field, value)
    organizer = current[1]
    db.add(
        AuditLog(
            event_id=event.id,
            actor_type="ORGANIZER",
            actor_id=organizer.id,
            action="EVENT_UPDATED",
            entity_type="EVENT",
            entity_id=event.id,
            metadata_json=updates,
        )
    )
    db.commit()
    db.refresh(event)
    return {"event": serialize_event(event)}


@router.get("/events/{event_id}/participants")
def list_participants(
    event_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if db.get(Event, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    rows = (
        db.query(EventParticipant, Participant)
        .join(Participant, EventParticipant.participant_id == Participant.id)
        .filter(EventParticipant.event_id == event_id)
        .order_by(Participant.email.asc())
        .all()
    )
    return {
        "participants": [
            {
                "id": participant.id,
                "email": participant.email,
                "displayName": participant.display_name,
                "eligible": membership.eligible,
                "checkedInAt": membership.checked_in_at,
                "score": membership.score,
            }
            for membership, participant in rows
        ]
    }


def ensure_task_editable(task: Task, db: Session) -> Event:
    event = db.get(Event, task.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.state not in {EventState.DRAFT.value, EventState.WAITING.value}:
        raise HTTPException(status_code=409, detail="Tasks cannot be edited after start")
    return event


@router.post("/events/{event_id}/tasks")
def create_task(
    event_id: str,
    payload: TaskRequest,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.state not in {EventState.DRAFT.value, EventState.WAITING.value}:
        raise HTTPException(status_code=409, detail="Tasks cannot be created after start")
    task = Task(
        event_id=event_id,
        **payload.model_dump(exclude={"metadata"}),
        metadata_json=payload.metadata,
    )
    db.add(task)
    db.flush()
    db.add(
        AuditLog(
            event_id=event_id,
            actor_type="ORGANIZER",
            actor_id=current[1].id,
            action="TASK_CREATED",
            entity_type="TASK",
            entity_id=task.id,
            metadata_json={"title": task.title},
        )
    )
    db.commit()
    db.refresh(task)
    return {"task": serialize_task(task)}


@router.get("/events/{event_id}/tasks")
def list_tasks(
    event_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if db.get(Event, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    tasks = db.query(Task).filter_by(event_id=event_id).order_by(Task.created_at.asc()).all()
    return {"tasks": [serialize_task(task) for task in tasks]}


@router.patch("/tasks/{task_id}")
def update_task(
    task_id: str,
    payload: TaskUpdateRequest,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    event = ensure_task_editable(task, db)
    updates = payload.model_dump(exclude_unset=True, exclude={"metadata"})
    for field, value in updates.items():
        setattr(task, field, value)
    if "metadata" in payload.model_fields_set:
        task.metadata_json = payload.metadata
    db.add(
        AuditLog(
            event_id=event.id,
            actor_type="ORGANIZER",
            actor_id=current[1].id,
            action="TASK_UPDATED",
            entity_type="TASK",
            entity_id=task.id,
            metadata_json=updates,
        )
    )
    db.commit()
    db.refresh(task)
    return {"task": serialize_task(task)}


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    event = ensure_task_editable(task, db)
    if db.query(TaskAssignment).filter_by(task_id=task.id).count() > 0:
        raise HTTPException(status_code=409, detail="Assigned tasks cannot be deleted")
    db.add(
        AuditLog(
            event_id=event.id,
            actor_type="ORGANIZER",
            actor_id=current[1].id,
            action="TASK_DELETED",
            entity_type="TASK",
            entity_id=task.id,
            metadata_json={"title": task.title},
        )
    )
    db.delete(task)
    db.commit()
    return {"taskId": task_id, "status": "deleted"}


@router.get("/events/{event_id}")
def get_dashboard(
    event_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    joined_participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == event.id,
        EventParticipant.checked_in_at.is_not(None),
    ).count()
    return {
        "event": {
            "id": event.id,
            "name": event.name,
            "slug": event.slug,
            "state": event.state,
        },
        "metrics": {
            "registeredParticipants": db.query(EventParticipant)
            .filter_by(event_id=event.id)
            .count(),
            "activeParticipants": (
                joined_participants if event.state == EventState.ACTIVE.value else 0
            ),
            "waitingParticipants": (
                joined_participants if event.state == EventState.WAITING.value else 0
            ),
            "joinedParticipants": joined_participants,
            "totalAssignments": db.query(TaskAssignment).filter_by(event_id=event.id).count(),
            "totalSubmissions": db.query(Submission)
            .join(TaskAssignment)
            .filter(TaskAssignment.event_id == event.id)
            .count(),
            "activeTasks": db.query(Task)
            .filter(Task.event_id == event.id, Task.active.is_(True))
            .count(),
            "approvedSubmissions": db.query(Submission)
            .join(TaskAssignment)
            .filter(
                TaskAssignment.event_id == event.id,
                Submission.status == SubmissionStatus.APPROVED.value,
            )
            .count(),
            "rejectedSubmissions": db.query(Submission)
            .join(TaskAssignment)
            .filter(
                TaskAssignment.event_id == event.id,
                Submission.status == SubmissionStatus.REJECTED.value,
            )
            .count(),
            "pendingProofReviews": db.query(Submission)
            .join(TaskAssignment)
            .filter(
                TaskAssignment.event_id == event.id,
                Submission.status == SubmissionStatus.PENDING.value,
            )
            .count(),
            "reimbursementRequests": db.query(TravelReimbursement)
            .filter(TravelReimbursement.event_id == event.id)
            .count(),
            "timeRemainingSeconds": max(
                0,
                int(
                    (
                        (
                            event.task_deadline_at.replace(tzinfo=timezone.utc)
                            if event.task_deadline_at.tzinfo is None
                            else event.task_deadline_at
                        )
                        - datetime.now(timezone.utc)
                    ).total_seconds()
                ),
            ),
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


@router.get("/events/{event_id}/submissions")
def list_submissions(
    event_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> dict[str, object]:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    rows = (
        db.query(Submission, TaskAssignment, Task, Participant)
        .join(TaskAssignment, Submission.assignment_id == TaskAssignment.id)
        .join(Task, TaskAssignment.task_id == Task.id)
        .join(Participant, Submission.participant_id == Participant.id)
        .filter(TaskAssignment.event_id == event_id)
        .all()
    )
    rows.sort(
        key=lambda row: (row[0].status != SubmissionStatus.PENDING.value, row[0].submitted_at)
    )
    return {
        "submissions": [
            {
                "id": submission.id,
                "status": submission.status,
                "participant": {
                    "displayName": participant.display_name,
                    "id": participant.id,
                },
                "task": {"id": task.id, "title": task.title, "points": task.points},
                "proof": {
                    "text": submission.text_content,
                    "url": submission.url,
                    "storageKey": submission.storage_key,
                    "downloadUrl": (
                        storage.get_download_url(submission.storage_key)
                        if submission.storage_key
                        else None
                    ),
                },
                "submittedAt": submission.submitted_at,
                "reviewNote": submission.review_note,
            }
            for submission, _, task, participant in rows
        ]
    }


@router.get("/events/{event_id}/leaderboard")
def admin_leaderboard(
    event_id: str,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if db.get(Event, event_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return {"leaderboard": serialize_leaderboard(calculate_leaderboard(db, event_id))}


@router.post("/submissions/{submission_id}/review")
def review_submission(
    submission_id: str,
    payload: SubmissionReviewRequest,
    current=Depends(get_current_organizer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _, organizer = current
    submission = db.query(Submission).filter_by(id=submission_id).with_for_update().one_or_none()
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    if submission.status != SubmissionStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Submission was already reviewed"
        )

    assignment = db.get(TaskAssignment, submission.assignment_id)
    if assignment is None or assignment.status != AssignmentStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Assignment is not reviewable"
        )
    task = db.get(Task, assignment.task_id)
    event_participant = (
        db.query(EventParticipant)
        .filter_by(event_id=assignment.event_id, participant_id=assignment.participant_id)
        .one_or_none()
    )
    if task is None or event_participant is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Review data is incomplete"
        )

    now = datetime.now(timezone.utc)
    submission.reviewed_at = now
    submission.reviewed_by = organizer.id
    submission.review_note = payload.note or None
    if payload.decision == "APPROVED":
        submission.status = SubmissionStatus.APPROVED.value
        assignment.status = AssignmentStatus.APPROVED.value
        assignment.resolved_at = now
        score_entry = db.query(ScoreEntry).filter_by(assignment_id=assignment.id).one_or_none()
        if score_entry is None:
            db.add(
                ScoreEntry(
                    event_id=assignment.event_id,
                    participant_id=assignment.participant_id,
                    assignment_id=assignment.id,
                    points=task.points,
                    reason=f"Approved task: {task.title}",
                )
            )
            event_participant.score += task.points
        action = "SUBMISSION_APPROVED"
    else:
        submission.status = SubmissionStatus.REJECTED.value
        assignment.status = AssignmentStatus.REJECTED.value
        assignment.resolved_at = now
        action = "SUBMISSION_REJECTED"

    db.add(
        AuditLog(
            event_id=assignment.event_id,
            actor_type="ORGANIZER",
            actor_id=organizer.id,
            action=action,
            entity_type="SUBMISSION",
            entity_id=submission.id,
            metadata_json={"decision": payload.decision, "note": payload.note},
        )
    )
    db.commit()
    return {
        "submissionId": submission.id,
        "status": submission.status,
        "assignmentStatus": assignment.status,
        "scoreAwarded": task.points if payload.decision == "APPROVED" else 0,
    }
