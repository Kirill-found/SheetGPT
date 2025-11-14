FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251114-1658-v6.6.7-RADICAL-FIX
RUN echo "CACHE BUST: $CACHEBUST - Building v6.6.7 with result pre-initialization"

LABEL version="6.6.7"
LABEL description="SheetGPT API v6.6.7 - RADICAL FIX: Pre-initialize variables before exec()"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
RUN echo "Installing v6.6.7 - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
