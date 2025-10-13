# ApplyLens API

FastAPI backend for ApplyLens job inbox application.

## Development

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -U pip
pip install .
uvicorn app.main:app --reload --port 8000
```text

## Seed Data

```bash
python app/seeds/seed_emails.py
```text

## Alembic Migrations

```bash
alembic upgrade head
```text
