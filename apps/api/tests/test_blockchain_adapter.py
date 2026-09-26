from dataclasses import dataclass

import pytest

from app.blockchain.rewards import (
    MonadRewardSettlementProvider,
    RewardInput,
    Web3MonadRewardPoolGateway,
)


VALID_INPUT = RewardInput(
    event_id="0x" + "11" * 32,
    participant_id="0x" + "22" * 32,
    reason_id="0x" + "33" * 32,
    recipient="0x" + "44" * 20,
    amount_wei=10**18,
)


@dataclass
class FakeGateway:
    calls: list[RewardInput]

    def reward_participant(
        self,
        event_id: str,
        participant_id: str,
        reason_id: str,
        recipient: str,
        amount_wei: int,
    ) -> str:
        self.calls.append(RewardInput(event_id, participant_id, reason_id, recipient, amount_wei))
        return "0xtransaction"


def test_monad_provider_delegates_to_gateway_and_returns_chain_result() -> None:
    gateway = FakeGateway(calls=[])
    provider = MonadRewardSettlementProvider(gateway, chain_id=143)

    result = provider.send_reward(VALID_INPUT)

    assert result.tx_hash == "0xtransaction"
    assert result.chain_id == 143
    assert gateway.calls == [VALID_INPUT]


def test_monad_provider_rejects_invalid_opaque_identifiers() -> None:
    gateway = FakeGateway(calls=[])
    provider = MonadRewardSettlementProvider(gateway, chain_id=143)

    with pytest.raises(ValueError, match="event_id"):
        provider.send_reward(RewardInput(**{**VALID_INPUT.__dict__, "event_id": "event"}))

    assert gateway.calls == []


def test_monad_provider_rejects_zero_rewards_before_rpc_call() -> None:
    gateway = FakeGateway(calls=[])
    provider = MonadRewardSettlementProvider(gateway, chain_id=143)

    with pytest.raises(ValueError, match="amount_wei"):
        provider.send_reward(RewardInput(**{**VALID_INPUT.__dict__, "amount_wei": 0}))

    assert gateway.calls == []


def test_web3_gateway_validates_before_rpc_submission() -> None:
    gateway = Web3MonadRewardPoolGateway(
        rpc_url="http://127.0.0.1:18545",
        private_key="0x" + "11" * 32,
        contract_address="0x" + "22" * 20,
        chain_id=143,
    )

    with pytest.raises(ValueError, match="event_id"):
        gateway.reward_participant(
            "event",
            VALID_INPUT.participant_id,
            VALID_INPUT.reason_id,
            VALID_INPUT.recipient,
            VALID_INPUT.amount_wei,
        )
