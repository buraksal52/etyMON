from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_participant
from app.file_validation import ALLOWED_UPLOAD_TYPES, validate_file_signature
from app.db.models import (
    AssignmentStatus,
    Event,
    EventState,
    Submission,
    SubmissionStatus,
    Task,
    TaskAssignment,
)
from app.db.session import get_db
from app.storage import StorageProvider, get_storage_provider

router = APIRouter(tags=["submissions"])


def validate_proof(task: Task, file: UploadFile | None, text: str | None, url: str | None) -> None:
    has_file = file is not None
    has_text = bool(text and text.strip())
    has_url = bool(url and url.strip())
    proof_type = task.proof_type
    if proof_type == "IMAGE" and not has_file:
        raise HTTPException(status_code=422, detail="Image proof is required")
    if proof_type == "URL" and not has_url:
        raise HTTPException(status_code=422, detail="URL proof is required")
    if proof_type == "TEXT" and not has_text:
        raise HTTPException(status_code=422, detail="Text proof is required")
    if proof_type == "IMAGE_AND_URL" and (not has_file or not has_url):
        raise HTTPException(status_code=422, detail="Image and URL proof are required")
    if proof_type == "TEXT_OR_URL" and not (has_text or has_url):
        raise HTTPException(status_code=422, detail="Text or URL proof is required")
    if has_file and file is not None and file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported proof file type")


@router.post("/assignments/{assignment_id}/submit")
async def submit_proof(
    assignment_id: str,
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    url: str | None = Form(default=None),
    current=Depends(get_current_participant),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> dict[str, object]:
    session, _, _ = current
    assignment = db.get(TaskAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if (
        assignment.participant_id != session.participant_id
        or assignment.event_id != session.event_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignment does not belong to participant",
        )

    existing = db.query(Submission).filter_by(assignment_id=assignment.id).one_or_none()
    if assignment.status == AssignmentStatus.SUBMITTED.value and existing is not None:
        return {
            "submissionId": existing.id,
            "status": existing.status,
            "storageKey": existing.storage_key,
        }
    if assignment.status != AssignmentStatus.ASSIGNED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assignment is not available for submission",
        )

    event = db.get(Event, assignment.event_id)
    task = db.get(Task, assignment.task_id)
    if event is None or task is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assignment data is incomplete",
        )
    now = datetime.now(timezone.utc)
    if event.state != EventState.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Event is not active")
    deadline = event.task_deadline_at
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if now >= deadline:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Submission deadline has passed"
        )
    validate_proof(task, file, text, url)

    storage_key = None
    if file is not None:
        extension, max_size = ALLOWED_UPLOAD_TYPES[file.content_type]
        content = await file.read(max_size + 1)
        if len(content) > max_size:
            raise HTTPException(status_code=413, detail="Proof file is too large")
        validate_file_signature(content, file.content_type)
        storage_key = (
            f"events/{event.id}/participants/{session.participant_id}/proofs/{uuid4()}.{extension}"
        )
        storage.put_bytes(storage_key, content, file.content_type)

    submission = Submission(
        assignment_id=assignment.id,
        participant_id=session.participant_id,
        text_content=text.strip() if text else None,
        url=url.strip() if url else None,
        storage_key=storage_key,
        status=SubmissionStatus.PENDING.value,
        submitted_at=now,
    )
    assignment.status = AssignmentStatus.SUBMITTED.value
    assignment.submitted_at = now
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return {
        "submissionId": submission.id,
        "status": submission.status,
        "storageKey": submission.storage_key,
    }
