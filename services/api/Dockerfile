FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

COPY . .

# Use environment variable for port, default to 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT:-8000}
