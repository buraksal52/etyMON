#!/usr/bin/env sh
set -eu

exec apps/api/.venv/bin/alembic -c apps/api/alembic.ini upgrade head
