from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RewardInput:
    """Opaque, already-normalized input for one native-token reward."""

    event_id: str
    participant_id: str
    reason_id: str
    recipient: str
    amount_wei: int


@dataclass(frozen=True)
class SettlementResult:
    tx_hash: str
    chain_id: int


class RewardSettlementProvider(Protocol):
    def send_reward(self, input: RewardInput) -> SettlementResult: ...


class MonadRewardPoolGateway(Protocol):
    """Transport boundary for the deployed RewardPool contract.

    The concrete RPC/signing client is intentionally injected here so score
    approval and application tests do not depend on a live Monad node.
    """

    def reward_participant(
        self,
        event_id: str,
        participant_id: str,
        reason_id: str,
        recipient: str,
        amount_wei: int,
    ) -> str: ...


class MonadRewardSettlementProvider:
    """Monad implementation of the application reward provider boundary."""

    def __init__(self, gateway: MonadRewardPoolGateway, chain_id: int) -> None:
        self.gateway = gateway
        self.chain_id = chain_id

    def send_reward(self, input: RewardInput) -> SettlementResult:
        validate_reward_input(input)
        tx_hash = self.gateway.reward_participant(
            input.event_id,
            input.participant_id,
            input.reason_id,
            input.recipient,
            input.amount_wei,
        )
        return SettlementResult(tx_hash=tx_hash, chain_id=self.chain_id)


def validate_reward_input(input: RewardInput) -> None:
    for field_name in ("event_id", "participant_id", "reason_id"):
        value = getattr(input, field_name)
        if len(value) != 66 or not value.startswith("0x"):
            raise ValueError(f"{field_name} must be a 32-byte hex identifier")
        try:
            int(value[2:], 16)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a 32-byte hex identifier") from exc
    if len(input.recipient) != 42 or not input.recipient.startswith("0x"):
        raise ValueError("recipient must be an EVM address")
    try:
        int(input.recipient[2:], 16)
    except ValueError as exc:
        raise ValueError("recipient must be an EVM address") from exc
    if input.amount_wei <= 0:
        raise ValueError("amount_wei must be greater than zero")
