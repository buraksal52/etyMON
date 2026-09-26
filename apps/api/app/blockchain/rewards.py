from dataclasses import dataclass
from typing import Protocol

from web3 import Web3

from app.settings import settings


REWARD_POOL_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "eventId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "participantId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "reasonId", "type": "bytes32"},
            {"internalType": "address payable", "name": "recipient", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "rewardParticipant",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


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


class Web3MonadRewardPoolGateway:
    """Signs and submits native-token rewards to the deployed RewardPool."""

    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        contract_address: str,
        chain_id: int,
    ) -> None:
        if not rpc_url or not private_key or not contract_address:
            raise ValueError("Monad RPC, signer key, and contract address are required")
        self.chain_id = chain_id
        self.web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
        self.account = self.web3.eth.account.from_key(private_key)
        self.contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(contract_address),
            abi=REWARD_POOL_ABI,
        )

    def reward_participant(
        self,
        event_id: str,
        participant_id: str,
        reason_id: str,
        recipient: str,
        amount_wei: int,
    ) -> str:
        validate_reward_input(
            RewardInput(
                event_id=event_id,
                participant_id=participant_id,
                reason_id=reason_id,
                recipient=recipient,
                amount_wei=amount_wei,
            )
        )
        transaction = self.contract.functions.rewardParticipant(
            self.web3.to_bytes(hexstr=event_id),
            self.web3.to_bytes(hexstr=participant_id),
            self.web3.to_bytes(hexstr=reason_id),
            self.web3.to_checksum_address(recipient),
            amount_wei,
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": self.web3.eth.get_transaction_count(self.account.address, "pending"),
                "chainId": self.chain_id,
                "value": 0,
                "gasPrice": self.web3.eth.gas_price,
            }
        )
        transaction["gas"] = self.web3.eth.estimate_gas(transaction)
        signed = self.account.sign_transaction(transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        return self.web3.to_hex(tx_hash)


def create_monad_reward_provider() -> "MonadRewardSettlementProvider":
    if settings.monad_chain_id is None:
        raise RuntimeError("MONAD_CHAIN_ID is not configured")
    gateway = Web3MonadRewardPoolGateway(
        rpc_url=settings.monad_rpc_url,
        private_key=settings.reward_signer_private_key,
        contract_address=settings.reward_pool_contract_address,
        chain_id=settings.monad_chain_id,
    )
    return MonadRewardSettlementProvider(gateway, chain_id=settings.monad_chain_id)


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
