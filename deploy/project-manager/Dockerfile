# Project Manager Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask docker

# Copy manager
COPY manager.py /app/

ENV PYTHONUNBUFFERED=1

EXPOSE 3009

CMD ["python", "manager.py"]
