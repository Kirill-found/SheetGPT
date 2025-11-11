FROM python:3.11-slim

# FORCE REBUILD - Break Railway cache
ARG BUILD_DATE=2025-11-11-19-20-v5.0.1-STRUCTURED-DATA
LABEL build_date=$BUILD_DATE
LABEL version="5.0.1-STRUCTURED-DATA"
LABEL model="gpt-4o"
LABEL rebuild="production-2025-11-11-19-20-ADD-STRUCTURED-DATA-FOR-TABLE-CREATION"

WORKDIR /app

# Copy backend files
COPY backend/requirements.txt backend/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# FORCE COPY backend - Break cache to get latest files with structured_data
# Updated: 2025-11-11-19-50 - structured_data feature
COPY backend backend

# Set working directory to backend
WORKDIR /app/backend

# Expose port (Railway will set PORT env variable)
EXPOSE 8000

# Start the application (use exec form with sh to support env variables)
# UPDATED: Use main.py (not main_simple.py) to enable conversation history + all features
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
