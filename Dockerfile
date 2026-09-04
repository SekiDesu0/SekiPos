FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p /app/db /app/static/cache

# Expose port
EXPOSE 5000

# Run with unbuffered output
ENV PYTHONUNBUFFERED=1

# Default timezone (Chile). Python code pins America/Santiago via zoneinfo,
# this also covers any OS-local time usage such as request logs.
ENV TZ=America/Santiago

CMD ["python", "app.py"]