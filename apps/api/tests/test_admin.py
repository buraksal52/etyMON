from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.db.models import Base, Event, EventParticipant, EventState, Organizer, Participant, Task
from app.db.session import get_db
from app.main import app


def make_admin_client() -> tuple[TestClient, str, object]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        event = Event(
            name="Admin Event",
            slug="admin-event",
            timezone="event-local",
            state=EventState.WAITING.value,
            task_deadline_at=datetime.now(timezone.utc),
        )
        organizer = Organizer(
            email="organizer@example.com",
            name="Organizer",
            password_hash_or_auth_provider_id=hash_password("secret"),
        )
        participant = Participant(email="participant@example.com", display_name="Participant")
        db.add_all([event, organizer, participant])
        db.flush()
        db.add(EventParticipant(event_id=event.id, participant_id=participant.id, eligible=True))
        db.add(
            Task(
                event_id=event.id,
                title="Test task",
                description="Test description",
                instructions="Test instructions",
                points=10,
                proof_type="IMAGE",
                active=True,
            )
        )
        db.commit()
        event_id = event.id

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), event_id, engine


def test_organizer_can_login_start_and_end_event() -> None:
    client, event_id, _ = make_admin_client()

    login = client.post(
        "/admin/login",
        json={"email": " ORGANIZER@example.com ", "password": "secret"},
    )
    assert login.status_code == 200
    assert "platform_admin_session" in client.cookies

    dashboard = client.get(f"/admin/events/{event_id}")
    assert dashboard.status_code == 200
    assert dashboard.json()["metrics"]["activeTasks"] == 1

    start = client.post(f"/admin/events/{event_id}/start")
    assert start.status_code == 200
    assert start.json()["state"] == "ACTIVE"

    end = client.post(f"/admin/events/{event_id}/end")
    assert end.status_code == 200
    assert end.json()["state"] == "ENDED"


def test_invalid_event_transitions_are_rejected() -> None:
    client, event_id, _ = make_admin_client()
    assert (
        client.post(
            "/admin/login", json={"email": "organizer@example.com", "password": "secret"}
        ).status_code
        == 200
    )

    assert client.post(f"/admin/events/{event_id}/end").status_code == 409
    assert client.post(f"/admin/events/{event_id}/start").status_code == 200
    assert client.post(f"/admin/events/{event_id}/start").status_code == 409
    assert client.post(f"/admin/events/{event_id}/end").status_code == 200
    assert client.post(f"/admin/events/{event_id}/start").status_code == 409
