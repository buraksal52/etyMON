"""Connects approved task rewards to the Monad settlement lifecycle."""

import logging
import time
from collections.abc import Callable, Iterable
from decimal import Decimal

from sqlalchemy.orm import Session
from web3 import Web3

from app.blockchain.rewards import (
    RewardInput,
    RewardSettlementProvider,
    create_monad_reward_provider,
)
from app.blockchain.settlement import RewardSettlementService
from app.db.models import Participant, RewardSettlement, SettlementStatus, Task
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

REWARD_TOKEN = "MON"
WEI_PER_TOKEN = Decimal(10) ** 18
CONFIRMATION_POLL_SECONDS = 2.0
CONFIRMATION_TIMEOUT_SECONDS = 60.0
MISSING_WALLET_REASON = "Participant has not added a wallet address"

ProviderFactory = Callable[[], RewardSettlementProvider]
SessionFactory = Callable[[], Session]


def get_reward_provider_factory() -> ProviderFactory:
    return create_monad_reward_provider


def get_settlement_session_factory() -> SessionFactory:
    return SessionLocal


def normalize_wallet_address(value: str) -> str:
    value = value.strip()
    if not Web3.is_address(value):
        raise ValueError("Wallet address must be a valid EVM address")
    return Web3.to_checksum_address(value)


def _opaque_id(*parts: str) -> str:
    # Internal UUIDs only; participant email never reaches the chain.
    return Web3.to_hex(Web3.keccak(text=":".join(("etymon", *parts))))


def build_reward_input(settlement: RewardSettlement, recipient: str) -> RewardInput:
    if settlement.assignment_id is None:
        raise ValueError("Task reward settlement requires an assignment")
    return RewardInput(
        event_id=_opaque_id("event", settlement.event_id),
        participant_id=_opaque_id("participant", settlement.event_id, settlement.participant_id),
        reason_id=_opaque_id("assignment", settlement.assignment_id),
        recipient=recipient,
        amount_wei=int((Decimal(settlement.amount) * WEI_PER_TOKEN).to_integral_value()),
    )


def serialize_settlement(
    settlement: RewardSettlement, participant: Participant | None, task: Task | None
) -> dict[str, object]:
    return {
        "id": settlement.id,
        "status": settlement.status,
        "amount": str(settlement.amount),
        "token": settlement.currency_or_token,
        "txHash": settlement.tx_hash,
        "chainId": settlement.chain_id,
        "lastError": settlement.last_error,
        "createdAt": settlement.created_at,
        "confirmedAt": settlement.confirmed_at,
        "participant": (
            {
                "id": participant.id,
                "displayName": participant.display_name,
                "walletAddress": participant.wallet_address,
            }
            if participant is not None
            else None
        ),
        "task": {"id": task.id, "title": task.title} if task is not None else None,
    }


def load_provider(factory: ProviderFactory) -> tuple[RewardSettlementProvider | None, str | None]:
    try:
        return factory(), None
    except Exception as exc:
        return None, f"Monad rewards are not configured: {exc}"[:500]


def advance_settlement(
    db: Session,
    settlement_id: str,
    provider: RewardSettlementProvider | None,
    unavailable_reason: str | None = None,
) -> RewardSettlement:
    """Move a settlement one step forward: submit it, or refresh its chain status."""
    settlement = db.get(RewardSettlement, settlement_id)
    if settlement is None:
        raise LookupError("Reward settlement not found")
    if settlement.status == SettlementStatus.CONFIRMED.value:
        return settlement
    if provider is None:
        return RewardSettlementService.hold(
            db, settlement_id, unavailable_reason or "Monad rewards are not configured"
        )
    if settlement.status == SettlementStatus.SUBMITTED.value:
        return refresh_settlement(db, settlement, provider)

    participant = db.get(Participant, settlement.participant_id)
    if participant is None or not participant.wallet_address:
        return RewardSettlementService.hold(db, settlement_id, MISSING_WALLET_REASON)

    service = RewardSettlementService(provider)
    try:
        return service.submit(
            db, settlement_id, build_reward_input(settlement, participant.wallet_address)
        )
    except Exception:
        logger.exception("Reward settlement %s failed to submit", settlement_id)
        db.expire_all()
        return db.get(RewardSettlement, settlement_id)


def refresh_settlement(
    db: Session, settlement: RewardSettlement, provider: RewardSettlementProvider
) -> RewardSettlement:
    if settlement.status != SettlementStatus.SUBMITTED.value or not settlement.tx_hash:
        return settlement
    mined = provider.transaction_status(settlement.tx_hash)
    service = RewardSettlementService(provider)
    if mined is True:
        return service.confirm(db, settlement.id)
    if mined is False:
        return service.mark_reverted(db, settlement.id)
    return settlement


def process_settlements(
    settlement_ids: Iterable[str],
    session_factory: SessionFactory,
    provider_factory: ProviderFactory,
) -> None:
    """Background job: submit settlements, then wait briefly for confirmations."""
    settlement_ids = list(settlement_ids)
    if not settlement_ids:
        return
    provider, unavailable_reason = load_provider(provider_factory)
    with session_factory() as db:
        awaiting: list[str] = []
        for settlement_id in settlement_ids:
            try:
                settlement = advance_settlement(db, settlement_id, provider, unavailable_reason)
            except Exception:
                logger.exception("Reward settlement %s could not be processed", settlement_id)
                db.rollback()
                continue
            if settlement.status == SettlementStatus.SUBMITTED.value:
                awaiting.append(settlement_id)

        if provider is None:
            return
        deadline = time.monotonic() + CONFIRMATION_TIMEOUT_SECONDS
        while awaiting:
            still_awaiting = []
            for settlement_id in awaiting:
                try:
                    settlement = refresh_settlement(
                        db, db.get(RewardSettlement, settlement_id), provider
                    )
                except Exception:
                    logger.exception("Reward settlement %s status check failed", settlement_id)
                    db.rollback()
                    continue
                if settlement.status == SettlementStatus.SUBMITTED.value:
                    still_awaiting.append(settlement_id)
            awaiting = still_awaiting
            if not awaiting or time.monotonic() >= deadline:
                break
            time.sleep(CONFIRMATION_POLL_SECONDS)
