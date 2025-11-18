FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251117-2320-MERGE-WITH-ORIGINAL-v7.2.4
RUN echo "CACHE BUST: $CACHEBUST - Building v7.2.4 - merge returns original+new columns"
# v7.2.4: Fix merge to return ALL columns (original + new), not just new column

LABEL version="7.2.4"
LABEL description="SheetGPT API v7.2.4 - Merge returns original columns + new column in same table"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251117-2320-v7.2.4-MERGE-WITH-ORIGINAL - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
