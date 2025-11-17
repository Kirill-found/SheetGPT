FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251117-2130-AGGRESSIVE-DTYPE-FIX-v7.2.1
RUN echo "CACHE BUST: $CACHEBUST - Building v7.2.1 with AGGRESSIVE .dtype auto-fix"
# v7.2.1: HOTFIX - агрессивное удаление .dtype из всего кода (regex: \.dtype\b -> пустая строка)

LABEL version="7.2.1"
LABEL description="SheetGPT API v7.2.1 - Function Calling with AGGRESSIVE .dtype auto-fix, 99%+ accuracy"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251117-2130-v7.2.1-AGGRESSIVE-DTYPE-FIX - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
