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
)
from app.db.session import get_db
from app.settings import settings
from app.storage import StorageProvider, get_storage_provider

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class SubmissionReviewRequest(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    note: str = Field(default="", max_length=2000)


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
