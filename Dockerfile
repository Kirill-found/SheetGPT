FROM python:3.11-slim

# FORCE REBUILD - Break Railway cache
ARG BUILD_DATE=2025-11-11-22-20-v5.0.2-FORCE-REBUILD
LABEL build_date=$BUILD_DATE
LABEL version="5.0.2-FORCE-REBUILD"
LABEL model="gpt-4o"
LABEL rebuild="production-2025-11-11-22-20-FORCE-ALL-LAYERS-REBUILD"

WORKDIR /app

# Copy backend files
COPY backend/requirements.txt backend/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# FORCE INVALIDATE CACHE - Use ARG to force rebuild on every commit
ARG CACHE_BUST=2025-11-11-22-20-ABSOLUTE-FINAL-FIX
RUN echo "Cache bust: $CACHE_BUST"

# Copy backend - will be forced to re-execute due to ARG change above
COPY backend backend

# FORCE REBUILD OF COPY LAYER - timestamp to invalidate cache
RUN echo "REBUILD-2025-11-11-22-42" > /app/backend/.rebuild_marker

# CRITICAL: Clear all Python cache files to force module reload
RUN find /app/backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
RUN find /app/backend -type f -name '*.pyc' -delete 2>/dev/null || true
RUN find /app/backend -type f -name '*.pyo' -delete 2>/dev/null || true

# Set working directory to backend
WORKDIR /app/backend

# Expose port (Railway will set PORT env variable)
EXPOSE 8000

# Start the application (use exec form with sh to support env variables)
# UPDATED: Use main.py (not main_simple.py) to enable conversation history + all features
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
