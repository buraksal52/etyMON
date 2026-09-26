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

Authentication and the event flows are implemented in later phases described
in `docs/`.

Development organizer credentials:

```text
email: organizer@example.com
password: phase3-demo-password
```

These credentials are for local seed data only and must not be used in
production.
