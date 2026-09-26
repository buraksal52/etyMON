FROM python:3.12-slim

WORKDIR /app

COPY apps/api/pyproject.toml ./
COPY apps/api/requirements.txt ./
COPY apps/api/app ./app
COPY apps/api/alembic.ini ./alembic.ini
COPY apps/api/alembic ./alembic
COPY scripts/create_admin.py ./scripts/create_admin.py

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
