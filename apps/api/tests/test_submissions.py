from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import create_session_token
from app.db.models import (
    AssignmentStatus,
    Base,
    Event,
    EventParticipant,
    EventState,
    Participant,
    Submission,
    SubmissionStatus,
    Task,
    TaskAssignment,
)
from app.db.session import get_db
from app.main import app
from app.storage import get_storage_provider


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_bytes(self, key: str, content: bytes, content_type: str) -> None:
        self.objects[key] = (content, content_type)


def make_submission_client() -> tuple[TestClient, str, str, object, FakeStorage]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    storage = FakeStorage()
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        event = Event(
            name="Submission Event",
            slug="submission-event",
            timezone="event-local",
            state=EventState.ACTIVE.value,
            task_deadline_at=now + timedelta(hours=1),
        )
        participant = Participant(email="submitter@example.com", display_name="Submitter")
        db.add_all([event, participant])
        db.flush()
        db.add(EventParticipant(event_id=event.id, participant_id=participant.id, eligible=True))
        task = Task(
            event_id=event.id,
            title="Photo task",
            description="Photo",
            instructions="Upload a photo and URL",
            points=10,
            proof_type="IMAGE_AND_URL",
        )
        db.add(task)
        db.flush()
        assignment = TaskAssignment(
            event_id=event.id,
            task_id=task.id,
            participant_id=participant.id,
            status=AssignmentStatus.ASSIGNED.value,
        )
        db.add(assignment)
        db.commit()
        event_id, assignment_id, participant_id = event.id, assignment.id, participant.id

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage_provider] = lambda: storage
    client = TestClient(app)
    client.cookies.set("platform_session", create_session_token(event_id, participant_id))
    return client, event_id, assignment_id, engine, storage


def test_image_and_url_submission_is_persisted_and_idempotent() -> None:
    client, _, assignment_id, engine, storage = make_submission_client()
    request = {
        "data": {"url": "https://example.com/proof"},
        "files": {"file": ("proof.png", b"\x89PNG\r\n\x1a\nimage-bytes", "image/png")},
    }

    first = client.post(f"/assignments/{assignment_id}/submit", **request)
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == SubmissionStatus.PENDING.value
    assert body["storageKey"].endswith(".png")
    assert len(storage.objects) == 1

    retry = client.post(f"/assignments/{assignment_id}/submit", **request)
    assert retry.status_code == 200
    assert retry.json()["submissionId"] == body["submissionId"]

    with Session(engine) as db:
        assignment = db.get(TaskAssignment, assignment_id)
        assert assignment is not None
        assert assignment.status == AssignmentStatus.SUBMITTED.value
        assert db.query(Submission).filter_by(assignment_id=assignment_id).count() == 1


def test_submission_rejects_unsupported_file_type_and_missing_proof() -> None:
    client, _, assignment_id, _, _ = make_submission_client()

    bad_type = client.post(
        f"/assignments/{assignment_id}/submit",
        data={"url": "https://example.com/proof"},
        files={"file": ("proof.exe", b"not-image", "application/octet-stream")},
    )
    assert bad_type.status_code == 415

    missing_url = client.post(
        f"/assignments/{assignment_id}/submit",
        files={"file": ("proof.png", b"\x89PNG\r\n\x1a\nimage-bytes", "image/png")},
    )
    assert missing_url.status_code == 422
