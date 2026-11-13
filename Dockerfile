# ==============================================================================
# STATE AUDIT AI — Production Backend Dockerfile (Root Context)
# Base Image: Python 3.11 Slim (Debian Linux)
# ==============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libglib2.0-0 \
    libgl1 \
    libfreetype6 \
    libjpeg62-turbo \
    zlib1g \
    libharfbuzz0b \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements from backend/
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code, alembic configurations, and migrations
COPY backend/ .

# Ensure startup entrypoint script has execution permissions
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8000}/api/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
