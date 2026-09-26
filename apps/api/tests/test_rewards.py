from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import SESSION_COOKIE, create_session_token, hash_password
from app.blockchain.processing import (
    MISSING_WALLET_REASON,
    get_reward_provider_factory,
    get_settlement_session_factory,
)
from app.blockchain.rewards import RewardInput, SettlementResult
from app.db.models import (
    AssignmentStatus,
    Base,
    Event,
    EventParticipant,
    EventState,
    Organizer,
    Participant,
    RewardSettlement,
    SettlementStatus,
    Submission,
    SubmissionStatus,
    Task,
    TaskAssignment,
)
from app.db.session import get_db
from app.main import app

WALLET = "0x" + "ab" * 20


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[RewardInput] = []
        self.fail = False
        self.mined: bool | None = True

    def send_reward(self, input: RewardInput) -> SettlementResult:
        self.calls.append(input)
        if self.fail:
            raise RuntimeError("RPC unavailable")
        return SettlementResult(tx_hash="0x" + "cd" * 32, chain_id=10143)

    def transaction_status(self, tx_hash: str) -> bool | None:
        return self.mined


class RewardHarness:
    def __init__(self, reward_amount: Decimal | None, wallet: str | None) -> None:
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.provider = FakeProvider()
        self.provider_available = True
        now = datetime.now(timezone.utc)
        with Session(self.engine) as db:
            event = Event(
                name="Reward Event",
                slug="reward-event",
                timezone="event-local",
                state=EventState.ACTIVE.value,
                task_deadline_at=now + timedelta(hours=1),
            )
            organizer = Organizer(
                email="rewards@example.com",
                name="Rewards",
                password_hash_or_auth_provider_id=hash_password("reward-secret"),
            )
            participant = Participant(
                email="earner@example.com", display_name="Earner", wallet_address=wallet
            )
            db.add_all([event, organizer, participant])
            db.flush()
            task = Task(
                event_id=event.id,
                title="Paid task",
                description="Do it",
                instructions="Do it",
                points=10,
                reward_amount=reward_amount,
                proof_type="URL",
            )
            db.add_all(
                [
                    EventParticipant(event_id=event.id, participant_id=participant.id, score=0),
                    task,
                ]
            )
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
            self.event_id = event.id
            self.participant_id = participant.id
            self.assignment_id = assignment.id
            self.submission_id = submission.id

        def override_db() -> Iterator[Session]:
            with Session(self.engine) as db:
                yield db

        def provider_factory() -> FakeProvider:
            if not self.provider_available:
                raise RuntimeError("MONAD_CHAIN_ID is not configured")
            return self.provider

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_settlement_session_factory] = lambda: (
            lambda: Session(self.engine)
        )
        app.dependency_overrides[get_reward_provider_factory] = lambda: provider_factory
        self.client = TestClient(app)
        login = self.client.post(
            "/admin/login", json={"email": "rewards@example.com", "password": "reward-secret"}
        )
        assert login.status_code == 200

    def approve(self) -> dict[str, object]:
        response = self.client.post(
            f"/admin/submissions/{self.submission_id}/review",
            json={"decision": "APPROVED", "note": ""},
        )
        assert response.status_code == 200
        return response.json()

    def as_participant(self) -> TestClient:
        self.client.cookies.set(
            SESSION_COOKIE, create_session_token(self.event_id, self.participant_id)
        )
        return self.client

    def settlement(self) -> RewardSettlement:
        with Session(self.engine) as db:
            return db.query(RewardSettlement).one()


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_approval_pays_task_reward_to_participant_wallet() -> None:
    harness = RewardHarness(Decimal("0.25"), WALLET)

    body = harness.approve()

    settlement = harness.settlement()
    assert body["scoreAwarded"] == 10
    assert body["rewardSettlementId"] == settlement.id
    assert settlement.status == SettlementStatus.CONFIRMED.value
    assert settlement.tx_hash == "0x" + "cd" * 32
    assert settlement.chain_id == 10143
    [call] = harness.provider.calls
    assert call.amount_wei == 25 * 10**16
    assert call.recipient == WALLET
    assert len(call.reason_id) == 66 and len(call.participant_id) == 66


def test_task_without_reward_creates_no_settlement() -> None:
    harness = RewardHarness(None, WALLET)

    body = harness.approve()

    assert body["rewardSettlementId"] is None
    with Session(harness.engine) as db:
        assert db.query(RewardSettlement).count() == 0
    assert harness.provider.calls == []


def test_reward_waits_for_wallet_then_pays_when_wallet_added() -> None:
    harness = RewardHarness(Decimal("1"), None)

    harness.approve()
    settlement = harness.settlement()
    assert settlement.status == SettlementStatus.PENDING.value
    assert settlement.last_error == MISSING_WALLET_REASON

    client = harness.as_participant()
    invalid = client.put(
        f"/events/{harness.event_id}/wallet", json={"walletAddress": "0x" + "z" * 40}
    )
    assert invalid.status_code == 422
    response = client.put(f"/events/{harness.event_id}/wallet", json={"walletAddress": WALLET})
    assert response.status_code == 200

    settlement = harness.settlement()
    assert settlement.status == SettlementStatus.CONFIRMED.value
    assert settlement.last_error is None
    assert client.get(f"/events/{harness.event_id}/me").json()["participant"]["walletAddress"]
    rewards = client.get(f"/events/{harness.event_id}/rewards").json()["rewards"]
    assert [(r["status"], r["amount"], r["task"]["title"]) for r in rewards] == [
        (SettlementStatus.CONFIRMED.value, "1.00000000", "Paid task")
    ]


def test_failed_submission_keeps_score_and_can_be_retried_by_admin() -> None:
    harness = RewardHarness(Decimal("0.5"), WALLET)
    harness.provider.fail = True

    body = harness.approve()

    assert body["scoreAwarded"] == 10
    settlement = harness.settlement()
    assert settlement.status == SettlementStatus.FAILED.value
    assert "RPC unavailable" in settlement.last_error
    with Session(harness.engine) as db:
        assert db.query(EventParticipant).one().score == 10

    listing = harness.client.get(f"/admin/events/{harness.event_id}/rewards").json()["rewards"]
    assert listing[0]["status"] == SettlementStatus.FAILED.value
    assert listing[0]["participant"]["walletAddress"] == WALLET

    harness.provider.fail = False
    retried = harness.client.post(f"/admin/rewards/{settlement.id}/retry")
    assert retried.status_code == 200
    assert retried.json()["reward"]["status"] == SettlementStatus.SUBMITTED.value

    confirmed = harness.client.post(f"/admin/rewards/{settlement.id}/retry")
    assert confirmed.json()["reward"]["status"] == SettlementStatus.CONFIRMED.value
    assert harness.client.post(f"/admin/rewards/{settlement.id}/retry").status_code == 409
    assert len(harness.provider.calls) == 2


def test_reverted_transaction_is_marked_failed() -> None:
    harness = RewardHarness(Decimal("0.5"), WALLET)
    harness.provider.mined = False

    harness.approve()

    settlement = harness.settlement()
    assert settlement.status == SettlementStatus.FAILED.value
    assert settlement.last_error == "Transaction reverted on chain"


def test_missing_monad_config_does_not_block_approval() -> None:
    harness = RewardHarness(Decimal("0.5"), WALLET)
    harness.provider_available = False

    body = harness.approve()

    assert body["scoreAwarded"] == 10
    settlement = harness.settlement()
    assert settlement.status == SettlementStatus.PENDING.value
    assert "not configured" in settlement.last_error
    assert harness.provider.calls == []


def test_organizer_can_set_task_reward_amount() -> None:
    harness = RewardHarness(None, WALLET)
    with Session(harness.engine) as db:
        db.query(Event).one().state = EventState.DRAFT.value
        db.commit()

    created = harness.client.post(
        f"/admin/events/{harness.event_id}/tasks",
        json={
            "title": "Reward task",
            "description": "d",
            "instructions": "i",
            "points": 5,
            "reward_amount": "0.1",
            "proof_type": "URL",
        },
    )
    assert created.status_code == 200
    task = created.json()["task"]
    assert task["rewardAmount"] == "0.10000000"
    assert task["rewardToken"] == "MON"

    updated = harness.client.patch(f"/admin/tasks/{task['id']}", json={"reward_amount": "2"})
    assert updated.status_code == 200
    assert updated.json()["task"]["rewardAmount"] == "2.00000000"
