from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.db.models import (
    AssignmentStatus,
    AuditLog,
    Base,
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
from app.main import app


def make_review_client() -> tuple[TestClient, str, str, object]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        event = Event(
            name="Review Event",
            slug="review-event",
            timezone="event-local",
            state=EventState.ACTIVE.value,
            task_deadline_at=now + timedelta(hours=1),
        )
        organizer = Organizer(
            email="reviewer@example.com",
            name="Reviewer",
            password_hash_or_auth_provider_id=hash_password("review-secret"),
        )
        participant = Participant(
            email="review-participant@example.com", display_name="Review Participant"
        )
        db.add_all([event, organizer, participant])
        db.flush()
        event_participant = EventParticipant(
            event_id=event.id, participant_id=participant.id, eligible=True, score=0
        )
        task = Task(
            event_id=event.id,
            title="Review task",
            description="Review",
            instructions="Review",
            points=42,
            proof_type="URL",
        )
        db.add_all([event_participant, task])
        db.flush()
        assignment = TaskAssignment(
            event_id=event.id,
            task_id=task.id,
            participant_id=participant.id,
            status=AssignmentStatus.SUBMITTED.value,
            submitted_at=now,
        )
        db.add(assignment)
        db.flush()
        submission = Submission(
            assignment_id=assignment.id,
            participant_id=participant.id,
            url="https://example.com/proof",
            status=SubmissionStatus.PENDING.value,
            submitted_at=now,
        )
        db.add(submission)
        db.commit()
        event_id, submission_id = event.id, submission.id

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    login = client.post(
        "/admin/login",
        json={"email": "reviewer@example.com", "password": "review-secret"},
    )
    assert login.status_code == 200
    return client, event_id, submission_id, engine


def test_organizer_can_list_and_approve_submission_once() -> None:
    client, event_id, submission_id, engine = make_review_client()

    listing = client.get(f"/admin/events/{event_id}/submissions")
    assert listing.status_code == 200
    assert listing.json()["submissions"][0]["status"] == SubmissionStatus.PENDING.value

    review = client.post(
        f"/admin/submissions/{submission_id}/review",
        json={"decision": "APPROVED", "note": "Valid proof"},
    )
    assert review.status_code == 200
    assert review.json()["scoreAwarded"] == 42

    duplicate = client.post(
        f"/admin/submissions/{submission_id}/review",
        json={"decision": "APPROVED", "note": "Duplicate"},
    )
    assert duplicate.status_code == 409

    with Session(engine) as db:
        assert (
            db.query(ScoreEntry)
            .filter_by(assignment_id=db.query(Submission).one().assignment_id)
            .count()
            == 1
        )
        assert db.query(EventParticipant).one().score == 42
        assert db.query(AuditLog).filter_by(action="SUBMISSION_APPROVED").count() == 1
        assert db.query(Submission).one().status == SubmissionStatus.APPROVED.value
        assert db.query(TaskAssignment).one().status == AssignmentStatus.APPROVED.value


def test_rejected_submission_does_not_award_points() -> None:
    client, _, submission_id, engine = make_review_client()

    review = client.post(
        f"/admin/submissions/{submission_id}/review",
        json={"decision": "REJECTED", "note": "Insufficient proof"},
    )
    assert review.status_code == 200
    assert review.json()["scoreAwarded"] == 0

    with Session(engine) as db:
        assert db.query(EventParticipant).one().score == 0
        assert db.query(ScoreEntry).count() == 0
        assert db.query(AuditLog).filter_by(action="SUBMISSION_REJECTED").count() == 1


def test_organizer_can_review_existing_submission_after_deadline() -> None:
    client, _, submission_id, engine = make_review_client()

    with Session(engine) as db:
        event = db.query(Event).one()
        event.task_deadline_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    response = client.post(
        f"/admin/submissions/{submission_id}/review",
        json={"decision": "APPROVED", "note": "Reviewed after event deadline"},
    )

    assert response.status_code == 200
