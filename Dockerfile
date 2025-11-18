FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251118-0102-FORMULA-GENERATION-v7.2.5
RUN echo "CACHE BUST: $CACHEBUST - Building v7.2.5 - Add Google Sheets formula for merge operations"
# v7.2.5: Add formula field to response for merge operations (e.g., =A2&" "&B2&" "&C2)

LABEL version="7.2.5"
LABEL description="SheetGPT API v7.2.5 - Returns Google Sheets formula for merge operations"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251118-0102-v7.2.5-FORMULA-GENERATION - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
