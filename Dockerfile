FROM python:3.11-slim

# ============ FORCE FULL REBUILD ============
# Change this timestamp to bust ALL cache layers
ENV FORCE_REBUILD="2025-12-02-11:30:00-v9.2.3-MEDIA-FIX"
RUN echo "=== FULL REBUILD: $FORCE_REBUILD ===" && date

LABEL version="9.2.3"
LABEL description="SheetGPT API v9.2.3 - Fixed media forwarding"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ .

# Verify version
RUN echo "=== Version check ===" && grep "version=" app/main.py | head -1

EXPOSE 8080

CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
