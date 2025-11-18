FROM python:3.11-slim

# CRITICAL: Change this on EVERY deployment to force rebuild
ARG CACHEBUST=20251118-0145-AI-TABLE-GENERATION-v7.3.0
RUN echo "CACHE BUST: $CACHEBUST - Building v7.3.0 - AI generates tables from knowledge"
# v7.3.0: Generate tables from AI knowledge without source data (e.g., "create table with European countries")

LABEL version="7.3.0"
LABEL description="SheetGPT API v7.3.0 - AI generates tables from knowledge base"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: Force copy layer to rebuild
# CRITICAL: This RUN must be AFTER requirements but BEFORE COPY to break Docker cache
RUN echo "CACHEBUST: 20251118-0145-v7.3.0-AI-TABLE-GENERATION - $(date)"

# Copy application
COPY backend/ .

# Verify main.py exists and show version
RUN cat app/main.py | grep "version=" | head -3

# Expose port
EXPOSE 8080

# Run app with PORT from environment (Railway sets this)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
