FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251115-0130-SPLIT-DATA-FIX-v6.6.12
RUN echo "CACHE BUST: $CACHEBUST - Building v6.6.12 with SPLIT DATA FIX"
# v6.6.12: SPLIT DATA FIX - Returns DataFrame as structured_data for Google Sheets

LABEL version="6.6.12"
LABEL description="SheetGPT API v6.6.12 - FIX: Split data now returned as structured_data"

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
