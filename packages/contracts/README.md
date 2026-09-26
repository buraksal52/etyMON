# Platform contracts

This package contains the Phase 12 Monad-compatible `RewardPool` contract.
It accepts native-token deposits, allows the owner or an authorized backend
account to pay a participant, and prevents a `reasonId` from being paid twice.

Run the contract tests from the repository root:

```bash
forge test --root packages/contracts
```

Deploy with Foundry after configuring the desired RPC and private key:

```bash
forge script packages/contracts/script/DeployRewardPool.s.sol:DeployRewardPool \
  --rpc-url "$MONAD_RPC_URL" \
  --private-key "$DEPLOYER_PRIVATE_KEY" \
  --broadcast
```

The deployed owner must explicitly authorize the backend account with
`setAuthorized` before backend reward settlement is enabled.
