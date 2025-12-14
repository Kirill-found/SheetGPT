FROM python:3.11-slim

# ============ FORCE FULL REBUILD ============
# Change this timestamp to bust ALL cache layers
ENV FORCE_REBUILD="2025-12-14-20:50:00-v10.1.0-VLOOKUP-SMARTGPT"
RUN echo "=== FULL REBUILD: $FORCE_REBUILD ===" && date

LABEL version="9.3.0"
LABEL description="SheetGPT API v9.3.0 - Privacy Policy for Chrome Web Store"

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
