from datetime import datetime, timezone
import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_participant
from app.db.models import (
    AssignmentStatus,
    Event,
    EventParticipant,
    EventState,
    Task,
    TaskAssignment,
)
from app.db.session import get_db

router = APIRouter(prefix="/events/{event_id}/tasks", tags=["tasks"])
UNRESOLVED_STATUSES = (AssignmentStatus.ASSIGNED.value, AssignmentStatus.SUBMITTED.value)


def timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def serialize_assignment(assignment: TaskAssignment, task: Task) -> dict[str, object]:
    return {
        "id": assignment.id,
        "status": assignment.status,
        "assignedAt": assignment.assigned_at,
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "instructions": task.instructions,
            "points": task.points,
            "proofType": task.proof_type,
            "startsAt": task.starts_at,
            "expiresAt": task.expires_at,
            "metadata": task.metadata_json,
        },
    }


@router.post("/next")
def assign_next_task(
    event_id: str,
    current=Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    session, _, _ = current
    if session.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event session mismatch")

    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    now = datetime.now(timezone.utc)
    if event.state != EventState.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Event is not active")
    if timestamp(now) >= timestamp(event.task_deadline_at):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task deadline has passed")

    event_participant = (
        db.query(EventParticipant)
        .filter_by(event_id=event_id, participant_id=session.participant_id, eligible=True)
        .with_for_update()
        .one_or_none()
    )
    if event_participant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Participant is not eligible"
        )

    assignments = (
        db.query(TaskAssignment)
        .filter_by(event_id=event_id, participant_id=session.participant_id)
        .all()
    )
    if any(assignment.status in UNRESOLVED_STATUSES for assignment in assignments):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Participant already has an unresolved task",
        )

    assigned_task_ids = {assignment.task_id for assignment in assignments}
    assignment_counts: dict[str, int] = {}
    for assignment in assignments:
        assignment_counts[assignment.task_id] = assignment_counts.get(assignment.task_id, 0) + 1

    candidates = []
    for task in db.query(Task).filter_by(event_id=event_id, active=True).all():
        if task.id in assigned_task_ids:
            continue
        if task.starts_at is not None and timestamp(task.starts_at) > timestamp(now):
            continue
        if task.expires_at is not None and timestamp(task.expires_at) <= timestamp(now):
            continue
        if (
            task.max_assignments is not None
            and assignment_counts.get(task.id, 0) >= task.max_assignments
        ):
            continue
        candidates.append(task)

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="No task is currently available"
        )

    selected = random.choices(
        candidates,
        weights=[max(1, task.assignment_weight) for task in candidates],
        k=1,
    )[0]
    assignment = TaskAssignment(
        event_id=event_id,
        task_id=selected.id,
        participant_id=session.participant_id,
        status=AssignmentStatus.ASSIGNED.value,
        assigned_at=now,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {"assignment": serialize_assignment(assignment, selected)}


@router.get("/current")
def get_current_task(
    event_id: str,
    current=Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    session, _, _ = current
    if session.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event session mismatch")
    assignment = (
        db.query(TaskAssignment)
        .filter(
            TaskAssignment.event_id == event_id,
            TaskAssignment.participant_id == session.participant_id,
            TaskAssignment.status.in_(UNRESOLVED_STATUSES),
        )
        .order_by(TaskAssignment.assigned_at.desc())
        .first()
    )
    latest_assignment = (
        db.query(TaskAssignment)
        .filter(
            TaskAssignment.event_id == event_id,
            TaskAssignment.participant_id == session.participant_id,
        )
        .order_by(TaskAssignment.assigned_at.desc())
        .first()
    )
    if assignment is None:
        if latest_assignment is None:
            return {"assignment": None, "lastAssignment": None}
        latest_task = db.get(Task, latest_assignment.task_id)
        if latest_task is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Assigned task not found",
            )
        return {
            "assignment": None,
            "lastAssignment": serialize_assignment(latest_assignment, latest_task),
        }
    task = db.get(Task, assignment.task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Assigned task not found"
        )
    return {"assignment": serialize_assignment(assignment, task), "lastAssignment": None}
