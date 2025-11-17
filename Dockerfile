FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251117-2310-MERGE-SUPPORT-v7.2.3
RUN echo "CACHE BUST: $CACHEBUST - Building v7.2.3 with merge/concat support"
# v7.2.3: Add structured_data support for merge/concat operations (объедини ФИО, создай колонку)

LABEL version="7.2.3"
LABEL description="SheetGPT API v7.2.3 - Returns structured_data for merge/concat operations"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251117-2310-v7.2.3-MERGE-SUPPORT - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
