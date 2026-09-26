from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Event, EventParticipant, EventState, Participant
from app.db.session import get_db
from app.main import app


def make_client() -> tuple[TestClient, str]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        event = Event(
            name="Test Event",
            slug="test-event",
            timezone="event-local",
            state=EventState.WAITING.value,
            task_deadline_at=datetime.now(timezone.utc),
        )
        participant = Participant(email="alice@example.com", display_name="Alice")
        db.add_all([event, participant])
        db.flush()
        db.add(EventParticipant(event_id=event.id, participant_id=participant.id, eligible=True))
        db.commit()
        event_id = event.id

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), event_id


def test_eligible_participant_can_join_and_read_session() -> None:
    client, event_id = make_client()

    join = client.post("/events/test-event/join", json={"email": " ALICE@example.com "})
    assert join.status_code == 200
    assert join.json()["state"] == "WAITING"
    assert "platform_session" in client.cookies

    status_response = client.get(f"/events/{event_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["state"] == "WAITING"

    me = client.get(f"/events/{event_id}/me")
    assert me.status_code == 200
    assert me.json()["participant"]["displayName"] == "Alice"


def test_unknown_email_is_rejected_without_session() -> None:
    client, _ = make_client()

    response = client.post("/events/test-event/join", json={"email": "unknown@example.com"})

    assert response.status_code == 403
    assert "platform_session" not in client.cookies
