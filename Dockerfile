FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251115-0000-SPLIT-DATA-v6.6.11
RUN echo "CACHE BUST: $CACHEBUST - Building v6.6.11 with SPLIT DATA support"
# v6.6.11: SPLIT DATA - Added text-to-columns example in prompt for splitting comma-separated data

LABEL version="6.6.11"
LABEL description="SheetGPT API v6.6.11 - ADDED: Text-to-columns split data support"

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
