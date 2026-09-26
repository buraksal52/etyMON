# Platform

Platform is a mobile-first hackathon participation platform for Monad events.

## Architecture

```text
Vercel (Next.js participant/admin web app)
                  |
                  v
Railway (FastAPI API) ---- Railway PostgreSQL
                  |
                  +---- Railway Storage Bucket (S3-compatible proofs/receipts)
                  |
                  +---- Monad RewardPool (optional reward settlement)
```

The browser calls FastAPI through `NEXT_PUBLIC_API_URL`. FastAPI owns
authentication, event state, task assignment, proof and receipt uploads,
organizer review, scoring, leaderboard data, and the optional Monad settlement
adapter.

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

# Create a real local organizer; the command prompts for a password.
python scripts/create_admin.py --email admin@example.com --name "Event Admin"
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

For a local UI demo without Docker/PostgreSQL, install the Python requirements
above, then run `bash scripts/dev-api.sh` alongside `npm run dev:web`.
This creates a persistent SQLite demo database in the ignored `storage-data/`
directory and seeds the Monad Hackathon event. Enter `admin123` on `/room`,
then use `participant1@example.com` (through `participant10@example.com`) to
join. This helper is only for local development; deployed environments use
PostgreSQL and migrations.

The Next.js app is intended for Vercel. The FastAPI app and PostgreSQL run on
Railway in deployed environments. Railway runs the Alembic migration as a
pre-deploy command. The seed command only reports current database counts; it
does not create demo events, participants, tasks, or organizer credentials.

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

Participants enter through the QR URL `/e/:slug` or by typing the event code,
which is the event slug. Both methods create the participant record on first
join, then place the participant in the waiting queue. The organizer starts
the event after participants reach the waiting screen.

State-changing browser requests are checked against the configured allowed
origins. Login and participant-join endpoints also have an in-memory MVP rate
limit; for multiple Railway API instances, replace it with a shared Redis- or
database-backed limiter.

## Environment variables

Copy `.env.example` for local development. In production configure at least:

- FastAPI: `APP_ENV`, `APP_URL`, `ALLOWED_ORIGINS`, `SESSION_SECRET`, and
  `DATABASE_URL`.
- Vercel: `NEXT_PUBLIC_API_URL=/api` and `API_PROXY_TARGET` set to the public
  Railway API URL. Next.js proxies `/api/*` to FastAPI so session cookies stay
  first-party (Safari and other browsers block cross-site API cookies).
- Railway Storage: `STORAGE_PROVIDER=railway`, `STORAGE_BUCKET`,
  `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, and `STORAGE_SECRET_KEY`.
- Rewards, only when enabled: `MONAD_RPC_URL`, `MONAD_CHAIN_ID`,
  `REWARD_POOL_CONTRACT_ADDRESS`, and `REWARD_SIGNER_PRIVATE_KEY`.

Do not commit real secrets. `ALLOWED_ORIGINS` must include the Vercel production
origin (and any intentionally used preview origin).

## Deployment

### Vercel frontend

1. Import the repository into Vercel and select the `apps/web` workspace, or
   keep the repository root and use the committed `vercel.json`.
2. Set `NEXT_PUBLIC_API_URL=/api` and `API_PROXY_TARGET` to the deployed
   Railway API URL.
3. Deploy. The configured build command is `npm run build`.

### Railway API and database

1. Create a Railway PostgreSQL service and an API service from this repository.
2. Keep the repository root as the service root so `railway.toml` and the
   `apps/api/Dockerfile` are used.
3. Set the FastAPI, database, storage, and allowed-origin variables listed
   above. Railway supplies `PORT`; the committed start command binds FastAPI
   to it.
4. Deploy. `railway.toml` runs `alembic -c alembic.ini upgrade head` before
   starting the API and exposes `/health` for the health check.
5. Create the first organizer with `scripts/create_admin.py`, then create the
   event and task pool from the admin flow. No demo data is inserted.

### Demo walkthrough

1. Sign in at `/admin`, create an event, add its task pool, and publish it.
2. Use the event dashboard's QR code or event code to join from `/e/<event-slug>`
   with a participant email and verify the waiting screen.
3. Watch the waiting count update, then start the event and verify that the
   participant gets a randomly assigned task.
4. Submit an allowed image proof, approve it from the submissions screen, and
   verify the score and leaderboard.
5. Request the next task, upload a travel receipt, approve it, and mark it
   paid from the reimbursement screen.
6. End the event and verify that a new task request is rejected.

## Admin routes

After signing in, the organizer dashboard is available at `/admin`. It
supports event creation/configuration, publishing and event controls,
live participant queue, task management, proof review, leaderboard review,
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
