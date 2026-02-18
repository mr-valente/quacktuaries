FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY docs/ ./docs/

# Create data directory
RUN mkdir -p /data

# Environment defaults
ENV SESSION_SECRET=change-me-too
ENV DB_PATH=/data/app.db
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
