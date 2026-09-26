#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Disposable local development data; production continues to use PostgreSQL.
mkdir -p storage-data
export DATABASE_URL="sqlite:///$PWD/storage-data/development.db"
export APP_ENV=development
export ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
export PYTHONPATH="$PWD/apps/api"

apps/api/.venv/bin/python - <<'PY'
from app.db.models import Base
from app.db.session import engine, SessionLocal
from app.db.seed import seed_development_data

Base.metadata.create_all(engine)
with SessionLocal() as db:
    seed_development_data(db)
PY

exec apps/api/.venv/bin/uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
