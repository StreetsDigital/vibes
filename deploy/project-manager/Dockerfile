# Project Manager Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir flask docker psutil

# Copy manager
COPY manager.py /app/

ENV PYTHONUNBUFFERED=1

EXPOSE 3009

CMD ["python", "manager.py"]
