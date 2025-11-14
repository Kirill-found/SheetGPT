FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251114-2035-v6.6.8-ALL-VERSIONS-FIXED
RUN echo "CACHE BUST: $CACHEBUST - Building v6.6.8 with WRAPPER for guaranteed variable initialization"

LABEL version="6.6.8"
LABEL description="SheetGPT API v6.6.8 - WRAPPER FIX: AI code wrapped in safe initializer"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251114-2035-v6.6.8-ALL-VERSIONS-FIXED - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
