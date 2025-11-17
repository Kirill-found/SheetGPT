FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251117-2100-CODE-EXECUTOR-FIX-v7.2.0
RUN echo "CACHE BUST: $CACHEBUST - Building v7.2.0 with SMART COLUMN MATCHING"
# v7.2.0: Smart column matching + auto string number parsing (e.g. "р.857 765" -> 857765)

LABEL version="7.2.0"
LABEL description="SheetGPT API v7.2.0 - Function Calling with smart column matching, auto string number parsing, 95%+ accuracy"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251117-2100-v7.2.0-CODE-EXECUTOR-FIX - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
