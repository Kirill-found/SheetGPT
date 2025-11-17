FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251117-1730-BACKEND-FIX-v6.6.16
RUN echo "CACHE BUST: $CACHEBUST - Building v6.6.16 with BACKEND FIX"
# v6.6.16: BACKEND FIX - Simplify split - always use first row as headers to _generate_structured_data_if_needed() instead of converted list

LABEL version="6.6.16"
LABEL description="SheetGPT API v6.6.16 - FIX: Split operations now correctly generate structured_data with operation_type"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251117-1730-v6.6.16-BACKEND-FIX - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
