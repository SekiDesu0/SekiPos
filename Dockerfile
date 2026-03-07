FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/
#COPY .env .

# Create the folder structure for the volume mounts
RUN mkdir -p /app/static/cache

EXPOSE 5000

# Run with unbuffered output so you can actually see the logs in Portainer
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]