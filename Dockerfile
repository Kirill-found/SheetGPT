FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251118-0210-EMPTY-DATA-FIX-v7.3.1
RUN echo "CACHE BUST: $CACHEBUST - Building v7.3.1 - Fix empty data detection for frontend"
# v7.3.1: Improved empty data detection - handles [[]], [[], []], etc. from frontend

LABEL version="7.3.1"
LABEL description="SheetGPT API v7.3.1 - Improved empty data detection for AI table generation"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251118-0210-v7.3.1-EMPTY-DATA-FIX - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
