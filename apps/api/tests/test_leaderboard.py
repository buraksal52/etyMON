from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import create_session_token, hash_password
from app.db.models import (
    AssignmentStatus,
    Base,
    Event,
    EventParticipant,
    EventState,
    Organizer,
    Participant,
    ScoreEntry,
    Task,
    TaskAssignment,
)
from app.db.session import get_db
from app.main import app


def make_leaderboard_client() -> tuple[TestClient, str, str, object]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with Session(engine) as db:
        event = Event(
            name="Leaderboard Event",
            slug="leaderboard-event",
            timezone="event-local",
            state=EventState.ACTIVE.value,
            task_deadline_at=base_time + timedelta(hours=1),
        )
        organizer = Organizer(
            email="leaderboard-organizer@example.com",
            name="Leaderboard Organizer",
            password_hash_or_auth_provider_id=hash_password("leaderboard-secret"),
        )
        participants = [
            Participant(email=f"leader{i}@example.com", display_name=name)
            for i, name in enumerate(["Alpha", "Beta", "Gamma", "Delta"], 1)
        ]
        db.add_all([event, organizer, *participants])
        db.flush()
        db.add_all(
            [
                EventParticipant(event_id=event.id, participant_id=participant.id, eligible=True)
                for participant in participants
            ]
        )
        task = Task(
            event_id=event.id,
            title="Scored task",
            description="Score",
            instructions="Score",
            points=50,
            proof_type="TEXT",
        )
        db.add(task)
        db.flush()
        assignments = []
        for participant in participants[:3]:
            assignment = TaskAssignment(
                event_id=event.id,
                task_id=task.id,
                participant_id=participant.id,
                status=AssignmentStatus.APPROVED.value,
            )
            assignments.append(assignment)
            db.add(assignment)
        db.flush()
        db.add_all(
            [
                ScoreEntry(
                    event_id=event.id,
                    participant_id=participants[0].id,
                    assignment_id=assignments[0].id,
                    points=50,
                    reason="first",
                    created_at=base_time,
                ),
                ScoreEntry(
                    event_id=event.id,
                    participant_id=participants[1].id,
                    assignment_id=assignments[1].id,
                    points=50,
                    reason="second",
                    created_at=base_time + timedelta(minutes=1),
                ),
                ScoreEntry(
                    event_id=event.id,
                    participant_id=participants[2].id,
                    assignment_id=assignments[2].id,
                    points=25,
                    reason="third-a",
                    created_at=base_time,
                ),
            ]
        )
        extra_assignment = TaskAssignment(
            event_id=event.id,
            task_id=task.id,
            participant_id=participants[2].id,
            status=AssignmentStatus.APPROVED.value,
        )
        db.add(extra_assignment)
        db.flush()
        db.add(
            ScoreEntry(
                event_id=event.id,
                participant_id=participants[2].id,
                assignment_id=extra_assignment.id,
                points=25,
                reason="third-b",
                created_at=base_time + timedelta(minutes=2),
            )
        )
        db.commit()
        event_id, first_participant_id = event.id, participants[0].id

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    client.cookies.set("platform_session", create_session_token(event_id, first_participant_id))
    admin_login = client.post(
        "/admin/login",
        json={"email": "leaderboard-organizer@example.com", "password": "leaderboard-secret"},
    )
    assert admin_login.status_code == 200
    return client, event_id, first_participant_id, engine


def test_leaderboard_uses_score_then_count_then_last_approval() -> None:
    client, event_id, _, engine = make_leaderboard_client()

    participant_response = client.get(f"/events/{event_id}/leaderboard")
    admin_response = client.get(f"/admin/events/{event_id}/leaderboard")

    assert participant_response.status_code == 200
    assert admin_response.status_code == 200
    assert participant_response.json() == admin_response.json()
    assert [row["participant"] for row in participant_response.json()["leaderboard"]] == [
        "Gamma",
        "Alpha",
        "Beta",
        "Delta",
    ]
    assert participant_response.json()["leaderboard"][0]["approvedTasks"] == 2
