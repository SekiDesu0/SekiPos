FROM python:3.11-slim

# Install system dependencies for eventlet/production networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY app.py .
COPY templates/ ./templates/
# Copy static folder, ensuring cache subfolder exists
COPY static/ ./static/
RUN mkdir -p /app/static/cache

# Expose the port Flask is running on
EXPOSE 5000

# Set environment variables for Flask
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]