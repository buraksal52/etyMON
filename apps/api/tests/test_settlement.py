from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.blockchain.rewards import RewardInput, SettlementResult
from app.blockchain.settlement import RewardSettlementService, SettlementTransitionError
from app.db.models import AuditLog, Base, Event, Participant, RewardSettlement, SettlementStatus


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[RewardInput] = []
        self.fail = False

    def send_reward(self, input: RewardInput) -> SettlementResult:
        self.calls.append(input)
        if self.fail:
            raise RuntimeError("RPC unavailable")
        return SettlementResult(tx_hash="0xtx", chain_id=143)


def make_settlement_db() -> tuple[Session, str, str]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    now = datetime.now(timezone.utc)
    event = Event(
        name="Settlement Event",
        slug="settlement-event",
        timezone="event-local",
        state="ENDED",
        task_deadline_at=now,
    )
    participant = Participant(email="settlement@example.com", display_name="Settler")
    db.add_all([event, participant])
    db.commit()
    return db, event.id, participant.id


VALID_REWARD = RewardInput(
    event_id="0x" + "11" * 32,
    participant_id="0x" + "22" * 32,
    reason_id="0x" + "33" * 32,
    recipient="0x" + "44" * 20,
    amount_wei=100,
)


def test_settlement_lifecycle_is_durable_and_idempotent() -> None:
    db, event_id, participant_id = make_settlement_db()
    provider = FakeProvider()
    service = RewardSettlementService(provider)
    settlement = service.create_pending(
        db,
        event_id=event_id,
        participant_id=participant_id,
        assignment_id="assignment-1",
        amount=Decimal("1.00"),
        currency_or_token="MON",
    )
    duplicate = service.create_pending(
        db,
        event_id=event_id,
        participant_id=participant_id,
        assignment_id="assignment-1",
        amount=Decimal("1.00"),
        currency_or_token="MON",
    )
    assert duplicate.id == settlement.id

    submitted = service.submit(db, settlement.id, VALID_REWARD)
    assert submitted.status == SettlementStatus.SUBMITTED.value
    assert submitted.tx_hash == "0xtx"
    assert len(provider.calls) == 1

    idempotent_submit = service.submit(db, settlement.id, VALID_REWARD)
    assert idempotent_submit.status == SettlementStatus.SUBMITTED.value
    assert len(provider.calls) == 1

    confirmed = service.confirm(db, settlement.id)
    assert confirmed.status == SettlementStatus.CONFIRMED.value
    assert confirmed.confirmed_at is not None
    assert len(db.query(AuditLog).filter_by(entity_id=settlement.id).all()) == 3


def test_failed_settlement_can_retry_and_confirm() -> None:
    db, event_id, participant_id = make_settlement_db()
    provider = FakeProvider()
    provider.fail = True
    service = RewardSettlementService(provider)
    settlement = service.create_pending(
        db,
        event_id=event_id,
        participant_id=participant_id,
        amount=Decimal("2.00"),
        currency_or_token="MON",
    )

    with pytest.raises(RuntimeError, match="RPC unavailable"):
        service.submit(db, settlement.id, VALID_REWARD)
    assert db.get(RewardSettlement, settlement.id).status == SettlementStatus.FAILED.value

    provider.fail = False
    retried = service.retry(db, settlement.id, VALID_REWARD)
    assert retried.status == SettlementStatus.SUBMITTED.value
    assert len(provider.calls) == 2
    service.confirm(db, settlement.id)


def test_invalid_transition_is_rejected() -> None:
    db, event_id, participant_id = make_settlement_db()
    service = RewardSettlementService(FakeProvider())
    settlement = service.create_pending(
        db,
        event_id=event_id,
        participant_id=participant_id,
        amount=Decimal("1.00"),
        currency_or_token="MON",
    )

    with pytest.raises(SettlementTransitionError, match="confirmed"):
        service.confirm(db, settlement.id)
