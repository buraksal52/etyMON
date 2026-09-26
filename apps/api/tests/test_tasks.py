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
    Task,
    TaskAssignment,
)
from app.db.session import get_db
from app.main import app


def make_task_client() -> tuple[TestClient, str, str, object]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        event = Event(
            name="Task Event",
            slug="task-event",
            timezone="event-local",
            state=EventState.ACTIVE.value,
            starts_at=now,
            task_deadline_at=now + timedelta(hours=1),
        )
        participant = Participant(email="task-user@example.com", display_name="Task User")
        db.add_all([event, participant])
        db.flush()
        db.add(EventParticipant(event_id=event.id, participant_id=participant.id, eligible=True))
        db.add_all(
            [
                Task(
                    event_id=event.id,
                    title="Available A",
                    description="A",
                    instructions="A",
                    points=10,
                    proof_type="IMAGE",
                    assignment_weight=1,
                ),
                Task(
                    event_id=event.id,
                    title="Available B",
                    description="B",
                    instructions="B",
                    points=20,
                    proof_type="URL",
                    assignment_weight=3,
                ),
                Task(
                    event_id=event.id,
                    title="Future Task",
                    description="Future",
                    instructions="Future",
                    points=30,
                    proof_type="TEXT",
                    starts_at=now + timedelta(hours=2),
                ),
            ]
        )
        db.commit()
        event_id, participant_id = event.id, participant.id

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    client.cookies.set("platform_session", create_session_token(event_id, participant_id))
    return client, event_id, participant_id, engine


def test_next_task_respects_current_assignment_and_candidate_rules() -> None:
    client, event_id, participant_id, engine = make_task_client()

    first = client.post(f"/events/{event_id}/tasks/next")
    assert first.status_code == 200
    first_assignment = first.json()["assignment"]
    assert first_assignment["task"]["title"] in {"Available A", "Available B"}

    current = client.get(f"/events/{event_id}/tasks/current")
    assert current.status_code == 200
    assert current.json()["assignment"]["id"] == first_assignment["id"]

    duplicate_request = client.post(f"/events/{event_id}/tasks/next")
    assert duplicate_request.status_code == 409

    with Session(engine) as db:
        assignment = db.get(TaskAssignment, first_assignment["id"])
        assert assignment is not None
        assignment.status = AssignmentStatus.APPROVED.value
        db.commit()

    resolved = client.get(f"/events/{event_id}/tasks/current")
    assert resolved.status_code == 200
    assert resolved.json()["assignment"] is None
    assert resolved.json()["lastAssignment"]["id"] == first_assignment["id"]
    assert resolved.json()["lastAssignment"]["status"] == AssignmentStatus.APPROVED.value

    second = client.post(f"/events/{event_id}/tasks/next")
    assert second.status_code == 200
    assert second.json()["assignment"]["task"]["title"] != first_assignment["task"]["title"]
    assert second.json()["assignment"]["task"]["title"] != "Future Task"


def test_task_request_rejects_after_deadline() -> None:
    client, event_id, _, engine = make_task_client()

    with Session(engine) as db:
        event = db.get(Event, event_id)
        assert event is not None
        event.task_deadline_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    response = client.post(f"/events/{event_id}/tasks/next")

    assert response.status_code == 409
