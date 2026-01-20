# Vibes Frontend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask flask-cors pyyaml

# Install Claude CLI
RUN apt-get update && apt-get install -y curl git && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @anthropic-ai/claude-code && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy app
COPY frontend/ /app/frontend/
COPY mcp_server/gastown_integration.py /app/mcp_server/

ENV PYTHONUNBUFFERED=1

EXPOSE 3000

WORKDIR /app/frontend

CMD ["python", "server.py", "--project", "/projects", "--port", "3000"]
