# Platform

Platform is a mobile-first hackathon participation platform for Monad events.

## Phase 0 local setup

Prerequisites: Node.js 24+, Python 3.12+, and Docker.

```bash
npm install
docker compose up -d postgres
python3 -m venv apps/api/.venv
source apps/api/.venv/bin/activate
pip install -r apps/api/requirements.txt
./scripts/migrate.sh
python apps/api/seed.py
```

Start the API:

```bash
uvicorn app.main:app --app-dir apps/api --reload --port 8000
```

Start the frontend in another terminal:

```bash
npm run dev:web
```

Health check: `http://localhost:8000/health`.

The Next.js app is intended for Vercel. The FastAPI app and PostgreSQL run on
Railway in deployed environments. Railway runs the Alembic migration as a
pre-deploy command. Phase 1 seed data is available with:

```bash
DATABASE_URL=postgresql+psycopg://platform:platform@localhost:5432/platform \
  apps/api/.venv/bin/python apps/api/seed.py
```

Without a `.env` file, development uses the private local filesystem provider
under `storage-data/` for proof and receipt uploads. Production must set
`STORAGE_PROVIDER=railway` and the Railway Storage Bucket credentials from
`.env.example`.

Authentication and the event flows are implemented in later phases described
in `docs/`.

Development organizer credentials:

```text
email: organizer@example.com
password: phase3-demo-password
```

These credentials are for local seed data only and must not be used in
production.

## Admin routes

After signing in, the organizer dashboard is available at `/admin`. It
supports event creation/configuration, publishing and event controls,
participant CSV import, task management, proof review, leaderboard review,
and travel reimbursement review.

Participant progress and travel reimbursement pages are available under the
event routes with the participant `eventId` query parameter:

```text
/e/:slug/progress?eventId=...
/e/:slug/reimbursement?eventId=...
```

## RewardPool contract

The Monad-compatible native-token contract lives in
`packages/contracts`. Run its local tests with:

```bash
forge test --root packages/contracts
```

Deployment requires the documented `MONAD_RPC_URL` and
`REWARD_SIGNER_PRIVATE_KEY` values:

```bash
forge script packages/contracts/script/DeployRewardPool.s.sol:DeployRewardPool \
  --rpc-url "$MONAD_RPC_URL" \
  --private-key "$REWARD_SIGNER_PRIVATE_KEY" \
  --broadcast
```

The backend settlement lifecycle is tested with a mock provider and is kept
separate from participant scoring. Configure a real Monad gateway before
enabling production settlement.
