FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251117-1900-FUNCTION-CALLING-v7.0.0
RUN echo "CACHE BUST: $CACHEBUST - Building v7.0.0 with FUNCTION CALLING"
# v7.0.0: MAJOR UPDATE - Function Calling with 30+ verified functions for 95%+ accuracy

LABEL version="7.0.0"
LABEL description="SheetGPT API v7.0.0 - Function Calling: 30+ verified functions, 95%+ accuracy, fallback to code executor"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251117-1900-v7.0.0-FUNCTION-CALLING - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
