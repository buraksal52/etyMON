from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.blockchain.rewards import RewardInput, RewardSettlementProvider
from app.db.models import AuditLog, RewardSettlement, SettlementStatus


class SettlementTransitionError(ValueError):
    pass


class RewardSettlementService:
    """Owns the durable lifecycle around an injected reward provider."""

    def __init__(self, provider: RewardSettlementProvider) -> None:
        self.provider = provider

    def create_pending(
        self,
        db: Session,
        *,
        event_id: str,
        participant_id: str,
        amount: Decimal,
        currency_or_token: str,
        assignment_id: str | None = None,
    ) -> RewardSettlement:
        if amount <= 0:
            raise ValueError("Settlement amount must be greater than zero")
        if assignment_id is not None:
            existing = (
                db.query(RewardSettlement)
                .filter_by(
                    event_id=event_id,
                    participant_id=participant_id,
                    assignment_id=assignment_id,
                )
                .one_or_none()
            )
            if existing is not None:
                return existing

        settlement = RewardSettlement(
            event_id=event_id,
            participant_id=participant_id,
            assignment_id=assignment_id,
            amount=amount,
            currency_or_token=currency_or_token,
            status=SettlementStatus.PENDING.value,
        )
        db.add(settlement)
        db.flush()
        self._audit(db, settlement, "REWARD_SETTLEMENT_CREATED")
        db.commit()
        db.refresh(settlement)
        return settlement

    def submit(
        self,
        db: Session,
        settlement_id: str,
        reward_input: RewardInput,
    ) -> RewardSettlement:
        settlement = self._get_locked(db, settlement_id)
        if settlement.status in {
            SettlementStatus.SUBMITTED.value,
            SettlementStatus.CONFIRMED.value,
        }:
            db.rollback()
            return settlement
        if settlement.status not in {
            SettlementStatus.PENDING.value,
            SettlementStatus.FAILED.value,
        }:
            raise SettlementTransitionError(
                f"Settlement cannot be submitted from {settlement.status}"
            )

        try:
            result = self.provider.send_reward(reward_input)
        except Exception as exc:
            settlement.status = SettlementStatus.FAILED.value
            settlement.last_error = str(exc)[:500]
            self._audit(
                db,
                settlement,
                "REWARD_SETTLEMENT_FAILED",
                {"error": str(exc)[:500]},
            )
            db.commit()
            raise

        settlement.status = SettlementStatus.SUBMITTED.value
        settlement.tx_hash = result.tx_hash
        settlement.chain_id = result.chain_id
        settlement.last_error = None
        self._audit(
            db,
            settlement,
            "REWARD_SETTLEMENT_SUBMITTED",
            {"txHash": result.tx_hash, "chainId": result.chain_id},
        )
        db.commit()
        db.refresh(settlement)
        return settlement

    def confirm(self, db: Session, settlement_id: str) -> RewardSettlement:
        settlement = self._get_locked(db, settlement_id)
        if settlement.status == SettlementStatus.CONFIRMED.value:
            db.rollback()
            return settlement
        if settlement.status != SettlementStatus.SUBMITTED.value:
            raise SettlementTransitionError(
                f"Settlement cannot be confirmed from {settlement.status}"
            )
        settlement.status = SettlementStatus.CONFIRMED.value
        settlement.confirmed_at = datetime.now(timezone.utc)
        self._audit(db, settlement, "REWARD_SETTLEMENT_CONFIRMED")
        db.commit()
        db.refresh(settlement)
        return settlement

    def mark_reverted(self, db: Session, settlement_id: str) -> RewardSettlement:
        """A submitted transaction was mined but reverted, so nothing was paid."""
        settlement = self._get_locked(db, settlement_id)
        if settlement.status != SettlementStatus.SUBMITTED.value:
            raise SettlementTransitionError(
                f"Settlement cannot be marked reverted from {settlement.status}"
            )
        settlement.status = SettlementStatus.FAILED.value
        settlement.last_error = "Transaction reverted on chain"
        self._audit(
            db,
            settlement,
            "REWARD_SETTLEMENT_REVERTED",
            {"txHash": settlement.tx_hash},
        )
        db.commit()
        db.refresh(settlement)
        return settlement

    @staticmethod
    def hold(db: Session, settlement_id: str, reason: str) -> RewardSettlement:
        """Record why a pending settlement cannot be submitted yet."""
        settlement = RewardSettlementService._get_locked(db, settlement_id)
        settlement.last_error = reason[:500]
        db.commit()
        db.refresh(settlement)
        return settlement

    def retry(
        self,
        db: Session,
        settlement_id: str,
        reward_input: RewardInput,
    ) -> RewardSettlement:
        return self.submit(db, settlement_id, reward_input)

    @staticmethod
    def _get_locked(db: Session, settlement_id: str) -> RewardSettlement:
        settlement = (
            db.query(RewardSettlement).filter_by(id=settlement_id).with_for_update().one_or_none()
        )
        if settlement is None:
            raise LookupError("Reward settlement not found")
        return settlement

    @staticmethod
    def _audit(
        db: Session,
        settlement: RewardSettlement,
        action: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        db.add(
            AuditLog(
                event_id=settlement.event_id,
                actor_type="SYSTEM",
                actor_id=None,
                action=action,
                entity_type="REWARD_SETTLEMENT",
                entity_id=settlement.id,
                metadata_json=metadata,
            )
        )
