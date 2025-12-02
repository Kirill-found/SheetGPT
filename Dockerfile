FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251202-1015-SUPPORT-BOT-v9.2.0
RUN echo "CACHE BUST: $CACHEBUST - Building v9.2.0 - Support bot with payments"
# v9.2.0: Support bot with payment flow - handles [[]], [[], []], etc. from frontend

LABEL version="9.2.0"
LABEL description="SheetGPT API v9.2.0 - Support bot with payment flow"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251202-1015-v9.2.0-SUPPORT-BOT - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
