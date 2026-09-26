from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import create_session_token, hash_password
from app.db.models import (
    AuditLog,
    Base,
    Event,
    EventParticipant,
    EventState,
    Organizer,
    Participant,
    ReimbursementStatus,
    TravelReimbursement,
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


def make_reimbursement_client() -> tuple[TestClient, str, str, object, FakeStorage]:
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
            name="Travel Event",
            slug="travel-event",
            timezone="event-local",
            state=EventState.ENDED.value,
            task_deadline_at=now - timedelta(hours=1),
        )
        organizer = Organizer(
            email="travel-organizer@example.com",
            name="Travel Organizer",
            password_hash_or_auth_provider_id=hash_password("secret"),
        )
        participant = Participant(email="traveler@example.com", display_name="Traveler")
        db.add_all([event, organizer, participant])
        db.flush()
        db.add(EventParticipant(event_id=event.id, participant_id=participant.id, eligible=True))
        db.commit()
        event_id, participant_id = event.id, participant.id

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage_provider] = lambda: storage
    client = TestClient(app)
    client.cookies.set("platform_session", create_session_token(event_id, participant_id))
    return client, event_id, participant_id, engine, storage


def test_participant_can_submit_and_list_private_reimbursement() -> None:
    client, event_id, _, engine, storage = make_reimbursement_client()

    response = client.post(
        f"/events/{event_id}/reimbursements",
        data={
            "amount": "125.50",
            "currency": "eur",
            "transportType": "Train",
            "description": "Return train ticket",
        },
        files={"file": ("ticket.pdf", b"%PDF-1.7 receipt", "application/pdf")},
    )
    assert response.status_code == 200
    reimbursement = response.json()["reimbursement"]
    assert reimbursement["status"] == ReimbursementStatus.SUBMITTED.value
    assert reimbursement["amount"] == "125.50"
    assert reimbursement["currency"] == "EUR"
    assert reimbursement["receiptUrl"].startswith("https://storage.test/signed/")
    assert len(storage.objects) == 1

    listing = client.get(f"/events/{event_id}/reimbursements/me")
    assert listing.status_code == 200
    assert listing.json()["reimbursements"][0]["id"] == reimbursement["id"]
    with Session(engine) as db:
        assert db.query(TravelReimbursement).one().status == ReimbursementStatus.SUBMITTED.value


def test_organizer_can_review_and_mark_reimbursement_paid() -> None:
    client, event_id, _, engine, _ = make_reimbursement_client()
    submitted = client.post(
        f"/events/{event_id}/reimbursements",
        files={"file": ("ticket.png", b"\x89PNG\r\n\x1a\nreceipt", "image/png")},
    )
    reimbursement_id = submitted.json()["reimbursement"]["id"]

    login = client.post(
        "/admin/login",
        json={"email": "travel-organizer@example.com", "password": "secret"},
    )
    assert login.status_code == 200
    listing = client.get(f"/admin/events/{event_id}/reimbursements")
    assert listing.status_code == 200
    assert listing.json()["reimbursements"][0]["participant"]["email"] == "traveler@example.com"

    review = client.post(
        f"/admin/reimbursements/{reimbursement_id}/review",
        json={"decision": "APPROVED", "note": "Receipt verified"},
    )
    assert review.status_code == 200
    assert review.json()["status"] == ReimbursementStatus.APPROVED.value

    paid = client.post(f"/admin/reimbursements/{reimbursement_id}/paid")
    assert paid.status_code == 200
    assert paid.json()["status"] == ReimbursementStatus.PAID.value
    assert client.post(f"/admin/reimbursements/{reimbursement_id}/paid").status_code == 409

    with Session(engine) as db:
        assert db.query(TravelReimbursement).one().status == ReimbursementStatus.PAID.value
        assert db.query(AuditLog).filter_by(entity_id=reimbursement_id).count() == 2
