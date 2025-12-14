FROM python:3.11-slim

# ============ FORCE FULL REBUILD ============
# Change this timestamp to bust ALL cache layers
ENV FORCE_REBUILD="2025-12-14-22:45:00-v10.2.0-SMART-FORECASTING-TRANSPARENCY"
RUN echo "=== FULL REBUILD: $FORCE_REBUILD ===" && date

LABEL version="10.1.1"
LABEL description="SheetGPT API v10.1.1 - VLOOKUP append column instead of overwrite"

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
