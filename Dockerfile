FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251114-2130-DEBUG-LOGGING-v6.6.9
RUN echo "CACHE BUST: $CACHEBUST - Building v6.6.9 with DETAILED LOGGING to diagnose error"
# v6.6.9: DEBUG LOGGING - Added trace points to find where exception occurs

LABEL version="6.6.9"
LABEL description="SheetGPT API v6.6.9 - DEBUG: Detailed logging to trace execution flow"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251114-2130-v6.6.9-DEBUG-LOGGING - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
