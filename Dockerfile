FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251117-2245-DYNAMIC-HIGHLIGHT-FIX-v7.2.2
RUN echo "CACHE BUST: $CACHEBUST - Building v7.2.2 with DYNAMIC highlight rows"
# v7.2.2: Fix hardcoded highlight_rows [8,5,3] -> dynamic extraction from AI result

LABEL version="7.2.2"
LABEL description="SheetGPT API v7.2.2 - Dynamic highlight extraction, fixes top-N highlighting bugs"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251117-2245-v7.2.2-DYNAMIC-HIGHLIGHT-FIX - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
