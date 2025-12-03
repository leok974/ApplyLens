FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

COPY . .

# Optional: Copy ML model artifacts if deploying ml_shadow or ml_live
# Uncomment these lines and build the model first using:
#   python -m scripts.train_email_classifier
# Then place model files in models/ directory before docker build
# COPY models/email_classifier_v1.joblib /app/models/email_classifier_v1.joblib
# COPY models/email_vectorizer_v1.joblib /app/models/email_vectorizer_v1.joblib

# Use environment variable for port, default to 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT:-8000}
