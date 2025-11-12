FROM python:3.11-slim

LABEL version="6.2.8"
LABEL description="SheetGPT API with custom_context support"

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ .

# Expose port
EXPOSE 8080

# Run app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
