# python:3.12-slim -- the dev venv in this repo runs 3.14 (whatever the host
# provides), but the app only requires 3.12+ typing/syntax, and 3.12-slim is
# a smaller, more widely cached image for a container build.
FROM python:3.12-slim

WORKDIR /app

# Only copy the manifest first so dependency installation is cached across
# rebuilds that don't touch requirements.txt.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# SEED_ON_START=true runs the deterministic seed generator before the API
# starts (docker-compose.yml sets this for a one-command demo). The seed
# script itself is idempotent without --reset -- it no-ops if the database
# already has employees -- so this is safe to leave on across restarts of a
# container whose Postgres volume persists.
CMD ["sh", "-c", "if [ \"$SEED_ON_START\" = \"true\" ]; then python -m app.seed.seed --count \"${SEED_COUNT:-10000}\"; fi && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
