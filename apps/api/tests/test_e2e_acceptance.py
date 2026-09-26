from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.db.models import (
    Base,
    Event,
    EventParticipant,
    EventState,
    Organizer,
    Participant,
    Task,
)
from app.db.session import get_db
from app.main import app
from app.storage import get_storage_provider


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_bytes(self, key: str, content: bytes, content_type: str) -> None:
        self.objects[key] = (content, content_type)

    def get_download_url(self, key: str, expires_in: int = 900) -> str:
        return f"https://storage.test/signed/{key}?expires={expires_in}"


def make_acceptance_clients() -> tuple[TestClient, TestClient, str, object, FakeStorage]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    organizer_email = "e2e-organizer@example.com"
    participant_email = "e2e-participant@example.com"
    with Session(engine) as db:
        event = Event(
            name="Acceptance Event",
            slug="acceptance-event",
            timezone="Europe/Istanbul",
            state=EventState.WAITING.value,
            task_deadline_at=now + timedelta(hours=1),
        )
        organizer = Organizer(
            email=organizer_email,
            name="Acceptance Organizer",
            password_hash_or_auth_provider_id=hash_password("secret"),
        )
        participant = Participant(email=participant_email, display_name="Acceptance Participant")
        db.add_all([event, organizer, participant])
        db.flush()
        db.add(EventParticipant(event_id=event.id, participant_id=participant.id, eligible=True))
        db.add_all(
            [
                Task(
                    event_id=event.id,
                    title="First task",
                    metadata_json={
                        "missionStage": 1,
                        "pythonGate": {"prompt": "Test gate", "answers": ["ok"]},
                    },
                    description="First task",
                    instructions="Upload a photo",
                    points=25,
                    proof_type="IMAGE",
                    assignment_weight=1,
                ),
                Task(
                    event_id=event.id,
                    title="Second task",
                    metadata_json={"missionStage": 2},
                    description="Second task",
                    instructions="Upload a photo",
                    points=15,
                    proof_type="IMAGE",
                    assignment_weight=1,
                ),
            ]
        )
        db.commit()
        event_id = event.id

    storage = FakeStorage()

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage_provider] = lambda: storage
    return TestClient(app), TestClient(app), event_id, engine, storage


def test_e2e_acceptance_flow() -> None:
    admin, participant, event_id, _, storage = make_acceptance_clients()
    try:
        event = participant.get("/events/acceptance-event")
        assert event.status_code == 200
        assert event.json()["state"] == EventState.WAITING.value

        joined = participant.post(
            "/events/acceptance-event/join",
            json={"email": " e2e-participant@example.com "},
        )
        assert joined.status_code == 200
        assert joined.json()["state"] == EventState.WAITING.value
        assert participant.get(f"/events/{event_id}/status").json()["state"] == "WAITING"

        login = admin.post(
            "/admin/login",
            json={"email": "e2e-organizer@example.com", "password": "secret"},
        )
        assert login.status_code == 200
        assert admin.get(f"/admin/events/{event_id}").status_code == 200

        started = admin.post(f"/admin/events/{event_id}/start")
        assert started.status_code == 200
        assert participant.get(f"/events/{event_id}/status").json()["state"] == "ACTIVE"

        assigned = participant.post(f"/events/{event_id}/tasks/next")
        assert assigned.status_code == 200
        assignment = assigned.json()["assignment"]
        assert assignment["task"]["title"] in {"First task", "Second task"}

        submitted = participant.post(
            f"/assignments/{assignment['id']}/submit",
            files={"file": ("proof.png", b"\x89PNG\r\n\x1a\nproof", "image/png")},
        )
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "PENDING"
        assert len(storage.objects) == 1

        submissions = admin.get(f"/admin/events/{event_id}/submissions")
        assert submissions.status_code == 200
        submission = submissions.json()["submissions"][0]
        assert submission["status"] == "PENDING"
        reviewed = admin.post(
            f"/admin/submissions/{submission['id']}/review",
            json={"decision": "APPROVED", "note": "Verified"},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "APPROVED"

        progress = participant.get(f"/events/{event_id}/progress")
        assert progress.status_code == 200
        assert progress.json()["score"] in {15, 25}
        assert progress.json()["counts"]["approved"] == 1
        leaderboard = participant.get(f"/events/{event_id}/leaderboard")
        assert leaderboard.status_code == 200
        assert leaderboard.json()["leaderboard"][0]["score"] in {15, 25}

        next_task = participant.post(f"/events/{event_id}/tasks/next", json={"answer": "ok"})
        assert next_task.status_code == 200
        assert next_task.json()["assignment"]["id"] != assignment["id"]

        reimbursement = participant.post(
            f"/events/{event_id}/reimbursements",
            data={
                "amount": "100.00",
                "currency": "eur",
                "transportType": "Train",
                "description": "Return ticket",
            },
            files={"file": ("receipt.pdf", b"%PDF-1.7 receipt", "application/pdf")},
        )
        assert reimbursement.status_code == 200
        reimbursement_id = reimbursement.json()["reimbursement"]["id"]
        listed = admin.get(f"/admin/events/{event_id}/reimbursements")
        assert listed.status_code == 200
        assert listed.json()["reimbursements"][0]["id"] == reimbursement_id
        approved = admin.post(
            f"/admin/reimbursements/{reimbursement_id}/review",
            json={"decision": "APPROVED", "note": "Verified"},
        )
        assert approved.status_code == 200
        paid = admin.post(f"/admin/reimbursements/{reimbursement_id}/paid")
        assert paid.status_code == 200
        assert paid.json()["status"] == "PAID"

        ended = admin.post(f"/admin/events/{event_id}/end")
        assert ended.status_code == 200
        assert ended.json()["state"] == EventState.ENDED.value
        assert participant.post(f"/events/{event_id}/tasks/next").status_code == 409
    finally:
        app.dependency_overrides.clear()
